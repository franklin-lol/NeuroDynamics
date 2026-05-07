#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║  GENESIS v3 — Psychoacoustic Engineering  ║ ROCKET EDITION  ║
╠══════════════════════════════════════════════════════════════╣
║  65 min | 44100 Hz | FLAC PCM-24 | Stereo                   ║
╚══════════════════════════════════════════════════════════════╝

USAGE:
  python genesis_v3.py                     # default: GENESIS profile
  python genesis_v3.py --profile HEALER    # deep delta / restoration
  python genesis_v3.py --profile ORACLE    # theta / Schumann focus
  python genesis_v3.py --profile WARRIOR   # beta/gamma / activation
  python genesis_v3.py --map               # print session map only, no render

REQUIRES:
  pip install numpy scipy soundfile

NEW IN v3 vs v2:
  1.  Beat-frequency jitter (±0.2 Hz 1/f) — beat itself is now unpredictable
  2.  Equal-power crossfades (√taper) — no loudness dip at transitions
  3.  Cross-Frequency Coupling (CFC) — theta envelope modulates gamma amplitude
      mirrors real theta-gamma phase-amplitude coupling in hippocampus
  4.  ASSR 80 Hz layer — independent brainstem + cortical entrainment pathway
  5.  Spatial ITD rotation — slow inter-aural phase sweep, vestibular engagement
  6.  Infra-modulation (0.033–0.1 Hz) — signal breathes, ANS entrainment
  7.  Stochastic Resonance optimization — noise amplitude = 15% of signal RMS
      SR theory: optimal noise improves sub-threshold signal detection
  8.  Solfeggio carrier cascade: 200→432→528→639→432→200 Hz across session
  9.  4 session profiles (GENESIS / HEALER / ORACLE / WARRIOR)
 10.  Session map export — full phase log written to .txt alongside FLAC
"""

import numpy as np
from scipy.signal import lfilter
import soundfile as sf
import os, sys, argparse, textwrap
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

SR       = 44100
OUT_DIR  = os.path.dirname(os.path.abspath(__file__))

# ══════════════════════════════════════════════════════════
#  SECTION 1 — NOISE GENERATORS
# ══════════════════════════════════════════════════════════

def _rng(seed: int) -> np.random.RandomState:
    return np.random.RandomState(seed)

def pink_noise(n: int, seed: int = 0) -> np.ndarray:
    """1/f pink noise — Voss-McCartney IIR"""
    b = [0.049922035, -0.095993537, 0.050612699, -0.004408786]
    a = [1.0, -2.494956002,  2.017265875, -0.522189400]
    raw = _rng(seed).standard_normal(n)
    return lfilter(b, a, raw).astype(np.float32)

def brown_noise(n: int, seed: int = 0) -> np.ndarray:
    """1/f² brown noise"""
    x = np.cumsum(_rng(seed).standard_normal(n) * 0.02).astype(np.float32)
    return x - x.mean()

def morph_noise(n: int, pw: float, bw: float, seed: int = 0) -> np.ndarray:
    """Blend pink (pw) and brown (bw) noise, normalised."""
    p = pink_noise(n, seed);    p /= (np.max(np.abs(p)) + 1e-9)
    b = brown_noise(n, seed+1); b /= (np.max(np.abs(b)) + 1e-9)
    m = p * pw + b * bw
    return (m / (np.max(np.abs(m)) + 1e-9)).astype(np.float32)

# ══════════════════════════════════════════════════════════
#  SECTION 2 — FREQUENCY SWEEP PRIMITIVES
# ══════════════════════════════════════════════════════════

def log_sweep(a: float, b: float, n: int) -> np.ndarray:
    """Perceptually-linear (logarithmic) frequency ramp."""
    if a <= 0 or b <= 0:
        return np.linspace(a, b, n, dtype=np.float64)
    return np.exp(np.linspace(np.log(a), np.log(b), n)).astype(np.float64)

# NEW v3 — beat jitter: adds ±depth Hz 1/f noise to the beat envelope
def jitter_envelope(sweep: np.ndarray, depth: float, seed: int) -> np.ndarray:
    """Apply ±depth Hz 1/f jitter to a frequency envelope array."""
    drift = pink_noise(len(sweep), seed).astype(np.float64)
    drift /= (np.max(np.abs(drift)) + 1e-9)
    return sweep + drift * depth

def build_carrier(c0: float, c1: float, n: int,
                  jitter_depth: float = 2.0, seed: int = 0) -> np.ndarray:
    """Carrier envelope with 1/f drift."""
    base = np.linspace(c0, c1, n, dtype=np.float64)
    drift = pink_noise(n, seed+200).astype(np.float64)
    drift /= (np.max(np.abs(drift)) + 1e-9)
    return base + drift * jitter_depth

# ══════════════════════════════════════════════════════════
#  SECTION 3 — BINAURAL ENGINE
#  Dual octave pair + beat jitter + phase-accurate integration
# ══════════════════════════════════════════════════════════

def dual_binaural(dur_s: float,
                  c0: float, c1: float,
                  b0: float, b1: float,
                  vol_p: float = 0.60,
                  vol_s: float = 0.22,
                  carrier_jitter: float = 2.0,
                  beat_jitter: float = 0.15,    # NEW v3
                  seed: int = 0) -> Tuple[np.ndarray, np.ndarray]:
    """
    Primary pair:   C (jittered)  |  C + B (beat-jittered)
    Secondary pair: C×2           |  C×2 + B/2
    Beat jitter on both primary and secondary.
    """
    n  = int(dur_s * SR)
    C  = build_carrier(c0, c1, n, carrier_jitter, seed)
    C2 = C * 2.0

    B_raw = log_sweep(b0, b1, n)
    B     = jitter_envelope(B_raw, beat_jitter,   seed+50)  # primary beat jitter
    B2    = jitter_envelope(B_raw / 2.0, beat_jitter*0.5, seed+51)

    pL  = 2*np.pi * np.cumsum(C)       / SR
    pR  = 2*np.pi * np.cumsum(C  + B)  / SR
    pL2 = 2*np.pi * np.cumsum(C2)      / SR
    pR2 = 2*np.pi * np.cumsum(C2 + B2) / SR

    L = (np.sin(pL)*vol_p + np.sin(pL2)*vol_s).astype(np.float32)
    R = (np.sin(pR)*vol_p + np.sin(pR2)*vol_s).astype(np.float32)
    return L, R

# ══════════════════════════════════════════════════════════
#  SECTION 4 — ISOCHRONIC ENGINE (dynamic envelope)
# ══════════════════════════════════════════════════════════

def isochronic(dur_s: float, freq: float,
               carrier: float = 200.0, vol: float = 0.14,
               attack_s: float = 4.0, decay_s: float = 4.0) -> np.ndarray:
    """Hard-edge iso with hanning anti-click + dynamic envelope."""
    if freq <= 0:
        return np.zeros(int(dur_s * SR), dtype=np.float32)
    n = int(dur_s * SR)
    t = np.arange(n, dtype=np.float64) / SR
    gate = (np.sin(2*np.pi*freq*t) >= 0).astype(np.float32)
    rn = int(0.006 * SR)
    if rn > 1:
        h = np.hanning(rn*2).astype(np.float32); h /= h.sum()
        gate = np.convolve(gate, h, mode='same')
    env = np.ones(n, dtype=np.float32)
    atk = min(int(attack_s*SR), n//3)
    dec = min(int(decay_s*SR),  n//3)
    if atk: env[:atk]  *= np.linspace(0, 1, atk, dtype=np.float32)
    if dec: env[-dec:] *= np.linspace(1, 0, dec, dtype=np.float32)
    return (np.sin(2*np.pi*carrier*t) * gate * env * vol).astype(np.float32)

# ══════════════════════════════════════════════════════════
#  SECTION 5 — NEW v3 DSP LAYERS
# ══════════════════════════════════════════════════════════

# ── 5.1  CROSS-FREQUENCY COUPLING (CFC)
#
#  In the brain: slow oscillations (theta 4–8 Hz) phase-modulate the
#  AMPLITUDE of fast oscillations (gamma 30–80 Hz). This is called
#  Theta-Gamma Phase-Amplitude Coupling (PAC) and underlies:
#    • Working memory (Lisman & Jensen 2013)
#    • Conscious integration across brain areas
#    • Hippocampal-prefrontal communication
#
#  Implementation: multiply gamma signal by theta-frequency envelope
#  strength=0.5 means gamma oscillates 50%→150% amplitude with theta.

def apply_cfc(gamma_sig: np.ndarray, dur_s: float,
              theta_freq: float = 6.0, strength: float = 0.5) -> np.ndarray:
    """Apply theta→gamma phase-amplitude coupling."""
    n = len(gamma_sig)
    t = np.arange(n, dtype=np.float64) / SR
    theta_env = 1.0 - strength + strength * (0.5 + 0.5*np.sin(2*np.pi*theta_freq*t))
    return (gamma_sig * theta_env.astype(np.float32))

# ── 5.2  ASSR 80 Hz LAYER
#
#  Auditory Steady-State Response: the brain generates synchronised
#  oscillations locked to periodic auditory stimuli. 40 Hz (gamma) ASSR
#  is generated in auditory cortex. 80 Hz ASSR is generated independently
#  in the cochlear nucleus + inferior colliculus (brainstem).
#  Adding both creates TWO separate cortical entrainment pathways.

def assr_80hz(dur_s: float, carrier: float = 200.0,
              vol: float = 0.05) -> np.ndarray:
    """80 Hz isochronic — ASSR brainstem pathway (keep very quiet: 3-6%)."""
    return isochronic(dur_s, 80.0, carrier, vol, attack_s=6.0, decay_s=6.0)

# ── 5.3  SPATIAL ITD ROTATION
#
#  Inter-Aural Time Delay (ITD) rotation: slowly sweeping the phase
#  relationship between L and R creates a perceived movement of the
#  sound image in 3D space. This:
#    • Engages spatial processing circuits (dorsal auditory stream)
#    • Activates vestibular-adjacent circuits
#    • Adds another dimension of anti-adaptation
#  period_s: time for one full 360° rotation (recommend 8–15s)

def spatial_rotation(L: np.ndarray, R: np.ndarray,
                     period_s: float = 12.0) -> Tuple[np.ndarray, np.ndarray]:
    """Slow inter-aural phase rotation — perceived 3D spatial movement."""
    n = len(L)
    t = np.arange(n, dtype=np.float64) / SR
    theta = 2*np.pi * t / period_s          # rotation angle
    cos_t = np.cos(theta).astype(np.float32)
    sin_t = np.sin(theta).astype(np.float32)
    L_rot = L * cos_t - R * sin_t
    R_rot = L * sin_t + R * cos_t
    return L_rot, R_rot

# ── 5.4  INFRA-MODULATION
#
#  Very slow (0.033–0.1 Hz) amplitude modulation of the full signal.
#  At 0.067 Hz → ~4 complete cycles per minute (deep meditative breathing).
#  Engages Autonomic Nervous System (ANS) via respiratory entrainment.
#  depth: 0.15 means signal breathes ±15% amplitude.

def infra_modulate(L: np.ndarray, R: np.ndarray,
                   freq_hz: float = 0.067, depth: float = 0.15,
                   phase_offset: float = 0.0) -> Tuple[np.ndarray, np.ndarray]:
    """Infra-frequency AM — the signal breathes."""
    n = len(L)
    t = np.arange(n, dtype=np.float64) / SR
    mod = (1.0 - depth + depth * np.sin(2*np.pi*freq_hz*t + phase_offset))
    mod = mod.astype(np.float32)
    return L * mod, R * mod

# ── 5.5  STOCHASTIC RESONANCE NOISE CALIBRATION
#
#  Stochastic Resonance (SR) theory: in nonlinear systems, an OPTIMAL
#  amount of noise actually IMPROVES signal detection — noise helps
#  sub-threshold signals cross detection threshold.
#  For neural entrainment: optimal noise ≈ 10–20% of signal RMS.
#  We compute actual entrainment RMS and set noise to SR_RATIO * RMS.

SR_RATIO = 0.15  # target: noise = 15% of signal RMS

def calibrated_noise(signal_L: np.ndarray, signal_R: np.ndarray,
                     pw: float, bw: float, seed: int = 0) -> np.ndarray:
    """Generate noise at stochastic-resonance-optimal amplitude."""
    n = len(signal_L)
    sig_rms = np.sqrt(np.mean(signal_L**2 + signal_R**2) / 2)
    nz = morph_noise(n, pw, bw, seed)
    nz_rms = np.sqrt(np.mean(nz**2)) + 1e-9
    target_rms = sig_rms * SR_RATIO
    return (nz * (target_rms / nz_rms)).astype(np.float32)

# ── 5.6  SCHUMANN HARMONIC STACK (upgraded from v2)
#  All 5 measured Schumann resonances as simultaneous binaural pairs
#  with individual beat jitter per harmonic

SCHUMANN_FREQS = [7.83, 14.3, 20.8, 27.3, 33.8]

def schumann_stack(dur_s: float, carrier: float = 432.0,
                   base_vol: float = 0.20, seed: int = 0) -> Tuple[np.ndarray, np.ndarray]:
    n = int(dur_s * SR)
    L = np.zeros(n, np.float32); R = np.zeros(n, np.float32)
    for i, freq in enumerate(SCHUMANN_FREQS):
        v = base_vol * (0.70 ** i)
        lv, rv = dual_binaural(dur_s, carrier, carrier, freq, freq,
                               vol_p=v, vol_s=v*0.25,
                               carrier_jitter=0.3,
                               beat_jitter=0.05,
                               seed=seed+i*10)
        L += lv; R += rv
    return L, R

# ══════════════════════════════════════════════════════════
#  SECTION 6 — EQUAL-POWER CROSSFADE ENGINE
#  v2 used LINEAR taper → 3dB loudness dip at midpoint
#  v3 uses √ taper → constant perceived loudness (equal-power)
# ══════════════════════════════════════════════════════════

def eq_power_fade(n: int) -> Tuple[np.ndarray, np.ndarray]:
    """Returns (fade_out, fade_in) equal-power tapers."""
    t = np.linspace(0.0, np.pi/2, n, dtype=np.float32)
    return np.cos(t), np.sin(t)   # cos² + sin² = 1

def crossfade_write(fh, prev_tail, new_L: np.ndarray, new_R: np.ndarray,
                    fade_s: float = 8.0):
    """
    Equal-power crossfade write to SoundFile handle.
    Returns new tail (last fade_s seconds) for next call.
    """
    fn = min(int(fade_s * SR), len(new_L) // 4)

    if fn < 2 or prev_tail is None:
        # First block: write body, hold tail
        body_L = new_L[:-fn] if fn > 0 else new_L
        body_R = new_R[:-fn] if fn > 0 else new_R
        if len(body_L): fh.write(np.stack([body_L, body_R], axis=1))
        return (new_L[-fn:].copy(), new_R[-fn:].copy()) if fn > 0 else (None, None)

    pL, pR = prev_tail
    fn = min(fn, len(pL), len(new_L))

    fo, fi = eq_power_fade(fn)   # equal-power tapers

    # Blend zone
    xL = pL[:fn] * fo + new_L[:fn] * fi
    xR = pR[:fn] * fo + new_R[:fn] * fi
    fh.write(np.stack([xL, xR], axis=1))

    # Body (skip first fn, hold last fn as next tail)
    body_L = new_L[fn:-fn] if len(new_L) > 2*fn else np.array([], np.float32)
    body_R = new_R[fn:-fn] if len(new_R) > 2*fn else np.array([], np.float32)
    if len(body_L): fh.write(np.stack([body_L, body_R], axis=1))

    tail_L = new_L[-fn:].copy()
    tail_R = new_R[-fn:].copy()
    return tail_L, tail_R

# ══════════════════════════════════════════════════════════
#  SECTION 7 — BLOCK DATA CLASS
# ══════════════════════════════════════════════════════════

@dataclass
class Block:
    label:         str
    dur_s:         float
    # Binaural
    c0:            float = 200.0  # carrier start
    c1:            float = None   # carrier end (defaults to c0)
    b0:            float = 10.0   # beat start
    b1:            float = None   # beat end (defaults to b0)
    carrier_jitter:float = 2.0
    beat_jitter:   float = 0.15
    # Noise
    noise_pw:      float = 0.5    # pink weight
    noise_bw:      float = 0.1    # brown weight
    # Isochronic layers: (freq, carrier, vol, attack_s, decay_s)
    iso_layers:    List  = field(default_factory=list)
    # v3 features
    cfc_theta:     float = 0.0    # 0 = off; >0 = theta freq for CFC
    cfc_strength:  float = 0.4
    itd_period:    float = 0.0    # 0 = off; rotation period in seconds
    infra_freq:    float = 0.0    # 0 = off
    infra_depth:   float = 0.12
    assr_80hz_vol: float = 0.0    # 0 = off
    schumann_mode: bool  = False  # use schumann_stack() as base
    seed:          int   = 0

    def __post_init__(self):
        if self.c1 is None: self.c1 = self.c0
        if self.b1 is None: self.b1 = self.b0

    def render(self) -> Tuple[np.ndarray, np.ndarray]:
        n = int(self.dur_s * SR)

        # ── Base signal
        if self.schumann_mode:
            L, R = schumann_stack(self.dur_s, self.c0,
                                  base_vol=0.20, seed=self.seed)
            # Add primary binaural underneath
            bL, bR = dual_binaural(self.dur_s, self.c0, self.c1,
                                   self.b0, self.b1,
                                   vol_p=0.25, vol_s=0.10,
                                   carrier_jitter=self.carrier_jitter,
                                   beat_jitter=self.beat_jitter,
                                   seed=self.seed+1)
            L += bL; R += bR
        else:
            L, R = dual_binaural(self.dur_s, self.c0, self.c1,
                                 self.b0, self.b1,
                                 vol_p=0.60, vol_s=0.22,
                                 carrier_jitter=self.carrier_jitter,
                                 beat_jitter=self.beat_jitter,
                                 seed=self.seed)

        # ── Isochronic layers (with optional CFC on gamma)
        for (freq_v, c_v, vol_v, atk, dec) in self.iso_layers:
            sig = isochronic(self.dur_s, freq_v, c_v, vol_v, atk, dec)
            # Apply CFC only to gamma (>30 Hz)
            if self.cfc_theta > 0 and freq_v >= 30.0:
                sig = apply_cfc(sig, self.dur_s,
                                self.cfc_theta, self.cfc_strength)
            L += sig; R += sig

        # ── ASSR 80 Hz
        if self.assr_80hz_vol > 0:
            a80 = assr_80hz(self.dur_s, carrier=200.0, vol=self.assr_80hz_vol)
            if self.cfc_theta > 0:
                a80 = apply_cfc(a80, self.dur_s, self.cfc_theta,
                                self.cfc_strength * 0.5)
            L += a80; R += a80

        # ── Stochastic-resonance calibrated noise
        nz = calibrated_noise(L, R, self.noise_pw, self.noise_bw, self.seed+300)
        L += nz; R += nz

        # ── Spatial ITD rotation
        if self.itd_period > 0:
            L, R = spatial_rotation(L, R, self.itd_period)

        # ── Infra-modulation
        if self.infra_freq > 0:
            L, R = infra_modulate(L, R, self.infra_freq,
                                  self.infra_depth,
                                  phase_offset=self.seed * 0.7)

        # ── Clip + normalize
        peak = max(np.max(np.abs(L)), np.max(np.abs(R))) + 1e-9
        if peak > 0.93:
            L = (L / peak * 0.90).astype(np.float32)
            R = (R / peak * 0.90).astype(np.float32)

        return L, R

# ══════════════════════════════════════════════════════════
#  SECTION 8 — SESSION PROFILES
#
#  Solfeggio carrier cascade per session:
#  GENESIS:  200 → 432 → 528 → 639 → 432 → 200
#  HEALER:   432 → 528 → 528 → 528 → 432 → 432
#  ORACLE:   432 → 432 → 432 → 432 → 432 → 432
#  WARRIOR:  200 → 200 → 432 → 432 → 200 → 200
# ══════════════════════════════════════════════════════════

def build_profile(name: str) -> List[Block]:

    if name == 'GENESIS':
        return [
            # ── B1  IGNITION  (0–5 min)
            # Hard gamma open. 80 Hz ASSR from second 1.
            # Carrier sweeps 200→432 Hz (transitions to Earth tuning).
            # ITD rotation: 12s period — immediate spatial activation.
            Block(
                label='IGNITION', dur_s=300,
                c0=200, c1=432, b0=36.0, b1=40.0,
                carrier_jitter=0.8, beat_jitter=0.08,
                noise_pw=1.0, noise_bw=0.0,
                iso_layers=[
                    (40.0, 200, 0.11, 5, 6),
                ],
                assr_80hz_vol=0.05,
                itd_period=12.0,
                infra_freq=0.0,
                seed=1
            ),
            # ── B2  EARTH SYNC  (5–13 min)
            # All 5 Schumann harmonics. 432 Hz carrier.
            # CFC starts: theta 7.83 Hz modulates gamma amplitude.
            # Infra-mod: 0.1 Hz (6 breaths/min — slow transition).
            Block(
                label='EARTH SYNC — SCHUMANN STACK', dur_s=480,
                c0=432, c1=432, b0=7.83, b1=7.83,
                carrier_jitter=0.3, beat_jitter=0.06,
                noise_pw=0.8, noise_bw=0.2,
                iso_layers=[
                    (14.3, 216, 0.07, 10, 10),   # Schumann 2nd harmonic
                    (40.0, 200, 0.06, 12,  8),   # gamma anchor
                ],
                cfc_theta=7.83, cfc_strength=0.3,
                assr_80hz_vol=0.04,
                infra_freq=0.10, infra_depth=0.12,
                schumann_mode=True,
                seed=2
            ),
            # ── B3  THETA GATEWAY  (13–22 min)
            # 7.83→4.5 Hz log descent. Carrier 432→528 Hz (Solfeggio MI).
            # CFC strengthens. Polyrhythmic iso: 6.0 + 40 Hz (irrational ratio).
            # Beat jitter peaks here — most unpredictable phase.
            Block(
                label='THETA GATEWAY', dur_s=540,
                c0=432, c1=528, b0=7.83, b1=4.5,
                carrier_jitter=1.8, beat_jitter=0.20,
                noise_pw=0.6, noise_bw=0.4,
                iso_layers=[
                    (6.0,  264, 0.12, 12, 10),  # 264 = 528/2
                    (40.0, 200, 0.07, 15,  5),
                ],
                cfc_theta=6.0, cfc_strength=0.45,
                assr_80hz_vol=0.04,
                itd_period=15.0,
                infra_freq=0.08, infra_depth=0.13,
                seed=3
            ),
            # ── B4  DELTA APPROACH  (22–31 min)
            # 4.5→2.0 Hz. Carrier holds 528 Hz.
            # ISO guide FADES OUT over 20s — clear handover to void.
            # Brown noise dominant. CFC max.
            Block(
                label='DELTA APPROACH', dur_s=540,
                c0=528, c1=528, b0=4.5, b1=2.0,
                carrier_jitter=2.5, beat_jitter=0.22,
                noise_pw=0.2, noise_bw=0.8,
                iso_layers=[
                    (4.5,  264, 0.10,  5, 25),  # iso fades OUT
                    (40.0, 200, 0.07,  5,  8),
                ],
                cfc_theta=5.5, cfc_strength=0.50,
                assr_80hz_vol=0.05,
                infra_freq=0.067, infra_depth=0.14,
                seed=4
            ),
            # ── B5  VOID CORE  (31–43 min)
            # 1.5 Hz FIXED — deepest functional delta.
            # Triple gamma: 33+40+80 Hz. 33+40 → 7 Hz phantom inter-mod.
            # CFC at peak. Maximum carrier jitter.
            # Infra-mod at 0.033 Hz (ultra-slow, 1 cycle/30s).
            # No iso guide — pure void with consciousness.
            Block(
                label='VOID CORE — 1.5 Hz DELTA', dur_s=720,
                c0=528, c1=528, b0=1.5, b1=1.5,
                carrier_jitter=3.0, beat_jitter=0.10,
                noise_pw=0.05, noise_bw=0.95,
                iso_layers=[
                    (33.0, 180, 0.06, 20, 20),
                    (40.0, 200, 0.08, 20, 20),
                ],
                cfc_theta=5.0, cfc_strength=0.55,
                assr_80hz_vol=0.05,
                itd_period=18.0,
                infra_freq=0.033, infra_depth=0.15,
                seed=5
            ),
            # ── B6  ASCENT SURGE  (43–49 min)
            # Hard re-entry: 1.5→12 Hz. Carrier 528→639 Hz (Solfeggio FA).
            # Spatial rotation speeds up (6s period) — activating.
            # All gamma layers at maximum.
            Block(
                label='ASCENT SURGE — 639 Hz', dur_s=360,
                c0=528, c1=639, b0=1.5, b1=12.0,
                carrier_jitter=1.5, beat_jitter=0.18,
                noise_pw=0.9, noise_bw=0.1,
                iso_layers=[
                    (40.0, 200, 0.13,  3, 5),
                    (33.0, 216, 0.08,  3, 5),
                ],
                cfc_theta=6.0, cfc_strength=0.35,
                assr_80hz_vol=0.06,
                itd_period=6.0,
                infra_freq=0.10, infra_depth=0.10,
                seed=6
            ),
            # ── B7  SCHUMANN INTEGRATION  (49–57 min)
            # 12→7.83 Hz return. Carrier 639→432 Hz.
            # ISO matches binaural beat freq → max entrainment.
            # CFC active (gamma learning + consolidation).
            Block(
                label='SCHUMANN INTEGRATION', dur_s=480,
                c0=639, c1=432, b0=12.0, b1=7.83,
                carrier_jitter=1.2, beat_jitter=0.12,
                noise_pw=0.85, noise_bw=0.15,
                iso_layers=[
                    (7.83, 432, 0.09,  6,  6),  # iso=binaural freq
                    (40.0, 200, 0.09,  6, 10),
                ],
                cfc_theta=7.83, cfc_strength=0.40,
                assr_80hz_vol=0.05,
                itd_period=12.0,
                infra_freq=0.083, infra_depth=0.11,
                seed=7
            ),
            # ── B8  ACTIVATION LOCK  (57–63 min)
            # 7.83→30 Hz. Carrier 432→200 Hz (return to neutral).
            # Full beta/gamma lock. 80 Hz ASSR peak.
            Block(
                label='ACTIVATION LOCK', dur_s=360,
                c0=432, c1=200, b0=7.83, b1=30.0,
                carrier_jitter=0.8, beat_jitter=0.10,
                noise_pw=1.0, noise_bw=0.0,
                iso_layers=[
                    (40.0, 200, 0.13,  5, 3),
                    (30.0, 216, 0.09,  8, 3),
                ],
                assr_80hz_vol=0.07,
                itd_period=9.0,
                infra_freq=0.0,
                seed=8
            ),
        ]

    elif name == 'HEALER':
        # Deep delta focus. 528 Hz dominant. Slower arc.
        return [
            Block(label='HEALER — OPEN',     dur_s=360, c0=528, c1=528,
                  b0=10.0, b1=6.0,  noise_pw=0.9, noise_bw=0.1,
                  iso_layers=[(6.0,264,0.10,8,8)], cfc_theta=6.0,
                  infra_freq=0.10, seed=11),
            Block(label='HEALER — DESCENT',  dur_s=600, c0=528, c1=528,
                  b0=6.0,  b1=2.0,  noise_pw=0.4, noise_bw=0.6,
                  iso_layers=[(5.0,264,0.09,10,15),(40.0,200,0.06,12,8)],
                  cfc_theta=5.0, cfc_strength=0.5,
                  infra_freq=0.067, infra_depth=0.15, seed=12),
            Block(label='HEALER — VOID 1',   dur_s=900, c0=528, c1=528,
                  b0=1.5,  b1=1.5,  noise_pw=0.0, noise_bw=1.0,
                  iso_layers=[(40.0,200,0.07,20,20),(33.0,180,0.05,25,25)],
                  cfc_theta=5.0, cfc_strength=0.6,
                  assr_80hz_vol=0.04,
                  infra_freq=0.033, infra_depth=0.16, seed=13),
            Block(label='HEALER — VOID 2',   dur_s=900, c0=528, c1=528,
                  b0=1.5,  b1=1.5,  noise_pw=0.0, noise_bw=1.0,
                  iso_layers=[(40.0,200,0.07,20,20)],
                  cfc_theta=4.5, cfc_strength=0.65,
                  assr_80hz_vol=0.04,
                  infra_freq=0.025, infra_depth=0.16, seed=14),
            Block(label='HEALER — RETURN',   dur_s=540, c0=528, c1=432,
                  b0=1.5,  b1=8.0,  noise_pw=0.8, noise_bw=0.2,
                  iso_layers=[(40.0,200,0.10,5,5)],
                  cfc_theta=6.0, cfc_strength=0.3,
                  infra_freq=0.083, seed=15),
            Block(label='HEALER — INTEGRATE',dur_s=300, c0=432, c1=432,
                  b0=8.0,  b1=12.0, noise_pw=1.0, noise_bw=0.0,
                  iso_layers=[(40.0,200,0.11,5,3)],
                  assr_80hz_vol=0.05, seed=16),
        ]

    elif name == 'ORACLE':
        # Schumann/theta focus. 432 Hz throughout.
        return [
            Block(label='ORACLE — SCHUMANN',  dur_s=600, c0=432, c1=432,
                  b0=7.83, b1=7.83, schumann_mode=True,
                  iso_layers=[(7.83,432,0.08,10,10)],
                  cfc_theta=7.83, cfc_strength=0.35,
                  infra_freq=0.083, infra_depth=0.12, seed=21),
            Block(label='ORACLE — THETA 1',   dur_s=720, c0=432, c1=432,
                  b0=7.83, b1=5.0, noise_pw=0.7, noise_bw=0.3,
                  iso_layers=[(6.0,216,0.11,12,10),(40.0,200,0.06,15,8)],
                  cfc_theta=6.0, cfc_strength=0.5,
                  itd_period=15.0,
                  infra_freq=0.067, seed=22),
            Block(label='ORACLE — THETA 2',   dur_s=720, c0=432, c1=432,
                  b0=5.0,  b1=4.0, noise_pw=0.5, noise_bw=0.5,
                  iso_layers=[(5.0,216,0.10,10,10),(40.0,200,0.07,12,8)],
                  cfc_theta=5.0, cfc_strength=0.55,
                  assr_80hz_vol=0.04,
                  infra_freq=0.05, infra_depth=0.14, seed=23),
            Block(label='ORACLE — SCHUMANN RETURN', dur_s=600, c0=432, c1=432,
                  b0=4.0, b1=7.83, schumann_mode=True,
                  iso_layers=[(7.83,432,0.09,8,8),(40.0,200,0.08,8,6)],
                  cfc_theta=7.83, cfc_strength=0.35,
                  itd_period=12.0,
                  infra_freq=0.083, seed=24),
            Block(label='ORACLE — SEAL',       dur_s=360, c0=432, c1=432,
                  b0=7.83, b1=14.0, noise_pw=1.0, noise_bw=0.0,
                  iso_layers=[(40.0,200,0.12,5,3),(14.0,216,0.08,8,3)],
                  assr_80hz_vol=0.05, seed=25),
        ]

    elif name == 'WARRIOR':
        # Beta/gamma dominant. Minimal delta. Full activation.
        return [
            Block(label='WARRIOR — CHARGE',  dur_s=300, c0=200, c1=200,
                  b0=30.0, b1=40.0, noise_pw=1.0, noise_bw=0.0,
                  iso_layers=[(40.0,200,0.13,4,5)],
                  assr_80hz_vol=0.07, itd_period=8.0, seed=31),
            Block(label='WARRIOR — PEAK',    dur_s=600, c0=200, c1=432,
                  b0=40.0, b1=40.0, noise_pw=1.0, noise_bw=0.0,
                  iso_layers=[(40.0,200,0.13,5,5),(80.0,200,0.04,8,8)],
                  assr_80hz_vol=0.08, itd_period=6.0, seed=32),
            Block(label='WARRIOR — DESCENT', dur_s=480, c0=432, c1=432,
                  b0=40.0, b1=12.0, noise_pw=0.8, noise_bw=0.2,
                  iso_layers=[(40.0,200,0.12,5,8),(33.0,216,0.07,5,8)],
                  cfc_theta=8.0, cfc_strength=0.30,
                  assr_80hz_vol=0.06, itd_period=8.0, seed=33),
            Block(label='WARRIOR — THETA',   dur_s=480, c0=432, c1=432,
                  b0=12.0, b1=7.83, noise_pw=0.7, noise_bw=0.3,
                  iso_layers=[(40.0,200,0.10,8,8)],
                  cfc_theta=7.83, cfc_strength=0.40,
                  assr_80hz_vol=0.05, seed=34),
            Block(label='WARRIOR — RELOAD',  dur_s=480, c0=432, c1=200,
                  b0=7.83, b1=35.0, noise_pw=1.0, noise_bw=0.0,
                  iso_layers=[(40.0,200,0.13,5,3),(35.0,216,0.09,5,3)],
                  assr_80hz_vol=0.07, itd_period=6.0, seed=35),
            Block(label='WARRIOR — LOCK',    dur_s=300, c0=200, c1=200,
                  b0=35.0, b1=40.0, noise_pw=1.0, noise_bw=0.0,
                  iso_layers=[(40.0,200,0.14,3,2)],
                  assr_80hz_vol=0.08, itd_period=5.0, seed=36),
        ]

    else:
        raise ValueError(f"Unknown profile: {name}. Use GENESIS/HEALER/ORACLE/WARRIOR")


# ══════════════════════════════════════════════════════════
#  SECTION 9 — PATTERN BREAK
# ══════════════════════════════════════════════════════════

def pattern_break(carrier: float = 432.0) -> Tuple[np.ndarray, np.ndarray]:
    """20s neutral 10 Hz — resets cortical prediction, not state."""
    L, R = dual_binaural(20.0, carrier, carrier, 10.0, 10.0,
                         vol_p=0.40, vol_s=0.12,
                         carrier_jitter=0.0, beat_jitter=0.0, seed=999)
    n = int(20 * SR)
    rn = int(3 * SR)
    ramp = np.linspace(0, 1, rn, dtype=np.float32)
    L[:rn] *= ramp; R[:rn] *= ramp
    L[-rn:] *= ramp[::-1]; R[-rn:] *= ramp[::-1]
    return L, R

# ══════════════════════════════════════════════════════════
#  SECTION 10 — SESSION MAP EXPORT
# ══════════════════════════════════════════════════════════

def export_map(blocks: List[Block], profile: str, out_path: str):
    lines = [
        "═" * 70,
        f"  GENESIS v3 — SESSION MAP",
        f"  Profile: {profile}",
        "═" * 70,
        ""
    ]
    t = 0.0
    for i, b in enumerate(blocks):
        end = t + b.dur_s
        lines.append(f"  [{i+1:02d}]  {b.label}")
        lines.append(f"        Time:     {t/60:.2f} → {end/60:.2f} min")
        lines.append(f"        Carrier:  {b.c0} → {b.c1} Hz")
        lines.append(f"        Beat:     {b.b0} → {b.b1} Hz  (log sweep)")
        lines.append(f"        Noise:    pink={b.noise_pw:.1f} brown={b.noise_bw:.1f}  (SR-calibrated)")
        if b.iso_layers:
            for (f,c,v,atk,dec) in b.iso_layers:
                lines.append(f"        ISO:      {f} Hz  carrier={c} Hz  vol={v}")
        if b.cfc_theta > 0:
            lines.append(f"        CFC:      theta={b.cfc_theta} Hz modulates gamma  strength={b.cfc_strength}")
        if b.assr_80hz_vol > 0:
            lines.append(f"        ASSR-80:  vol={b.assr_80hz_vol} (brainstem pathway)")
        if b.itd_period > 0:
            lines.append(f"        ITD rot:  period={b.itd_period}s")
        if b.infra_freq > 0:
            lines.append(f"        Infra:    {b.infra_freq} Hz  depth={b.infra_depth}")
        if b.schumann_mode:
            lines.append(f"        MODE:     Schumann harmonic stack (7.83+14.3+20.8+27.3+33.8 Hz)")
        lines.append("")
        t = end

    lines += [
        "═" * 70,
        "  GENESIS v3 — LAYER LEGEND",
        "═" * 70,
        "  Binaural:   Phase diff between L/R → perceived beat in brain",
        "  Isochronic: Hard-pulsed AM → stronger cortical evoked response",
        "  CFC:        Theta envelope modulates gamma amplitude (real PAC)",
        "  ASSR-80Hz:  Brainstem + cortical entrainment, independent of 40Hz",
        "  ITD rot:    Slow spatial rotation → vestibular engagement",
        "  Infra-mod:  Ultra-slow AM → ANS / respiratory entrainment",
        "  SR noise:   Stochastic-resonance calibrated to 15% signal RMS",
        "═" * 70,
    ]
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f"  Map: {out_path}")

# ══════════════════════════════════════════════════════════
#  SECTION 11 — MAIN
# ══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description='GENESIS v3 — Psychoacoustic Engine',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
        Profiles:
          GENESIS  full-spectrum: ignition→void→integration (default)
          HEALER   deep delta restoration, 528 Hz focus
          ORACLE   Schumann/theta navigation, 432 Hz
          WARRIOR  beta/gamma activation, minimal delta
        """)
    )
    parser.add_argument('--profile', default='GENESIS',
                        choices=['GENESIS','HEALER','ORACLE','WARRIOR'])
    parser.add_argument('--map', action='store_true',
                        help='Print session map and exit (no render)')
    args = parser.parse_args()

    profile = args.profile.upper()
    blocks  = build_profile(profile)

    # Break placement: after first block, after block at ~40%, after void block
    # Auto-detect: break after any block >600s
    BREAK_AFTER = {i for i, b in enumerate(blocks) if b.dur_s >= 600}
    BREAK_AFTER.add(0)

    total_core   = sum(b.dur_s for b in blocks)
    total_breaks = len(BREAK_AFTER) * 20
    total_s      = total_core + total_breaks

    out_flac = os.path.join(OUT_DIR, f"GENESIS_v3_{profile}_{int(total_s//60)}min.flac")
    out_map  = out_flac.replace('.flac', '_MAP.txt')

    # Session map
    export_map(blocks, profile, out_map)
    if args.map:
        print(open(out_map, encoding='utf-8').read())
        return

    print("═" * 68)
    print(f"  GENESIS v3 — {profile}")
    print(f"  SR: {SR} Hz | FLAC PCM-24 | Stereo")
    print(f"  Duration: {total_s/60:.1f} min  |  {len(blocks)} blocks + {len(BREAK_AFTER)} breaks")
    print(f"  Output: {out_flac}")
    print("═" * 68)
    print("  v3 stack: CFC | ASSR-80Hz | ITD-rotation | infra-mod |")
    print("  beat-jitter | eq-power-xfade | SR-calibrated noise | profiles")
    print("═" * 68)

    with sf.SoundFile(out_flac, 'w', samplerate=SR,
                      channels=2, format='FLAC', subtype='PCM_24') as fh:
        # Set Metadata
        fh.artist    = 'franklin-sys'
        fh.date      = '2026'
        fh.license   = 'https://franklin-sys.vercel.app/'
        fh.copyright = 'franklin-sys (2026) | https://franklin-sys.vercel.app/'

        prev_tail = None

        for i, block in enumerate(blocks):
            pct = sum(b.dur_s for b in blocks[:i]) / total_core * 100
            bar = '█' * int(pct/5) + '░' * (20 - int(pct/5))
            sys.stdout.write(f"\r  [{bar}] {pct:4.0f}%  {block.label[:38]:<38s}")
            sys.stdout.flush()

            L, R = block.render()

            # Global fade-in on first block
            if i == 0:
                fn = int(5 * SR)
                ramp = np.linspace(0, 1, fn, dtype=np.float32)
                L[:fn] *= ramp; R[:fn] *= ramp

            prev_tail = crossfade_write(fh, prev_tail, L, R, fade_s=8.0)
            del L, R

            if i in BREAK_AFTER:
                bL, bR = pattern_break(carrier=blocks[i].c1)
                prev_tail = crossfade_write(fh, prev_tail, bL, bR, fade_s=3.0)
                del bL, bR

        # Final tail + fade-out
        if prev_tail and len(prev_tail[0]):
            tL, tR = prev_tail
            fn = min(int(6*SR), len(tL))
            ramp = np.linspace(1, 0, fn, dtype=np.float32)
            tL[-fn:] *= ramp; tR[-fn:] *= ramp
            fh.write(np.stack([tL, tR], axis=1))

    size_mb = os.path.getsize(out_flac) / 1024 / 1024
    print(f"\r  {'█'*20}  100%  COMPLETE{' '*30}")
    print("═" * 68)
    print(f"  {out_flac}")
    print(f"  {total_s/60:.1f} min | {size_mb:.1f} MB | PCM-24 FLAC")
    print("═" * 68)
    print()
    print("  PROTOCOL:")
    print("  — Проводные наушники обязательно (BT убивает фазу ITD)")
    print("  — Громкость: 20–30% — v3 плотнее v2, тише = лучше")
    print("  — GENESIS: не засыпать первые 5 мин (gamma ignition)")
    print("  — HEALER: можно засыпать — архитектура это учитывает")
    print("  — Не чаще 1 раза в 2 дня (нейропластичность, SR-эффект)")
    print("  — 10 мин тишины после — интеграция критична")

if __name__ == '__main__':
    main()