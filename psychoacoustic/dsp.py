import numpy as np
from .core import SR, log_sweep, jitter_envelope, build_carrier

SCHUMANN = [7.83, 14.3, 20.8, 27.3, 33.8]


def dual_binaural(dur_s, c0, c1, b0, b1,
                  vol_p=0.60, vol_s=0.22,
                  carrier_jitter=2.0, beat_jitter=0.15,
                  seed=0, beat_array=None):
    """
    Dual octave-pair binaural with 1/f jitter on both carrier and beat.
    Primary: C | C+B  |  Secondary: C×2 | C×2+B/2
    beat_array: pre-computed beat envelope (overrides b0/b1).
    """
    n = int(dur_s * SR)
    C = build_carrier(c0, c1, n, carrier_jitter, seed)

    if beat_array is not None:
        B = np.asarray(beat_array[:n], dtype=np.float64)
    else:
        B = jitter_envelope(log_sweep(b0, b1, n), beat_jitter, seed + 50)
    B2 = B / 2.0

    pL  = 2*np.pi * np.cumsum(C)         / SR
    pR  = 2*np.pi * np.cumsum(C + B)     / SR
    pL2 = 2*np.pi * np.cumsum(C * 2.0)   / SR
    pR2 = 2*np.pi * np.cumsum(C * 2.0 + B2) / SR

    L = (np.sin(pL)*vol_p + np.sin(pL2)*vol_s).astype(np.float32)
    R = (np.sin(pR)*vol_p + np.sin(pR2)*vol_s).astype(np.float32)
    return L, R


def isochronic(dur_s, freq, carrier=200.0, vol=0.14, attack_s=4.0, decay_s=4.0):
    """Hard-gated AM tone with hanning anti-click + dynamic amplitude envelope."""
    if freq <= 0:
        return np.zeros(int(dur_s * SR), dtype=np.float32)
    n = int(dur_s * SR)
    t = np.arange(n, dtype=np.float64) / SR
    gate = (np.sin(2*np.pi*freq*t) >= 0).astype(np.float32)
    rn = int(0.006 * SR)
    if rn > 1:
        h = np.hanning(rn*2).astype(np.float32); h /= h.sum()
        gate = np.convolve(gate, h, mode='same')
    env = np.ones(n, np.float32)
    atk = min(int(attack_s*SR), n//3)
    dec = min(int(decay_s*SR),  n//3)
    if atk: env[:atk]  *= np.linspace(0, 1, atk, np.float32)
    if dec: env[-dec:] *= np.linspace(1, 0, dec, np.float32)
    return (np.sin(2*np.pi*carrier*t) * gate * env * vol).astype(np.float32)


def apply_cfc(gamma_sig, dur_s, theta_freq=6.0, strength=0.5):
    """
    Theta→Gamma Phase-Amplitude Coupling (PAC).
    Theta envelope modulates gamma amplitude — mirrors hippocampal CFC.
    """
    n = len(gamma_sig)
    t = np.arange(n, dtype=np.float64) / SR
    env = (1.0 - strength + strength * (0.5 + 0.5*np.sin(2*np.pi*theta_freq*t)))
    return (gamma_sig * env.astype(np.float32))


def assr_80hz(dur_s, carrier=200.0, vol=0.05):
    """80 Hz ASSR — brainstem + inferior colliculus pathway, independent of 40Hz cortical."""
    return isochronic(dur_s, 80.0, carrier, vol, attack_s=6.0, decay_s=6.0)


def schumann_stack(dur_s, carrier=432.0, base_vol=0.20, seed=0):
    """All 5 Schumann resonances as simultaneous binaural pairs (Earth coherence sync)."""
    n = int(dur_s * SR)
    L = np.zeros(n, np.float32); R = np.zeros(n, np.float32)
    for i, freq in enumerate(SCHUMANN):
        v = base_vol * (0.70 ** i)
        lv, rv = dual_binaural(dur_s, carrier, carrier, freq, freq,
                               vol_p=v, vol_s=v*0.25,
                               carrier_jitter=0.3, beat_jitter=0.05,
                               seed=seed + i*10)
        L += lv; R += rv
    return L, R


def spatial_rotation(L, R, period_s=12.0):
    """Slow inter-aural phase rotation → vestibular engagement, anti-adaptation."""
    n = len(L)
    t = np.arange(n, dtype=np.float64) / SR
    cos_t = np.cos(2*np.pi*t/period_s).astype(np.float32)
    sin_t = np.sin(2*np.pi*t/period_s).astype(np.float32)
    return L*cos_t - R*sin_t, L*sin_t + R*cos_t


def infra_modulate(L, R, freq_hz=0.067, depth=0.15, phase_offset=0.0):
    """Ultra-slow AM → ANS + respiratory entrainment. Signal breathes."""
    n = len(L)
    t = np.arange(n, dtype=np.float64) / SR
    mod = (1.0 - depth + depth * np.sin(2*np.pi*freq_hz*t + phase_offset)).astype(np.float32)
    return L * mod, R * mod


def pattern_break(carrier=432.0):
    """20s neutral 10 Hz reset — breaks cortical prediction lock without disrupting state."""
    L, R = dual_binaural(20.0, carrier, carrier, 10.0, 10.0,
                         vol_p=0.40, vol_s=0.12,
                         carrier_jitter=0.0, beat_jitter=0.0, seed=999)
    rn = int(3 * SR)
    ramp = np.linspace(0, 1, rn, np.float32)
    L[:rn] *= ramp; R[:rn] *= ramp
    L[-rn:] *= ramp[::-1]; R[-rn:] *= ramp[::-1]
    return L, R
