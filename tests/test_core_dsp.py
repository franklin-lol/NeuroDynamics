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
    "GENESIS", "WALK", "SLEEP", "HEALER", "ORACLE", "WARRIOR", "GATEWAY_EDGE",
])
def test_profile_smoke(name):
    blocks = build_profile(name)
    assert len(blocks) >= 3
    b = blocks[0]
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
