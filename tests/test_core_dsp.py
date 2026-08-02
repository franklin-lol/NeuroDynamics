import numpy as np
import pytest
from psychoacoustic.core import SR, crossfade_write
from psychoacoustic.block import Block
from psychoacoustic.dsp import (
    isochronic, schumann_stack, comfort_filter, ambient_bridge,
    ffr_prime_burst, monaural_beat_layer, soft_ceiling, budget_am_depths,
    respiratory_entrainment_mod, _SCHUMANN_TAPER,
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
    "GATEWAY_EDGE", "CHAKRA_ASCENT", "DEEP_DIVE",
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


def test_deep_dive_structure():
    """DEEP_DIVE PRO: 9 blocks, all soft carrier, no carrier jumps, ~120 min."""
    blocks = build_profile("DEEP_DIVE")
    assert len(blocks) == 9
    labels = [b.label for b in blocks]
    assert any("SETTLE" in x for x in labels)
    assert any("ABYSS" in x for x in labels)
    assert any("F21" in x for x in labels)
    assert any("F27" in x for x in labels)
    assert any("SEAL" in x for x in labels)

    # All carriers stay at 200 Hz (no jumps = no silence gaps at night)
    for b in blocks:
        assert b.c0 == 200 and b.c1 == 200, f"{b.label} carrier not 200"

    # All blocks skip ambient bridges
    for b in blocks:
        assert b.skip_ambient_bridge, f"{b.label} missing skip_ambient_bridge"

    # At least 4 blocks use beat_ctrl (adaptive drift)
    ctrl_count = sum(1 for b in blocks if b.beat_ctrl)
    assert ctrl_count >= 4, f"Only {ctrl_count} beat_ctrl blocks"

    # Total core time ~120 min (± tolerance)
    core = sum(b.dur_s for b in blocks)
    assert 110 * 60 <= core <= 130 * 60, f"Core time {core/60:.1f} min"

    # Night-safe gains: all blocks <= 0.55
    for b in blocks:
        assert b.block_gain <= 0.55, f"{b.label} gain {b.block_gain} too loud"


def test_deep_dive_beat_ctrl_render():
    """Render a short beat_ctrl block from DEEP_DIVE — no NaN, within ceiling."""
    from dataclasses import replace
    blocks = build_profile("DEEP_DIVE")
    # Pick the ABYSS block (has beat_ctrl)
    abyss = next(b for b in blocks if "ABYSS" in b.label)
    short = replace(abyss, dur_s=2.0)
    L, R = short.render()
    assert not np.any(np.isnan(L))
    assert not np.any(np.isnan(R))
    peak = max(np.max(np.abs(L)), np.max(np.abs(R)))
    assert peak <= 0.56, f"Peak {peak} exceeds ceiling"
