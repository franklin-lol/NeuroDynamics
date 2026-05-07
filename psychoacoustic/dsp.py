import numpy as np
from scipy.signal import lfilter, iirfilter, sosfilt, butter
from .core import SR, log_sweep, jitter_envelope, build_carrier, pink_noise

SCHUMANN = [7.83, 14.3, 20.8, 27.3, 33.8]

# ══════════════════════════════════════════════════════════
#  CARRIER SYNTHESIS  — тембральная палитра
# ══════════════════════════════════════════════════════════

def _apply_carrier_type(phase: np.ndarray, ctype: str) -> np.ndarray:
    """
    'sine'   pure sine
    'warm'   FM β=0.28 ratio=1.5 — bell / tibetan bowl
    'rich'   additive 5 harmonics 1/n — singing bowl / cello
    'soft'   fundamental + whisper 2nd — zero fatigue (SLEEP/HEALER)
    'organ'  drawbar: strong 2nd+3rd
    """
    if ctype == 'warm':
        return np.sin(phase + 0.28*np.sin(1.5*phase)).astype(np.float32)
    elif ctype == 'rich':
        s = (0.600*np.sin(phase)   + 0.240*np.sin(2*phase)
           + 0.100*np.sin(3*phase) + 0.040*np.sin(4*phase)
           + 0.020*np.sin(5*phase))
        return s.astype(np.float32)
    elif ctype == 'soft':
        return (0.88*np.sin(phase) + 0.10*np.sin(2*phase)
              + 0.02*np.sin(3*phase)).astype(np.float32)
    elif ctype == 'organ':
        return (0.55*np.sin(phase)   + 0.30*np.sin(2*phase)
              + 0.12*np.sin(3*phase) + 0.03*np.sin(4*phase)).astype(np.float32)
    else:
        return np.sin(phase).astype(np.float32)


# ══════════════════════════════════════════════════════════
#  DETUNED DRONE PAD
#  3 микро-расстроенных несущих → хорус, "дышащий" объём.
#  Детюнинг ±0.07 – 0.22 Hz создаёт медленные амплитудные биения
#  внутри самого дрона (независимо от бинауральных биений).
# ══════════════════════════════════════════════════════════

def detuned_drone(dur_s: float, carrier: float,
                  detune_hz: float = 0.15,
                  vol: float = 0.14,
                  ctype: str = 'warm',
                  seed: int = 0) -> np.ndarray:
    """
    3-voice detuned pad: carrier-Δ, carrier, carrier+Δ.
    Returns mono signal (add to both L and R for pad bed).
    """
    n   = int(dur_s * SR)
    t   = np.arange(n, dtype=np.float64) / SR
    # Микро-LFO на самом детюнинге (0.005 Hz) → живое дыхание
    lfo_d = 0.003 * np.sin(2*np.pi*0.005*t + seed)
    freqs = [carrier - detune_hz - lfo_d*0.5,
             carrier,
             carrier + detune_hz + lfo_d*0.5]
    out = np.zeros(n, np.float64)
    vols = [0.38, 0.46, 0.38]
    for f_arr, v in zip(freqs, vols):
        if isinstance(f_arr, np.ndarray):
            ph = 2*np.pi * np.cumsum(f_arr) / SR
        else:
            ph = 2*np.pi * f_arr * t
        out += v * _apply_carrier_type(ph, ctype)
    out /= (np.max(np.abs(out)) + 1e-9)
    return (out * vol).astype(np.float32)


# ══════════════════════════════════════════════════════════
#  RESONANT WIND PAD
#  Розовый шум → узкополосный полосовой фильтр на несущей.
#  Результат: "поющий ветер" / "гул чаши" гармонирующий с биением.
# ══════════════════════════════════════════════════════════

def resonant_wind_pad(dur_s: float, carrier: float,
                      bw_hz: float = 18.0,
                      vol: float = 0.08,
                      seed: int = 0) -> np.ndarray:
    """
    Narrow BP filter centered on carrier frequency.
    bw_hz: -3dB bandwidth (wider = airier, narrower = more tonal)
    """
    n    = int(dur_s * SR)
    nyq  = SR / 2.0
    lo   = max(10.0, carrier - bw_hz/2) / nyq
    hi   = min(0.499, (carrier + bw_hz/2) / nyq)
    # 4th-order Butterworth bandpass
    sos  = butter(4, [lo, hi], btype='band', output='sos')
    raw  = pink_noise(n, seed)
    filt = sosfilt(sos, raw).astype(np.float32)
    peak = np.max(np.abs(filt)) + 1e-9
    # LFO-volume (0.05 Hz) → звук "дышит"
    t    = np.arange(n, dtype=np.float32) / SR
    lfo  = 0.7 + 0.3 * np.sin(2*np.pi*0.05*t + seed*0.9)
    return (filt / peak * vol * lfo)


# ══════════════════════════════════════════════════════════
#  LFO FILTER SWEEP  (Organic Breathing on binaural signal)
#  Медленно (0.04-0.07 Hz) перемещает LP cutoff → живой, тёплый
# ══════════════════════════════════════════════════════════

def lfo_filter(signal: np.ndarray,
               fc_center: float = 900.0,
               fc_depth: float  = 400.0,
               lfo_hz: float    = 0.05,
               seed: int        = 0) -> np.ndarray:
    """
    Time-varying LP via frame-based processing (frame = 512 samples).
    fc oscillates fc_center ± fc_depth at lfo_hz.
    """
    n       = len(signal)
    frame   = 512
    nyq     = SR / 2.0
    out     = np.zeros(n, np.float32)
    t_frame = np.arange(0, n, frame, dtype=np.float64) / SR
    zi      = np.zeros(2)

    for i, t0 in enumerate(t_frame):
        f0 = i * frame
        f1 = min(f0 + frame, n)
        # Instantaneous cutoff
        lfo_val = np.sin(2*np.pi*lfo_hz*t0 + seed*0.7)
        fc  = np.clip(fc_center + fc_depth*lfo_val, 80.0, nyq*0.97)
        b, a = butter(2, fc/nyq, btype='low')
        seg, zi_new = lfilter(b, a, signal[f0:f1], zi=zi)
        out[f0:f1] = seg.astype(np.float32)
        zi = zi_new

    return out


# ══════════════════════════════════════════════════════════
#  DUAL BINAURAL
# ══════════════════════════════════════════════════════════

def dual_binaural(dur_s, c0, c1, b0, b1,
                  vol_p=0.60, vol_s=0.22,
                  carrier_jitter=2.0, beat_jitter=0.15,
                  seed=0, beat_array=None,
                  carrier_type='sine'):
    n  = int(dur_s * SR)
    C  = build_carrier(c0, c1, n, carrier_jitter, seed)
    B  = (np.asarray(beat_array[:n], dtype=np.float64) if beat_array is not None
          else jitter_envelope(log_sweep(b0, b1, n), beat_jitter, seed+50))
    B2 = B / 2.0
    pL  = 2*np.pi*np.cumsum(C)          / SR
    pR  = 2*np.pi*np.cumsum(C+B)        / SR
    pL2 = 2*np.pi*np.cumsum(C*2.0)      / SR
    pR2 = 2*np.pi*np.cumsum(C*2.0+B2)   / SR
    L = (_apply_carrier_type(pL,  carrier_type)*vol_p
       + _apply_carrier_type(pL2, carrier_type)*vol_s).astype(np.float32)
    R = (_apply_carrier_type(pR,  carrier_type)*vol_p
       + _apply_carrier_type(pR2, carrier_type)*vol_s).astype(np.float32)
    return L, R


# ══════════════════════════════════════════════════════════
#  ISOCHRONIC
# ══════════════════════════════════════════════════════════

def isochronic(dur_s, freq, carrier=200.0, vol=0.14,
               attack_s=4.0, decay_s=4.0, carrier_type='sine'):
    if freq <= 0:
        return np.zeros(int(dur_s*SR), dtype=np.float32)
    n   = int(dur_s*SR)
    t   = np.arange(n, dtype=np.float64) / SR
    gate = (np.sin(2*np.pi*freq*t) >= 0).astype(np.float32)
    rn   = int(0.006*SR)
    if rn > 1:
        h = np.hanning(rn*2).astype(np.float32); h /= h.sum()
        gate = np.convolve(gate, h, mode='same')
    env = np.ones(n, np.float32)
    atk = min(int(attack_s*SR), n//3)
    dec = min(int(decay_s*SR),  n//3)
    if atk: env[:atk]  *= np.linspace(0,1,atk,np.float32)
    if dec: env[-dec:] *= np.linspace(1,0,dec,np.float32)
    tone = _apply_carrier_type(2*np.pi*carrier*t, carrier_type)
    return (tone * gate * env * vol).astype(np.float32)


def apply_cfc(gamma_sig, dur_s, theta_freq=6.0, strength=0.5):
    n   = len(gamma_sig)
    t   = np.arange(n, dtype=np.float64) / SR
    env = 1.0-strength+strength*(0.5+0.5*np.sin(2*np.pi*theta_freq*t))
    return (gamma_sig * env.astype(np.float32))


def assr_80hz(dur_s, carrier=200.0, vol=0.05):
    return isochronic(dur_s, 80.0, carrier, vol, attack_s=6.0, decay_s=6.0)


def schumann_stack(dur_s, carrier=432.0, base_vol=0.20, seed=0, carrier_type='warm'):
    n = int(dur_s*SR)
    L = np.zeros(n, np.float32); R = np.zeros(n, np.float32)
    for i, freq in enumerate(SCHUMANN):
        v = base_vol * (0.70**i)
        lv, rv = dual_binaural(dur_s, carrier, carrier, freq, freq,
                               vol_p=v, vol_s=v*0.25,
                               carrier_jitter=0.3, beat_jitter=0.05,
                               seed=seed+i*10, carrier_type=carrier_type)
        L += lv; R += rv
    return L, R


# ══════════════════════════════════════════════════════════
#  3D SPATIAL — azimuth + elevation Lissajous orbit
# ══════════════════════════════════════════════════════════

def spatial_rotation(L, R, period_s=12.0):
    """2D horizontal ITD rotation."""
    n   = len(L)
    t   = np.arange(n, dtype=np.float64) / SR
    c   = np.cos(2*np.pi*t/period_s).astype(np.float32)
    s   = np.sin(2*np.pi*t/period_s).astype(np.float32)
    return L*c - R*s, L*s + R*c


def spatial_rotation_3d(L, R, az_period=12.0, el_period=29.0, el_depth=0.35):
    """
    3D orbital: azimuth circle + elevation sine, prime-ratio periods.
    Lissajous trajectory → non-repeating spatial path per session.
    El cue via amplitude asymmetry: engages parietal/vestibular for OBE.
    """
    n   = len(L)
    t   = np.arange(n, dtype=np.float64) / SR
    az  = 2*np.pi*t/az_period
    Laz = (L*np.cos(az) - R*np.sin(az)).astype(np.float32)
    Raz = (L*np.sin(az) + R*np.cos(az)).astype(np.float32)
    el        = el_depth * np.sin(2*np.pi*t/el_period + np.pi/3).astype(np.float32)
    el_gain   = (1.0 + 0.18*el).astype(np.float32)
    el_spread = np.clip(1.0 - 0.10*el, 0.70, 1.30).astype(np.float32)
    return (Laz*el_gain*el_spread), (Raz*el_gain/el_spread)


# ══════════════════════════════════════════════════════════
#  INFRA-MODULATION
# ══════════════════════════════════════════════════════════

def infra_modulate(L, R, freq_hz=0.067, depth=0.15, phase_offset=0.0):
    n   = len(L)
    t   = np.arange(n, dtype=np.float64) / SR
    mod = (1.0-depth+depth*np.sin(2*np.pi*freq_hz*t+phase_offset)).astype(np.float32)
    return L*mod, R*mod


# ══════════════════════════════════════════════════════════
#  PATTERN BREAK
# ══════════════════════════════════════════════════════════

def pattern_break(carrier=432.0, carrier_type='sine'):
    L, R = dual_binaural(20.0, carrier, carrier, 10.0, 10.0,
                         vol_p=0.40, vol_s=0.12,
                         carrier_jitter=0.0, beat_jitter=0.0,
                         seed=999, carrier_type='sine')
    rn   = int(3*SR)
    ramp = np.linspace(0,1,rn,np.float32)
    L[:rn]*=ramp; R[:rn]*=ramp
    L[-rn:]*=ramp[::-1]; R[-rn:]*=ramp[::-1]
    return L, R
