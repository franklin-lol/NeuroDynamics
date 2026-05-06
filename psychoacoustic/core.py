import numpy as np
from scipy.signal import lfilter

SR = 44100
_SR_NOISE_RATIO = 0.15  # stochastic resonance optimum: noise = 15% signal RMS


def _rng(seed): return np.random.RandomState(seed)

# ── Noise

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
    """Noise amplitude set to SR-optimal 15% of signal RMS."""
    n = len(sig_L)
    sig_rms = np.sqrt(np.mean(sig_L**2 + sig_R**2) / 2) + 1e-9
    nz = morph_noise(n, pw, bw, seed)
    nz_rms = np.sqrt(np.mean(nz**2)) + 1e-9
    return (nz * (sig_rms * _SR_NOISE_RATIO / nz_rms)).astype(np.float32)

# ── Sweeps

def log_sweep(a, b, n):
    if a <= 0 or b <= 0:
        return np.linspace(a, b, n, dtype=np.float64)
    return np.exp(np.linspace(np.log(a), np.log(b), n)).astype(np.float64)

def jitter_envelope(sweep, depth, seed):
    d = pink_noise(len(sweep), seed).astype(np.float64)
    d /= np.max(np.abs(d)) + 1e-9
    return sweep + d * depth

def build_carrier(c0, c1, n, jitter_depth=2.0, seed=0):
    base = np.linspace(c0, c1, n, dtype=np.float64)
    d = pink_noise(n, seed + 200).astype(np.float64)
    d /= np.max(np.abs(d)) + 1e-9
    return base + d * jitter_depth

# ── Crossfade (equal-power √taper — no loudness dip)

def _eq_power_fade(n):
    t = np.linspace(0.0, np.pi / 2, n, dtype=np.float32)
    return np.cos(t), np.sin(t)

def crossfade_write(fh, prev_tail, new_L, new_R, fade_s=8.0):
    fn = min(int(fade_s * SR), len(new_L) // 4)
    if fn < 2 or prev_tail is None:
        body_L = new_L[:-fn] if fn > 0 else new_L
        body_R = new_R[:-fn] if fn > 0 else new_R
        if len(body_L): fh.write(np.stack([body_L, body_R], axis=1))
        return (new_L[-fn:].copy(), new_R[-fn:].copy()) if fn > 0 else (None, None)

    pL, pR = prev_tail
    fn = min(fn, len(pL), len(new_L))
    fo, fi = _eq_power_fade(fn)
    fh.write(np.stack([pL[:fn]*fo + new_L[:fn]*fi,
                       pR[:fn]*fo + new_R[:fn]*fi], axis=1))
    body_L = new_L[fn:-fn] if len(new_L) > 2*fn else np.array([], np.float32)
    body_R = new_R[fn:-fn] if len(new_R) > 2*fn else np.array([], np.float32)
    if len(body_L): fh.write(np.stack([body_L, body_R], axis=1))
    return new_L[-fn:].copy(), new_R[-fn:].copy()
