import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Optional
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
    # ── Organic layers
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
    # ── MONAURAL — follows B_raw sweep when monaural_beat_hz <= 0
    use_monaural:     bool  = False
    monaural_vol:     float = 0.05
    monaural_beat_hz: float = 0.0     # 0.0 → lock to binaural sweep
    # ── FORMANT / SATURATION / REVERB
    use_formant:        bool  = False
    formant_intensity:  float = 0.18
    formant_vowel:      str   = 'A'       # A|O|U|E|M
    formant_morph_vowel: Optional[str] = None  # e.g. 'M' for AUM tail
    formant_morph_s:    float = 0.0
    use_saturate:       bool  = False
    saturate_drive:     float = 0.10
    use_reverb:         bool  = False
    reverb_wet:         float = 0.10
    reverb_rt60:        float = 700.0
    # ── Anti-sizzle / soft introductions
    use_silk:           bool  = True   # LP anti-whistle (auto-stronger on high carriers)
    silk_cutoff_hz:     float = 5200.0
    allow_sharp_iso:    bool  = False  # True only for WARRIOR peak blocks
    intro_fade_s:       float = 10.0   # cosine fade-in of whole block (0=off)
    outro_fade_s:       float = 8.0
    # ── RESPIRATORY — optional bpm ramp via breath_bpm_end
    use_respiratory:    bool  = False
    breath_bpm:         float = 6.0
    breath_bpm_end:     Optional[float] = None
    breath_depth:       float = 0.14
    # ── Focus mix (dual-frequency open-loop)
    use_focus_mix:      bool  = False
    focus_body_beat:    float = 2.0
    focus_cortex_beat:  float = 10.0
    focus_vol_body:     float = 0.07
    focus_vol_cortex:   float = 0.05
    # ── Continuous underbed inside block
    use_underbed:       bool  = True
    underbed_vol:       float = 0.014
    # ── Premium organic atmosphere (river / ghosts / bowls / drift)
    # On by default for all profiles; WARRIOR auto-resolves to 'minimal'.
    use_organic:        bool  = True
    organic_style:      str   = 'auto'   # auto|rest|sleep|edge|focus|chakra|minimal
    organic_intensity:  float = 1.0
    use_carrier_drift:  bool  = True
    carrier_drift_hz:   float = 0.85     # peak Hz wander (beat untouched)
    carrier_drift_rate: float = 0.018
    use_spectral_breath: bool = True     # mild wet LP morph on full mix
    spectral_breath_mix: float = 0.10
    # ── AM depth budget cap (infra + respiratory combined)
    am_depth_cap:       float = 0.26
    # ── Master
    block_gain:          float = 1.0
    use_comfort_eq:      bool  = False
    soft_ceiling_fs:     float = 0.50
    # ── Structured quiet before this block (renderer inserts)
    quiet_before_s:      float = 0.0
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
                            monaural_beat_layer, respiratory_entrainment_mod,
                            comfort_filter, soft_ceiling, budget_am_depths,
                            underbed_noise, focus_mix_layer, silk_lowpass)
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
        drift = self.carrier_drift_hz if self.use_carrier_drift else 0.0
        kw = dict(carrier_jitter=self.carrier_jitter,
                  beat_jitter=self.beat_jitter,
                  seed=self.seed,
                  beat_array=B_raw,
                  carrier_type=self.carrier_type,
                  carrier_drift=drift,
                  carrier_drift_rate=self.carrier_drift_rate)

        if self.schumann_mode:
            L, R = schumann_stack(self.dur_s, self.c0,
                                  base_vol=0.18, seed=self.seed,
                                  carrier_type=self.carrier_type)
            bL, bR = dual_binaural(self.dur_s, self.c0, self.c1,
                                   self.b0, self.b1,
                                   vol_p=0.25, vol_s=0.10, **kw)
            L += bL; R += bR
        else:
            L, R = dual_binaural(self.dur_s, self.c0, self.c1,
                                 self.b0, self.b1,
                                 vol_p=0.60, vol_s=0.22, **kw)

        # ── Focus mix (body delta + cortex alpha/beta)
        if self.use_focus_mix:
            fL, fR = focus_mix_layer(
                self.dur_s, self.c0,
                body_beat=self.focus_body_beat,
                cortex_beat=self.focus_cortex_beat,
                vol_body=self.focus_vol_body,
                vol_cortex=self.focus_vol_cortex,
                ctype='soft' if self.carrier_type == 'sine' else self.carrier_type,
                seed=self.seed + 50)
            L += fL; R += fR

        # ── φ-layer
        if self.use_phi:
            pL, pR = phi_beat_layer(self.dur_s, self.c0, B_raw,
                                    vol=0.14, seed=self.seed)
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

        # ── Monaural beat layer — sweep-locked to B_raw by default
        if self.use_monaural:
            if self.monaural_beat_hz > 0:
                mono = monaural_beat_layer(self.dur_s, self.c0,
                                           beat_freq=self.monaural_beat_hz,
                                           vol=self.monaural_vol,
                                           ctype=self.carrier_type,
                                           seed=self.seed + 1000)
            else:
                mono = monaural_beat_layer(self.dur_s, self.c0,
                                           vol=self.monaural_vol,
                                           ctype=self.carrier_type,
                                           seed=self.seed + 1000,
                                           beat_array=B_raw)
            L += mono; R += mono

        # ── ISO layers + CFC (soft min attack unless allow_sharp_iso)
        for (fv, cv, vv, atk, dec) in self.iso_layers:
            if not self.allow_sharp_iso:
                floor = min(12.0, max(6.0, self.dur_s * 0.20))
                atk = max(float(atk), floor)
                dec = max(float(dec), floor * 0.75)
            # High iso carriers whistle easily — cap carrier for gamma beds
            cv_use = float(cv)
            if fv >= 30.0 and cv_use > 220.0:
                cv_use = 200.0
            sig = isochronic(self.dur_s, fv, cv_use, vv, atk, dec,
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

        # ── Continuous underbed
        if self.use_underbed and self.underbed_vol > 0:
            bed = underbed_noise(self.dur_s, vol=self.underbed_vol,
                                 seed=self.seed + 1200)
            L += bed; R += bed

        # ── Premium organic atmosphere (river / ghosts / bowls)
        if self.use_organic and self.organic_intensity > 0:
            from .organic import organic_atmosphere, resolve_organic_style
            ostyle = resolve_organic_style(
                self.label, self.b0, self.b1, self.c0, self.c1,
                self.allow_sharp_iso, self.use_focus_mix,
                self.organic_style)
            # Soft carriers prefer soft ghosts; keep organ less whistly
            octype = 'soft' if self.carrier_type in ('sine', 'soft') else self.carrier_type
            if octype == 'organ':
                octype = 'warm'
            oL, oR = organic_atmosphere(
                self.dur_s,
                carrier=0.5 * (float(self.c0) + float(self.c1)),
                style=ostyle,
                intensity=float(self.organic_intensity),
                seed=self.seed + 1400,
                ctype=octype)
            L += oL; R += oR

        # ── LFO filter sweep
        if self.use_lfo_filter:
            L = lfo_filter(L, self.lfo_fc, self.lfo_depth,
                           self.lfo_rate, self.seed + 800)
            R = lfo_filter(R, self.lfo_fc, self.lfo_depth,
                           self.lfo_rate, self.seed + 801)

        # ── Formant resonator (vowel + optional morph)
        if self.use_formant:
            L = formant_resonator(
                L, self.formant_intensity,
                vowel=self.formant_vowel,
                morph_vowel=self.formant_morph_vowel,
                morph_s=self.formant_morph_s)
            R = formant_resonator(
                R, self.formant_intensity,
                vowel=self.formant_vowel,
                morph_vowel=self.formant_morph_vowel,
                morph_s=self.formant_morph_s)

        # ── Tube saturation
        if self.use_saturate:
            L = tube_saturate(L, self.saturate_drive)
            R = tube_saturate(R, self.saturate_drive)

        # ── Mild spectral breath on full mix (organic living air)
        if self.use_spectral_breath and self.spectral_breath_mix > 0:
            from .organic import spectral_breath
            # Keep quieter on sharp / high-carrier blocks
            mix = float(self.spectral_breath_mix)
            if self.allow_sharp_iso:
                mix *= 0.45
            cmax = max(float(self.c0), float(self.c1))
            if cmax >= 700:
                mix *= 0.7
            L, R = spectral_breath(L, R, mix=mix, rate_hz=0.024,
                                   seed=self.seed + 1500)

        # ── Anti-sizzle silk (stronger on high carriers — chakra upper / organ)
        if self.use_silk:
            cut = self.silk_cutoff_hz
            cmax = max(float(self.c0), float(self.c1))
            if cmax >= 700:
                cut = min(cut, 4200.0)
            elif cmax >= 500:
                cut = min(cut, 4800.0)
            L = silk_lowpass(L, cut)
            R = silk_lowpass(R, cut)

        # ── Calibrated SR-noise
        nz = calibrated_noise(L, R, self.noise_pw, self.noise_bw,
                              self.seed + 300)
        L += nz; R += nz

        # ── Spatial chain
        if self.spatial_3d and self.itd_period > 0:
            L, R = spatial_rotation_3d(L, R,
                                       az_period=self.itd_period,
                                       el_period=self.el_period,
                                       el_depth=self.el_depth)
        elif self.itd_period > 0:
            L, R = spatial_rotation(L, R, self.itd_period)

        # AM depth budget: infra + respiratory share one cap
        infra_d = self.infra_depth if self.infra_freq > 0 else 0.0
        breath_d = self.breath_depth if self.use_respiratory else 0.0
        infra_d, breath_d = budget_am_depths(infra_d, breath_d,
                                             cap=self.am_depth_cap)

        if self.infra_freq > 0 and infra_d > 0:
            L, R = infra_modulate(L, R, self.infra_freq,
                                  infra_d,
                                  phase_offset=self.seed * 0.7)

        if self.use_respiratory and breath_d > 0:
            mod  = respiratory_entrainment_mod(
                self.dur_s, self.breath_bpm, breath_d,
                breath_bpm_end=self.breath_bpm_end)
            L = (L * mod).astype(np.float32)
            R = (R * mod).astype(np.float32)

        if self.use_hrtf:
            L, R = hrtf_externalize(L, R,
                                    az_sweep_period=self.hrtf_az_sweep,
                                    elevation_deg=self.hrtf_elevation)

        if self.use_reverb:
            L, R = room_reverb(L, R,
                               rt60_ms=self.reverb_rt60,
                               wet=self.reverb_wet)

        # ── Soft block intro/outro (prevents post-quiet "slam")
        n = len(L)
        if self.intro_fade_s > 0:
            fn = min(int(self.intro_fade_s * SR), n // 3)
            if fn > 2:
                ramp = (0.5 - 0.5 * np.cos(
                    np.linspace(0, np.pi, fn, dtype=np.float32))).astype(np.float32)
                L[:fn] *= ramp
                R[:fn] *= ramp
        if self.outro_fade_s > 0:
            fn = min(int(self.outro_fade_s * SR), n // 3)
            if fn > 2:
                ramp = (0.5 + 0.5 * np.cos(
                    np.linspace(0, np.pi, fn, dtype=np.float32))).astype(np.float32)
                L[-fn:] *= ramp
                R[-fn:] *= ramp

        # ── Master chain: pre-norm → comfort EQ → soft ceiling → block_gain
        peak = max(np.max(np.abs(L)), np.max(np.abs(R))) + 1e-9
        if peak > 0.56:
            L = (L / peak * 0.56).astype(np.float32)
            R = (R / peak * 0.56).astype(np.float32)

        if self.use_comfort_eq:
            # Stronger silk on high carriers
            cmax = max(float(self.c0), float(self.c1))
            hi_db = -4.5 if cmax >= 700 else (-3.5 if cmax >= 500 else -3.5)
            L, R = comfort_filter(L, R, high_db=hi_db)

        L, R = soft_ceiling(L, R, ceiling=self.soft_ceiling_fs, knee=0.08)

        if self.block_gain != 1.0:
            scale = np.float32(self.block_gain)
            L = (L * scale).astype(np.float32)
            R = (R * scale).astype(np.float32)

        return L.astype(np.float32), R.astype(np.float32)
