import numpy as np
from scipy.signal import lfilter, sosfilt, butter, oaconvolve
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

def tube_saturate(sig: np.ndarray, drive=0.10) -> np.ndarray:
    """Arctan soft-clip. `drive` may be a scalar OR a same-length ndarray
    (e.g. a _smooth_wander contour) for a slowly "breathing" warmth that
    mimics a tube stage's thermal drift — still one vectorized arctan
    pass, identical cost to the scalar case."""
    d  = np.clip(np.asarray(drive, dtype=np.float64), 0.01, 0.40)
    k  = np.tan(np.pi * d / 2.0)
    ak = np.arctan(k)
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

# ══════════════════════════════════════════════════════════
#  FORMANT RESONATOR — vowel presets (bija-inspired)
#  Symbolic / intentional timbre layer — not physiology.
# ══════════════════════════════════════════════════════════

VOWEL_FORMANTS = {
    # (f_center_hz, bandwidth_hz, relative_gain)
    'A': [(700.0, 160.0, 0.38), (1200.0, 200.0, 0.26), (2500.0, 280.0, 0.10)],
    'O': [(500.0, 140.0, 0.40), (900.0,  180.0, 0.24), (2400.0, 260.0, 0.09)],
    'U': [(320.0, 120.0, 0.42), (800.0,  160.0, 0.20), (2200.0, 240.0, 0.08)],
    'E': [(480.0, 140.0, 0.36), (1800.0, 220.0, 0.22), (2500.0, 260.0, 0.09)],
    'M': [(250.0, 100.0, 0.45), (1000.0, 120.0, 0.14), (1800.0, 200.0, 0.06)],
}


def _formant_bank(sig: np.ndarray, bands, intensity: float) -> np.ndarray:
    nyq = SR / 2.0
    out = sig.astype(np.float32).copy()
    for f_center, bw, gain in bands:
        lo = max(0.01, (f_center - bw / 2) / nyq)
        hi = min(0.499, (f_center + bw / 2) / nyq)
        if lo >= hi:
            continue
        sos = butter(2, [lo, hi], btype='band', output='sos')
        res = sosfilt(sos, sig).astype(np.float32)
        out += res * gain * intensity
    return out


def formant_resonator(sig: np.ndarray, intensity: float = 0.25,
                      vowel: str = 'A',
                      morph_vowel: str = None,
                      morph_s: float = 0.0) -> np.ndarray:
    """
    Vocal formant bank. Optional end-of-block morph (e.g. A→U→M / AUM).
    F3 gains kept conservative to avoid whistle/sizzle.
    """
    v0 = vowel.upper() if vowel else 'A'
    bands0 = VOWEL_FORMANTS.get(v0, VOWEL_FORMANTS['A'])
    if not morph_vowel or morph_s <= 0:
        return _formant_bank(sig, bands0, intensity)

    v1 = morph_vowel.upper()
    bands1 = VOWEL_FORMANTS.get(v1, bands0)
    n = len(sig)
    mn = min(int(morph_s * SR), n // 2)
    if mn < 8:
        return _formant_bank(sig, bands0, intensity)

    a = _formant_bank(sig, bands0, intensity)
    b = _formant_bank(sig, bands1, intensity)
    out = a.copy()
    # Morph only the tail
    w = np.linspace(0.0, 1.0, mn, dtype=np.float32)
    out[-mn:] = (a[-mn:] * (1.0 - w) + b[-mn:] * w).astype(np.float32)
    return out


def silk_lowpass(sig: np.ndarray, cutoff_hz: float = 5200.0) -> np.ndarray:
    """Gentle anti-sizzle LP — removes piercing HF without killing warmth."""
    nyq = SR / 2.0
    w = np.clip(cutoff_hz / nyq, 0.01, 0.49)
    sos = butter(2, w, btype='low', output='sos')
    return sosfilt(sos, sig.astype(np.float64)).astype(np.float32)


def comfort_filter(L: np.ndarray, R: np.ndarray,
                   low_hz:  float = 100.0,
                   low_db:  float = 1.5,
                   high_hz: float = 6500.0,
                   high_db: float = -3.5,
                   spectral_tilt: bool = True) -> tuple:
    """
    Mastering EQ: warm low shelf + stronger high silk (anti-whistle).
    high_db default −3.5 @ 6.5 kHz (was −2.5 @ 7.5) for permanent listening.
    spectral_tilt=True adds gentle −0.5 dB/oct gradient (200 Hz–4 kHz) for analog warmth.
    """
    nyq   = SR / 2.0
    A_low = 10 ** (low_db  / 20.0)
    A_hi  = 10 ** (high_db / 20.0)
    w_lo  = np.clip(low_hz  / nyq, 0.001, 0.499)
    w_hi  = np.clip(high_hz / nyq, 0.001, 0.499)
    sos_lo = butter(1, w_lo, btype='low',  output='sos')
    sos_hi = butter(1, w_hi, btype='high', output='sos')

    # Spectral tilt shelf (200 Hz–4 kHz) for analog character
    tilt_sos = None
    if spectral_tilt:
        # −0.5 dB/oct from 200 Hz to 4 kHz = ~−2.15 dB total across 4.3 octaves
        tilt_db = -2.15
        A_tilt = 10 ** (tilt_db / 20.0)
        w_tilt = np.clip(200.0 / nyq, 0.001, 0.499)
        tilt_sos = butter(1, w_tilt, btype='high', output='sos')

    out = []
    for sig in (L, R):
        s   = sig.astype(np.float64)
        lo  = sosfilt(sos_lo, s)
        hi  = sosfilt(sos_hi, s)
        mid = s - lo - hi

        if tilt_sos is not None:
            tilt_hi = sosfilt(tilt_sos, s)
            tilt_lo = s - tilt_hi
            s = tilt_lo + tilt_hi * A_tilt

        out.append((lo * A_low + mid + hi * A_hi).astype(np.float32))
    return out[0], out[1]


# ══════════════════════════════════════════════════════════
#  SYNTHETIC ROOM REVERB
# ══════════════════════════════════════════════════════════

def _synth_room_ir(ir_n: int, t_ir: np.ndarray, rt60_ms: float,
                   taps, jitter: float = 0.0, seed: int = 0) -> np.ndarray:
    """Schroeder-style synthetic IR: exp decay + sparse early reflections.
    jitter>0 perturbs tap delay/gain deterministically (per seed) — used to
    generate a *second*, independently-seeded IR rather than time-reversing
    the first (see room_reverb docstring)."""
    decay = np.exp(-6.91 * t_ir / (rt60_ms * 0.001)).astype(np.float32)
    ir = decay.copy()
    rng = np.random.RandomState(int(seed) & 0xFFFFFFFF) if jitter > 0 else None
    for d_ms, g in taps:
        if rng is not None:
            d_ms = d_ms * (1.0 + jitter * float(rng.uniform(-1.0, 1.0)))
            g    = g    * (1.0 + jitter * float(rng.uniform(-1.0, 1.0)))
        d = int(d_ms * 0.001 * SR)
        if 0 <= d < ir_n:
            ir[d] += g
    ir /= (np.max(np.abs(ir)) + 1e-9)
    return ir


def room_reverb(L: np.ndarray, R: np.ndarray,
                rt60_ms: float = 700.0,
                wet: float     = 0.10,
                seed: int      = 0) -> tuple:
    """
    Synthetic room IR (decay + 3 early reflections), convolved per channel.

    L and R use two INDEPENDENTLY-seeded IRs (same rt60/tap recipe, small
    jitter) instead of the old ir[::-1] trick for R. A time-reversed decay
    curve is physically backwards — its energy *rises* across the IR and
    relocates the strongest early reflection (was +8ms) to the tail — so
    the previous R channel had an inverted, unnatural decay shape. Two
    forward-decaying, independently-jittered IRs cost the same one extra
    fftconvolve and are a genuinely closer analogue to how two ears
    receive correlated-but-not-identical room reflections.
    """
    ir_n = max(64, int(rt60_ms * 0.001 * SR))
    t_ir = np.arange(ir_n, dtype=np.float64) / SR
    taps = [(8, 0.45), (17, 0.30), (31, 0.18)]
    ir_L = _synth_room_ir(ir_n, t_ir, rt60_ms, taps, jitter=0.0, seed=seed)
    ir_R = _synth_room_ir(ir_n, t_ir, rt60_ms, taps, jitter=0.12, seed=seed + 97)
    revL = oaconvolve(L.astype(np.float64),
                       ir_L.astype(np.float64))[:len(L)].astype(np.float32)
    revR = oaconvolve(R.astype(np.float64),
                       ir_R.astype(np.float64))[:len(R)].astype(np.float32)
    return (L + revL * wet).astype(np.float32), (R + revR * wet).astype(np.float32)


# ══════════════════════════════════════════════════════════
#  MONAURAL BEAT LAYER  — sweep-locked to binaural B_raw
# ══════════════════════════════════════════════════════════

def monaural_beat_layer(dur_s: float, carrier: float,
                        beat_freq: float = 0.0,
                        vol: float = 0.05,
                        ctype: str = 'warm',
                        seed: int  = 0,
                        beat_array=None) -> np.ndarray:
    """AM carrier locked to beat envelope (follows binaural sweep when beat_array set)."""
    n  = int(dur_s * SR)
    t  = np.arange(n, dtype=np.float64) / SR
    ph = 2.0 * np.pi * carrier * t
    carrier_sig = _apply_carrier_type(ph, ctype).astype(np.float64)
    if beat_array is not None:
        B = np.asarray(beat_array[:n], dtype=np.float64)
        if len(B) == 0:
            B = np.full(n, 7.0, dtype=np.float64)
        elif len(B) < n:
            B = np.pad(B, (0, n - len(B)), mode='edge')
        B = np.nan_to_num(B, nan=7.0)
        phase = 2.0 * np.pi * np.cumsum(B) / SR
        am = 0.5 + 0.5 * np.cos(phase)
    else:
        bf = beat_freq if beat_freq > 0 else 10.0
        am = 0.5 + 0.5 * np.cos(2.0 * np.pi * bf * t)
    env = np.ones(n, np.float32)
    rn  = min(int(8.0 * SR), n // 4)
    if rn > 1:
        env[:rn]  = np.linspace(0.0, 1.0, rn)
        env[-rn:] = np.linspace(1.0, 0.0, rn)
    return (carrier_sig * am * env * vol).astype(np.float32)


# ══════════════════════════════════════════════════════════
#  FOCUS MIX  — dual-frequency open-loop (Monroe-style F10 idea)
#  Body/delta-ish pair + cortex/alpha-beta pair, subliminal vols.
# ══════════════════════════════════════════════════════════

def focus_mix_layer(dur_s: float, carrier: float,
                    body_beat: float = 2.0,
                    cortex_beat: float = 10.0,
                    vol_body: float = 0.08,
                    vol_cortex: float = 0.06,
                    ctype: str = 'soft',
                    seed: int = 0) -> tuple:
    """Second binaural pair stack: body (low) + cortex (higher) Focus-style mix."""
    Lb, Rb = dual_binaural(dur_s, carrier, carrier, body_beat, body_beat,
                           vol_p=vol_body, vol_s=vol_body * 0.22,
                           carrier_jitter=0.8, beat_jitter=0.04,
                           seed=seed, carrier_type=ctype)
    Lc, Rc = dual_binaural(dur_s, carrier * 1.02, carrier * 1.02,
                           cortex_beat, cortex_beat,
                           vol_p=vol_cortex, vol_s=vol_cortex * 0.20,
                           carrier_jitter=0.6, beat_jitter=0.04,
                           seed=seed + 11, carrier_type=ctype)
    return (Lb + Lc).astype(np.float32), (Rb + Rc).astype(np.float32)


# ══════════════════════════════════════════════════════════
#  RESPIRATORY ENTRAINMENT  — ramp + 35:65 exhale bias
# ══════════════════════════════════════════════════════════

def respiratory_entrainment_mod(dur_s: float,
                                breath_bpm: float = 6.0,
                                depth: float      = 0.15,
                                breath_bpm_end: float = None,
                                use_golden_ratio: bool = False) -> np.ndarray:
    """
    Open-loop breathing AM. Optional linear bpm ramp (breath_bpm -> breath_bpm_end).
    Asymmetry ~35% inhale / 65% exhale for vagal bias.
    use_golden_ratio adds secondary LFO at PHI * breath_rate for fractal pattern.
    """
    PHI = 1.6180339887498948482
    n    = int(dur_s * SR)
    t    = np.arange(n, dtype=np.float64) / SR
    if breath_bpm_end is not None and abs(breath_bpm_end - breath_bpm) > 1e-6:
        bpm = np.linspace(breath_bpm, breath_bpm_end, n, dtype=np.float64)
        freq = bpm / 60.0
        phase = 2.0 * np.pi * np.cumsum(freq) / SR
    else:
        freq = breath_bpm / 60.0
        phase = 2.0 * np.pi * freq * t
    raw   = 0.5 + 0.5 * np.sin(phase - np.pi / 2)

    if use_golden_ratio:
        golden_freq = breath_bpm * PHI / 60.0
        golden_phase = 2.0 * np.pi * golden_freq * t
        raw = raw + 0.04 * np.sin(golden_phase)
        raw = np.clip(raw, 0.0, 1.0)

    asym  = np.where(raw > 0.5,
                     0.5 + (raw - 0.5) * 1.05,
                     raw * 0.70)
    asym  = np.clip(asym, 0.0, 1.0).astype(np.float32)
    return (1.0 - depth + depth * asym).astype(np.float32)


# ══════════════════════════════════════════════════════════
#  AM DEPTH BUDGET  — prevent stacked envelope pumping
# ══════════════════════════════════════════════════════════

def budget_am_depths(*depths: float, cap: float = 0.26) -> list:
    """Scale AM depths so sum(depths) <= cap while preserving ratios."""
    vals = [max(0.0, float(d)) for d in depths]
    total = sum(vals)
    if total <= cap or total < 1e-12:
        return vals
    scale = cap / total
    return [v * scale for v in vals]


def soft_ceiling(L: np.ndarray, R: np.ndarray,
                 ceiling: float = 0.50,
                 knee: float = 0.08) -> tuple:
    """
    Soft-knee peak ceiling (lookahead-free). Compresses peaks above (ceiling-knee)
    toward ceiling without hard clipping. Preserves relative L/R for binaural.
    """
    peak = max(float(np.max(np.abs(L))), float(np.max(np.abs(R)))) + 1e-9
    if peak <= ceiling - knee:
        return L.astype(np.float32), R.astype(np.float32)
    if peak <= ceiling:
        t = (peak - (ceiling - knee)) / knee
        target = peak - (peak - ceiling) * t * 0.5
        scale = target / peak
        return (L * scale).astype(np.float32), (R * scale).astype(np.float32)
    scale = (ceiling * 0.98) / peak
    return (L * scale).astype(np.float32), (R * scale).astype(np.float32)


# ══════════════════════════════════════════════════════════
#  UNDERBED — continuous pink/brown floor for session continuity
# ══════════════════════════════════════════════════════════

def underbed_noise(dur_s: float, vol: float = 0.018,
                   pink_w: float = 0.65, brown_w: float = 0.35,
                   seed: int = 0) -> tuple:
    """Quiet morph noise bed (~ -35 dBFS at vol=0.018) with Haas stereo."""
    from .core import morph_noise
    n = int(dur_s * SR)
    nz = morph_noise(n, pink_w, brown_w, seed) * vol
    L = nz.astype(np.float32)
    # Haas decorrelation for R
    rng = np.random.RandomState(int(seed + 999) & 0xFFFFFFFF)
    delay_samples = int(SR * rng.uniform(0.0004, 0.0010))
    R = np.roll(nz, delay_samples).astype(np.float32) * 0.97
    return L, R


# ══════════════════════════════════════════════════════════
#  DETUNED DRONE PAD
# ══════════════════════════════════════════════════════════

def detuned_drone(dur_s: float, carrier: float,
                  detune_hz: float = 0.15,
                  vol: float       = 0.14,
                  ctype: str       = 'warm',
                  seed: int        = 0) -> tuple:
    """Detuned drone pad with Haas stereo decorrelation."""
    n     = int(dur_s * SR)
    t     = np.arange(n, dtype=np.float64) / SR
    lfo_d = 0.003 * np.sin(2 * np.pi * 0.005 * t + (seed * 0.1) % (2 * np.pi))
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
    L = (out * vol).astype(np.float32)
    # Haas decorrelation: 0.3–1.2 ms delay for R
    rng = np.random.RandomState(int(seed) & 0xFFFFFFFF)
    delay_samples = int(SR * rng.uniform(0.0003, 0.0012))
    R = np.roll(L, delay_samples) * 0.98
    return L, R


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
    return (flt / peak * vol * lfo).astype(np.float32)


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
                  carrier_type='sine',
                  carrier_drift=0.0, carrier_drift_rate=0.018):
    n  = int(dur_s * SR)
    C  = build_carrier(c0, c1, n, carrier_jitter, seed,
                       drift_depth=carrier_drift,
                       drift_rate=carrier_drift_rate)
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
#  ISOCHRONIC  — soft-gate v2 (permanent-safe)
#
#  v1: 18/12/8 ms — reduced clicks
#  v2: 26/16/10 ms (+ ASSR-80 uses 32 ms) — minimize roughness
#      (modulation 20–80 Hz is the main permanent-listening killer)
# ══════════════════════════════════════════════════════════

def isochronic(dur_s, freq, carrier=200.0, vol=0.14,
               attack_s=4.0, decay_s=4.0, carrier_type='sine',
               smooth_ms: float = None):
    if freq <= 0:
        return np.zeros(int(dur_s * SR), dtype=np.float32)
    n    = int(dur_s * SR)
    t    = np.arange(n, dtype=np.float64) / SR
    # Raised-cosine gate (softer than hard square before smoothing)
    gate = (0.5 + 0.5 * np.sin(2 * np.pi * freq * t)).astype(np.float32)

    if smooth_ms is not None:
        rn = int(smooth_ms * 0.001 * SR)
    elif freq >= 60.0:
        rn = int(0.032 * SR)   # 32ms: ASSR-80 / ultrasonic roughness band
    elif freq >= 30.0:
        rn = int(0.026 * SR)   # 26ms: gamma
    elif freq >= 15.0:
        rn = int(0.016 * SR)   # 16ms: beta
    else:
        rn = int(0.010 * SR)   # 10ms: alpha/theta

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


def apply_cfc(gamma_sig, dur_s, theta_freq=6.0, strength=0.5,
              envelope_type='sine', asymmetry=0.5):
    """
    Cross-frequency coupling: theta envelope modulates gamma amplitude.

    envelope_type: 'sine' (symmetric, default) or 'asymmetric' (sawtooth-like).
    asymmetry: fraction of theta cycle for ramp-up (0.5=symmetric, 0.8=sharp drop).
    """
    n   = len(gamma_sig)
    t   = np.arange(n, dtype=np.float64) / SR
    strength = min(float(strength), 0.55)
    theta_phase = np.mod(2 * np.pi * theta_freq * t, 2 * np.pi)

    if envelope_type == 'asymmetric':
        ramp_up = np.clip(asymmetry, 0.1, 0.9)
        phase_norm = theta_phase / (2 * np.pi)
        env_theta = np.where(
            phase_norm < ramp_up,
            phase_norm / ramp_up,
            1.0 - (phase_norm - ramp_up) / (1.0 - ramp_up) * 0.1
        )
        from scipy.signal import savgol_filter
        window = min(n, int(SR * 0.01))
        if window > 3 and window % 2 == 0:
            window += 1
        if window > 3:
            env_theta = savgol_filter(env_theta, window, 2)
        env_theta = np.clip(env_theta, 0.0, 1.0)
    else:
        env_theta = 0.5 - 0.5 * np.sin(2 * np.pi * theta_freq * t)

    env = (1.0 - strength + strength * env_theta).astype(np.float32)
    return (gamma_sig * env)


def assr_80hz(dur_s, carrier=200.0, vol=0.05):
    return isochronic(dur_s, 80.0, carrier, vol,
                      attack_s=8.0, decay_s=8.0, smooth_ms=32.0)


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


def hilbert_spatial_rotation(L: np.ndarray, R: np.ndarray,
                              period_s: float = 12.0) -> tuple:
    """
    Phase-decorrelated rotation via Hilbert transform.
    Eliminates comb-filter artifacts at fast rotation rates (<10s period).
    """
    from scipy.signal import hilbert
    n = len(L)
    t = np.arange(n, dtype=np.float64) / SR
    L_analytic = hilbert(L.astype(np.float64))
    R_analytic = hilbert(R.astype(np.float64))
    rot = np.exp(1j * 2.0 * np.pi * t / period_s)
    L_rot = np.real(L_analytic * rot).astype(np.float32)
    R_rot = np.real(R_analytic * np.conj(rot)).astype(np.float32)
    return L_rot, R_rot


def subharmonic_resonator(dur_s: float, carrier_hz: float,
                          depth: int = 4, vol: float = 0.08,
                          seed: int = 0) -> tuple:
    n  = len(L)
    t  = np.arange(n, dtype=np.float64) / SR
    az = 2 * np.pi * t / az_period
    Laz = (L * np.cos(az) - R * np.sin(az)).astype(np.float32)
    Raz = (L * np.sin(az) + R * np.cos(az)).astype(np.float32)
    el       = el_depth * np.sin(2 * np.pi * t / el_period + np.pi / 3).astype(np.float32)
    el_gain  = (1.0 + 0.18 * el).astype(np.float32)
    el_spread = np.clip(1.0 - 0.10 * el, 0.70, 1.30).astype(np.float32)
    return (Laz * el_gain * el_spread), (Raz * el_gain / el_spread)


def subharmonic_resonator(dur_s: float, carrier_hz: float,
                          depth: int = 4, vol: float = 0.08,
                          seed: int = 0) -> tuple:
    """
    Generates subharmonics f/2, f/3, ..., f/(depth+1) below carrier.
    Creates body resonance (chest 60 Hz, skull 120 Hz) without demanding low-freq drivers.
    """
    n = int(dur_s * SR)
    t = np.arange(n, dtype=np.float64) / SR
    out = np.zeros(n, dtype=np.float64)
    for i in range(1, depth + 1):
        f_sub = carrier_hz / (i + 1)
        if f_sub < 20.0:
            continue
        detune = 0.004 * np.sin(2*np.pi * 0.007 * t * i + seed * 0.3)
        phase = 2*np.pi * np.cumsum(f_sub + detune) / SR
        amp = 1.0 / ((i + 1)**1.3)
        out += amp * np.sin(phase)
    out /= (np.max(np.abs(out)) + 1e-9)
    L = (out * vol).astype(np.float32)
    # Haas decorrelation
    delay = int(0.0008 * SR)
    R = np.roll(L, delay) * 0.96
    return L, R


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
    pad_L, pad_R = detuned_drone(dur_s, carrier, detune_hz=0.18, vol=0.10,
                                  ctype='soft', seed=seed + 100)
    L += pad_L; R += pad_R
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
#  FFR PRIME BURST  — soft, subliminal warm-up (~−13 dBFS)
# ══════════════════════════════════════════════════════════

def ffr_prime_burst(carrier: float = 200.0,
                    carrier_type: str = 'soft',
                    dur_s: float = 20.0) -> tuple:
    ctype = carrier_type if carrier_type != 'sine' else 'soft'
    iso = isochronic(dur_s, 40.0, carrier, vol=0.055,
                     attack_s=6.0, decay_s=7.0, carrier_type=ctype,
                     smooth_ms=28.0)
    L_b, R_b = dual_binaural(dur_s, carrier, carrier, 40.0, 40.0,
                              vol_p=0.14, vol_s=0.045,
                              carrier_jitter=0.5, beat_jitter=0.0,
                              seed=7777, carrier_type=ctype)
    bed_L, bed_R = underbed_noise(dur_s, vol=0.022, seed=7778)
    L = (L_b + iso + bed_L).astype(np.float32)
    R = (R_b + iso + bed_R).astype(np.float32)
    fn   = min(int(7 * SR), len(L) // 3)
    ramp = np.linspace(0, 1, fn, np.float32)
    L[:fn] *= ramp;  R[:fn] *= ramp
    L[-fn:] *= ramp[::-1]; R[-fn:] *= ramp[::-1]
    # Target ≈ −13 dBFS (~0.224 FS)
    L, R = soft_ceiling(L, R, ceiling=0.224, knee=0.04)
    return L, R


def structured_quiet(dur_s: float = 60.0, vol: float = 0.012,
                     seed: int = 0) -> tuple:
    """Gateway-style internalization: near-silence with underbed only."""
    bed_L, bed_R = underbed_noise(dur_s, vol=vol, pink_w=0.55, brown_w=0.45, seed=seed)
    fn = min(int(5.0 * SR), len(bed_L) // 4)
    ramp = np.linspace(0, 1, fn, np.float32)
    bed_L = bed_L.copy()
    bed_R = bed_R.copy()
    bed_L[:fn] *= ramp
    bed_L[-fn:] *= ramp[::-1]
    bed_R[:fn] *= ramp
    bed_R[-fn:] *= ramp[::-1]
    return bed_L.astype(np.float32), bed_R.astype(np.float32)


# ══════════════════════════════════════════════════════════
#  HARMONIC SERIES BINAURAL — redundant entrainment across spectral channels
# ══════════════════════════════════════════════════════════

def harmonic_binaural(dur_s: float,
                      base_carrier: float,
                      beat_freq: float,
                      num_partials: int = 4,
                      vol: float = 0.30,
                      carrier_types: list = None,
                      carrier_jitter: float = 1.0,
                      seed: int = 0) -> tuple:
    """
    Harmonic series binaural: n partials at n*base_carrier, all sharing the
    same beat_freq. Creates redundant entrainment across spectral channels.
    Per-partial carrier jitter for warmth and anti-metallic feel.
    """
    n = int(dur_s * SR)
    t = np.arange(n, dtype=np.float64) / SR
    L = np.zeros(n, dtype=np.float64)
    R = np.zeros(n, dtype=np.float64)

    if carrier_types is None:
        carrier_types = ['sine'] * num_partials

    for i in range(num_partials):
        harm_n = i + 1
        c = base_carrier * harm_n
        amp = 1.0 / harm_n
        ct = carrier_types[i % len(carrier_types)]

        jitter = pink_noise(n, seed + i * 77).astype(np.float64)
        jitter /= np.max(np.abs(jitter)) + 1e-9
        C = c + jitter * carrier_jitter

        pL = 2.0 * np.pi * np.cumsum(C) / SR
        pR = 2.0 * np.pi * np.cumsum(C + beat_freq) / SR

        L += _apply_carrier_type(pL, ct).astype(np.float64) * amp
        R += _apply_carrier_type(pR, ct).astype(np.float64) * amp

    peak = max(np.max(np.abs(L)), np.max(np.abs(R))) + 1e-9
    L = (L / peak * vol).astype(np.float32)
    R = (R / peak * vol).astype(np.float32)
    return L, R


# ══════════════════════════════════════════════════════════
#  POLYRHYTHMIC ISOCHRONIC — multiple layers at frequency ratios
# ══════════════════════════════════════════════════════════

def polyrhythmic_isochronic(dur_s: float,
                            ratios: list = None,
                            base_freq: float = 6.0,
                            carriers: list = None,
                            vols: list = None,
                            attack_s: float = 8.0,
                            decay_s: float = 8.0,
                            seed: int = 0) -> np.ndarray:
    """
    Multiple isochronic layers at polyrhythmic ratios of a base frequency.
    E.g. ratios=[3,2] at base_freq=6 -> layers at 6Hz and 4Hz.
    Each layer on a different carrier for spectral separation.
    """
    if ratios is None:
        ratios = [3, 2]
    n_layers = len(ratios)
    if carriers is None:
        carriers = [200.0 + i * 40 for i in range(n_layers)]
    if vols is None:
        vols = [0.06 / n_layers] * n_layers

    out = np.zeros(int(dur_s * SR), dtype=np.float32)
    for i, (ratio, carrier, vol) in enumerate(zip(ratios, carriers, vols)):
        freq = base_freq * ratio / ratios[0]
        layer = isochronic(dur_s, freq, carrier, vol,
                          attack_s, decay_s,
                          carrier_type='soft')
        out += layer
    return out


# ══════════════════════════════════════════════════════════
#  FM CARRIER — modulator at brainwave frequency
# ══════════════════════════════════════════════════════════

def fm_carrier(dur_s: float,
               carrier_freq: float,
               mod_freq: float = 0.0,
               mod_index: float = 1.0,
               beat_freq: float = 10.0,
               vol: float = 0.30) -> tuple:
    """
    FM synthesis carrier where modulator runs at brainwave frequency.
    Creates difference tones that match the target beat frequency.
    """
    n = int(dur_s * SR)
    t = np.arange(n, dtype=np.float64) / SR

    if mod_freq <= 0:
        mod_freq = beat_freq

    mod_phase = 2.0 * np.pi * mod_freq * t
    fm_L = carrier_freq * t + (mod_index * mod_freq / (2.0 * np.pi)) * np.sin(mod_phase)
    fm_R = (carrier_freq + beat_freq) * t + (mod_index * mod_freq / (2.0 * np.pi)) * np.sin(mod_phase)

    L = (vol * np.sin(2.0 * np.pi * fm_L)).astype(np.float32)
    R = (vol * np.sin(2.0 * np.pi * fm_R)).astype(np.float32)
    return L, R


# ══════════════════════════════════════════════════════════
#  SHEPARD CARRIER — infinite pitch illusion with binaural beat
# ══════════════════════════════════════════════════════════

def shepard_carrier(dur_s: float,
                    center_freq: float = 300.0,
                    sweep_rate: float = 0.05,
                    beat_freq: float = 10.0,
                    num_octaves: int = 5,
                    sigma: float = 1.0,
                    vol: float = 0.20,
                    seed: int = 0) -> tuple:
    """
    Shepard tone carrier: octave-stacked sinusoids with Gaussian spectral
    envelope. center_freq sweeps slowly for infinite pitch illusion.
    Beat offset applied to all octaves simultaneously.
    """
    n = int(dur_s * SR)
    t = np.arange(n, dtype=np.float64) / SR
    L = np.zeros(n, dtype=np.float64)
    R = np.zeros(n, dtype=np.float64)

    cf = center_freq * np.power(2.0, sweep_rate * t / center_freq)

    for octave in range(-num_octaves // 2, num_octaves // 2 + 1):
        log_dist = octave
        weight = np.exp(-0.5 * (log_dist / sigma) ** 2)
        if weight < 0.01:
            continue
        f_oct = cf * np.power(2.0, octave)
        pL = 2.0 * np.pi * np.cumsum(f_oct) / SR
        pR = 2.0 * np.pi * np.cumsum(f_oct + beat_freq) / SR
        L += weight * np.sin(pL)
        R += weight * np.sin(pR)

    peak = max(np.max(np.abs(L)), np.max(np.abs(R))) + 1e-9
    L = (L / peak * vol).astype(np.float32)
    R = (R / peak * vol).astype(np.float32)
    return L, R


# ══════════════════════════════════════════════════════════
#  SR NOISE ON ENTRAINMENT — per-channel calibrated noise
# ══════════════════════════════════════════════════════════

def apply_sr_noise(signal_L: np.ndarray,
                   signal_R: np.ndarray,
                   sr_ratio: float = 0.282,
                   seed: int = 0) -> tuple:
    """
    Apply calibrated stochastic resonance noise directly to an entrainment
    signal (not just ambient bed). Per-channel independent noise for
    stereo decorrelation.
    """
    from .core import morph_noise

    n = len(signal_L)
    nz_L = morph_noise(n, 0.5, 0.5, seed)
    nz_R = morph_noise(n, 0.5, 0.5, seed + 999)

    sig_rms_L = np.sqrt(np.mean(signal_L**2)) + 1e-9
    sig_rms_R = np.sqrt(np.mean(signal_R**2)) + 1e-9
    nz_rms_L = np.sqrt(np.mean(nz_L**2)) + 1e-9
    nz_rms_R = np.sqrt(np.mean(nz_R**2)) + 1e-9

    nz_L = (nz_L * (sig_rms_L * sr_ratio / nz_rms_L)).astype(np.float32)
    nz_R = (nz_R * (sig_rms_R * sr_ratio / nz_rms_R)).astype(np.float32)

    return (signal_L + nz_L).astype(np.float32), (signal_R + nz_R).astype(np.float32)
