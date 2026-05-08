"""
HRTF — Brown-Duda Spherical Head Model + Pinna Approximation

Реализация аналитической модели сферической головы Брауна-Дуды (1998).
"Золотой стандарт" аналитических HRTF без внешних файлов.

  1. ITD (Woodworth 1962) — частотно-независимая задержка по углу азимута
  2. Brown-Duda ILD filter — one-pole/one-zero IIR, имитирует частотно-
     зависимое огибание звука вокруг головы.
     FIX v3.3: предыдущая версия имела a=[1,-0.0] (FIR, нет полюса).
     Теперь истинный IIR: полюс даёт частотно-зависимую тень головы.
  3. Pinna comb filter — спектральный notch ~8–10 kHz (elevation cue)
  4. Elevation: HF shelving EQ
  5. Dynamic sweep: chunk-based azimuth rotation

Источники:
  Brown C.P., Duda R.O. (1998) "A structural model for binaural sound synthesis"
  Woodworth R.S. (1938) "Experimental psychology"
"""

import numpy as np
from scipy.signal import lfilter, sosfilt, butter
from .core import SR

# ── Физические константы
_HEAD_R  = 0.0875       # радиус головы, м
_SOUND_C = 343.0        # скорость звука, м/с
_OMEGA0  = _SOUND_C / _HEAD_R  # ≈ 3920 rad/s → f₀ ≈ 624 Hz (Brown-Duda crossover)


# ══════════════════════════════════════════════════════════
#  1. WOODWORTH ITD
# ══════════════════════════════════════════════════════════

def _woodworth_itd_samples(azimuth_rad: float) -> int:
    """
    Woodworth (1938): ITD = (r/c) * (sin θ + θ)  для |θ| ≤ π/2
    + = правое ухо запаздывает (источник справа).
    """
    az  = np.clip(azimuth_rad, -np.pi / 2, np.pi / 2)
    itd = (_HEAD_R / _SOUND_C) * (np.sin(az) + az)
    return int(round(itd * SR))


# ══════════════════════════════════════════════════════════
#  2. BROWN-DUDA ILD FILTER  (исправленный — истинный IIR)
#
#  Физика: контралатеральное ухо находится в "тени" головы.
#  Высокие частоты (короткая λ) — блокируются головой.
#  Низкие частоты (длинная λ) — огибают голову (меньше тени).
#  → фильтр для контралатерального уха: LP-shelf.
#
#  FIX: scipy.butter(1) — bilinear transform 1-st order Butterworth
#  даёт ровно one-pole/one-zero IIR (как в Brown-Duda), но
#  со стабильными и физически мотивированными коэффициентами.
#  Cutoff fc_hz плавно падает с 20 кГц (фронт, нет тени)
#  до ~600 Гц (сторона, максимальная тень).
# ══════════════════════════════════════════════════════════

def _brown_duda_ild_filter(az_abs_rad: float) -> tuple:
    """
    Brown-Duda (1998) head-shadow IIR — one-pole / one-zero.

    H(s) = (s/ω₀ + 1/α) / (s/ω₀ + 1)
    Bilinear transform, prewarped at f₀ = ω₀/(2π) ≈ 624 Hz.

    Properties (analytically verified):
      DC gain  = 1/α  →  low-freq ILD matches free-field measurements
      HF gain  = 1.0  →  high-freq diffraction wraps around head (no blockage)
      Pole     = (-1+K)/(1+K) ≈ -0.915  (stable, causal)

    α(θ) = 1.0 + 0.5·|sin θ|
      front (0°):  α=1.00  DC=1.000  (no shadow — flat response)
      mid   (45°): α=1.35  DC=0.739  (-2.6 dB low-freq ILD)
      side  (90°): α=1.50  DC=0.667  (-3.5 dB low-freq ILD = max shadow)

    FIX vs previous Butterworth LP:
      Butterworth: DC=1, HF≈0 — attenuates high freq (wrong physics,
                   wrong Brown-Duda spectrum shape)
      Brown-Duda:  DC=1/α, HF=1 — matches paper + measured HRTF data

    az_abs_rad: |azimuth| in [0, π/2]
    Returns: (b, a) 2-tap IIR for scipy.signal.lfilter
    """
    az    = np.clip(az_abs_rad, 0.0, np.pi / 2)
    alpha = 1.0 + 0.5 * np.sin(az)          # 1.0 (front) → 1.5 (side)

    # Bilinear transform of H(s) = (s/ω₀ + 1/α) / (s/ω₀ + 1)
    # K = ω₀/(2·SR)  — prewarping approximation (error < 0.5% at f₀=624 Hz)
    K    = (_OMEGA0) / (2.0 * SR)
    norm = 1.0 / (1.0 + K)

    b = np.array([(1.0 + K / alpha) * norm,   # b₀
                  (-1.0 + K / alpha) * norm])  # b₁
    a = np.array([1.0,
                  (-1.0 + K) * norm])          # a₁  (pole ≈ -0.915, stable)
    return b, a


# ══════════════════════════════════════════════════════════
#  3. PINNA COMB FILTER
# ══════════════════════════════════════════════════════════

def _apply_pinna(sig: np.ndarray, delay_ms: float = 0.30,
                 gain: float = 0.20) -> np.ndarray:
    """Задержка + аттенюация → spect. notch ~8–10 kHz (elevation cue)."""
    n   = len(sig)
    d   = max(1, int(delay_ms * 0.001 * SR))
    ref = np.zeros(n, np.float32)
    if d < n:
        ref[d:] = sig[:-d] * gain
    return (sig + ref).astype(np.float32)


# ══════════════════════════════════════════════════════════
#  4. ELEVATION SPECTRAL TILT
# ══════════════════════════════════════════════════════════

def _elevation_shelf(sig: np.ndarray, elevation_rad: float) -> np.ndarray:
    """HF shelf EQ: выше горизонта → +presence, ниже → -presence."""
    if abs(elevation_rad) < 0.05:
        return sig
    gain_db = np.clip(elevation_rad / (np.pi / 2) * 4.0, -6.0, 6.0)
    fc      = 4000.0
    K       = np.tan(np.pi * fc / SR)
    A       = 10.0 ** (gain_db / 40.0)
    b0      = A * (K + A) / (K + 1.0)
    b1      = A * (A - K) / (K + 1.0)
    a1      = (1.0 - K)   / (K + 1.0)
    return lfilter([b0, b1], [1.0, a1], sig).astype(np.float32)


# ══════════════════════════════════════════════════════════
#  MAIN: STATIC HRTF
# ══════════════════════════════════════════════════════════

def hrtf_static(L: np.ndarray, R: np.ndarray,
                azimuth_deg:   float = 0.0,
                elevation_deg: float = 0.0,
                distance:      float = 1.0) -> tuple:
    """
    Применяет полную Brown-Duda HRTF модель к стерео-паре.
    azimuth_deg:   -90…+90  (отрицательный = слева)
    elevation_deg: -45…+45
    distance:      1.0 норма, >1 дальше (-6dB/удвоение + air LP)
    """
    az_rad = np.radians(np.clip(azimuth_deg, -90.0, 90.0))
    el_rad = np.radians(elevation_deg)
    az_abs = abs(az_rad)            # для симметричного ILD фильтра
    n      = len(L)

    # ── 1. Woodworth ITD
    itd = _woodworth_itd_samples(az_rad)  # > 0: источник справа

    if itd > 0:
        # источник справа: левое ухо задерживается
        pad     = np.zeros(itd, np.float32)
        L_out   = np.concatenate([pad, L[:-itd]]).astype(np.float32)
        R_out   = R.copy().astype(np.float32)
    elif itd < 0:
        # источник слева: правое ухо задерживается
        d       = -itd
        pad     = np.zeros(d, np.float32)
        L_out   = L.copy().astype(np.float32)
        R_out   = np.concatenate([pad, R[:-d]]).astype(np.float32)
    else:
        L_out, R_out = L.copy().astype(np.float32), R.copy().astype(np.float32)

    # ── 2. Brown-Duda ILD (контралатеральное ухо = "в тени")
    b, a = _brown_duda_ild_filter(az_abs)
    if az_rad >= 0:                 # источник справа → левое ухо в тени
        L_out = lfilter(b, a, L_out).astype(np.float32)
    else:                           # источник слева → правое ухо в тени
        R_out = lfilter(b, a, R_out).astype(np.float32)

    # ── 3. Pinna comb notch — оба уха
    L_out = _apply_pinna(L_out)
    R_out = _apply_pinna(R_out)

    # ── 4. Elevation shelf
    L_out = _elevation_shelf(L_out, el_rad)
    R_out = _elevation_shelf(R_out, el_rad)

    # ── 5. Distance model
    if distance != 1.0:
        gain  = 1.0 / max(0.1, distance)
        L_out = (L_out * gain).astype(np.float32)
        R_out = (R_out * gain).astype(np.float32)
        if distance > 1.5:
            fc  = max(500.0, 18000.0 / distance)
            nyq = SR / 2.0
            sos = butter(2, min(fc / nyq, 0.99), btype='low', output='sos')
            L_out = sosfilt(sos, L_out).astype(np.float32)
            R_out = sosfilt(sos, R_out).astype(np.float32)

    return L_out, R_out


# ══════════════════════════════════════════════════════════
#  MAIN: DYNAMIC HRTF EXTERNALIZATION
#  Используется в block.render() при use_hrtf=True.
#  az_sweep_period=0  → фиксированный азимут ~22° справа
#  az_sweep_period>0  → медленная ротация (chunk = 0.5 с)
# ══════════════════════════════════════════════════════════

def hrtf_externalize(L: np.ndarray, R: np.ndarray,
                     az_sweep_period: float = 0.0,
                     elevation_deg:   float = 0.0) -> tuple:
    """
    Brown-Duda HRTF для частичной экстернализации.
    Статический режим: азимут 22° → выносит образ из центра головы.
    Sweep-режим: chunk-based (0.5 с/chunk) ротация ±80° по азимуту.
    """
    if az_sweep_period <= 0:
        return hrtf_static(L, R, azimuth_deg=22.0,
                           elevation_deg=elevation_deg)

    n      = len(L)
    chunk  = int(0.5 * SR)
    out_L  = np.zeros(n, np.float32)
    out_R  = np.zeros(n, np.float32)

    for i in range(0, n, chunk):
        i1     = min(i + chunk, n)
        t_mid  = (i + i1) / 2.0 / SR
        az_deg = 80.0 * np.sin(2 * np.pi * t_mid / az_sweep_period)
        sl, sr = hrtf_static(L[i:i1], R[i:i1],
                             azimuth_deg=az_deg,
                             elevation_deg=elevation_deg)
        out_L[i:i1] = sl
        out_R[i:i1] = sr

    return out_L, out_R
