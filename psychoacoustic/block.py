import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple
from .core import SR, calibrated_noise


@dataclass
class Block:
    label:            str
    dur_s:            float
    # ── Binaural
    c0:               float = 200.0
    c1:               float = None
    b0:               float = 10.0
    b1:               float = None
    carrier_jitter:   float = 2.0
    beat_jitter:      float = 0.15
    carrier_type:     str   = 'sine'   # sine|warm|rich|soft|organ
    # ── Noise
    noise_pw:         float = 0.5
    noise_bw:         float = 0.1
    # ── ISO layers: (freq, carrier_hz, vol, attack_s, decay_s)
    iso_layers:       List  = field(default_factory=list)
    # ── CFC
    cfc_theta:        float = 0.0
    cfc_strength:     float = 0.4
    # ── Spatial
    itd_period:       float = 0.0
    spatial_3d:       bool  = False
    el_period:        float = 29.0
    el_depth:         float = 0.35
    # ── Infra
    infra_freq:       float = 0.0
    infra_depth:      float = 0.12
    # ── ASSR-80
    assr_80hz_vol:    float = 0.0
    # ── Modes
    schumann_mode:    bool  = False
    use_chaos:        bool  = False
    chaos_depth:      float = 0.22
    use_hrtf:         bool  = False
    hrtf_elevation:   float = 0.0
    hrtf_az_sweep:    float = 0.0
    use_phi:          bool  = False
    phase_lock:       bool  = False
    phase_lock_depth: float = 0.20
    # ── Дорогой звук: базовые слои
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
    # ── ATMOSPHERE — Granular Engine
    use_granular:        bool  = False
    granular_grain_ms:   float = 80.0
    granular_density:    float = 12.0
    granular_pitch_st:   float = 0.30
    granular_scatter:    float = 0.50
    granular_vol:        float = 0.11
    # ── MONAURAL BEAT LAYER — двойной entrainment pathway
    #    AM-модуляция несущей на beat_freq → brainstem pathway (без наушников).
    #    beat_freq=0.0: автоматически берёт b0 блока.
    use_monaural:     bool  = False
    monaural_vol:     float = 0.05
    monaural_beat_hz: float = 0.0     # 0.0 → auto = b0
    # ── FORMANT RESONATOR — живой, голосовой тембр
    #    F1/F2/F3 bandpass bank → ощущение "живого" источника.
    use_formant:        bool  = False
    formant_intensity:  float = 0.22  # 0.15–0.35
    # ── TUBE SATURATION — аналоговое тепло
    #    arctan soft-clip, drive 0.08–0.14: едва слышимые чётные гармоники.
    use_saturate:       bool  = False
    saturate_drive:     float = 0.10
    # ── ROOM REVERB — пространственная глубина
    #    Synthetic IR reverb. НЕ применять к SLEEP (сохранить ITD точность).
    use_reverb:         bool  = False
    reverb_wet:         float = 0.10
    reverb_rt60:        float = 700.0
    # ── RESPIRATORY ENTRAINMENT — синхронизация дыхания
    #    Ultra-slow AM (breath_bpm/60 Hz) → vagal tone / HRV coherence.
    #    4.0 bpm = Yoga Nidra (SLEEP/HEALER)
    #    6.0 bpm = HRV coherence peak (ORACLE/GENESIS)
    use_respiratory:    bool  = False
    breath_bpm:         float = 6.0
    breath_depth:       float = 0.14
    # ── Master gain (per-block loudness)
    #    Applied AFTER normalize(0.56 FS).
    #    SLEEP delta: 0.55 → 0.56×0.55 = 0.308 FS (-10.2 dBFS от оригинала)
    #    SLEEP OBE:   0.65 → 0.364 FS
    #    HEALER void: 0.55 → 0.308 FS
    block_gain:          float = 1.0
    seed:             int   = 0

    def __post_init__(self):
        if self.c1 is None: self.c1 = self.c0
        if self.b1 is None: self.b1 = self.b0

    # ──────────────────────────────────────────────────────────────────────
    def render(self) -> Tuple[np.ndarray, np.ndarray]:
        from .core  import log_sweep, jitter_envelope
        from .dsp   import (dual_binaural, isochronic, apply_cfc,
                            assr_80hz, schumann_stack, spatial_rotation,
                            spatial_rotation_3d, infra_modulate,
                            detuned_drone, resonant_wind_pad, lfo_filter,
                            tube_saturate, formant_resonator, room_reverb,
                            monaural_beat_layer, respiratory_entrainment_mod)
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

        if self.phase_lock and self.infra_freq > 0:
            t     = np.arange(n, dtype=np.float64) / SR
            B_raw *= (1.0 + self.phase_lock_depth
                      * np.sin(2 * np.pi * self.infra_freq * t + self.seed * 0.7))
            B_raw  = np.clip(B_raw, 0.3, 120.0)

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

        # ── Detuned drone pad
        if self.use_drone:
            pad = detuned_drone(self.dur_s, self.c0,
                                detune_hz=self.drone_detune,
                                vol=self.drone_vol,
                                ctype=self.carrier_type,
                                seed=self.seed + 600)
            L += pad; R += pad

        # ── ATMOSPHERE: Granular cloud
        if self.use_granular:
            from .granular import granular_cloud
            gL = granular_cloud(self.dur_s, self.c0,
                                grain_size_ms=self.granular_grain_ms,
                                density=self.granular_density,
                                pitch_scatter_st=self.granular_pitch_st,
                                time_scatter=self.granular_scatter,
                                vol=self.granular_vol,
                                ctype=self.carrier_type,
                                seed=self.seed + 900)
            gR = granular_cloud(self.dur_s, self.c0,
                                grain_size_ms=self.granular_grain_ms,
                                density=self.granular_density,
                                pitch_scatter_st=self.granular_pitch_st,
                                time_scatter=self.granular_scatter,
                                vol=self.granular_vol,
                                ctype=self.carrier_type,
                                seed=self.seed + 901)
            L += gL; R += gR

        # ── Resonant wind pad
        if self.use_wind:
            wind = resonant_wind_pad(self.dur_s, self.c0,
                                     bw_hz=self.wind_bw,
                                     vol=self.wind_vol,
                                     seed=self.seed + 700)
            L += wind; R += wind

        # ── Monaural beat layer (brainstem pathway — дополняет бинауральный)
        if self.use_monaural:
            beat_hz = self.monaural_beat_hz if self.monaural_beat_hz > 0 else self.b0
            mono = monaural_beat_layer(self.dur_s, self.c0,
                                       beat_freq=beat_hz,
                                       vol=self.monaural_vol,
                                       ctype=self.carrier_type,
                                       seed=self.seed + 1000)
            L += mono; R += mono

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

        # ── LFO filter sweep (тембральное дыхание)
        if self.use_lfo_filter:
            L = lfo_filter(L, self.lfo_fc, self.lfo_depth,
                           self.lfo_rate, self.seed + 800)
            R = lfo_filter(R, self.lfo_fc, self.lfo_depth,
                           self.lfo_rate, self.seed + 801)

        # ── Formant resonator (живой, голосовой тембр)
        if self.use_formant:
            L = formant_resonator(L, self.formant_intensity)
            R = formant_resonator(R, self.formant_intensity)

        # ── Tube saturation (аналоговое тепло, очень мягкое)
        if self.use_saturate:
            L = tube_saturate(L, self.saturate_drive)
            R = tube_saturate(R, self.saturate_drive)

        # ── Calibrated SR-noise
        nz = calibrated_noise(L, R, self.noise_pw, self.noise_bw,
                              self.seed + 300)
        L += nz; R += nz

        # ══════════════════════════════════════════════════════════════
        #  ПРОСТРАНСТВЕННАЯ ЦЕПОЧКА — порядок критичен:
        #  1. Spatial rotation  — создаёт L/R панораму
        #  2. Infra-modulation  — медленная AM поверх панорамы
        #  3. Respiratory AM    — вторая ultra-slow AM (дыхание)
        #  4. HRTF              — выносит образ из головы
        #  5. Room reverb       — пространственная глубина (после HRTF)
        # ══════════════════════════════════════════════════════════════

        # 1. Spatial rotation
        if self.spatial_3d and self.itd_period > 0:
            L, R = spatial_rotation_3d(L, R,
                                       az_period=self.itd_period,
                                       el_period=self.el_period,
                                       el_depth=self.el_depth)
        elif self.itd_period > 0:
            L, R = spatial_rotation(L, R, self.itd_period)

        # 2. Infra-modulation
        if self.infra_freq > 0:
            L, R = infra_modulate(L, R, self.infra_freq,
                                  self.infra_depth,
                                  phase_offset=self.seed * 0.7)

        # 3. Respiratory entrainment (vagal sync)
        if self.use_respiratory:
            mod  = respiratory_entrainment_mod(self.dur_s,
                                               self.breath_bpm,
                                               self.breath_depth)
            L = (L * mod).astype(np.float32)
            R = (R * mod).astype(np.float32)

        # 4. HRTF externalization
        if self.use_hrtf:
            L, R = hrtf_externalize(L, R,
                                    az_sweep_period=self.hrtf_az_sweep,
                                    elevation_deg=self.hrtf_elevation)

        # 5. Room reverb (только для блоков где это задано)
        if self.use_reverb:
            L, R = room_reverb(L, R,
                               rt60_ms=self.reverb_rt60,
                               wet=self.reverb_wet)

        # ── Normalize: target 0.56 FS  (-4.0 dBFS vs 0.88 оригинал)
        peak = max(np.max(np.abs(L)), np.max(np.abs(R))) + 1e-9
        if peak > 0.56:
            L = (L / peak * 0.56).astype(np.float32)
            R = (R / peak * 0.56).astype(np.float32)

        # ── Per-block master gain
        if self.block_gain != 1.0:
            scale = np.float32(self.block_gain)
            L = (L * scale).astype(np.float32)
            R = (R * scale).astype(np.float32)

        return L.astype(np.float32), R.astype(np.float32)
