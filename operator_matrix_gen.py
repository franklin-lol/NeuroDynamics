#!/usr/bin/env python3
"""
OPERATOR MATRIX — Psychoacoustic Engineering Suite v3.0
Sessions: 4 | SR: 44100 Hz | FLAC PCM_24 | Stereo

12 architectural upgrades over v2:
  ① Beat jitter ±0.15 Hz 1/f — breaks brain's beat prediction (not just carrier)
  ② Equal-power √taper xfade — no -3 dB dip at phase transitions
  ③ Cross-Frequency Coupling (CFC/PAC) — theta phase gates gamma amplitude
     mirrors hippocampal theta-trough gamma (Lisman & Jensen 2013)
  ④ 80 Hz ASSR — brainstem/cortical SSAEP pathway, independent of 40 Hz gamma
  ⑤ Slow ILD spatial rotation (0.05–0.12 Hz) — vestibular co-engagement
  ⑥ Infra-modulation 0.03–0.07 Hz AM — signal breathes, prevents plateau
  ⑦ Stochastic Resonance noise: noise_rms = SR_RATIO × signal_rms (Gammaitoni 1998)
  ⑧ Dual binaural octave pair: primary(C,B) + octave(2C, B/2) — richer percept
  ⑨ All 5 Schumann harmonics (7.83/14.3/20.8/27.3/33.8 Hz) noise AM stack
  ⑩ Logarithmic beat sweeps — perceptually uniform scale
  ⑪ Pattern-break phases (20 s @ 10 Hz α neutral) — resets neural lock-in
  ⑫ 528 Hz carrier in Void blocks (Solfeggio MI) — timbral anchor shift

Session highlights:
  Walk   30 min — dual binaural + ASSR + CFC@7 Hz + spatial rotation
  Void   40 min — log sweeps + 528 Hz void carrier + CFC + Schumann + pattern break
  Sleep 120 min — 3 × awareness windows, Schumann in deep hold, CFC trigger at window
  Divine 45 min — full stack: 432 Hz + all 5 Schumann + dual + CFC + spatial + infra

Usage: python3 operator_matrix_gen_v3.py
Output: ./operator_output/*.flac  (PCM_24, 44100 Hz, stereo)
Deps:   pip install numpy scipy soundfile --break-system-packages
"""

import numpy as np
from scipy.signal import lfilter, butter, sosfilt
import soundfile as sf
import os, sys, time

# ═══════════════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════════════
SR       = 44100
BD       = 'PCM_24'
PEAK     = 0.88
SR_RATIO = 0.28   # Stochastic Resonance optimal: noise_rms / signal_rms ≈ -11 dB

SCHUMANN_HZ = np.array([7.83, 14.3, 20.8, 27.3, 33.8], dtype=np.float64)

OUT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd(),
    'operator_output'
)
os.makedirs(OUT, exist_ok=True)

RNG = np.random.default_rng()   # per-run entropy — unique noise every invocation


# ═══════════════════════════════════════════════════════════════════════
# DSP PRIMITIVES
# ═══════════════════════════════════════════════════════════════════════

def pink_noise(n: int, rng: np.random.Generator = RNG) -> np.ndarray:
    """Kasdin 1995 IIR 1/f. 512-sample pre-roll fills filter transient."""
    b = np.array([0.049922035, -0.095993537,  0.050612699, -0.004408786])
    a = np.array([1.0,         -2.494956002,   2.017265875, -0.522189400])
    return lfilter(b, a, rng.standard_normal(n + 512))[512:].astype(np.float32)


def brown_noise(n: int, rng: np.random.Generator = RNG) -> np.ndarray:
    """1/f² via cumsum. HP Butterworth 20 Hz removes DC drift."""
    raw = rng.standard_normal(n + 512) * 0.02
    brn = np.cumsum(raw)[512:]
    sos = butter(2, 20.0 / (SR / 2.0), btype='high', output='sos')
    return sosfilt(sos, brn).astype(np.float32)


def rms_f64(x: np.ndarray) -> float:
    return float(np.sqrt(np.mean(x.astype(np.float64) ** 2)))


def norm(x: np.ndarray, peak: float = PEAK) -> np.ndarray:
    m = np.max(np.abs(x))
    return (x * (peak / m)).astype(np.float32) if m > 1e-9 else x.astype(np.float32)


def hard_limit(x: np.ndarray) -> np.ndarray:
    return np.clip(x, -PEAK, PEAK).astype(np.float32)


def noise_block(n: int, noise_type: str, rng: np.random.Generator) -> np.ndarray:
    if noise_type == 'pink':
        return pink_noise(n, rng)
    if noise_type == 'brown':
        return brown_noise(n, rng)
    return np.zeros(n, dtype=np.float32)


def beat_array(b_start: float, b_end: float, n: int, log: bool = False) -> np.ndarray:
    """Beat frequency array (log or linear). Floor at 0.3 Hz to avoid log(0)."""
    if log:
        s, e = max(b_start, 0.3), max(b_end, 0.3)
        return np.exp(np.linspace(np.log(s), np.log(e), n, dtype=np.float64))
    return np.linspace(b_start, b_end, n, dtype=np.float64)


def schumann_am(n: int, rng: np.random.Generator, depth: float = 0.025) -> np.ndarray:
    """
    All 5 Schumann harmonics as AM envelope.
    Random phase per band → no lock-in with binaural beat.
    Total AM depth ≤ 12.5% (subliminal, not audible as individual tones).
    """
    t = np.arange(n, dtype=np.float64) / SR
    env = np.ones(n, dtype=np.float64)
    for f in SCHUMANN_HZ:
        phi = rng.uniform(0.0, 2.0 * np.pi)
        env += depth * np.sin(2.0 * np.pi * f * t + phi)
    return env.astype(np.float32)


# ═══════════════════════════════════════════════════════════════════════
# SIGNAL GENERATORS
# ═══════════════════════════════════════════════════════════════════════

def binaural_pair(
        dur_s: float,
        c_start: float, c_end: float,
        b_start: float, b_end: float,
        volume: float = 0.82,
        phi_L: float = 0.0, phi_R: float = 0.0,
        phi_L2: float = 0.0, phi_R2: float = 0.0,
        beat_jitter: bool = False, beat_jitter_depth: float = 0.15,
        anti_adapt: bool = False, adapt_depth: float = 1.5,
        dual: bool = False,
        log_sweep: bool = False,
        rng: np.random.Generator = RNG,
) -> tuple:
    """
    Phase-continuous binaural sweep. Dual binaural: octave pair at 2×C, ½B, 35% vol.
    Returns (L, R, phi_L, phi_R, phi_L2, phi_R2, theta_phase_arr).
    theta_phase_arr — cumulative beat integral — drives CFC gamma.
    """
    n       = int(dur_s * SR)
    carrier = np.linspace(c_start, c_end, n, dtype=np.float64)
    beat    = beat_array(b_start, b_end, n, log=log_sweep)

    if anti_adapt and adapt_depth > 0:
        carrier += norm(pink_noise(n, rng).astype(np.float64)) * adapt_depth

    if beat_jitter and beat_jitter_depth > 0:
        jit  = norm(pink_noise(n, rng).astype(np.float64)) * beat_jitter_depth
        beat = np.clip(beat + jit, 0.2, beat.max() + beat_jitter_depth * 2.0)

    # Cumulative theta phase — for CFC
    theta_phase = np.cumsum(2.0 * np.pi * beat / SR)

    # Primary binaural pair
    dL  = 2.0 * np.pi * carrier / SR
    dR  = 2.0 * np.pi * (carrier + beat) / SR
    pL  = phi_L + np.cumsum(dL)
    pR  = phi_R + np.cumsum(dR)

    L   = (np.sin(pL) * volume).astype(np.float32)
    R   = (np.sin(pR) * volume).astype(np.float32)
    npL, npR = float(pL[-1]), float(pR[-1])
    npL2, npR2 = phi_L2, phi_R2

    # Octave pair
    if dual:
        dL2 = 2.0 * np.pi * (carrier * 2.0) / SR
        dR2 = 2.0 * np.pi * (carrier * 2.0 + beat * 0.5) / SR
        pL2 = phi_L2 + np.cumsum(dL2)
        pR2 = phi_R2 + np.cumsum(dR2)
        L  += (np.sin(pL2) * volume * 0.35).astype(np.float32)
        R  += (np.sin(pR2) * volume * 0.35).astype(np.float32)
        npL2, npR2 = float(pL2[-1]), float(pR2[-1])

    return L, R, npL, npR, npL2, npR2, theta_phase


def isochronic(
        dur_s: float,
        beat_hz: float,
        carrier: float = 200.0,
        volume: float = 0.18,
        duty: float = 0.50,
        ramp_ms: float = 8.0,
) -> np.ndarray:
    """Per-pulse raised-cosine gate — zero droop, zero click."""
    if beat_hz is None or beat_hz <= 0 or volume <= 0:
        return np.zeros(int(dur_s * SR), dtype=np.float32)
    n       = int(dur_s * SR)
    t       = np.arange(n, dtype=np.float64) / SR
    cy      = (t * beat_hz) % 1.0
    rf      = min(ramp_ms / 1000.0 * beat_hz, duty * 0.45)
    gate    = np.where(
        cy < rf,
        0.5 * (1.0 - np.cos(np.pi * cy / max(rf, 1e-9))),
        np.where(
            cy < duty - rf,
            1.0,
            np.where(
                cy < duty,
                0.5 * (1.0 + np.cos(np.pi * (cy - (duty - rf)) / max(rf, 1e-9))),
                0.0,
            )
        )
    ).astype(np.float32)
    return hard_limit(np.sin(2.0 * np.pi * carrier * t).astype(np.float32) * gate * volume)


def gamma_static(dur_s: float, carrier: float = 252.0,
                 volume: float = 0.07) -> np.ndarray:
    """40 Hz raised-cosine isochronic — static amplitude."""
    return isochronic(dur_s, 40.0, carrier, volume, duty=0.40, ramp_ms=5.0)


def gamma_cfc(dur_s: float, theta_phase: np.ndarray,
              carrier: float = 252.0, volume: float = 0.08) -> np.ndarray:
    """
    CFC (Phase-Amplitude Coupling): theta beat phase gates 40 Hz gamma amplitude.
    Gamma peaks at theta trough (phase=π) — replicates hippocampal PAC.
    theta_phase: precomputed cumulative phase = cumsum(2π·beat/SR).
    """
    n   = int(dur_s * SR)
    t   = np.arange(n, dtype=np.float64) / SR
    # Remap theta_phase to length n if mismatched
    if len(theta_phase) != n:
        idx = np.round(np.linspace(0, len(theta_phase) - 1, n)).astype(int)
        tp  = theta_phase[idx]
    else:
        tp  = theta_phase
    # Envelope: peaks at theta trough (cos argument +π → maximum at phase=π)
    am   = ((1.0 + np.cos(tp + np.pi)) * 0.5).astype(np.float32)
    tone = np.sin(2.0 * np.pi * 40.0 * t).astype(np.float32)
    return hard_limit(tone * am * volume)


def assr_80hz(dur_s: float, carrier: float = 320.0,
              volume: float = 0.05) -> np.ndarray:
    """
    80 Hz ASSR (Auditory Steady-State Response).
    Carrier 320 Hz: separated from binaural (200/432 Hz) and gamma (252/260 Hz).
    Activates independent brainstem + primary auditory cortex pathway.
    """
    return isochronic(dur_s, 80.0, carrier, volume, duty=0.38, ramp_ms=3.5)


def spatial_ild(
        dur_s: float,
        carrier: float = 230.0,
        rotation_hz: float = 0.08,
        volume: float = 0.06,
        rng: np.random.Generator = RNG,
) -> tuple:
    """
    Slow ILD (Interaural Level Difference) spatial rotation.
    Bandpass noise at carrier Hz panned ±60° at rotation_hz.
    Equal-power pan law: L²+R² = const.
    Returns (L, R) float32.
    """
    n     = int(dur_s * SR)
    t     = np.arange(n, dtype=np.float64) / SR
    angle = (np.pi / 3.0) * np.sin(2.0 * np.pi * rotation_hz * t)
    pan_L = np.cos(np.pi / 4.0 + angle / 2.0).astype(np.float32)
    pan_R = np.sin(np.pi / 4.0 + angle / 2.0).astype(np.float32)
    # Bandpass noise: ±15% bandwidth around carrier
    nyq   = SR / 2.0
    lo    = np.clip(carrier * 0.85 / nyq, 0.001, 0.99)
    hi    = np.clip(carrier * 1.15 / nyq, lo + 0.01, 0.999)
    sos   = butter(2, [lo, hi], btype='band', output='sos')
    raw   = rng.standard_normal(n + 512)
    sig   = sosfilt(sos, raw)[512:].astype(np.float32)
    sig   = norm(sig) * volume
    return sig * pan_L, sig * pan_R


def infra_env(n: int, hz: float = 0.05, depth: float = 0.08) -> np.ndarray:
    """Sub-Hz AM breathing envelope. Range [1-depth, 1+depth]."""
    t = np.arange(n, dtype=np.float64) / SR
    return (1.0 + depth * np.sin(2.0 * np.pi * hz * t)).astype(np.float32)


# ═══════════════════════════════════════════════════════════════════════
# PHASE ENGINE v3 — stateful, all layers composited
# ═══════════════════════════════════════════════════════════════════════

class PhaseEngine:
    """
    Stateful binaural phase tracker across consecutive phases.
    Tracks primary (phi_L, phi_R) and octave pair (phi_L2, phi_R2).

    Phase config dict keys (all optional unless noted):
      dur_s           float  [required] — duration in seconds
      beat_start      float  [required] — beat freq Hz at phase start
      beat_end        float  [required] — beat freq Hz at phase end
      carrier_start   float  — binaural carrier Hz (default 200)
      carrier_end     float  — binaural carrier Hz at end (default = carrier_start)
      carrier_override float — overrides both carrier_start and carrier_end
      volume          float  — binaural amplitude (default 0.82)
      log_sweep       bool   — logarithmic beat sweep (default False)
      anti_adapt      bool   — carrier 1/f jitter (default False)
      adapt_depth     float  — carrier jitter Hz (default 1.5)
      beat_jitter     bool   — ① beat freq 1/f jitter (default False)
      beat_jitter_depth float — Hz (default 0.15)
      dual_binaural   bool   — ⑧ octave pair (default False)
      noise_type      str    — 'pink'|'brown'|None
      noise_vol       float  — noise target = noise_vol × signal_rms (default 0.28)
      sr_noise        bool   — ⑦ SR-normalized noise (default True)
      schumann_stack  bool   — ⑨ Schumann AM on noise (default False)
      iso_beat        float  — primary isochronic Hz (default None = off)
      iso_vol         float  — primary iso amplitude (default 0.13)
      iso_carrier     float  — primary iso carrier Hz (default 200)
      iso_ramp_ms     float  — iso attack/decay ms (default 8)
      iso_beat2       float  — secondary isochronic Hz (default None)
      iso_vol2        float  — secondary iso amplitude (default 0.06)
      iso_carrier2    float  — secondary iso carrier Hz (default 175)
      gamma_vol       float  — gamma amplitude (default 0 = off)
      gamma_carrier   float  — gamma carrier Hz (default 252)
      cfc             bool   — ③ theta PAC gamma (default False)
      assr_vol        float  — ④ 80 Hz ASSR amplitude (default 0 = off)
      spatial_hz      float  — ⑤ ILD rotation Hz (default 0 = off)
      spatial_vol     float  — spatial amplitude (default 0.06)
      infra_hz        float  — ⑥ sub-Hz AM Hz (default 0 = off)
      infra_depth     float  — AM depth 0–1 (default 0.08)
      xfade_ms        float  — crossfade tail to reserve (handled by stream_session)
    """
    def __init__(self, rng: np.random.Generator = None):
        self.rng    = rng or np.random.default_rng()
        self.phi_L  = self.phi_R  = 0.0
        self.phi_L2 = self.phi_R2 = 0.0

    def reset(self):
        self.phi_L = self.phi_R = self.phi_L2 = self.phi_R2 = 0.0

    def build(self, cfg: dict) -> tuple:
        rng = self.rng
        dur = cfg['dur_s']
        n   = int(dur * SR)
        co  = cfg.get('carrier_override')
        c0  = co if co is not None else cfg.get('carrier_start', 200.0)
        c1  = co if co is not None else cfg.get('carrier_end',   c0)

        # ── ① Binaural core (+ beat jitter + ⑧ dual + ⑩ log sweep) ──
        L, R, self.phi_L, self.phi_R, self.phi_L2, self.phi_R2, theta_ph = binaural_pair(
            dur, c0, c1,
            cfg['beat_start'], cfg['beat_end'],
            volume            = cfg.get('volume', 0.82),
            phi_L             = self.phi_L,
            phi_R             = self.phi_R,
            phi_L2            = self.phi_L2,
            phi_R2            = self.phi_R2,
            beat_jitter       = cfg.get('beat_jitter', False),
            beat_jitter_depth = cfg.get('beat_jitter_depth', 0.15),
            anti_adapt        = cfg.get('anti_adapt', False),
            adapt_depth       = cfg.get('adapt_depth', 1.5),
            dual              = cfg.get('dual_binaural', False),
            log_sweep         = cfg.get('log_sweep', False),
            rng               = rng,
        )

        sig_rms = rms_f64(L)   # reference for SR noise scaling

        # ── ⑦ Noise (SR-normalized) + ⑨ Schumann AM ────────────────
        ntype = cfg.get('noise_type')
        nvol  = cfg.get('noise_vol', SR_RATIO)   # default = SR_RATIO
        if ntype and nvol > 0:
            noise = noise_block(n, ntype, rng)
            if cfg.get('schumann_stack', False):
                noise = noise * schumann_am(n, rng)
            if cfg.get('sr_noise', True):
                target_rms = sig_rms * nvol
                n_rms      = rms_f64(noise)
                noise      = (noise * (target_rms / max(n_rms, 1e-9))).astype(np.float32)
            else:
                noise = norm(noise) * nvol
            L += noise
            R += noise

        # ── Primary isochronic ────────────────────────────────────────
        iso1 = cfg.get('iso_beat')
        iv1  = cfg.get('iso_vol', 0.13)
        ic1  = cfg.get('iso_carrier', 200.0)
        irm  = cfg.get('iso_ramp_ms', 8.0)
        if iso1 is not None and iv1 > 0:
            sig = isochronic(dur, iso1, ic1, iv1, ramp_ms=irm)
            L += sig; R += sig

        # ── Secondary isochronic ──────────────────────────────────────
        iso2 = cfg.get('iso_beat2')
        iv2  = cfg.get('iso_vol2', 0.06)
        ic2  = cfg.get('iso_carrier2', 175.0)
        if iso2 is not None and iv2 > 0:
            sig = isochronic(dur, iso2, ic2, iv2, duty=0.35, ramp_ms=6.0)
            L += sig; R += sig

        # ── ③ Gamma (CFC or static) ───────────────────────────────────
        gv  = cfg.get('gamma_vol', 0.0)
        gc  = cfg.get('gamma_carrier', 252.0)
        if gv > 0:
            g = gamma_cfc(dur, theta_ph, gc, gv) if cfg.get('cfc', False) \
                else gamma_static(dur, gc, gv)
            L += g; R += g

        # ── ④ 80 Hz ASSR ──────────────────────────────────────────────
        av = cfg.get('assr_vol', 0.0)
        if av > 0:
            a = assr_80hz(dur, carrier=320.0, volume=av)
            L += a; R += a

        # ── ⑤ Spatial ILD rotation ───────────────────────────────────
        sp_hz  = cfg.get('spatial_hz', 0.0)
        sp_vol = cfg.get('spatial_vol', 0.06)
        if sp_hz > 0 and sp_vol > 0:
            spL, spR = spatial_ild(dur, 230.0, sp_hz, sp_vol, rng)
            L += spL; R += spR

        # ── ⑥ Infra-modulation ───────────────────────────────────────
        ih  = cfg.get('infra_hz', 0.0)
        id_ = cfg.get('infra_depth', 0.08)
        if ih > 0 and id_ > 0:
            env = infra_env(n, ih, id_)
            L *= env; R *= env

        return hard_limit(L), hard_limit(R)


# ═══════════════════════════════════════════════════════════════════════
# STREAM SESSION — equal-power √taper crossfade (② upgrade)
# Memory: O(max_phase_samples) regardless of total session length
# ═══════════════════════════════════════════════════════════════════════

def stream_session(
        filename: str,
        phases: list,
        fade_in_s: float = 5.0,
        fade_out_s: float = 6.0,
        rng: np.random.Generator = None,
) -> str:
    rng     = rng or np.random.default_rng()
    eng     = PhaseEngine(rng)
    path    = os.path.join(OUT, filename)
    n_ph    = len(phases)
    total_s = sum(p['dur_s'] for p in phases)

    pending_L: np.ndarray = None
    pending_R: np.ndarray = None
    pending_n: int        = 0

    with sf.SoundFile(path, 'w', samplerate=SR, channels=2,
                      format='FLAC', subtype=BD) as f:
        # Set Metadata
        f.artist  = 'franklin-sys'
        f.date    = '2026'
        f.comment = 'https://franklin-sys.vercel.app/'

        for i, ph in enumerate(phases):
            L, R = eng.build(ph)

            # Equal-power fade-in on first phase (sin ramp: 0→1)
            if i == 0:
                fi_n = min(int(fade_in_s * SR), len(L) // 4)
                if fi_n > 0:
                    t_fi = np.linspace(0.0, np.pi / 2, fi_n, dtype=np.float32)
                    ramp = np.sin(t_fi)
                    L[:fi_n] *= ramp; R[:fi_n] *= ramp

            # ② Equal-power crossfade blend with pending tail
            if pending_L is not None and pending_n > 0:
                blend = min(pending_n, len(L))
                t_xf  = np.linspace(0.0, np.pi / 2, blend, dtype=np.float32)
                fo    = np.cos(t_xf)    # fade-out: 1→0, power = cos²
                fi_   = np.sin(t_xf)   # fade-in:  0→1, power = sin²
                # cos²+sin²=1 everywhere → constant total power
                xL    = pending_L[-blend:] * fo + L[:blend] * fi_
                xR    = pending_R[-blend:] * fo + R[:blend] * fi_
                f.write(np.stack([hard_limit(xL), hard_limit(xR)], axis=1))
                L = L[blend:]; R = R[blend:]

            pending_L = pending_R = None
            pending_n = 0

            # Equal-power fade-out on last phase (cos ramp: 1→0)
            if i == n_ph - 1:
                fo_n = min(int(fade_out_s * SR), len(L) // 4)
                if fo_n > 0:
                    t_fo = np.linspace(0.0, np.pi / 2, fo_n, dtype=np.float32)
                    ramp = np.cos(t_fo)
                    L[-fo_n:] *= ramp; R[-fo_n:] *= ramp
                f.write(np.stack([L, R], axis=1))
            else:
                xf_n = int(phases[i + 1].get('xfade_ms', 200) * SR / 1000)
                if xf_n > 0 and len(L) > xf_n:
                    f.write(np.stack([L[:-xf_n], R[:-xf_n]], axis=1))
                    pending_L = L[-xf_n:].copy()
                    pending_R = R[-xf_n:].copy()
                    pending_n = xf_n
                else:
                    f.write(np.stack([L, R], axis=1))

            del L, R
            pct = (i + 1) / n_ph * 100
            sys.stdout.write(f"\r    ph {i+1:2d}/{n_ph}  {pct:5.1f}%  ...")
            sys.stdout.flush()

    size_mb = os.path.getsize(path) / 1024 / 1024
    print(f"\r  ✓  {filename:58s} [{total_s/60:5.1f} min | {size_mb:5.1f} MB]")
    return path


# ═══════════════════════════════════════════════════════════════════════
# PATTERN BREAK — ⑪ 20 s neutral alpha reset between deep phases
# ═══════════════════════════════════════════════════════════════════════

def pattern_break(dur_s: float = 20.0, beat_hz: float = 10.0) -> dict:
    """
    Inserts a brief alpha neutral phase (⑪) to disrupt neural lock-in.
    The sharp beat step followed by xfade is the mechanism — not a smooth transition.
    beat_hz: target reset frequency (10 Hz alpha default; 7.83 Hz for Schumann sessions).
    """
    return dict(
        dur_s=dur_s, beat_start=beat_hz, beat_end=beat_hz,
        carrier_start=200, carrier_end=200,
        noise_type='pink', noise_vol=0.20,
        sr_noise=True, xfade_ms=400,
        volume=0.72,
    )


# ═══════════════════════════════════════════════════════════════════════
# SESSION 1 — ПРОГУЛКА (30 MIN)
# "РАСШИРЕННЫЙ НАБЛЮДАТЕЛЬ"
#
# Design: Keep operator present and aware in motion — no trance.
# Key features: dual binaural, ASSR cortical activation, CFC at theta-alpha
#               boundary (7 Hz), slow spatial rotation, beat jitter from Ph2.
#
# Duration: 240+480+480+360+240 = 1800s = 30 min ✓
# ═══════════════════════════════════════════════════════════════════════

def session_walk() -> str:
    print("\n[1/4] ПРОГУЛКА — Расширенный Наблюдатель (30 min)")
    phases = [
        # Ph.1  0–4 min  | Soft alignment — pure binaural, ASSR on, no additives
        dict(dur_s=240, beat_start=12.0, beat_end=10.0,
             carrier_start=200, carrier_end=200,
             assr_vol=0.04,
             volume=0.83),

        # Ph.2  4–12 min | Dual binaural + beat jitter active — ASSR continues
        #                  Spatial starts (gentle 0.06 Hz — barely perceptible)
        dict(dur_s=480, beat_start=10.0, beat_end=8.5,
             carrier_start=200, carrier_end=202,
             dual_binaural=True, beat_jitter=True,
             noise_type='pink', noise_vol=0.22, sr_noise=True,
             assr_vol=0.04, spatial_hz=0.06, spatial_vol=0.05,
             gamma_vol=0.06, gamma_carrier=252,
             volume=0.82),

        # Ph.3  12–20 min | SMR-alpha plateau — anti_adapt, spatial widens
        #                   gamma static (not yet CFC — alpha not optimal PAC)
        dict(dur_s=480, beat_start=8.5, beat_end=7.5,
             carrier_start=202, carrier_end=205,
             dual_binaural=True, beat_jitter=True,
             anti_adapt=True, adapt_depth=1.2,
             noise_type='pink', noise_vol=0.25, sr_noise=True,
             spatial_hz=0.08, spatial_vol=0.06,
             gamma_vol=0.07, gamma_carrier=250,
             volume=0.80),

        # Ph.4  20–26 min | Theta edge — CFC engages (beat=7 Hz → valid PAC range)
        #                   infra breathing begins — peak operator window
        dict(dur_s=360, beat_start=7.5, beat_end=7.0,
             carrier_start=205, carrier_end=207,
             dual_binaural=True, beat_jitter=True,
             anti_adapt=True, adapt_depth=1.0,
             noise_type='pink', noise_vol=0.25, sr_noise=True,
             spatial_hz=0.10, spatial_vol=0.06,
             gamma_vol=0.08, gamma_carrier=248, cfc=True,
             infra_hz=0.05, infra_depth=0.07,
             volume=0.80),

        # Ph.5  26–30 min | Lift to 8.0 Hz (not 9.0 — no state snap)
        #                   CFC trails, spatial fades out, ASSR returns
        dict(dur_s=240, beat_start=7.0, beat_end=8.0,
             carrier_start=207, carrier_end=205,
             dual_binaural=True, beat_jitter=True,
             noise_type='pink', noise_vol=0.20, sr_noise=True,
             gamma_vol=0.06, gamma_carrier=250, cfc=False,
             assr_vol=0.03, infra_hz=0.05, infra_depth=0.05,
             volume=0.82),
    ]
    return stream_session("01_WALK_Observer_30min.flac", phases,
                          fade_in_s=4.0, fade_out_s=5.0)


# ═══════════════════════════════════════════════════════════════════════
# SESSION 2 — МЕДИТАЦИЯ (40 MIN)
# "ПУСТОТА С СОЗНАНИЕМ"
#
# Design: Guided descent, logarithmic sweeps, 528 Hz void carrier,
#         CFC in theta corridor, Schumann in void, pattern break before critical.
# Rule: iso ONLY in descent (Ph1-Ph2), NOT in void — disrupts state cohesion.
#
# Duration: 420+600+20+540+540+280 = 2400s = 40 min ✓
# ═══════════════════════════════════════════════════════════════════════

def session_meditation() -> str:
    print("\n[2/4] МЕДИТАЦИЯ — Пустота с Сознанием (40 min)")
    phases = [
        # Ph.1  0–7 min  | Alpha-theta bridge — ASSR on, beat jitter, log sweep
        dict(dur_s=420, beat_start=10.0, beat_end=6.0,
             carrier_start=200, carrier_end=200,
             beat_jitter=True, log_sweep=True,
             noise_type='pink', noise_vol=0.22, sr_noise=True,
             assr_vol=0.04,
             volume=0.83),

        # Ph.2  7–17 min | Theta corridor — iso at 175 Hz (perceptual separation)
        #                  ASSR off (too activating for theta), CFC begins at 5 Hz
        dict(dur_s=600, beat_start=6.0, beat_end=3.5,
             carrier_start=200, carrier_end=201,
             beat_jitter=True, log_sweep=True,
             noise_type='pink', noise_vol=0.25, sr_noise=True,
             iso_beat=4.5, iso_vol=0.11, iso_carrier=175.0, iso_ramp_ms=10.0,
             gamma_vol=0.06, gamma_carrier=252, cfc=True,
             volume=0.80),

        # ⑪ PATTERN BREAK — 20 s @ 10 Hz neutral α (lock-in reset before void entry)
        {**pattern_break(20.0, beat_hz=10.0), 'xfade_ms': 500},

        # Ph.3  17–26 min | Critical descent — iso OFF, CFC gamma, brown + Schumann
        #                   infra breathing, carrier stays 200 (528 only in void)
        dict(dur_s=540, beat_start=3.5, beat_end=2.5,
             carrier_start=201, carrier_end=201,
             beat_jitter=True, log_sweep=True,
             noise_type='brown', noise_vol=0.28, sr_noise=True,
             schumann_stack=True,
             gamma_vol=0.08, gamma_carrier=260, cfc=True,
             infra_hz=0.04, infra_depth=0.08,
             volume=0.78),

        # Ph.4  26–35 min | THE VOID (9 min) — ⑫ 528 Hz carrier
        #                   Pure delta + CFC gamma + Schumann + infra + anti_adapt
        #                   iso completely OFF — no disruption to void state
        dict(dur_s=540, beat_start=2.5, beat_end=2.3,
             carrier_override=528.0,
             beat_jitter=True, beat_jitter_depth=0.10,
             anti_adapt=True, adapt_depth=0.7,
             noise_type='brown', noise_vol=0.30, sr_noise=True,
             schumann_stack=True,
             gamma_vol=0.08, gamma_carrier=260, cfc=True,
             infra_hz=0.035, infra_depth=0.10,
             xfade_ms=600,
             volume=0.77),

        # Ph.5  35–40 min | Exit — preserves integration state, gamma trails
        #                   Return to 200 Hz carrier over xfade
        dict(dur_s=280, beat_start=2.3, beat_end=4.5,
             carrier_start=200, carrier_end=200,
             beat_jitter=True, log_sweep=True,
             noise_type='pink', noise_vol=0.20, sr_noise=True,
             gamma_vol=0.05, gamma_carrier=255, cfc=False,
             infra_hz=0.04, infra_depth=0.06,
             volume=0.80),
    ]
    return stream_session("02_MEDITATION_Void_40min.flac", phases,
                          fade_in_s=5.0, fade_out_s=6.0)


# ═══════════════════════════════════════════════════════════════════════
# SESSION 3 — СОН / ВЫХОД (120 MIN)
# "ОКНА ОСОЗНАНИЯ"
#
# Architecture: descent → deep sink → 3× [hold | window open | window close]
# Window B = functional OBE trigger: rapid beat jump + CFC gamma spike
# Keep layers minimal — complex DSP can disrupt natural sleep architecture.
# ASSR only in descent. Schumann in holds. CFC only at Window B.
#
# Duration:
#   descent:   600+600      = 1200s
#   deep_sink: 1200         = 1200s
#   cycle 1-2: 2×1800       = 3600s
#   cycle 3:   600+300+300  = 1200s
#   TOTAL:                    7200s = 120 min ✓
# ═══════════════════════════════════════════════════════════════════════

def session_sleep() -> str:
    print("\n[3/4] СОН — Окна Осознания (120 min)")

    def awareness_cycle(base_carrier: float) -> list:
        c = base_carrier
        return [
            # A — DEEP HOLD (20 min)
            #     Schumann stack on brown noise, anti_adapt, beat_jitter
            dict(dur_s=1200, beat_start=2.0, beat_end=2.0,
                 carrier_start=c, carrier_end=c,
                 beat_jitter=True, beat_jitter_depth=0.10,
                 anti_adapt=True, adapt_depth=0.6,
                 noise_type='brown', noise_vol=0.28, sr_noise=True,
                 schumann_stack=True,
                 infra_hz=0.035, infra_depth=0.08,
                 volume=0.75),

            # B — WINDOW OPEN (5 min) — OBE trigger
            #     Rapid beat jump 2→6 Hz + CFC gamma surge = max cortical activation
            #     infra off (clarity needed), carrier shifts +1 Hz (perceptual novelty)
            dict(dur_s=300, beat_start=2.0, beat_end=6.0,
                 carrier_start=c, carrier_end=c + 1.0,
                 beat_jitter=True, log_sweep=True,
                 noise_type='brown', noise_vol=0.20, sr_noise=True,
                 gamma_vol=0.11, gamma_carrier=255, cfc=True,
                 xfade_ms=250,
                 volume=0.78),

            # C — WINDOW CLOSE (5 min) — graceful descent, gamma trails
            dict(dur_s=300, beat_start=6.0, beat_end=2.0,
                 carrier_start=c + 1.0, carrier_end=c,
                 beat_jitter=True, log_sweep=True,
                 noise_type='brown', noise_vol=0.25, sr_noise=True,
                 schumann_stack=True,
                 gamma_vol=0.06, gamma_carrier=252, cfc=False,
                 infra_hz=0.04, infra_depth=0.07,
                 volume=0.75),
        ]

    phases = [
        # DESCENT  0–20 min — ASSR on for cortical priming before sleep
        dict(dur_s=600, beat_start=9.0, beat_end=5.5,
             carrier_start=200, carrier_end=200,
             beat_jitter=True, log_sweep=True,
             noise_type='pink', noise_vol=0.22, sr_noise=True,
             assr_vol=0.04,
             volume=0.82),
        dict(dur_s=600, beat_start=5.5, beat_end=3.0,
             carrier_start=200, carrier_end=200,
             beat_jitter=True, log_sweep=True,
             noise_type='brown', noise_vol=0.25, sr_noise=True,
             assr_vol=0.03,
             volume=0.80),

        # INITIAL DEEP SINK  20–40 min
        dict(dur_s=1200, beat_start=3.0, beat_end=2.0,
             carrier_start=200, carrier_end=200,
             beat_jitter=True, log_sweep=True,
             noise_type='brown', noise_vol=0.28, sr_noise=True,
             infra_hz=0.04, infra_depth=0.08,
             volume=0.76),
    ]

    # 3 awareness cycles — carrier shifts per cycle (anti-habituation over 2h)
    phases += awareness_cycle(201.0)
    phases += awareness_cycle(202.5)

    # Cycle 3: A-phase shortened to 600s for exact 120 min total
    c3 = 204.0
    phases += [
        dict(dur_s=600, beat_start=2.0, beat_end=2.0,
             carrier_start=c3, carrier_end=c3,
             beat_jitter=True, beat_jitter_depth=0.10,
             anti_adapt=True, adapt_depth=0.6,
             noise_type='brown', noise_vol=0.28, sr_noise=True,
             schumann_stack=True,
             infra_hz=0.035, infra_depth=0.08,
             volume=0.75),
        dict(dur_s=300, beat_start=2.0, beat_end=6.0,
             carrier_start=c3, carrier_end=c3 + 1.0,
             beat_jitter=True, log_sweep=True,
             noise_type='brown', noise_vol=0.20, sr_noise=True,
             gamma_vol=0.11, gamma_carrier=255, cfc=True,
             xfade_ms=250, volume=0.78),
        dict(dur_s=300, beat_start=6.0, beat_end=2.5,
             carrier_start=c3 + 1.0, carrier_end=c3,
             beat_jitter=True,
             noise_type='brown', noise_vol=0.25, sr_noise=True,
             schumann_stack=True,
             gamma_vol=0.06, gamma_carrier=252,
             infra_hz=0.04, infra_depth=0.07,
             volume=0.75),
    ]

    total_s = sum(p['dur_s'] for p in phases)
    print(f"    Total: {total_s/60:.1f} min ({len(phases)} phases)")
    return stream_session("03_SLEEP_Windows_120min.flac", phases,
                          fade_in_s=8.0, fade_out_s=10.0)


# ═══════════════════════════════════════════════════════════════════════
# SESSION 4 — DIVINE (45 MIN)
# "АРХИТЕКТ — ОПЕРАТОР МАТРИЦЫ"
#
# Full stack. Every feature active at maximum coherence.
# Carrier: 432 Hz (A432 harmonic reference throughout)
# Entry: 7.83 Hz = Schumann primary
# Sub-gamma: 33 Hz at 175 Hz carrier (phantom = 40-33 = 7 Hz)
# Deep beat: 3.5 Hz = phantom/2 → delta ↔ sub-gamma ↔ gamma resonance stack
# Schumann: all 5 harmonics on noise floor
# Spatial: Ph1-Ph3 (not in deep void — focus needed)
# Pattern break: between Ph3 and Ph4 (7.83 Hz — keeps Schumann reference)
#
# Duration: 480+420+420+20+540+420+240+160 = 2700s = 45 min ✓
# ═══════════════════════════════════════════════════════════════════════

def session_divine() -> str:
    print("\n[4/4] АРХИТЕКТ — Оператор Матрицы (45 min) [DIVINE]")
    phases = [
        # Ph.1  0–8 min   | Schumann sync — Earth resonance entry
        #                   ASSR + dual binaural + spatial from the start
        dict(dur_s=480, beat_start=10.0, beat_end=7.83,
             carrier_start=432, carrier_end=432,
             dual_binaural=True, beat_jitter=True, log_sweep=True,
             noise_type='pink', noise_vol=0.22, sr_noise=True,
             assr_vol=0.05, spatial_hz=0.06, spatial_vol=0.05,
             volume=0.83),

        # Ph.2  8–15 min  | Hold 7.83 Hz — sub-gamma 33 Hz activates
        #                   All 5 Schumann harmonics on noise
        dict(dur_s=420, beat_start=7.83, beat_end=7.83,
             carrier_start=432, carrier_end=433,
             dual_binaural=True, beat_jitter=True,
             noise_type='pink', noise_vol=0.24, sr_noise=True,
             schumann_stack=True,
             iso_beat=33.0, iso_vol=0.07, iso_carrier=175.0,
             assr_vol=0.04, spatial_hz=0.07, spatial_vol=0.05,
             infra_hz=0.05, infra_depth=0.07,
             volume=0.81),

        # Ph.3  15–22 min | Theta descent — CFC begins, dual stays, spatial widens
        dict(dur_s=420, beat_start=7.83, beat_end=4.0,
             carrier_start=433, carrier_end=434,
             dual_binaural=True, beat_jitter=True, log_sweep=True,
             noise_type='brown', noise_vol=0.26, sr_noise=True,
             schumann_stack=True,
             iso_beat=33.0, iso_vol=0.06, iso_carrier=175.0,
             gamma_vol=0.08, gamma_carrier=260, cfc=True,
             spatial_hz=0.09, spatial_vol=0.06,
             infra_hz=0.05, infra_depth=0.08,
             volume=0.79),

        # ⑪ PATTERN BREAK — 20 s @ 7.83 Hz (Schumann reference maintained)
        {**pattern_break(20.0, beat_hz=7.83), 'carrier_override': 432.0, 'xfade_ms': 500},

        # Ph.4  22–31 min | DEEP — 3-way resonance stack
        #                   beat=3.5 Hz = (40-33)/2 → delta:sub-gamma:gamma alignment
        #                   anti_adapt + beat_jitter, spatial OFF (focus)
        dict(dur_s=540, beat_start=4.0, beat_end=3.5,
             carrier_start=434, carrier_end=436,
             dual_binaural=True, beat_jitter=True, log_sweep=True,
             anti_adapt=True, adapt_depth=0.9,
             noise_type='brown', noise_vol=0.30, sr_noise=True,
             schumann_stack=True,
             iso_beat=33.0, iso_vol=0.06, iso_carrier=175.0,
             gamma_vol=0.09, gamma_carrier=260, cfc=True,
             infra_hz=0.04, infra_depth=0.09,
             volume=0.77),

        # Ph.5  31–38 min | VOID POINT — absolute delta + dual gamma lock
        #                   iso trails at minimum (0.04) — barely present
        dict(dur_s=420, beat_start=3.5, beat_end=2.0,
             carrier_start=436, carrier_end=436,
             dual_binaural=True, beat_jitter=True, log_sweep=True,
             beat_jitter_depth=0.08,
             anti_adapt=True, adapt_depth=0.7,
             noise_type='brown', noise_vol=0.30, sr_noise=True,
             schumann_stack=True,
             iso_beat=33.0, iso_vol=0.04, iso_carrier=175.0,
             gamma_vol=0.09, gamma_carrier=260, cfc=True,
             infra_hz=0.035, infra_depth=0.10,
             volume=0.76),

        # Ph.6  38–42 min | Schumann return — re-anchor 2→7.83 Hz
        dict(dur_s=240, beat_start=2.0, beat_end=7.83,
             carrier_start=436, carrier_end=434,
             dual_binaural=True, beat_jitter=True, log_sweep=True,
             noise_type='pink', noise_vol=0.23, sr_noise=True,
             schumann_stack=True,
             gamma_vol=0.06, gamma_carrier=255, cfc=False,
             infra_hz=0.05, infra_depth=0.07,
             volume=0.79),

        # Ph.7  42–45 min | Alpha integration — waking coherence lock
        dict(dur_s=160, beat_start=7.83, beat_end=10.0,
             carrier_start=434, carrier_end=432,
             dual_binaural=True, beat_jitter=True,
             noise_type='pink', noise_vol=0.20, sr_noise=True,
             assr_vol=0.04,
             volume=0.83),
    ]
    return stream_session("04_DIVINE_Architect_45min.flac", phases,
                          fade_in_s=5.0, fade_out_s=6.0)


# ═══════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    t0 = time.time()
    print("═" * 66)
    print("  OPERATOR MATRIX v3.0 — Psychoacoustic Engineering Suite")
    print(f"  SR: {SR} Hz | {BD} FLAC | Stereo | Non-deterministic RNG")
    print(f"  SR_RATIO: {SR_RATIO} ({20*np.log10(SR_RATIO):.1f} dB) | "
          f"SCHUMANN: {list(SCHUMANN_HZ)}")
    print(f"  Output: {OUT}")
    print("═" * 66)

    files = [
        session_walk(),
        session_meditation(),
        session_sleep(),
        session_divine(),
    ]

    elapsed  = time.time() - t0
    total_mb = sum(os.path.getsize(p) / 1024 / 1024 for p in files)

    print("\n" + "═" * 66)
    print(f"  ALL SESSIONS COMPLETE")
    print(f"  Elapsed: {elapsed:.0f}s | Total: {total_mb:.1f} MB | Files: {len(files)}")
    print("═" * 66)