import numpy as np
from scipy.signal import lfilter, iirfilter, sosfilt, butter, fftconvolve
from .core import SR, log_sweep, jitter_envelope, build_carrier, pink_noise

SCHUMANN = [7.83, 14.3, 20.8, 27.3, 33.8]

# Aggressively attenuated taper for Schumann resonances 3-5.
# OLD: 0.70^i  → [1.0, 0.70, 0.49, 0.34, 0.24]  (20-33Hz at 24-49% = audible tremolo/squeal)
# NEW: [1.0, 0.45, 0.12, 0.04, 0.01]              (20-33Hz at 1-12% = subliminal only)
_SCHUMANN_TAPER = [1.0, 0.45, 0.12, 0.04, 0.01]


# ══════════════════════════════════════════════════════════
#  CARRIER SYNTHESIS
# ══════════════════════════════════════════════════════════

def _apply_carrier_type(phase: np.ndarray, ctype: str) -> np.ndarray:
    if ctype == 'warm':
        return np.sin(phase + 0.28 * np.sin(1.5 * phase)).astype(np.float32)
    elif ctype == 'rich':
        s = (0.600 * np.sin(phase)   + 0.240 * np.sin(2 * phase)
           + 0.100 * np.sin(3 * phase) + 0.040 * np.sin(4 * phase)
           + 0.020 * np.sin(5 * phase))
        return s.astype(np.float32)
    elif ctype == 'soft':
        return (0.88 * np.sin(phase) + 0.10 * np.sin(2 * phase)
              + 0.02 * np.sin(3 * phase)).astype(np.float32)
    elif ctype == 'organ':
        return (0.55 * np.sin(phase)   + 0.30 * np.sin(2 * phase)
              + 0.12 * np.sin(3 * phase) + 0.03 * np.sin(4 * phase)).astype(np.float32)
    else:
        return np.sin(phase).astype(np.float32)


# ══════════════════════════════════════════════════════════
#  TUBE SATURATION
# ══════════════════════════════════════════════════════════

def tube_saturate(sig: np.ndarray, drive: float = 0.10) -> np.ndarray:
    drive = float(np.clip(drive, 0.01, 0.40))
    k     = float(np.tan(np.pi * drive / 2.0))
    ak    = float(np.arctan(k))
    return (np.arctan(sig.astype(np.float64) * k) / ak).astype(np.float32)


# ══════════════════════════════════════════════════════════
#  COMFORT FILTER  — мастеринговый EQ для премиум звучания
#
#  Трёхполосный split: Low | Mid | High — раздельное усиление.
#  Low shelf  +1.5 dB @ 100 Hz  → тепло, тело, глубина.
#  High shelf −2.5 dB @ 7.5 kHz → шёлк, снижение усталости слуха.
#  Применять: SLEEP, HEALER, ORACLE блоки после нормализации.
#  Не применять к WARRIOR — там нужна острота gamma.
# ══════════════════════════════════════════════════════════

def comfort_filter(L: np.ndarray, R: np.ndarray,
                   low_hz:  float = 100.0,
                   low_db:  float = 1.5,
                   high_hz: float = 7500.0,
                   high_db: float = -2.5) -> tuple:
    """
    Mastering EQ: warm low shelf + gentle high-frequency silk.
    3-band split: Lo / Mid / Hi — individual gain per band — recombine.
    Preserves binaural phase: gain is linear (no phase shift added).
    """
    nyq   = SR / 2.0
    A_low = 10 ** (low_db  / 20.0)   # 1.188 = boost
    A_hi  = 10 ** (high_db / 20.0)   # 0.749 = cut
    w_lo  = np.clip(low_hz  / nyq, 0.001, 0.499)
    w_hi  = np.clip(high_hz / nyq, 0.001, 0.499)
    sos_lo = butter(1, w_lo, btype='low',  output='sos')
    sos_hi = butter(1, w_hi, btype='high', output='sos')
    out = []
    for sig in (L, R):
        s   = sig.astype(np.float64)
        lo  = sosfilt(sos_lo, s)
        hi  = sosfilt(sos_hi, s)
        mid = s - lo - hi
        out.append((lo * A_low + mid + hi * A_hi).astype(np.float32))
    return out[0], out[1]


# ══════════════════════════════════════════════════════════
#  FORMANT RESONATOR
# ══════════════════════════════════════════════════════════

def formant_resonator(sig: np.ndarray, intensity: float = 0.25) -> np.ndarray:
    nyq = SR / 2.0
    out = sig.astype(np.float32)
    for f_center, bw, gain in [
        (700.0,  160.0, 0.38),
        (1200.0, 200.0, 0.26),
        (2500.0, 320.0, 0.14),
    ]:
        lo   = max(0.01, (f_center - bw / 2) / nyq)
        hi   = min(0.499, (f_center + bw / 2) / nyq)
        if lo >= hi:
            continue
        sos  = butter(2, [lo, hi], btype='band', output='sos')
        res  = sosfilt(sos, sig).astype(np.float32)
        out += res * gain * intensity
    return out


# ══════════════════════════════════════════════════════════
#  SYNTHETIC ROOM REVERB
# ══════════════════════════════════════════════════════════

def room_reverb(L: np.ndarray, R: np.ndarray,
                rt60_ms: float = 700.0,
                wet: float     = 0.10) -> tuple:
    ir_n = max(64, int(rt60_ms * 0.001 * SR))
    t_ir = np.arange(ir_n, dtype=np.float64) / SR
    decay = np.exp(-6.91 * t_ir / (rt60_ms * 0.001)).astype(np.float32)
    ir    = decay.copy()
    for d_ms, g in [(8, 0.45), (17, 0.30), (31, 0.18)]:
        d = int(d_ms * 0.001 * SR)
        if d < ir_n:
            ir[d] += g
    ir /= (np.max(np.abs(ir)) + 1e-9)
    revL = fftconvolve(L.astype(np.float64),
                       ir.astype(np.float64))[:len(L)].astype(np.float32)
    revR = fftconvolve(R.astype(np.float64),
                       ir[::-1].astype(np.float64))[:len(R)].astype(np.float32)
    return (L + revL * wet).astype(np.float32), (R + revR * wet).astype(np.float32)


# ══════════════════════════════════════════════════════════
#  MONAURAL BEAT LAYER
# ══════════════════════════════════════════════════════════

def monaural_beat_layer(dur_s: float, carrier: float,
                        beat_freq: float,
                        vol: float = 0.05,
                        ctype: str = 'warm',
                        seed: int  = 0) -> np.ndarray:
    n  = int(dur_s * SR)
    t  = np.arange(n, dtype=np.float64) / SR
    ph = 2.0 * np.pi * carrier * t
    carrier_sig = _apply_carrier_type(ph, ctype).astype(np.float64)
    am  = 0.5 + 0.5 * np.cos(2.0 * np.pi * beat_freq * t)
    env = np.ones(n, np.float32)
    rn  = min(int(8.0 * SR), n // 4)
    if rn > 1:
        env[:rn]  = np.linspace(0.0, 1.0, rn)
        env[-rn:] = np.linspace(1.0, 0.0, rn)
    return (carrier_sig * am * env * vol).astype(np.float32)


# ══════════════════════════════════════════════════════════
#  RESPIRATORY ENTRAINMENT
# ══════════════════════════════════════════════════════════

def respiratory_entrainment_mod(dur_s: float,
                                breath_bpm: float = 6.0,
                                depth: float      = 0.15) -> np.ndarray:
    n    = int(dur_s * SR)
    t    = np.arange(n, dtype=np.float64) / SR
    freq = breath_bpm / 60.0
    phase = 2.0 * np.pi * freq * t
    raw   = 0.5 + 0.5 * np.sin(phase - np.pi / 2)
    asym  = np.where(raw > 0.5,
                     0.5 + (raw - 0.5) * 1.20,
                     raw * 0.80)
    asym  = np.clip(asym, 0.0, 1.0).astype(np.float32)
    return (1.0 - depth + depth * asym).astype(np.float32)


# ══════════════════════════════════════════════════════════
#  DETUNED DRONE PAD
# ══════════════════════════════════════════════════════════

def detuned_drone(dur_s: float, carrier: float,
                  detune_hz: float = 0.15,
                  vol: float       = 0.14,
                  ctype: str       = 'warm',
                  seed: int        = 0) -> np.ndarray:
    n     = int(dur_s * SR)
    t     = np.arange(n, dtype=np.float64) / SR
    lfo_d = 0.003 * np.sin(2 * np.pi * 0.005 * t + seed)
    freqs = [carrier - detune_hz - lfo_d * 0.5,
             carrier,
             carrier + detune_hz + lfo_d * 0.5]
    out   = np.zeros(n, np.float64)
    vols  = [0.38, 0.46, 0.38]
    for f_arr, v in zip(freqs, vols):
        if isinstance(f_arr, np.ndarray):
            ph = 2 * np.pi * np.cumsum(f_arr) / SR
        else:
            ph = 2 * np.pi * f_arr * t
        out += v * _apply_carrier_type(ph, ctype)
    out /= (np.max(np.abs(out)) + 1e-9)
    return (out * vol).astype(np.float32)


# ══════════════════════════════════════════════════════════
#  RESONANT WIND PAD
# ══════════════════════════════════════════════════════════

def resonant_wind_pad(dur_s: float, carrier: float,
                      bw_hz: float = 18.0,
                      vol: float   = 0.08,
                      seed: int    = 0) -> np.ndarray:
    n   = int(dur_s * SR)
    nyq = SR / 2.0
    lo  = max(10.0, carrier - bw_hz / 2) / nyq
    hi  = min(0.499, (carrier + bw_hz / 2) / nyq)
    sos = butter(4, [lo, hi], btype='band', output='sos')
    raw = pink_noise(n, seed)
    flt = sosfilt(sos, raw).astype(np.float32)
    peak = np.max(np.abs(flt)) + 1e-9
    t   = np.arange(n, dtype=np.float32) / SR
    lfo = 0.7 + 0.3 * np.sin(2 * np.pi * 0.05 * t + seed * 0.9)
    return (flt / peak * vol * lfo)


# ══════════════════════════════════════════════════════════
#  LFO FILTER SWEEP
# ══════════════════════════════════════════════════════════

def lfo_filter(signal: np.ndarray,
               fc_center: float = 900.0,
               fc_depth: float  = 400.0,
               lfo_hz: float    = 0.05,
               seed: int        = 0) -> np.ndarray:
    n      = len(signal)
    frame  = 512
    nyq    = SR / 2.0
    out    = np.zeros(n, np.float32)
    t_fr   = np.arange(0, n, frame, dtype=np.float64) / SR
    zi     = np.zeros(2)
    for i, t0 in enumerate(t_fr):
        f0 = i * frame
        f1 = min(f0 + frame, n)
        fc = np.clip(fc_center + fc_depth * np.sin(2 * np.pi * lfo_hz * t0 + seed * 0.7),
                     80.0, nyq * 0.97)
        b, a = butter(2, fc / nyq, btype='low')
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
          else jitter_envelope(log_sweep(b0, b1, n), beat_jitter, seed + 50))
    B2 = B / 2.0
    pL  = 2 * np.pi * np.cumsum(C)       / SR
    pR  = 2 * np.pi * np.cumsum(C + B)   / SR
    pL2 = 2 * np.pi * np.cumsum(C * 2.0) / SR
    pR2 = 2 * np.pi * np.cumsum(C * 2.0 + B2) / SR
    L = (_apply_carrier_type(pL,  carrier_type) * vol_p
       + _apply_carrier_type(pL2, carrier_type) * vol_s).astype(np.float32)
    R = (_apply_carrier_type(pR,  carrier_type) * vol_p
       + _apply_carrier_type(pR2, carrier_type) * vol_s).astype(np.float32)
    return L, R


# ══════════════════════════════════════════════════════════
#  ISOCHRONIC
#
#  FIX: адаптивное сглаживание gate по частоте.
#  Старое: 6ms для всех — при 40 Hz период=25ms, полупериод=12.5ms,
#          6ms window < 50% half-period → клики/buzz слышимы.
#  Новое:  18ms для gamma (≥30 Hz) — полностью покрывает gate edge,
#          12ms для beta (15-30 Hz), 8ms для alpha/theta.
# ══════════════════════════════════════════════════════════

def isochronic(dur_s, freq, carrier=200.0, vol=0.14,
               attack_s=4.0, decay_s=4.0, carrier_type='sine'):
    if freq <= 0:
        return np.zeros(int(dur_s * SR), dtype=np.float32)
    n    = int(dur_s * SR)
    t    = np.arange(n, dtype=np.float64) / SR
    gate = (np.sin(2 * np.pi * freq * t) >= 0).astype(np.float32)

    # Adaptive gate smoothing — eliminates harsh buzzing from fast gates
    if freq >= 30.0:
        rn = int(0.018 * SR)   # 18ms: gamma (period=25ms, covers full transition)
    elif freq >= 15.0:
        rn = int(0.012 * SR)   # 12ms: beta
    else:
        rn = int(0.008 * SR)   # 8ms:  alpha/theta

    if rn > 1:
        h = np.hanning(rn * 2).astype(np.float32); h /= h.sum()
        gate = np.convolve(gate, h, mode='same')
    env = np.ones(n, np.float32)
    atk = min(int(attack_s * SR), n // 3)
    dec = min(int(decay_s * SR),  n // 3)
    if atk: env[:atk]  *= np.linspace(0, 1, atk, np.float32)
    if dec: env[-dec:] *= np.linspace(1, 0, dec, np.float32)
    tone = _apply_carrier_type(2 * np.pi * carrier * t, carrier_type)
    return (tone * gate * env * vol).astype(np.float32)


def apply_cfc(gamma_sig, dur_s, theta_freq=6.0, strength=0.5):
    n   = len(gamma_sig)
    t   = np.arange(n, dtype=np.float64) / SR
    env = 1.0 - strength + strength * (0.5 - 0.5 * np.sin(2 * np.pi * theta_freq * t))
    return (gamma_sig * env.astype(np.float32))


def assr_80hz(dur_s, carrier=200.0, vol=0.05):
    return isochronic(dur_s, 80.0, carrier, vol, attack_s=6.0, decay_s=6.0)


# ══════════════════════════════════════════════════════════
#  SCHUMANN STACK
#
#  FIX: тейпер 0.70^i → _SCHUMANN_TAPER
#  Резонансы 3-5 (20.8-33.8 Hz) теперь подпороговые.
#  Voздействие сохраняется, слышимый tremolo/squeal устранён.
# ══════════════════════════════════════════════════════════

def schumann_stack(dur_s, carrier=432.0, base_vol=0.20, seed=0, carrier_type='warm'):
    n = int(dur_s * SR)
    L = np.zeros(n, np.float32); R = np.zeros(n, np.float32)
    for i, freq in enumerate(SCHUMANN):
        v = base_vol * _SCHUMANN_TAPER[i]
        lv, rv = dual_binaural(dur_s, carrier, carrier, freq, freq,
                               vol_p=v, vol_s=v * 0.25,
                               carrier_jitter=0.3, beat_jitter=0.05,
                               seed=seed + i * 10, carrier_type=carrier_type)
        L += lv; R += rv
    return L, R


# ══════════════════════════════════════════════════════════
#  3D SPATIAL
# ══════════════════════════════════════════════════════════

def spatial_rotation(L, R, period_s=12.0):
    n = len(L)
    t = np.arange(n, dtype=np.float64) / SR
    c = np.cos(2 * np.pi * t / period_s).astype(np.float32)
    s = np.sin(2 * np.pi * t / period_s).astype(np.float32)
    return L * c - R * s, L * s + R * c


def spatial_rotation_3d(L, R, az_period=12.0, el_period=29.0, el_depth=0.35):
    n  = len(L)
    t  = np.arange(n, dtype=np.float64) / SR
    az = 2 * np.pi * t / az_period
    Laz = (L * np.cos(az) - R * np.sin(az)).astype(np.float32)
    Raz = (L * np.sin(az) + R * np.cos(az)).astype(np.float32)
    el       = el_depth * np.sin(2 * np.pi * t / el_period + np.pi / 3).astype(np.float32)
    el_gain  = (1.0 + 0.18 * el).astype(np.float32)
    el_spread = np.clip(1.0 - 0.10 * el, 0.70, 1.30).astype(np.float32)
    return (Laz * el_gain * el_spread), (Raz * el_gain / el_spread)


# ══════════════════════════════════════════════════════════
#  INFRA-MODULATION
# ══════════════════════════════════════════════════════════

def infra_modulate(L, R, freq_hz=0.067, depth=0.15, phase_offset=0.0):
    n   = len(L)
    t   = np.arange(n, dtype=np.float64) / SR
    mod = (1.0 - depth + depth * np.sin(2 * np.pi * freq_hz * t + phase_offset)).astype(np.float32)
    return L * mod, R * mod


# ══════════════════════════════════════════════════════════
#  AMBIENT BRIDGE  — замена pattern_break
#
#  Проблема pattern_break (v_old):
#    vol_p=0.40 чистый синус, 10Hz биение, carrier_type='sine' всегда.
#    = тест-тон. В SLEEP: 4 раза за сессию = звук рвётся.
#
#  Решение: ultra-тихий органический мост.
#    Drone + wind при несущей блока, 0.5Hz биение (sub-perceptual),
#    -18 dBFS = присутствие без внимания, 7s fade = нет "click".
# ══════════════════════════════════════════════════════════

def ambient_bridge(carrier: float = 432.0,
                   carrier_type: str = 'soft',
                   dur_s: float = 20.0,
                   seed: int = 42) -> tuple:
    """
    Premium organic bridge between session phases.
    Maintains continuity without drawing conscious attention.
    """
    # Sub-perceptual binaural: 0.5 Hz pulse — one slow breath, not a beat
    L, R = dual_binaural(dur_s, carrier, carrier, 0.5, 0.5,
                         vol_p=0.07, vol_s=0.02,
                         carrier_jitter=1.2, beat_jitter=0.0,
                         seed=seed, carrier_type='soft')
    # Detuned drone: familiar warmth at session's carrier frequency
    pad = detuned_drone(dur_s, carrier, detune_hz=0.18, vol=0.10,
                        ctype='soft', seed=seed + 100)
    L += pad; R += pad
    # Wind: familiar texture, prevents absolute silence
    wind = resonant_wind_pad(dur_s, carrier, bw_hz=22.0, vol=0.07, seed=seed + 200)
    L += wind; R += wind
    # -18 dBFS master level: audible but dissolves into background
    pk    = max(np.max(np.abs(L)), np.max(np.abs(R))) + 1e-9
    scale = min(0.126 / pk, 1.0)
    L     = (L * scale).astype(np.float32)
    R     = (R * scale).astype(np.float32)
    # 7s gradual fade — no perceptible start/stop boundary
    fn   = min(int(7.0 * SR), len(L) // 3)
    ramp = np.linspace(0.0, 1.0, fn, dtype=np.float32)
    L[:fn]  *= ramp;         R[:fn]  *= ramp
    L[-fn:] *= ramp[::-1];   R[-fn:] *= ramp[::-1]
    return L, R


def pattern_break(carrier=432.0, carrier_type='sine'):
    """Backward-compat alias → ambient_bridge."""
    return ambient_bridge(carrier=carrier, carrier_type='soft')


# ══════════════════════════════════════════════════════════
#  FFR PRIME BURST
# ══════════════════════════════════════════════════════════

def ffr_prime_burst(carrier: float = 200.0,
                    carrier_type: str = 'warm',
                    dur_s: float = 18.0) -> tuple:
    iso = isochronic(dur_s, 40.0, carrier, vol=0.10,
                     attack_s=4.0, decay_s=5.0, carrier_type=carrier_type)
    L_b, R_b = dual_binaural(dur_s, carrier, carrier, 40.0, 40.0,
                              vol_p=0.25, vol_s=0.08,
                              carrier_jitter=0.0, beat_jitter=0.0,
                              seed=7777, carrier_type=carrier_type)
    L = (L_b + iso).astype(np.float32)
    R = (R_b + iso).astype(np.float32)
    fn   = min(int(4 * SR), len(L) // 4)
    ramp = np.linspace(0, 1, fn, np.float32)
    L[:fn] *= ramp;  R[:fn] *= ramp
    L[-fn:] *= ramp[::-1]; R[-fn:] *= ramp[::-1]
    pk = max(np.max(np.abs(L)), np.max(np.abs(R))) + 1e-9
    if pk > 0.56:
        L = (L / pk * 0.50).astype(np.float32)
        R = (R / pk * 0.50).astype(np.float32)
    return L, R
