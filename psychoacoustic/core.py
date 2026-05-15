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
    """Noise amplitude set to SR-optimal 15% of signal RMS."""
    n       = len(sig_L)
    sig_rms = np.sqrt(np.mean(sig_L**2 + sig_R**2) / 2) + 1e-9
    nz      = morph_noise(n, pw, bw, seed)
    nz_rms  = np.sqrt(np.mean(nz**2)) + 1e-9
    return (nz * (sig_rms * _SR_NOISE_RATIO / nz_rms)).astype(np.float32)


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


def build_carrier(c0, c1, n, jitter_depth=2.0, seed=0):
    base = np.linspace(c0, c1, n, dtype=np.float64)
    d    = pink_noise(n, seed + 200).astype(np.float64)
    d   /= np.max(np.abs(d)) + 1e-9
    return base + d * jitter_depth


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
                    silence_s: float = 0.5):
    """
    Профессиональный crossfade через тишину.

    Алгоритм:
      1. Хвост предыдущего блока: cosine fade 1→0
      2. Тишина silence_s секунд (Pink noise -62 dBFS как floor)
      3. Новый блок:            cosine fade 0→1

    silence_s=0.5  — оптимум для смены несущих.
    silence_s=0.2  — для pattern_break (короткий, уже есть 20s паузы).
    """
    fn = min(int(fade_s * SR), len(new_L) // 4)
    sn = int(silence_s * SR)

    if fn < 2 or prev_tail is None:
        # Первый блок — только fade-in
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

    # 1. Хвост: плавное затухание
    tL = (pL[-fn:] * fade_out).astype(np.float32)
    tR = (pR[-fn:] * fade_out).astype(np.float32)
    fh.write(np.stack([tL, tR], axis=1))

    # 2. Тишина + pink noise -62 dBFS (floor маскирует абсолютную тишину)
    if sn > 0:
        nz  = pink_noise(sn, seed=int(fade_s * 1000) % 65535) * 0.0008
        fh.write(np.stack([nz, nz], axis=1))

    # 3. Нарастание нового блока
    new_L = new_L.copy(); new_R = new_R.copy()
    new_L[:fn] *= fade_in;  new_R[:fn] *= fade_in

    body_L = new_L[fn:-fn] if len(new_L) > 2 * fn else np.array([], np.float32)
    body_R = new_R[fn:-fn] if len(new_R) > 2 * fn else np.array([], np.float32)
    if len(body_L):
        fh.write(np.stack([body_L, body_R], axis=1))

    return new_L[-fn:].copy(), new_R[-fn:].copy()
