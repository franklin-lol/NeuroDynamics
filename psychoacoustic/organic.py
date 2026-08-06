"""
Premium organic atmosphere — beds that sit UNDER entrainment.

Rules:
  - Never invent beat frequencies; carriers stay continuous.
  - Levels stay well below primary binaural (−20…−34 dB class).
  - All textures are procedural (no external samples / licenses).
"""
from __future__ import annotations

import numpy as np
from scipy.signal import butter, sosfilt, lfilter

from .core import SR, pink_noise, brown_noise, morph_noise
from .dsp import _apply_carrier_type


# Inharmonic partials inspired by singing bowls (relative to fundamental)
_BOWL_PARTIALS = (
    (1.00, 1.00),
    (2.76, 0.42),
    (5.40, 0.18),
    (8.93, 0.08),
)

# Soft temple-bell inharmonics
_BELL_PARTIALS = (
    (1.00, 1.00),
    (2.00, 0.55),
    (3.01, 0.28),
    (4.16, 0.12),
    (5.43, 0.06),
)


def _rng(seed: int) -> np.random.RandomState:
    return np.random.RandomState(int(seed) & 0xFFFFFFFF)


def _fade_edges(sig: np.ndarray, fade_s: float = 0.35) -> np.ndarray:
    n = len(sig)
    fn = min(int(fade_s * SR), max(1, n // 8))
    if fn < 2:
        return sig
    ramp = np.linspace(0.0, 1.0, fn, dtype=np.float32)
    out = sig.astype(np.float32, copy=True)
    out[:fn] *= ramp
    out[-fn:] *= ramp[::-1]
    return out


def _smooth_wander(n: int, seed: int, cutoff: float = 0.08) -> np.ndarray:
    """Extremely slow unit-ish wander from pink noise.
    Computed at a coarse control rate (this signal has no content anywhere
    near audio rate) then linearly interpolated to n samples — same slow
    character, a small fraction of the memory/CPU of a full-rate lfilter
    pass, and the IIR pole sits at a sane a=exp(-2*pi*cutoff/ctrl_hz)
    instead of ~0.9999997 at 44.1kHz (better-conditioned, not just cheaper)."""
    ctrl_hz = 20.0
    n_ctrl = max(48, int(np.ceil(n / SR * ctrl_hz)) + 4)
    raw = pink_noise(n_ctrl, seed).astype(np.float64)
    a = float(np.exp(-2.0 * np.pi * cutoff / ctrl_hz))
    w = lfilter([1.0 - a], [1.0, -a], raw)
    w -= w.mean()
    peak = np.max(np.abs(w)) + 1e-9
    w = w / peak
    if n <= 1:
        return np.full(max(n, 0), w[0], dtype=np.float64)
    x_ctrl = np.linspace(0.0, 1.0, n_ctrl)
    x_full = np.linspace(0.0, 1.0, n)
    return np.interp(x_full, x_ctrl, w).astype(np.float64)


# ══════════════════════════════════════════════════════════
#  CARRIER MICRO-DRIFT  (feed into build_carrier / dual_binaural)
# ══════════════════════════════════════════════════════════

def carrier_drift_hz(n: int, depth_hz: float = 0.9,
                    rate_hz: float = 0.018, seed: int = 0) -> np.ndarray:
    """
    Multi-LFO + ultra-slow wander in Hz. Peak ≈ depth_hz.
    Does not touch beat — only carrier center motion.
    """
    if depth_hz <= 0 or n < 8:
        return np.zeros(n, dtype=np.float64)
    t = np.arange(n, dtype=np.float64) / SR
    lfo = (
        0.52 * np.sin(2 * np.pi * rate_hz * t + seed * 0.31)
        + 0.28 * np.sin(2 * np.pi * rate_hz * 0.41 * t + 1.73)
        + 0.20 * np.sin(2 * np.pi * rate_hz * 1.67 * t + 0.91)
    )
    wander = _smooth_wander(n, seed + 17, cutoff=0.035)
    return (depth_hz * (0.72 * lfo + 0.28 * wander)).astype(np.float64)


# ══════════════════════════════════════════════════════════
#  HARMONIC GHOSTS
# ══════════════════════════════════════════════════════════

def harmonic_ghosts(dur_s: float, carrier: float, vol: float = 0.028,
                    seed: int = 0, ctype: str = 'soft') -> tuple:
    """
    Quiet 2nd/3rd partials with independent slow AM + micro-detune.
    Stereo: slight L/R phase offset for width without ITD beat.
    """
    n = int(dur_s * SR)
    t = np.arange(n, dtype=np.float64) / SR
    rng = _rng(seed + 3)
    out_L = np.zeros(n, dtype=np.float64)
    out_R = np.zeros(n, dtype=np.float64)

    specs = (
        (2.0, 0.55, 0.011 + rng.uniform(-0.002, 0.002), 0.04),
        (3.0, 0.28, 0.007 + rng.uniform(-0.0015, 0.0015), 0.055),
        (0.5, 0.18, 0.009 + rng.uniform(-0.002, 0.002), 0.03),  # sub-octave ghost
    )
    for i, (ratio, gain, rate, det_hz) in enumerate(specs):
        f = float(carrier) * ratio
        if f < 40.0 or f > 4200.0:
            continue
        det_L = det_hz * (0.6 + 0.4 * np.sin(2 * np.pi * rate * 0.37 * t))
        det_R = -det_hz * (0.6 + 0.4 * np.sin(2 * np.pi * rate * 0.41 * t + 1.1))
        ph_L = 2 * np.pi * np.cumsum(f + det_L) / SR
        ph_R = 2 * np.pi * np.cumsum(f + det_R) / SR + 0.17
        # Sine + slow noise-wander AM (non-periodic breathing per partial,
        # decorrelated across partials via the +i seed offset)
        ghost_wander = _smooth_wander(n, seed + 50 + i, cutoff=0.02)
        am = (0.52 + 0.36 * np.sin(2 * np.pi * rate * t + seed * 0.2)
              + 0.12 * ghost_wander)
        # Soften high ghosts
        hi_attn = 1.0 if f < 900 else (0.55 if f < 1800 else 0.28)
        g = gain * hi_attn * am
        out_L += g * _apply_carrier_type(ph_L, ctype)
        out_R += g * _apply_carrier_type(ph_R, ctype)

    peak = max(np.max(np.abs(out_L)), np.max(np.abs(out_R))) + 1e-9
    scale = vol / peak
    return (out_L * scale).astype(np.float32), (out_R * scale).astype(np.float32)


# ══════════════════════════════════════════════════════════
#  SINGING BOWL / SOFT BELL  (event grains)
# ══════════════════════════════════════════════════════════

def _inharmonic_strike(n: int, f0: float, partials, attack_s: float,
                       decay_s: float, beat_hz: float, seed: int,
                       ctype: str = 'soft') -> np.ndarray:
    t = np.arange(n, dtype=np.float64) / SR
    out = np.zeros(n, dtype=np.float64)
    for ratio, gain in partials:
        f = f0 * ratio
        if f > SR * 0.45:
            continue
        # Twin partials for slow bowl shimmer
        d = beat_hz * (0.35 + 0.15 * (ratio - 1.0))
        ph_a = 2 * np.pi * f * t
        ph_b = 2 * np.pi * (f + d) * t + seed * 0.05
        tone = 0.62 * _apply_carrier_type(ph_a, ctype) + 0.38 * np.sin(ph_b)
        # Resonant noise tick (bowl scrape)
        if ratio < 1.5:
            nz = pink_noise(n, seed + int(ratio * 11))
            nyq = SR / 2.0
            lo = max(0.01, (f * 0.92) / nyq)
            hi = min(0.49, (f * 1.12) / nyq)
            if lo < hi:
                sos = butter(2, [lo, hi], btype='band', output='sos')
                scrape = sosfilt(sos, nz).astype(np.float64)
                scrape /= np.max(np.abs(scrape)) + 1e-9
                tone = 0.88 * tone + 0.12 * scrape
        out += gain * tone

    atk_n = max(2, int(attack_s * SR))
    # Exponential-ish decay via cosine release after attack
    env = np.ones(n, dtype=np.float64)
    env[:atk_n] = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, atk_n))
    # Decay from peak
    tau = max(0.15, decay_s)
    env *= np.exp(-t / tau)
    # Soften onset further
    env[:atk_n] *= np.linspace(0.0, 1.0, atk_n)
    out *= env
    peak = np.max(np.abs(out)) + 1e-9
    return (out / peak).astype(np.float32)


def singing_bowl_event(dur_s: float, f0: float, vol: float = 0.045,
                       seed: int = 0) -> tuple:
    """Long singing-bowl strike, stereo with gentle width."""
    n = int(dur_s * SR)
    body = _inharmonic_strike(
        n, f0, _BOWL_PARTIALS,
        attack_s=0.55, decay_s=min(14.0, dur_s * 0.85),
        beat_hz=0.22 + (seed % 7) * 0.02,
        seed=seed, ctype='soft')
    # Slight R delay (~0.8 ms) for space
    delay = int(0.0008 * SR)
    L = body
    R = np.zeros_like(body)
    if delay < n:
        R[delay:] = body[:-delay] * 0.96
        R[:delay] = body[:delay] * 0.4
    else:
        R = body * 0.96
    return (L * vol).astype(np.float32), (R * vol).astype(np.float32)


def soft_bell_event(dur_s: float, f0: float, vol: float = 0.032,
                    seed: int = 0) -> tuple:
    n = int(dur_s * SR)
    body = _inharmonic_strike(
        n, f0, _BELL_PARTIALS,
        attack_s=0.012, decay_s=min(6.5, dur_s * 0.7),
        beat_hz=0.08, seed=seed, ctype='sine')
    body = _fade_edges(body, 0.02)
    # Narrow stereo
    pan = 0.35 + 0.3 * ((seed % 10) / 10.0)
    L = body * (1.0 - pan * 0.35) * vol
    R = body * (1.0 + pan * 0.35) * vol
    return L.astype(np.float32), R.astype(np.float32)


# ══════════════════════════════════════════════════════════
#  RIVER / WATER BED
# ══════════════════════════════════════════════════════════

def river_bed(dur_s: float, vol: float = 0.022, seed: int = 0) -> tuple:
    """
    Layered water-like noise: deep brown flow + mid sparkle, decorrelated L/R.
    """
    n = int(dur_s * SR)
    t = np.arange(n, dtype=np.float64) / SR
    nyq = SR / 2.0

    flow = brown_noise(n, seed)
    flow /= np.max(np.abs(flow)) + 1e-9
    sos_lo = butter(3, min(0.49, 380.0 / nyq), btype='low', output='sos')
    flow = sosfilt(sos_lo, flow).astype(np.float64)

    sparkle = pink_noise(n, seed + 5)
    sparkle /= np.max(np.abs(sparkle)) + 1e-9
    lo = max(0.01, 180.0 / nyq)
    hi = min(0.49, 1400.0 / nyq)
    sos_bp = butter(2, [lo, hi], btype='band', output='sos')
    sparkle = sosfilt(sos_bp, sparkle).astype(np.float64)

    # Bubble AM: periodic-ish sine pair + a slow filtered-noise macro-swell
    # (river bubbling isn't perfectly periodic — the wander term is what
    # keeps it from sounding like a two-oscillator LFO loop).
    wander = _smooth_wander(n, seed + 21, cutoff=0.025)
    am = 0.60 + 0.20 * (
        0.55 * np.sin(2 * np.pi * 0.07 * t + seed * 0.2)
        + 0.45 * np.sin(2 * np.pi * 0.031 * t + 1.4)
    ) + 0.16 * wander
    mono = (0.72 * flow + 0.28 * sparkle) * am

    # Decorrelate R with short allpass-ish delay + different seed noise mix
    alt = morph_noise(n, 0.55, 0.45, seed + 9).astype(np.float64)
    alt = sosfilt(sos_lo, alt)
    alt /= np.max(np.abs(alt)) + 1e-9
    delay = int(0.014 * SR)
    R = np.zeros(n, dtype=np.float64)
    R[delay:] = mono[:-delay] * 0.78 + alt[delay:] * 0.22 * am[delay:]
    R[:delay] = mono[:delay] * 0.5
    L = mono * 0.92 + alt * 0.08

    peak = max(np.max(np.abs(L)), np.max(np.abs(R))) + 1e-9
    scale = vol / peak
    return (L * scale).astype(np.float32), (R * scale).astype(np.float32)


# ══════════════════════════════════════════════════════════
#  SPECTRAL BREATH  (slow LP morph — texture rotation feel)
# ══════════════════════════════════════════════════════════

def spectral_breath(sig_L: np.ndarray, sig_R: np.ndarray,
                    fc_lo: float = 700.0, fc_hi: float = 2400.0,
                    rate_hz: float = 0.028, mix: float = 0.22,
                    seed: int = 0) -> tuple:
    """
    Parallel soft LP morph: two fixed LPs crossfaded by a slow LFO.
    Keeps the dry path intact so entrainment carriers stay present.
    (Vectorized — safe on multi-minute blocks.)
    """
    n = len(sig_L)
    if mix <= 0 or n < 64:
        return sig_L, sig_R
    m = float(np.clip(mix, 0.0, 0.45))
    nyq = SR / 2.0
    lo = float(np.clip(fc_lo, 120.0, nyq * 0.85))
    hi = float(np.clip(fc_hi, lo + 80.0, nyq * 0.95))
    sos_lo = butter(2, lo / nyq, btype='low', output='sos')
    sos_hi = butter(2, hi / nyq, btype='low', output='sos')

    t = np.arange(n, dtype=np.float64) / SR
    morph = 0.5 + 0.5 * np.sin(2 * np.pi * rate_hz * t + seed * 0.4)
    morph = (0.65 * morph + 0.35 * (
        0.5 + 0.5 * np.sin(2 * np.pi * rate_hz * 0.37 * t + 1.2))).astype(np.float32)

    def _one(sig: np.ndarray) -> np.ndarray:
        wet_lo = sosfilt(sos_lo, sig).astype(np.float32)
        wet_hi = sosfilt(sos_hi, sig).astype(np.float32)
        wet = wet_lo * (1.0 - morph) + wet_hi * morph
        dry = sig.astype(np.float32)
        return ((1.0 - m) * dry + m * wet).astype(np.float32)

    return _one(sig_L), _one(sig_R)


# ══════════════════════════════════════════════════════════
#  MICRO-EVENT SCHEDULER
# ══════════════════════════════════════════════════════════

def schedule_resonant_events(dur_s: float, carrier: float,
                             style: str, intensity: float,
                             seed: int = 0) -> tuple:
    """
    Sparse bowl / bell events. Spacing ~40–110 s depending on style.
    """
    n = int(dur_s * SR)
    L = np.zeros(n, dtype=np.float32)
    R = np.zeros(n, dtype=np.float32)
    if intensity <= 0 or dur_s < 12.0:
        return L, R

    rng = _rng(seed + 40)
    if style == 'void':
        # DEEP DIVE PRO: zero discrete events, always — independent of
        # whatever intensity the caller passes (organic_atmosphere already
        # zeroes it via _STYLE_MIX's ev_scale, but a direct caller must not
        # silently inherit 'rest' bowl_p=0.65 through the else-branch below).
        return L, R
    elif style == 'minimal':
        mean_gap, bowl_p, vol_scale = 95.0, 0.25, 0.55
    elif style == 'sleep':
        mean_gap, bowl_p, vol_scale = 70.0, 0.75, 0.85
    elif style == 'chakra':
        mean_gap, bowl_p, vol_scale = 48.0, 0.80, 1.05
    elif style == 'edge':
        mean_gap, bowl_p, vol_scale = 55.0, 0.55, 0.80
    elif style == 'focus':
        mean_gap, bowl_p, vol_scale = 80.0, 0.35, 0.65
    else:  # rest
        mean_gap, bowl_p, vol_scale = 52.0, 0.65, 0.95

    t = 8.0 + rng.uniform(0.0, mean_gap * 0.4)
    while t < dur_s - 6.0:
        ev_dur = float(rng.uniform(5.5, 11.0))
        # Pitch near carrier / soft fifth / octave below — stay musical to bed
        choices = [
            float(carrier),
            float(carrier) * 0.5,
            float(carrier) * 1.5,
            float(carrier) * 0.75,
        ]
        # Keep bowl fundamentals in a pleasant band
        f0 = float(np.clip(rng.choice(choices), 90.0, 520.0))
        if rng.rand() < bowl_p:
            eL, eR = singing_bowl_event(
                ev_dur, f0,
                vol=0.038 * intensity * vol_scale * float(rng.uniform(0.75, 1.1)),
                seed=seed + int(t * 10))
        else:
            eL, eR = soft_bell_event(
                ev_dur, f0 * float(rng.uniform(1.0, 1.8)),
                vol=0.026 * intensity * vol_scale * float(rng.uniform(0.7, 1.05)),
                seed=seed + int(t * 10) + 3)

        i0 = int(t * SR)
        i1 = min(n, i0 + len(eL))
        ln = i1 - i0
        if ln > 8:
            L[i0:i1] += eL[:ln]
            R[i0:i1] += eR[:ln]
        t += mean_gap * float(rng.uniform(0.65, 1.35))

    return L, R


# ══════════════════════════════════════════════════════════
#  MASTER ORGANIC MIX
# ══════════════════════════════════════════════════════════

_STYLE_MIX = {
    # river, ghosts, events
    'rest':    (0.020, 0.026, 1.00),
    'sleep':   (0.028, 0.020, 0.90),
    'edge':    (0.012, 0.024, 0.85),
    'focus':   (0.010, 0.018, 0.55),
    'chakra':  (0.014, 0.030, 1.10),
    'minimal': (0.006, 0.012, 0.35),
    # DEEP DIVE PRO: continuous bed only — events HARD-ZEROED (no bowl/bell
    # strike is a "discrete event" the liminal/auto phases must not produce).
    'void':    (0.010, 0.016, 0.00),
}


def organic_atmosphere(dur_s: float, carrier: float,
                       style: str = 'rest',
                       intensity: float = 1.0,
                       seed: int = 0,
                       ctype: str = 'soft') -> tuple:
    """
    Full organic bed (L, R). Safe to add after binaural / before master.
    """
    n = int(dur_s * SR)
    if intensity <= 0 or n < 32:
        z = np.zeros(n, dtype=np.float32)
        return z, z

    style = style if style in _STYLE_MIX else 'rest'
    river_v, ghost_v, ev_scale = _STYLE_MIX[style]
    river_v *= intensity
    ghost_v *= intensity

    L = np.zeros(n, dtype=np.float32)
    R = np.zeros(n, dtype=np.float32)

    if river_v > 0.001:
        rL, rR = river_bed(dur_s, vol=river_v, seed=seed + 100)
        L += rL
        R += rR

    if ghost_v > 0.001:
        gL, gR = harmonic_ghosts(dur_s, carrier, vol=ghost_v,
                                 seed=seed + 200, ctype=ctype)
        L += gL
        R += gR

    eL, eR = schedule_resonant_events(
        dur_s, carrier, style, intensity * ev_scale, seed=seed + 300)
    L += eL
    R += eR

    # Cap organic bus so it never dominates
    peak = max(float(np.max(np.abs(L))), float(np.max(np.abs(R)))) + 1e-9
    soft_cap = 0.09 * float(np.clip(intensity, 0.3, 1.4))
    if peak > soft_cap:
        s = soft_cap / peak
        L = (L * s).astype(np.float32)
        R = (R * s).astype(np.float32)

    return L.astype(np.float32), R.astype(np.float32)


def resolve_organic_style(label: str, b0: float, b1: float, c0: float, c1: float,
                          allow_sharp_iso: bool, use_focus_mix: bool,
                          style: str = 'auto') -> str:
    if style and style != 'auto':
        return style
    lab = (label or '').upper()
    if 'DEEP DIVE' in lab or 'DEEP_DIVE' in lab:
        return 'void'
    if allow_sharp_iso or max(b0, b1) >= 28.0 or 'WARRIOR' in lab:
        return 'minimal'
    if 'SLEEP' in lab or max(b0, b1) <= 3.2:
        return 'sleep'
    if 'CHAKRA' in lab or max(c0, c1) >= 520.0:
        return 'chakra'
    if use_focus_mix or 'EDGE' in lab or 'GATEWAY' in lab:
        return 'edge'
    if 'WALK' in lab or 'FOCUS' in lab or 'GENESIS' in lab:
        return 'focus' if 'WALK' in lab else 'rest'
    return 'rest'
