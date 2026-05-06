import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple
from .core import SR, calibrated_noise
from .dsp import (dual_binaural, isochronic, apply_cfc,
                  assr_80hz, schumann_stack, spatial_rotation, infra_modulate)


@dataclass
class Block:
    label:          str
    dur_s:          float
    # Binaural sweep
    c0:             float = 200.0
    c1:             float = None
    b0:             float = 10.0
    b1:             float = None
    carrier_jitter: float = 2.0
    beat_jitter:    float = 0.15
    # Noise (stochastic-resonance calibrated)
    noise_pw:       float = 0.5    # pink weight
    noise_bw:       float = 0.1    # brown weight
    # ISO layers: (freq_hz, carrier_hz, vol, attack_s, decay_s)
    iso_layers:     List  = field(default_factory=list)
    # Cross-Frequency Coupling
    cfc_theta:      float = 0.0
    cfc_strength:   float = 0.4
    # Spatial / modulation
    itd_period:     float = 0.0
    infra_freq:     float = 0.0
    infra_depth:    float = 0.12
    # ASSR-80
    assr_80hz_vol:  float = 0.0
    # Schumann stack mode
    schumann_mode:  bool  = False
    # Optional modules
    use_chaos:      bool  = False   # Lorenz beat modulation
    chaos_depth:    float = 0.22
    use_hrtf:       bool  = False   # pinna externalization
    use_phi:        bool  = False   # φ-ratio 3rd binaural layer
    # Cross-modal phase lock: infra drives beat freq
    phase_lock:     bool  = False   # infra → beat coupling
    phase_lock_depth: float = 0.20
    seed:           int   = 0

    def __post_init__(self):
        if self.c1 is None: self.c1 = self.c0
        if self.b1 is None: self.b1 = self.b0

    # ──────────────────────────────────────────────────────
    def render(self) -> Tuple[np.ndarray, np.ndarray]:
        from .core import log_sweep, jitter_envelope
        from .chaos import chaos_modulate
        from .hrtf import hrtf_externalize
        from .phi import phi_beat_layer

        n = int(self.dur_s * SR)

        # ── Beat envelope (may be overridden by chaos / phase_lock)
        B_raw = log_sweep(self.b0, self.b1, n)

        if self.use_chaos:
            B_raw = chaos_modulate(B_raw, depth=self.chaos_depth, seed=self.seed + 400)
        else:
            B_raw = jitter_envelope(B_raw, self.beat_jitter, self.seed + 50)

        # Cross-modal phase lock: infra envelope → beat modulation
        # When you breathe out (infra dips), beat slows; inhale → beat rises
        if self.phase_lock and self.infra_freq > 0:
            t = np.arange(n, dtype=np.float64) / SR
            infra_env = np.sin(2*np.pi*self.infra_freq*t + self.seed*0.7)
            B_raw = B_raw * (1.0 + self.phase_lock_depth * infra_env)
            B_raw = np.clip(B_raw, 0.3, 120.0)

        # ── Base binaural signal
        if self.schumann_mode:
            L, R = schumann_stack(self.dur_s, self.c0, base_vol=0.20, seed=self.seed)
            bL, bR = dual_binaural(self.dur_s, self.c0, self.c1,
                                   self.b0, self.b1,
                                   vol_p=0.25, vol_s=0.10,
                                   carrier_jitter=self.carrier_jitter,
                                   beat_jitter=self.beat_jitter,
                                   seed=self.seed + 1, beat_array=B_raw)
            L += bL; R += bR
        else:
            L, R = dual_binaural(self.dur_s, self.c0, self.c1,
                                 self.b0, self.b1,
                                 vol_p=0.60, vol_s=0.22,
                                 carrier_jitter=self.carrier_jitter,
                                 beat_jitter=self.beat_jitter,
                                 seed=self.seed, beat_array=B_raw)

        # ── φ layer (3rd binaural at carrier×φ)
        if self.use_phi:
            pL, pR = phi_beat_layer(self.dur_s, self.c0, B_raw, vol=0.16, seed=self.seed)
            L += pL; R += pR

        # ── Isochronic layers + CFC
        for (fv, cv, vv, atk, dec) in self.iso_layers:
            sig = isochronic(self.dur_s, fv, cv, vv, atk, dec)
            if self.cfc_theta > 0 and fv >= 30.0:
                sig = apply_cfc(sig, self.dur_s, self.cfc_theta, self.cfc_strength)
            L += sig; R += sig

        # ── ASSR-80
        if self.assr_80hz_vol > 0:
            a80 = assr_80hz(self.dur_s, carrier=200.0, vol=self.assr_80hz_vol)
            if self.cfc_theta > 0:
                a80 = apply_cfc(a80, self.dur_s, self.cfc_theta, self.cfc_strength*0.5)
            L += a80; R += a80

        # ── SR-calibrated noise
        nz = calibrated_noise(L, R, self.noise_pw, self.noise_bw, self.seed + 300)
        L += nz; R += nz

        # ── Spatial ITD rotation
        if self.itd_period > 0:
            L, R = spatial_rotation(L, R, self.itd_period)

        # ── Infra-modulation (after phase_lock has already shaped beat)
        if self.infra_freq > 0:
            L, R = infra_modulate(L, R, self.infra_freq,
                                  self.infra_depth,
                                  phase_offset=self.seed * 0.7)

        # ── HRTF externalization
        if self.use_hrtf:
            L, R = hrtf_externalize(L, R)

        # ── Normalize
        peak = max(np.max(np.abs(L)), np.max(np.abs(R))) + 1e-9
        if peak > 0.93:
            L = (L / peak * 0.90).astype(np.float32)
            R = (R / peak * 0.90).astype(np.float32)

        return L.astype(np.float32), R.astype(np.float32)
