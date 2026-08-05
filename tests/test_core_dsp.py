import numpy as np
import pytest
from psychoacoustic.core import SR, crossfade_write, adaptive_drift_envelope
from psychoacoustic.block import Block
from psychoacoustic.dsp import (
    isochronic, schumann_stack, comfort_filter, ambient_bridge,
    ffr_prime_burst, monaural_beat_layer, soft_ceiling, budget_am_depths,
    respiratory_entrainment_mod, _SCHUMANN_TAPER, room_reverb,
)
from psychoacoustic.profiles import build_profile
from psychoacoustic.core import log_sweep


def test_normalization_limit():
    """Soft ceiling after master chain keeps peak under 0.50 FS (gain=1)."""
    b = Block(label="Test", dur_s=1.0, c0=200.0, b0=10.0,
              use_drone=True, drone_vol=1.0, use_underbed=False)
    L, R = b.render()
    peak = max(np.max(np.abs(L)), np.max(np.abs(R)))
    assert peak <= 0.505


def test_comfort_eq_then_ceiling():
    """Comfort EQ before soft ceiling must not re-break the limit."""
    b = Block(label="Test", dur_s=1.0, c0=200.0, b0=10.0,
              use_drone=True, drone_vol=1.0, use_comfort_eq=True,
              use_underbed=False, soft_ceiling_fs=0.50)
    L, R = b.render()
    peak = max(np.max(np.abs(L)), np.max(np.abs(R)))
    assert peak <= 0.505
    assert not np.any(np.isnan(L))


def test_no_nan_values():
    b = Block(label="Test", dur_s=1.0, use_chaos=True, use_hrtf=True,
              use_reverb=True, use_formant=True, use_comfort_eq=True)
    L, R = b.render()
    assert not np.any(np.isnan(L))
    assert not np.any(np.isnan(R))


def test_isochronic_smoothness():
    """Soft-gate v2: gamma 40 Hz jumps must stay tiny."""
    sig = isochronic(dur_s=1.0, freq=40.0, carrier=200.0, vol=0.1)
    max_jump = np.max(np.abs(np.diff(sig)))
    assert max_jump < 0.004, f"Too harsh jump in Gamma gate: {max_jump}"


def test_assr_80_smoothness():
    sig = isochronic(dur_s=1.0, freq=80.0, carrier=200.0, vol=0.05,
                     smooth_ms=32.0, attack_s=8.0, decay_s=8.0)
    max_jump = np.max(np.abs(np.diff(sig)))
    assert max_jump < 0.004, f"ASSR-80 too harsh: {max_jump}"


def test_schumann_taper():
    expected = [1.0, 0.45, 0.12, 0.04, 0.01]
    assert np.allclose(_SCHUMANN_TAPER, expected)
    L, R = schumann_stack(dur_s=1.0, carrier=432.0, base_vol=0.20)
    assert np.max(np.abs(L)) < 0.8


def test_ambient_bridge_levels():
    L, R = ambient_bridge(carrier=432.0, dur_s=2.0)
    peak = max(np.max(np.abs(L)), np.max(np.abs(R)))
    assert peak <= 0.13
    assert peak > 0.05


def test_ffr_prime_soft():
    """FFR prime should sit near −13 dBFS, not slam the start."""
    L, R = ffr_prime_burst(carrier=200.0, carrier_type='soft', dur_s=2.0)
    peak = max(np.max(np.abs(L)), np.max(np.abs(R)))
    assert peak <= 0.24
    assert peak > 0.05
    assert not np.any(np.isnan(L))


def test_comfort_filter_response():
    n = int(SR * 2)
    noise = np.random.normal(0, 0.1, n).astype(np.float32)
    fL, fR = comfort_filter(noise, noise, low_db=6.0, high_db=-6.0)

    def get_rms(sig, f_min, f_max):
        from scipy.signal import butter, sosfilt
        sos = butter(4, [f_min / (SR / 2), f_max / (SR / 2)],
                     btype='band', output='sos')
        return np.sqrt(np.mean(sosfilt(sos, sig) ** 2))

    assert get_rms(fL, 20, 80) > get_rms(noise, 20, 80)
    assert get_rms(fL, 10000, 15000) < get_rms(noise, 10000, 15000)


def test_monaural_follows_sweep():
    """Sweep-locked monaural phase should track B_raw cumsum."""
    n = int(1.0 * SR)
    B = log_sweep(4.0, 12.0, n)
    mono = monaural_beat_layer(1.0, 200.0, vol=0.1, beat_array=B)
    # Envelope of |mono| should show modulation energy (not flat)
    env = np.abs(mono)
    # High-pass-ish fluctuation: std of envelope should be meaningful
    assert np.std(env) > 0.01
    assert not np.any(np.isnan(mono))


def test_am_depth_budget():
    a, b = budget_am_depths(0.20, 0.20, cap=0.26)
    assert abs(a + b - 0.26) < 1e-6
    assert a == pytest.approx(0.13)
    c, d = budget_am_depths(0.10, 0.10, cap=0.26)
    assert c == pytest.approx(0.10)


def test_respiratory_ramp():
    mod = respiratory_entrainment_mod(2.0, breath_bpm=6.0, depth=0.15,
                                      breath_bpm_end=4.0)
    assert mod.shape[0] == int(2.0 * SR)
    assert np.min(mod) >= 1.0 - 0.15 - 1e-3
    assert np.max(mod) <= 1.0 + 1e-3


def test_soft_ceiling():
    x = np.ones(1000, np.float32) * 0.9
    L, R = soft_ceiling(x, x, ceiling=0.50)
    assert np.max(np.abs(L)) <= 0.50


def test_crossfade_silence_and_equal_power():
    class FakeFile:
        def __init__(self):
            self.data = []

        def write(self, x):
            self.data.append(x)

    fh = FakeFile()
    prev = (np.ones(int(SR), dtype=np.float32),
            np.ones(int(SR), dtype=np.float32))
    new_L = np.ones(int(5 * SR), dtype=np.float32)
    new_R = np.ones(int(5 * SR), dtype=np.float32)
    crossfade_write(fh, prev, new_L, new_R, fade_s=1.0, silence_s=0.5)
    assert len(fh.data[1]) == int(0.5 * SR)

    fh2 = FakeFile()
    crossfade_write(fh2, prev, new_L.copy(), new_R.copy(),
                    fade_s=1.0, silence_s=0.0, equal_power=True)
    # No silence chunk — first write is overlapped mix
    assert len(fh2.data) >= 1
    mix = fh2.data[0]
    assert mix.shape[0] == int(1.0 * SR)


@pytest.mark.parametrize("name", [
    "GENESIS", "WALK", "SLEEP", "HEALER", "ORACLE", "WARRIOR",
    "GATEWAY_EDGE", "CHAKRA_ASCENT", "DEEP_DIVE_PRO_NIGHT",
])
def test_profile_smoke(name):
    from dataclasses import replace
    blocks = build_profile(name)
    assert len(blocks) >= 3
    # Shorten only for smoke speed — params/path stay identical
    b = replace(blocks[0], dur_s=min(2.0, blocks[0].dur_s))
    L, R = b.render()
    peak = max(np.max(np.abs(L)), np.max(np.abs(R)))
    assert not np.any(np.isnan(L))
    assert peak <= 0.56


def test_gateway_edge_ladder():
    blocks = build_profile("GATEWAY_EDGE")
    labels = [b.label for b in blocks]
    assert any("F10" in x for x in labels)
    assert any("F12" in x for x in labels)
    assert any("F15" in x for x in labels)
    assert any("INTERRUPT" in x for x in labels)
    assert any("F21" in x for x in labels)
    assert any("SEAL" in x for x in labels)
    core = sum(b.dur_s for b in blocks)
    assert 25 * 60 <= core <= 35 * 60
    # Interrupt must stay soft carrier (no organ scream)
    intr = next(b for b in blocks if "INTERRUPT" in b.label)
    assert intr.carrier_type == "soft"
    assert intr.block_gain <= 0.60


def test_chakra_ascent_ladder():
    blocks = build_profile("CHAKRA_ASCENT")
    assert len(blocks) == 7
    carriers = [b.c0 for b in blocks]
    assert carriers == [396, 417, 528, 639, 741, 852, 963]
    elevs = [b.hrtf_elevation for b in blocks]
    assert elevs[0] < elevs[-1]
    crown = blocks[-1]
    assert crown.formant_morph_vowel == "M"
    from dataclasses import replace
    L, R = replace(crown, dur_s=2.0).render()
    assert not np.any(np.isnan(L))
    assert max(np.max(np.abs(L)), np.max(np.abs(R))) <= 0.56


def test_vowel_formants_and_silk():
    from psychoacoustic.dsp import formant_resonator, silk_lowpass, VOWEL_FORMANTS
    assert set(VOWEL_FORMANTS) >= {"A", "O", "U", "M"}
    n = int(SR * 0.5)
    x = np.random.randn(n).astype(np.float32) * 0.1
    y = formant_resonator(x, 0.15, vowel="U", morph_vowel="M", morph_s=0.2)
    z = silk_lowpass(y, 4000.0)
    assert y.shape == x.shape
    assert z.shape == x.shape
    assert not np.any(np.isnan(z))


def test_organic_atmosphere_and_drift():
    from psychoacoustic.organic import (
        organic_atmosphere, carrier_drift_hz, resolve_organic_style,
        river_bed, singing_bowl_event)
    from psychoacoustic.core import build_carrier

    n = int(SR * 2.0)
    drift = carrier_drift_hz(n, depth_hz=0.9, seed=7)
    assert drift.shape == (n,)
    assert np.max(np.abs(drift)) < 2.0

    C = build_carrier(200, 210, n, jitter_depth=1.0, seed=1,
                      drift_depth=0.8)
    assert C.shape == (n,)
    assert not np.any(np.isnan(C))

    rL, rR = river_bed(2.0, vol=0.02, seed=2)
    assert rL.shape == rR.shape
    bL, bR = singing_bowl_event(3.0, 220.0, vol=0.04, seed=3)
    assert np.max(np.abs(bL)) > 0

    for style in ("rest", "sleep", "edge", "chakra", "minimal", "focus"):
        oL, oR = organic_atmosphere(3.0, 200.0, style=style,
                                    intensity=1.0, seed=9)
        assert oL.shape == oR.shape
        assert not np.any(np.isnan(oL))
        peak = max(np.max(np.abs(oL)), np.max(np.abs(oR)))
        assert peak <= 0.12

    assert resolve_organic_style("WARRIOR — PEAK", 40, 40, 200, 200,
                                 True, False) == "minimal"
    assert resolve_organic_style("SLEEP — DEEP", 2, 2, 100, 100,
                                 False, False) == "sleep"

    b = Block(label="Organic Rest", dur_s=2.0, c0=200.0, b0=8.0,
              use_organic=True, organic_style="rest",
              use_carrier_drift=True, use_comfort_eq=True)
    L, R = b.render()
    assert not np.any(np.isnan(L))
    assert max(np.max(np.abs(L)), np.max(np.abs(R))) <= 0.56


def test_deep_dive_pro_night_structure():
    """~120 min core, unbroken (skip_ambient_bridge), void-style throughout,
    beat trends downward block-to-block, no iso/formant/schumann anywhere."""
    blocks = build_profile("DEEP_DIVE_PRO_NIGHT")
    labels = [b.label for b in blocks]
    for kw in ("PREP", "BODY OFF", "STABLE", "DEEP THETA", "LIMINAL",
               "AUTO"):
        assert any(kw in x for x in labels), f"missing phase: {kw}"

    core = sum(b.dur_s for b in blocks)
    assert 115 * 60 <= core <= 125 * 60

    for b in blocks:
        assert b.skip_ambient_bridge is True, b.label
        assert b.organic_style == "void", b.label
        assert not b.iso_layers, b.label
        assert b.use_formant is False, b.label
        assert b.schumann_mode is False, b.label
        assert b.c0 == 200 and b.c1 == 200, "carrier must stay fixed " \
            "(no jump -> renderer always uses equal-power join)"
        assert b.beat_ctrl, f"{b.label} must drive beat via beat_ctrl, " \
            "not log_sweep"

    # Beat frequency must trend downward across the session (deepest last),
    # comparing each block's OWN control-point endpoints (b0/b1 mirror them
    # for display; dual_binaural ignores b0/b1 once beat_array is passed).
    starts = [b.beat_ctrl[0][1] for b in blocks]
    ends   = [b.beat_ctrl[-1][1] for b in blocks]
    assert starts == sorted(starts, reverse=True)
    assert ends == sorted(ends, reverse=True)
    assert ends[0] > ends[-1]

    # Only BODY OFF gets the F10-style body/cortex duality; nothing past it.
    focus_flags = [b.use_focus_mix for b in blocks]
    assert focus_flags == [False, True, False, False, False, False]

    # Final block must actually taper toward silence (long exit ramp), not
    # stop abruptly — this is a night session meant to end in sleep.
    assert blocks[-1].outro_fade_s >= 120.0


def test_deep_dive_void_style_zero_events():
    """'void' must never produce a bowl/bell strike, at any intensity —
    checked at both the low-level scheduler and the full atmosphere mix."""
    from psychoacoustic.organic import schedule_resonant_events, organic_atmosphere
    for intensity in (0.1, 1.0, 5.0):
        L, R = schedule_resonant_events(4.0, 200.0, "void",
                                        intensity=intensity, seed=1)
        assert np.max(np.abs(L)) == 0.0
        assert np.max(np.abs(R)) == 0.0
    oL, oR = organic_atmosphere(4.0, 200.0, style="void",
                                intensity=1.0, seed=1)
    assert not np.any(np.isnan(oL))
    # Still non-silent overall (continuous river/ghost bed keeps it "alive")
    assert np.max(np.abs(oL)) > 0.0


def test_adaptive_drift_envelope_shape():
    """Dwell-then-small-step contract: plateaus honored at their fractions,
    per-sample step stays smooth (no clicks), stays within clip bounds."""
    n = int(20 * SR)  # short stand-in duration; control points are fractional
    ctrl = [(0.0, 6.0), (0.24, 6.0), (0.27, 5.5), (0.51, 5.5),
           (0.54, 5.0), (0.78, 5.0), (0.81, 4.5), (1.0, 4.5)]
    B = adaptive_drift_envelope(n, ctrl, micro_amp=0.07, micro_rate=0.009,
                                seed=1)
    assert B.shape == (n,)
    assert not np.any(np.isnan(B))
    assert np.max(np.abs(np.diff(B))) < 0.01, "per-sample jump too sharp"
    for frac, expected in ((0.10, 6.0), (0.40, 5.5), (0.65, 5.0),
                          (0.95, 4.5)):
        assert abs(B[int(frac * n)] - expected) < 0.3
    assert B.min() >= 0.3 and B.max() <= 120.0


def test_room_reverb_channels_independent_and_decaying():
    """Regression guard for the ir[::-1] fix: R must not mirror L, and both
    channels must show a decaying (not rising) impulse response."""
    n = int(0.2 * SR)
    imp = np.zeros(n, dtype=np.float32)
    imp[0] = 1.0
    L, R = room_reverb(imp, imp, rt60_ms=700.0, wet=1.0, seed=42)
    assert not np.allclose(R[:2000], L[:2000][::-1])
    assert np.argmax(np.abs(L)) < 50
    assert np.argmax(np.abs(R)) < 50
    assert np.mean(np.abs(L[-100:])) < np.mean(np.abs(L[:100]))
    assert np.mean(np.abs(R[-100:])) < np.mean(np.abs(R[:100]))
