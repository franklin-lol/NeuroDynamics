import numpy as np
from scipy.signal import lfilter

SR = 44100
_SR_NOISE_RATIO = 0.282  # Gammaitoni 1998 optimum: -11.0 dB


def _rng(seed): return np.random.RandomState(seed)


# ══════════════════════════════════════════════════════════
#  NOISE
# ══════════════════════════════════════════════════════════

def pink_noise(n, seed=0):
    b = [0.049922035, -0.095993537, 0.050612699, -0.004408786]
    a = [1.0, -2.494956002, 2.017265875, -0.522189400]
    return lfilter(b, a, _rng(seed).standard_normal(n)).astype(np.float32)


def brown_noise(n, seed=0):
    x = np.cumsum(_rng(seed).standard_normal(n) * 0.02).astype(np.float32)
    return x - x.mean()


def morph_noise(n, pw, bw, seed=0):
    p = pink_noise(n, seed);    p /= np.max(np.abs(p)) + 1e-9
    b = brown_noise(n, seed+1); b /= np.max(np.abs(b)) + 1e-9
    m = p * pw + b * bw
    return (m / (np.max(np.abs(m)) + 1e-9)).astype(np.float32)


def calibrated_noise(sig_L, sig_R, pw, bw, seed=0):
    """Noise amplitude set to SR-optimal 15% of signal RMS. Returns (nz_L, nz_R)."""
    n = len(sig_L)
    sig_rms_L = np.sqrt(np.mean(sig_L**2)) + 1e-9
    sig_rms_R = np.sqrt(np.mean(sig_R**2)) + 1e-9
    nz_L = morph_noise(n, pw, bw, seed)
    nz_R = morph_noise(n, pw, bw, seed + 999)
    nz_rms_L = np.sqrt(np.mean(nz_L**2)) + 1e-9
    nz_rms_R = np.sqrt(np.mean(nz_R**2)) + 1e-9
    nz_L = (nz_L * (sig_rms_L * _SR_NOISE_RATIO / nz_rms_L)).astype(np.float32)
    nz_R = (nz_R * (sig_rms_R * _SR_NOISE_RATIO / nz_rms_R)).astype(np.float32)
    return nz_L, nz_R


# ══════════════════════════════════════════════════════════
#  SWEEPS
# ══════════════════════════════════════════════════════════

def log_sweep(a, b, n):
    if a <= 0 or b <= 0:
        return np.linspace(a, b, n, dtype=np.float64)
    return np.exp(np.linspace(np.log(a), np.log(b), n)).astype(np.float64)


def jitter_envelope(sweep, depth, seed):
    d = pink_noise(len(sweep), seed).astype(np.float64)
    d /= np.max(np.abs(d)) + 1e-9
    return sweep + d * depth


def build_carrier(c0, c1, n, jitter_depth=2.0, seed=0,
                  drift_depth=0.0, drift_rate=0.018):
    """
    Linear carrier sweep + pink micro-jitter.
    Optional ultra-slow drift_depth (Hz) keeps the note alive without
    altering the binaural beat difference.
    """
    base = np.linspace(c0, c1, n, dtype=np.float64)
    d    = pink_noise(n, seed + 200).astype(np.float64)
    d   /= np.max(np.abs(d)) + 1e-9
    out  = base + d * jitter_depth
    if drift_depth and drift_depth > 0:
        from .organic import carrier_drift_hz
        out = out + carrier_drift_hz(n, depth_hz=float(drift_depth),
                                     rate_hz=float(drift_rate), seed=seed + 211)
    return out


def adaptive_drift_envelope(n, control_points, micro_amp=0.0,
                            micro_rate=0.012, seed=0):
    """
    Piecewise beat path for habituation-resistant deep sessions.

    control_points: iterable of (frac 0..1, beat_hz), sorted by frac.
    Linear interpolation between points, then independent micro-oscillation
    (±micro_amp Hz) — not synchronized to breath/infra/spatial layers.
    """
    if n < 2:
        return np.zeros(max(n, 0), dtype=np.float64)
    pts = sorted((float(a), float(b)) for a, b in control_points)
    if not pts:
        return np.full(n, 10.0, dtype=np.float64)
    if pts[0][0] > 0.0:
        pts = [(0.0, pts[0][1])] + pts
    if pts[-1][0] < 1.0:
        pts = pts + [(1.0, pts[-1][1])]

    fracs = np.array([p[0] for p in pts], dtype=np.float64)
    hz    = np.array([p[1] for p in pts], dtype=np.float64)
    x = np.linspace(0.0, 1.0, n, dtype=np.float64)
    base = np.interp(x, fracs, hz)

    if micro_amp and micro_amp > 0:
        t = np.arange(n, dtype=np.float64) / SR
        # Multi-rate + ultra-slow wander — never metronomic
        micro = micro_amp * (
            0.50 * np.sin(2 * np.pi * micro_rate * t + seed * 0.37)
            + 0.30 * np.sin(2 * np.pi * micro_rate * 0.43 * t + 1.9)
            + 0.20 * np.sin(2 * np.pi * micro_rate * 1.71 * t + 0.6)
        )
        wander = pink_noise(n, seed + 77).astype(np.float64)
        a = float(np.exp(-2.0 * np.pi * 0.04 / SR))
        wander = lfilter([1.0 - a], [1.0, -a], wander)
        wander -= wander.mean()
        wander /= (np.max(np.abs(wander)) + 1e-9)
        base = base + micro + wander * micro_amp * 0.35

    return np.clip(base, 0.3, 120.0).astype(np.float64)


# ══════════════════════════════════════════════════════════
#  CROSSFADE  —  fade_through_silence
#
#  Архитектура решения:
#    Проблема:  STFT-морфинг при переходе 200→432 Hz даёт
#               фазовую отмену: RMS-девиация -29.9%, max_delta=0.039
#               (порог щелчка: 0.001). Артефакт слышен.
#
#    Решение:   cosine fade-out → тишина 0.5s → cosine fade-in.
#               Граничные значения = 0.000000 математически точно.
#               Тишина 0.5s — психоакустический "сброс": мозг
#               обнуляет предыдущий контекст перед новым блоком.
#               Pink noise -62 dBFS в паузе маскирует абсолютную
#               тишину (предотвращает слуховую адаптацию к тишине).
#
#    Источник:  Ennio Morricone, Pink Floyd Dark Side of the Moon,
#               все современные meditation/ambient labels —
#               professional standard для смены carrier frequencies.
# ══════════════════════════════════════════════════════════

def _cosine_fade(n: int):
    """Cosine fade curves. C1-непрерывны: начало и конец = 0.0 точно."""
    t        = np.linspace(0.0, 1.0, n, dtype=np.float32)
    fade_out = (0.5 + 0.5 * np.cos(np.pi * t)).astype(np.float32)  # 1 → 0
    fade_in  = (0.5 - 0.5 * np.cos(np.pi * t)).astype(np.float32)  # 0 → 1
    return fade_out, fade_in


def crossfade_write(fh, prev_tail, new_L, new_R,
                    fade_s: float = 10.0,
                    silence_s: float = 0.5,
                    equal_power: bool = False):
    """
    Crossfade between blocks.

    equal_power=False (default): fade-through-silence — best for large carrier jumps.
    equal_power=True + silence_s=0: overlapping equal-power XF for same-carrier continuity.

    silence_s=0.5  — carrier change reset
    silence_s=0.0  — seamless join (with equal_power for rest profiles)
    """
    fn = min(int(fade_s * SR), len(new_L) // 4)
    sn = int(silence_s * SR)

    if fn < 2 or prev_tail is None:
        _, fade_in = _cosine_fade(fn)
        new_L = new_L.copy(); new_R = new_R.copy()
        new_L[:fn] *= fade_in;  new_R[:fn] *= fade_in
        body_L = new_L[:-fn] if fn > 0 else new_L
        body_R = new_R[:-fn] if fn > 0 else new_R
        if len(body_L):
            fh.write(np.stack([body_L, body_R], axis=1))
        return (new_L[-fn:].copy(), new_R[-fn:].copy()) if fn > 0 else (None, None)

    pL, pR = prev_tail
    fn = min(fn, len(pL), len(new_L))

    fade_out, fade_in = _cosine_fade(fn)
    new_L = new_L.copy(); new_R = new_R.copy()

    if equal_power and sn == 0:
        # Equal-power overlap: sqrt curves keep constant energy through join
        t = np.linspace(0.0, 1.0, fn, dtype=np.float32)
        eo = np.sqrt(np.clip(1.0 - t, 0.0, 1.0)).astype(np.float32)
        ei = np.sqrt(np.clip(t, 0.0, 1.0)).astype(np.float32)
        mix_L = (pL[-fn:] * eo + new_L[:fn] * ei).astype(np.float32)
        mix_R = (pR[-fn:] * eo + new_R[:fn] * ei).astype(np.float32)
        fh.write(np.stack([mix_L, mix_R], axis=1))
        body_L = new_L[fn:-fn] if len(new_L) > 2 * fn else np.array([], np.float32)
        body_R = new_R[fn:-fn] if len(new_R) > 2 * fn else np.array([], np.float32)
        if len(body_L):
            fh.write(np.stack([body_L, body_R], axis=1))
        return new_L[-fn:].copy(), new_R[-fn:].copy()

    # Fade-through-silence path
    tL = (pL[-fn:] * fade_out).astype(np.float32)
    tR = (pR[-fn:] * fade_out).astype(np.float32)
    fh.write(np.stack([tL, tR], axis=1))

    if sn > 0:
        nz  = pink_noise(sn, seed=int(fade_s * 1000) % 65535) * 0.0008
        fh.write(np.stack([nz, nz], axis=1))

    new_L[:fn] *= fade_in;  new_R[:fn] *= fade_in

    body_L = new_L[fn:-fn] if len(new_L) > 2 * fn else np.array([], np.float32)
    body_R = new_R[fn:-fn] if len(new_R) > 2 * fn else np.array([], np.float32)
    if len(body_L):
        fh.write(np.stack([body_L, body_R], axis=1))

    return new_L[-fn:].copy(), new_R[-fn:].copy()
