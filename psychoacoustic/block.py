import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple
from .core import SR, calibrated_noise


@dataclass
class Block:
    label:            str
    dur_s:            float
    # Binaural
    c0:               float = 200.0
    c1:               float = None
    b0:               float = 10.0
    b1:               float = None
    carrier_jitter:   float = 2.0
    beat_jitter:      float = 0.15
    carrier_type:     str   = 'sine'   # sine|warm|rich|soft|organ
    # Noise
    noise_pw:         float = 0.5
    noise_bw:         float = 0.1
    # ISO layers: (freq, carrier_hz, vol, attack_s, decay_s)
    iso_layers:       List  = field(default_factory=list)
    # CFC
    cfc_theta:        float = 0.0
    cfc_strength:     float = 0.4
    # Spatial
    itd_period:       float = 0.0
    spatial_3d:       bool  = False
    el_period:        float = 29.0
    el_depth:         float = 0.35
    # Infra
    infra_freq:       float = 0.0
    infra_depth:      float = 0.12
    # ASSR-80
    assr_80hz_vol:    float = 0.0
    # Modes
    schumann_mode:    bool  = False
    use_chaos:        bool  = False
    chaos_depth:      float = 0.22
    use_hrtf:         bool  = False
    hrtf_elevation:   float = 0.0     # deg, -45…+45
    hrtf_az_sweep:    float = 0.0     # sec per sweep (0=static)
    use_phi:          bool  = False
    phase_lock:       bool  = False
    phase_lock_depth: float = 0.20
    # "Дорогой" звук
    use_drone:        bool  = False
    drone_vol:        float = 0.10
    drone_detune:     float = 0.15
    use_wind:         bool  = False
    wind_vol:         float = 0.07
    wind_bw:          float = 18.0
    use_lfo_filter:   bool  = False
    lfo_fc:           float = 900.0
    lfo_depth:        float = 400.0
    lfo_rate:         float = 0.05
    seed:             int   = 0

    def __post_init__(self):
        if self.c1 is None: self.c1 = self.c0
        if self.b1 is None: self.b1 = self.b0

    # ──────────────────────────────────────────────────────
    def render(self) -> Tuple[np.ndarray, np.ndarray]:
        from .core  import log_sweep, jitter_envelope
        from .dsp   import (dual_binaural, isochronic, apply_cfc,
                            assr_80hz, schumann_stack, spatial_rotation,
                            spatial_rotation_3d, infra_modulate,
                            detuned_drone, resonant_wind_pad, lfo_filter)
        from .chaos import chaos_modulate
        from .hrtf  import hrtf_externalize
        from .phi   import phi_beat_layer

        n = int(self.dur_s * SR)

        # ── Beat envelope
        B_raw = log_sweep(self.b0, self.b1, n)
        if self.use_chaos:
            B_raw = chaos_modulate(B_raw, depth=self.chaos_depth,
                                   seed=self.seed + 400)
        else:
            B_raw = jitter_envelope(B_raw, self.beat_jitter, self.seed + 50)

        # Cross-modal phase lock: infra envelope → beat modulation
        if self.phase_lock and self.infra_freq > 0:
            t     = np.arange(n, dtype=np.float64) / SR
            B_raw *= (1.0 + self.phase_lock_depth
                      * np.sin(2 * np.pi * self.infra_freq * t + self.seed * 0.7))
            B_raw = np.clip(B_raw, 0.3, 120.0)

        # ── Base binaural
        kw = dict(carrier_jitter=self.carrier_jitter,
                  beat_jitter=self.beat_jitter,
                  seed=self.seed,
                  beat_array=B_raw,
                  carrier_type=self.carrier_type)

        if self.schumann_mode:
            L, R = schumann_stack(self.dur_s, self.c0,
                                  base_vol=0.20, seed=self.seed,
                                  carrier_type=self.carrier_type)
            bL, bR = dual_binaural(self.dur_s, self.c0, self.c1,
                                   self.b0, self.b1,
                                   vol_p=0.25, vol_s=0.10, **kw)
            L += bL; R += bR
        else:
            L, R = dual_binaural(self.dur_s, self.c0, self.c1,
                                 self.b0, self.b1,
                                 vol_p=0.60, vol_s=0.22, **kw)

        # ── φ-layer
        if self.use_phi:
            pL, pR = phi_beat_layer(self.dur_s, self.c0, B_raw,
                                    vol=0.16, seed=self.seed)
            L += pL; R += pR

        # ── "Дорогой" звук: detuned drone pad
        if self.use_drone:
            pad = detuned_drone(self.dur_s, self.c0,
                                detune_hz=self.drone_detune,
                                vol=self.drone_vol,
                                ctype=self.carrier_type,
                                seed=self.seed + 600)
            L += pad; R += pad

        # ── "Дорогой" звук: resonant wind pad
        if self.use_wind:
            wind = resonant_wind_pad(self.dur_s, self.c0,
                                     bw_hz=self.wind_bw,
                                     vol=self.wind_vol,
                                     seed=self.seed + 700)
            L += wind; R += wind

        # ── ISO layers + CFC
        for (fv, cv, vv, atk, dec) in self.iso_layers:
            sig = isochronic(self.dur_s, fv, cv, vv, atk, dec,
                             carrier_type=self.carrier_type)
            if self.cfc_theta > 0 and fv >= 30.0:
                sig = apply_cfc(sig, self.dur_s,
                                self.cfc_theta, self.cfc_strength)
            L += sig; R += sig

        # ── ASSR-80
        if self.assr_80hz_vol > 0:
            a80 = assr_80hz(self.dur_s, carrier=200.0, vol=self.assr_80hz_vol)
            if self.cfc_theta > 0:
                a80 = apply_cfc(a80, self.dur_s,
                                self.cfc_theta, self.cfc_strength * 0.5)
            L += a80; R += a80

        # ── LFO filter sweep (тембральное дыхание, до пространственной обработки)
        if self.use_lfo_filter:
            L = lfo_filter(L, self.lfo_fc, self.lfo_depth,
                           self.lfo_rate, self.seed + 800)
            R = lfo_filter(R, self.lfo_fc, self.lfo_depth,
                           self.lfo_rate, self.seed + 801)

        # ── SR-calibrated noise (до пространственной обработки)
        nz = calibrated_noise(L, R, self.noise_pw, self.noise_bw,
                              self.seed + 300)
        L += nz; R += nz

        # ══════════════════════════════════════════════════
        #  ПРОСТРАНСТВЕННАЯ ЦЕПОЧКА — ПОРЯДОК КРИТИЧЕН:
        #  1. Spatial rotation (ITD orbit)  — создаёт L/R панораму
        #  2. Infra-modulation              — медленная AM поверх панорамы
        #  3. HRTF externalization          — последний шаг: "выносит"
        #     образ из головы, применяется к уже сформированной панораме
        # ══════════════════════════════════════════════════

        # 1. Spatial rotation
        if self.spatial_3d and self.itd_period > 0:
            L, R = spatial_rotation_3d(L, R,
                                       az_period=self.itd_period,
                                       el_period=self.el_period,
                                       el_depth=self.el_depth)
        elif self.itd_period > 0:
            L, R = spatial_rotation(L, R, self.itd_period)

        # 2. Infra-modulation (медленная AM, не меняет пространство)
        if self.infra_freq > 0:
            L, R = infra_modulate(L, R, self.infra_freq,
                                  self.infra_depth,
                                  phase_offset=self.seed * 0.7)

        # 3. HRTF externalization (последний пространственный слой)
        if self.use_hrtf:
            L, R = hrtf_externalize(L, R,
                                    az_sweep_period=self.hrtf_az_sweep,
                                    elevation_deg=self.hrtf_elevation)

        # ── Normalize (порог 0.90 — безопаснее для последующей конвертации)
        peak = max(np.max(np.abs(L)), np.max(np.abs(R))) + 1e-9
        if peak > 0.90:
            L = (L / peak * 0.88).astype(np.float32)
            R = (R / peak * 0.88).astype(np.float32)

        return L.astype(np.float32), R.astype(np.float32)
