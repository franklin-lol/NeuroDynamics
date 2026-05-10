import numpy as np
from scipy.signal import lfilter

SR = 44100
_SR_NOISE_RATIO = 0.282  # Gammaitoni 1998 optimum: -11.0 dB (was 0.15 = -16.5 dB, under-stimulation)


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

# ── Crossfade (Spectral STFT Morphing — Phase: ATMOSPHERE)

def _spectral_morph(pL, pR, nL, nR, n):
    """
    STFT Overlap-Add morphing between two stereo buffers.
    Interpolates complex spectra to ensure smooth harmonic transitions.
    """
    nfft = 2048
    hop  = 512
    w    = np.hanning(nfft)
    
    # Pad to fit frames
    pad = nfft
    pL_p = np.pad(pL, (0, pad)); pR_p = np.pad(pR, (0, pad))
    nL_p = np.pad(nL, (0, pad)); nR_p = np.pad(nR, (0, pad))
    
    outL = np.zeros(n + pad, dtype=np.float32)
    outR = np.zeros(n + pad, dtype=np.float32)
    
    for i in range(0, n, hop):
        ratio = i / n
        # STFT frames
        f_pL = np.fft.rfft(pL_p[i:i+nfft] * w)
        f_pR = np.fft.rfft(pR_p[i:i+nfft] * w)
        f_nL = np.fft.rfft(nL_p[i:i+nfft] * w)
        f_nR = np.fft.rfft(nR_p[i:i+nfft] * w)
        
        # Linear interpolation in complex domain (morph)
        # Matches phase if frequencies are close, else creates smooth spectral blur
        m_L = f_pL * (1.0 - ratio) + f_nL * ratio
        m_R = f_pR * (1.0 - ratio) + f_nR * ratio
        
        outL[i:i+nfft] += np.fft.irfft(m_L).astype(np.float32) * w
        outR[i:i+nfft] += np.fft.irfft(m_R).astype(np.float32) * w
        
    # Constant overlap-add gain correction (Hann 50% overlap = 1.5 sum)
    gain = 2.0 / 3.0 # for 75% overlap or 1.0/sum(w**2) approx
    return outL[:n] * 0.66, outR[:n] * 0.66

def crossfade_write(fh, prev_tail, new_L, new_R, fade_s=8.0):
    fn = min(int(fade_s * SR), len(new_L) // 4)
    if fn < 2 or prev_tail is None:
        body_L = new_L[:-fn] if fn > 0 else new_L
        body_R = new_R[:-fn] if fn > 0 else new_R
        if len(body_L): fh.write(np.stack([body_L, body_R], axis=1))
        return (new_L[-fn:].copy(), new_R[-fn:].copy()) if fn > 0 else (None, None)

    pL, pR = prev_tail
    fn = min(fn, len(pL), len(new_L))
    
    # Use spectral morphing for the transition
    mL, mR = _spectral_morph(pL[:fn], pR[:fn], new_L[:fn], new_R[:fn], fn)
    fh.write(np.stack([mL, mR], axis=1))
    
    body_L = new_L[fn:-fn] if len(new_L) > 2*fn else np.array([], np.float32)
    body_R = new_R[fn:-fn] if len(new_R) > 2*fn else np.array([], np.float32)
    if len(body_L): fh.write(np.stack([body_L, body_R], axis=1))
    return new_L[-fn:].copy(), new_R[-fn:].copy()
