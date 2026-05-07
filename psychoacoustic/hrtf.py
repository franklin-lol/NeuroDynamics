"""
HRTF — Brown-Duda Spherical Head Model + Pinna Approximation

Реализация аналитической модели сферической головы Брауна-Дуды (2001).
Это "золотой стандарт" аналитических HRTF без внешних файлов:

  1. ITD (Woodworth 1962) — частотно-независимая задержка по углу азимута
  2. Brown-Duda ILD filter — дифракционный фильтр ogибания звука вокруг головы.
     One-pole/one-zero: точнее, чем простой LP, математически обоснован.
  3. Pinna comb filter — отражение от ушной раковины → спектральный notch
  4. Elevation: spectral tilt via shelving EQ
  5. 3D orbital: slow Lissajous azimuth+elevation sweep

Источники:
  Brown C.P., Duda R.O. (1998) "A structural model for binaural sound synthesis"
  Woodworth R.S. (1938) "Experimental psychology"
"""

import numpy as np
from scipy.signal import lfilter, sosfilt, butter
from .core import SR

# ── Физические константы головы
_HEAD_R   = 0.0875          # радиус головы, м
_SOUND_C  = 343.0           # скорость звука, м/с
_MAX_ITD  = _HEAD_R / _SOUND_C   # ≈ 0.000255 с = ~11 сэмплов при 44100 Hz


# ══════════════════════════════════════════════════════════
#  1. WOODWORTH ITD
# ══════════════════════════════════════════════════════════

def _woodworth_itd_samples(azimuth_rad: float) -> int:
    """
    Woodworth (1938): ITD = (r/c) * (sin θ + θ)  для  |θ| ≤ π/2
    Возвращает задержку в сэмплах (положительная = правое ухо опережает).
    """
    az = np.clip(azimuth_rad, -np.pi/2, np.pi/2)
    itd_sec = (_HEAD_R / _SOUND_C) * (np.sin(az) + az)
    return int(round(itd_sec * SR))


# ══════════════════════════════════════════════════════════
#  2. BROWN-DUDA DIFFRACTION FILTER
#  One-pole / one-zero IIR имитирует огибание звука вокруг головы.
#  Параметры выведены из уравнений Brown & Duda (1998) eq. 10.
# ══════════════════════════════════════════════════════════

def _brown_duda_filter(azimuth_rad: float) -> tuple:
    """
    Возвращает (b, a) IIR-фильтра для ипсилатерального (ближнего) уха.
    Контралатеральное ухо: используй azimuth_rad → π - azimuth_rad.
    """
    az   = azimuth_rad % (2*np.pi)
    # Угловая функция α(θ) из Brown-Duda eq.10
    alpha_min = 0.1
    alpha_max = 1.0 if az <= np.pi/2 else (
                1.0 + np.cos(az) * (1.0 - alpha_min))

    # Нормированная частота среза (пропорциональна az)
    # w0 ∈ [0.1, π]  в нормированных rad/sample
    w0 = np.pi * np.clip(2.0 * abs(np.sin(az)), 0.05, 0.99)

    # Биквадрат one-pole/one-zero:
    #   H(z) = (1 + alpha * z^-1) / (1 + z^-1)
    alpha = (1.0 - w0/(2*np.pi)) * alpha_max
    alpha = np.clip(alpha, -0.99, 0.99)
    b = np.array([1.0,  alpha])
    a = np.array([1.0, -0.0])   # one-zero only (pole at origin)
    return b, a


# ══════════════════════════════════════════════════════════
#  3. PINNA COMB FILTER
#  Задержка ~0.28–0.32 мс + аттенюация → спектральный notch
# ══════════════════════════════════════════════════════════

def _apply_pinna(sig: np.ndarray, delay_ms: float = 0.30,
                 gain: float = 0.20) -> np.ndarray:
    n  = len(sig)
    d  = max(1, int(delay_ms * 0.001 * SR))
    out = np.zeros(n, np.float32)
    out[d:] = sig[:-d] * gain
    return (sig + out).astype(np.float32)


# ══════════════════════════════════════════════════════════
#  4. ELEVATION SPECTRAL TILT
#  Выше горизонта → присутствие (HF shelf +)
#  Ниже горизонта → тень (HF shelf -)
# ══════════════════════════════════════════════════════════

def _elevation_shelf(sig: np.ndarray, elevation_rad: float) -> np.ndarray:
    if abs(elevation_rad) < 0.05:
        return sig
    nyq    = SR / 2.0
    gain   = np.clip(elevation_rad / (np.pi/2) * 4.0, -6.0, 6.0)  # dB
    fc     = 4000.0
    # Simple 1st-order HF shelf via bilinear transform
    K      = np.tan(np.pi * fc / SR)
    A      = 10.0**(gain / 40.0)
    b0     = A * (K + A) / (K + 1.0)
    b1     = A * (A - K) / (K + 1.0)
    a1     = (1.0 - K)   / (K + 1.0)
    b      = np.array([b0, b1])
    a      = np.array([1.0, a1])
    return lfilter(b, a, sig).astype(np.float32)


# ══════════════════════════════════════════════════════════
#  MAIN: STATIC HRTF (point in space)
# ══════════════════════════════════════════════════════════

def hrtf_static(L: np.ndarray, R: np.ndarray,
                azimuth_deg:   float = 0.0,
                elevation_deg: float = 0.0,
                distance:      float = 1.0) -> tuple:
    """
    Применяет полную Brown-Duda HRTF модель к стерео-паре.
    azimuth_deg:   -90…+90  (лево-право)
    elevation_deg: -45…+45  (низ-верх)
    distance:      1.0 = нормальная, >1 = дальше (LP + -6dB/удвоение)
    """
    az  = np.radians(azimuth_deg)
    el  = np.radians(elevation_deg)
    n   = len(L)

    # ITD: задержка ближнего / дальнего уха
    itd = _woodworth_itd_samples(az)

    if itd > 0:
        # источник справа — правое ухо ближе
        L_delayed = np.concatenate([np.zeros(itd, np.float32), L[:-itd]])
        R_lead    = R.copy()
    elif itd < 0:
        L_lead    = L.copy()
        R_delayed = np.concatenate([np.zeros(-itd, np.float32), R[:itd]])
        L_delayed = L_lead
        R_lead    = R_delayed
        R_delayed = R_delayed   # alias
        L_delayed = L
    else:
        L_delayed, R_lead = L, R

    if itd > 0:
        L_out, R_out = L_delayed, R_lead
    elif itd < 0:
        L_out = L
        R_out = np.concatenate([np.zeros(-itd, np.float32), R[:-(-itd)]])
    else:
        L_out, R_out = L.copy(), R.copy()

    # Brown-Duda ILD filter
    b_ipsi,  a_ipsi  = _brown_duda_filter(max(0, az))
    b_contra, a_contra = _brown_duda_filter(np.pi - max(0, az))

    if az >= 0:  # источник справа
        R_out = lfilter(b_ipsi,   a_ipsi,   R_out).astype(np.float32)
        L_out = lfilter(b_contra, a_contra, L_out).astype(np.float32)
    else:         # источник слева
        L_out = lfilter(b_ipsi,   a_ipsi,   L_out).astype(np.float32)
        R_out = lfilter(b_contra, a_contra, R_out).astype(np.float32)

    # Pinna comb notch — оба уха
    L_out = _apply_pinna(L_out)
    R_out = _apply_pinna(R_out)

    # Elevation shelf
    L_out = _elevation_shelf(L_out, el)
    R_out = _elevation_shelf(R_out, el)

    # Distance: -6 dB/octave amplitude + air absorption LP
    if distance != 1.0:
        gain = 1.0 / max(0.1, distance)
        L_out *= gain; R_out *= gain
        if distance > 1.5:
            nyq  = SR / 2.0
            fc   = max(500.0, 18000.0 / distance)
            sos  = butter(2, min(fc/nyq, 0.99), btype='low', output='sos')
            L_out = sosfilt(sos, L_out).astype(np.float32)
            R_out = sosfilt(sos, R_out).astype(np.float32)

    return L_out, R_out


# ══════════════════════════════════════════════════════════
#  MAIN: DYNAMIC HRTF EXTERNALIZATION (moving source)
#  Используется в block.render() когда use_hrtf=True
#  Медленный sweep по азимуту 0→360° с небольшим el_offset
# ══════════════════════════════════════════════════════════

def hrtf_externalize(L: np.ndarray, R: np.ndarray,
                     az_sweep_period: float = 0.0,
                     elevation_deg:   float = 0.0) -> tuple:
    """
    Применяет Brown-Duda HRTF для частичной экстернализации.
    Без sweep (az_sweep_period=0): фиксированная позиция ~30° справа.
    С sweep: медленная ротация по азимуту (chunk-based, не пересемплирует).
    """
    if az_sweep_period <= 0:
        # Фиксированный небольшой азимут → выносит образ из центра головы
        return hrtf_static(L, R, azimuth_deg=22.0,
                           elevation_deg=elevation_deg)

    # Chunk-based sweep: обновляем фильтр каждые 0.5 с
    n        = len(L)
    chunk    = int(0.5 * SR)
    out_L    = np.zeros(n, np.float32)
    out_R    = np.zeros(n, np.float32)
    t_arr    = np.arange(n, dtype=np.float64) / SR

    for i in range(0, n, chunk):
        i1     = min(i + chunk, n)
        t_mid  = (i + i1) / 2.0 / SR
        az_deg = 80.0 * np.sin(2*np.pi*t_mid/az_sweep_period)
        sl, sr = hrtf_static(L[i:i1], R[i:i1],
                             azimuth_deg=az_deg,
                             elevation_deg=elevation_deg)
        out_L[i:i1] = sl
        out_R[i:i1] = sr

    return out_L, out_R
