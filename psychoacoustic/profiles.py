"""
Профили сессий NeuroDynamics — Permanent God-Tier (1A + 2B).

Permanent mode (GENESIS/WALK/SLEEP/HEALER/ORACLE):
  comfort EQ · soft ceiling · gamma iso ≤0.09 · ASSR ≤0.04
  monaural locked to binaural sweep · underbed · AM budget

Sharp-safe (WARRIOR):
  higher iso/ASSR · no comfort on peak blocks · soft-gate + ceiling + atk≥4s

Gateway Edge (~30 min):
  F10 → F12 → F15 → interrupt → F21 touch → seal

Deep Dive Pro Night (~121 min):
  PREP → BODY OFF → STABLE THETA → DEEP THETA → LIMINAL → AUTO/VOID
  Fixed carrier, beat_ctrl/adaptive_drift_envelope throughout, void-style
  organic bed (events hard-zeroed), skip_ambient_bridge — one unbroken
  descent, ends in a 4-minute taper to silence.
"""

from .block import Block


def build_profile(name: str):
    n = name.upper().replace('-', '_').replace(' ', '_')
    if   n == 'GENESIS':  return _genesis()
    elif n == 'WALK':     return _walk()
    elif n == 'SLEEP':    return _sleep()
    elif n == 'HEALER':   return _healer()
    elif n == 'ORACLE':   return _oracle()
    elif n == 'WARRIOR':  return _warrior()
    elif n in ('GATEWAY_EDGE', 'GATEWAY', 'EDGE'):
        return _gateway_edge()
    elif n in ('CHAKRA_ASCENT', 'CHAKRA', 'ASCENT'):
        return _chakra_ascent()
    elif n in ('DEEP_DIVE_PRO_NIGHT', 'DEEP_DIVE_PRO', 'DEEP_DIVE',
               'DEEP_DIVE_NIGHT'):
        return _deep_dive_pro_night()
    else:
        raise ValueError(
            f"Unknown profile '{name}'. "
            f"Use: GENESIS WALK SLEEP HEALER ORACLE WARRIOR "
            f"GATEWAY_EDGE CHAKRA_ASCENT DEEP_DIVE_PRO_NIGHT")


# ══════════════════════════════════════════════════════════
#  GENESIS — ~66 min core (+ FFR/bridges/quiet)
# ══════════════════════════════════════════════════════════

def _genesis():
    return [
        Block(
            label='IGNITION', dur_s=300,
            c0=200, c1=432, b0=36.0, b1=40.0,
            carrier_type='warm',
            carrier_jitter=0.8, beat_jitter=0.08,
            noise_pw=1.0, noise_bw=0.0,
            iso_layers=[(40.0, 200, 0.08, 6, 8)],
            assr_80hz_vol=0.035,
            itd_period=12.0, use_hrtf=True, hrtf_az_sweep=0,
            use_drone=True, drone_vol=0.08,
            use_monaural=True, monaural_vol=0.04,
            use_saturate=True, saturate_drive=0.08,
            use_comfort_eq=True, block_gain=0.78,
            seed=1
        ),
        Block(
            label='EARTH SYNC', dur_s=480,
            c0=432, c1=432, b0=7.83, b1=7.83,
            carrier_type='warm',
            carrier_jitter=0.3, beat_jitter=0.06,
            noise_pw=0.8, noise_bw=0.2,
            iso_layers=[(14.3, 216, 0.055, 12, 12),
                        (40.0, 200, 0.05, 14, 10)],
            cfc_theta=7.83, cfc_strength=0.28,
            assr_80hz_vol=0.03,
            infra_freq=0.10, infra_depth=0.10,
            schumann_mode=True,
            use_hrtf=True, hrtf_az_sweep=16.0,
            use_wind=True, wind_vol=0.06, wind_bw=14.0,
            use_lfo_filter=True, lfo_fc=800.0, lfo_depth=350.0, lfo_rate=0.04,
            use_monaural=True, monaural_vol=0.04,
            use_formant=True, formant_intensity=0.16,
            use_saturate=True, saturate_drive=0.08,
            use_respiratory=True, breath_bpm=6.0, breath_depth=0.12,
            use_comfort_eq=True, block_gain=0.75,
            seed=2
        ),
        Block(
            label='THETA GATEWAY', dur_s=540,
            c0=432, c1=528, b0=7.83, b1=4.5,
            carrier_type='warm',
            carrier_jitter=1.8, beat_jitter=0.18,
            noise_pw=0.6, noise_bw=0.4,
            iso_layers=[(6.0,  264, 0.09, 14, 12),
                        (40.0, 200, 0.055, 16,  8)],
            cfc_theta=6.0, cfc_strength=0.40,
            assr_80hz_vol=0.03,
            itd_period=15.0, use_hrtf=True, hrtf_az_sweep=0,
            infra_freq=0.08, infra_depth=0.11,
            use_chaos=True, chaos_depth=0.14,
            use_drone=True, drone_vol=0.08, drone_detune=0.12,
            use_lfo_filter=True, lfo_fc=700.0, lfo_depth=300.0, lfo_rate=0.05,
            use_monaural=True, monaural_vol=0.04,
            use_formant=True, formant_intensity=0.18,
            use_saturate=True, saturate_drive=0.08,
            use_respiratory=True, breath_bpm=5.5, breath_bpm_end=4.5,
            breath_depth=0.13,
            use_comfort_eq=True, block_gain=0.72,
            seed=3
        ),
        Block(
            label='DELTA APPROACH', dur_s=540,
            c0=528, c1=528, b0=4.5, b1=2.0,
            carrier_type='soft',
            carrier_jitter=2.5, beat_jitter=0.20,
            noise_pw=0.2, noise_bw=0.8,
            iso_layers=[(4.5,  264, 0.08,  8, 25),
                        (40.0, 200, 0.05, 10, 12)],
            cfc_theta=5.5, cfc_strength=0.42,
            assr_80hz_vol=0.03,
            infra_freq=0.067, infra_depth=0.12,
            phase_lock=True, phase_lock_depth=0.15,
            use_wind=True, wind_vol=0.06, wind_bw=12.0,
            use_monaural=True, monaural_vol=0.035,
            use_saturate=True, saturate_drive=0.07,
            use_respiratory=True, breath_bpm=5.0, breath_bpm_end=4.0,
            breath_depth=0.13,
            use_comfort_eq=True, block_gain=0.68,
            use_focus_mix=True, focus_body_beat=2.0, focus_cortex_beat=10.0,
            seed=4
        ),
        Block(
            label='VOID CORE', dur_s=720,
            c0=528, c1=528, b0=1.5, b1=1.5,
            carrier_type='soft',
            carrier_jitter=3.0, beat_jitter=0.08,
            noise_pw=0.0, noise_bw=1.0,
            iso_layers=[(33.0, 180, 0.045, 22, 22),
                        (40.0, 200, 0.055, 22, 22)],
            cfc_theta=5.0, cfc_strength=0.45,
            assr_80hz_vol=0.03,
            spatial_3d=True, itd_period=18.0, el_period=29.0,
            infra_freq=0.033, infra_depth=0.12,
            use_chaos=True, chaos_depth=0.16,
            use_wind=True, wind_vol=0.05, wind_bw=10.0,
            use_formant=True, formant_intensity=0.18,
            use_reverb=True, reverb_rt60=900.0, reverb_wet=0.09,
            use_respiratory=True, breath_bpm=4.5, breath_bpm_end=4.0,
            breath_depth=0.14,
            use_comfort_eq=True, block_gain=0.62,
            use_focus_mix=True, focus_body_beat=1.5, focus_cortex_beat=8.0,
            quiet_before_s=60.0,
            seed=5
        ),
        Block(
            label='ASCENT SURGE', dur_s=360,
            c0=528, c1=639, b0=1.5, b1=12.0,
            carrier_type='warm',
            carrier_jitter=1.5, beat_jitter=0.16,
            noise_pw=0.9, noise_bw=0.1,
            iso_layers=[(40.0, 200, 0.08, 6, 8),
                        (33.0, 216, 0.055, 6, 8)],
            cfc_theta=6.0, cfc_strength=0.30,
            assr_80hz_vol=0.035,
            spatial_3d=True, itd_period=8.0, el_period=11.0,
            infra_freq=0.10, infra_depth=0.09,
            use_hrtf=True, hrtf_az_sweep=6.0, hrtf_elevation=15.0,
            use_drone=True, drone_vol=0.08,
            use_monaural=True, monaural_vol=0.04,
            use_saturate=True, saturate_drive=0.08,
            use_respiratory=True, breath_bpm=5.0, breath_depth=0.11,
            use_comfort_eq=True, block_gain=0.72,
            seed=6
        ),
        Block(
            label='SCHUMANN INTEGRATION', dur_s=480,
            c0=639, c1=432, b0=12.0, b1=7.83,
            carrier_type='warm',
            carrier_jitter=1.2, beat_jitter=0.10,
            noise_pw=0.85, noise_bw=0.15,
            iso_layers=[(7.83, 432, 0.07,  8,  8),
                        (40.0, 200, 0.06, 10, 12)],
            cfc_theta=7.83, cfc_strength=0.35,
            assr_80hz_vol=0.03,
            itd_period=12.0, use_hrtf=True, hrtf_az_sweep=12.0,
            infra_freq=0.083, infra_depth=0.10,
            schumann_mode=True,
            use_wind=True, wind_vol=0.055,
            use_lfo_filter=True, lfo_fc=850.0, lfo_depth=380.0, lfo_rate=0.04,
            use_monaural=True, monaural_vol=0.04,
            use_formant=True, formant_intensity=0.16,
            use_saturate=True, saturate_drive=0.08,
            use_respiratory=True, breath_bpm=6.0, breath_depth=0.11,
            use_comfort_eq=True, block_gain=0.74,
            seed=7
        ),
        Block(
            label='ACTIVATION LOCK', dur_s=360,
            c0=432, c1=200, b0=7.83, b1=30.0,
            carrier_type='warm',
            carrier_jitter=0.8, beat_jitter=0.10,
            noise_pw=1.0, noise_bw=0.0,
            iso_layers=[(40.0, 200, 0.085, 6, 5),
                        (30.0, 216, 0.06, 10, 5)],
            assr_80hz_vol=0.04,
            itd_period=9.0, use_hrtf=True, hrtf_az_sweep=0,
            use_drone=True, drone_vol=0.07,
            use_monaural=True, monaural_vol=0.045,
            use_saturate=True, saturate_drive=0.08,
            use_comfort_eq=True, block_gain=0.78,
            seed=8
        ),
    ]


# ══════════════════════════════════════════════════════════
#  WALK — ~32 min core
# ══════════════════════════════════════════════════════════

def _walk():
    return [
        Block(
            label='WALK — ALIGN', dur_s=300,
            c0=200, c1=200, b0=12.0, b1=10.0,
            carrier_type='warm',
            carrier_jitter=0.5, beat_jitter=0.06,
            noise_pw=1.0, noise_bw=0.0,
            use_hrtf=True, itd_period=10.0,
            use_drone=True, drone_vol=0.08,
            use_monaural=True, monaural_vol=0.04,
            use_formant=True, formant_intensity=0.16,
            use_saturate=True, saturate_drive=0.08,
            use_reverb=True, reverb_rt60=500.0, reverb_wet=0.08,
            use_comfort_eq=True, block_gain=0.78,
            seed=41
        ),
        Block(
            label='WALK — EXPAND', dur_s=600,
            c0=200, c1=204, b0=10.0, b1=8.0,
            carrier_type='warm',
            carrier_jitter=1.2, beat_jitter=0.10,
            noise_pw=1.0, noise_bw=0.0,
            iso_layers=[(40.0, 200, 0.05, 12, 10)],
            cfc_theta=8.0, cfc_strength=0.22,
            itd_period=12.0, use_hrtf=True,
            infra_freq=0.10, infra_depth=0.09,
            use_drone=True, drone_vol=0.08, drone_detune=0.12,
            use_wind=True,  wind_vol=0.05,
            use_monaural=True, monaural_vol=0.04,
            use_formant=True, formant_intensity=0.17,
            use_saturate=True, saturate_drive=0.08,
            use_reverb=True, reverb_rt60=550.0, reverb_wet=0.09,
            use_respiratory=True, breath_bpm=6.0, breath_depth=0.11,
            use_comfort_eq=True, block_gain=0.76,
            seed=42
        ),
        Block(
            label='WALK — OPERATOR', dur_s=600,
            c0=204, c1=206, b0=8.0, b1=7.5,
            carrier_type='warm',
            carrier_jitter=1.8, beat_jitter=0.12,
            noise_pw=0.9, noise_bw=0.1,
            iso_layers=[(40.0, 200, 0.055, 10, 8)],
            cfc_theta=7.5, cfc_strength=0.26,
            assr_80hz_vol=0.03,
            itd_period=14.0, use_hrtf=True,
            infra_freq=0.083, infra_depth=0.09,
            use_drone=True, drone_vol=0.09, drone_detune=0.14,
            use_phi=True,
            use_lfo_filter=True, lfo_fc=750.0, lfo_depth=300.0, lfo_rate=0.04,
            use_monaural=True, monaural_vol=0.04,
            use_formant=True, formant_intensity=0.17,
            use_saturate=True, saturate_drive=0.08,
            use_reverb=True, reverb_rt60=600.0, reverb_wet=0.09,
            use_respiratory=True, breath_bpm=6.0, breath_depth=0.11,
            use_comfort_eq=True, block_gain=0.76,
            seed=43
        ),
        Block(
            label='WALK — RETURN', dur_s=300,
            c0=206, c1=200, b0=7.5, b1=10.0,
            carrier_type='warm',
            carrier_jitter=0.8, beat_jitter=0.08,
            noise_pw=1.0, noise_bw=0.0,
            iso_layers=[(40.0, 200, 0.05, 6, 6)],
            itd_period=10.0, use_hrtf=True,
            use_drone=True, drone_vol=0.07,
            use_monaural=True, monaural_vol=0.035,
            use_formant=True, formant_intensity=0.15,
            use_saturate=True, saturate_drive=0.08,
            use_reverb=True, reverb_rt60=500.0, reverb_wet=0.08,
            use_comfort_eq=True, block_gain=0.78,
            seed=44
        ),
    ]


# ══════════════════════════════════════════════════════════
#  SLEEP — ~87 min core (+ quiet windows)
# ══════════════════════════════════════════════════════════

def _sleep():
    return [
        Block(label='SLEEP — SETTLE', dur_s=600,
              c0=200, c1=200, b0=10.0, b1=5.5,
              carrier_type='soft', noise_pw=1.0, noise_bw=0.0,
              infra_freq=0.10, infra_depth=0.09,
              use_wind=True, wind_vol=0.05,
              use_respiratory=True, breath_bpm=5.5, breath_bpm_end=4.5,
              breath_depth=0.12,
              use_monaural=True, monaural_vol=0.03,
              block_gain=0.52, use_comfort_eq=True,
              seed=51),

        Block(label='SLEEP — DRIFT', dur_s=600,
              c0=200, c1=200, b0=5.5, b1=3.0,
              carrier_type='soft', noise_pw=0.4, noise_bw=0.6,
              infra_freq=0.067, infra_depth=0.11,
              use_wind=True, wind_vol=0.05,
              use_respiratory=True, breath_bpm=4.5, breath_bpm_end=4.0,
              breath_depth=0.13,
              use_monaural=True, monaural_vol=0.03,
              block_gain=0.52, use_comfort_eq=True,
              seed=52),

        Block(label='SLEEP — DEEP 1', dur_s=900,
              c0=200, c1=200, b0=3.0, b1=2.0,
              carrier_type='soft', noise_pw=0.0, noise_bw=1.0,
              infra_freq=0.033, infra_depth=0.12,
              use_granular=True, granular_grain_ms=120.0,
              granular_density=6.0, granular_pitch_st=0.12,
              granular_scatter=0.60, granular_vol=0.05,
              use_respiratory=True, breath_bpm=4.0, breath_depth=0.14,
              use_focus_mix=True, focus_body_beat=2.0, focus_cortex_beat=9.0,
              use_monaural=True, monaural_vol=0.025,
              block_gain=0.52, use_comfort_eq=True,
              seed=53),

        Block(label='SLEEP — WINDOW 1', dur_s=300,
              c0=200, c1=201, b0=2.0, b1=6.0,
              carrier_type='warm', noise_pw=0.2, noise_bw=0.8,
              iso_layers=[(40.0, 200, 0.065, 6, 8)],
              cfc_theta=6.0, cfc_strength=0.35, assr_80hz_vol=0.03,
              spatial_3d=True, itd_period=8.0, el_period=13.0, el_depth=0.35,
              use_hrtf=True, hrtf_az_sweep=8.0, hrtf_elevation=10.0,
              use_chaos=True, chaos_depth=0.14,
              use_drone=True, drone_vol=0.06,
              use_monaural=True, monaural_vol=0.035,
              block_gain=0.58, use_comfort_eq=True,
              quiet_before_s=45.0,
              seed=54),

        Block(label='SLEEP — HOLD 1', dur_s=120,
              c0=201, c1=201, b0=6.0, b1=6.0,
              carrier_type='warm', noise_pw=0.3, noise_bw=0.7,
              iso_layers=[(40.0, 200, 0.06, 6, 6)],
              cfc_theta=6.0, cfc_strength=0.38,
              use_hrtf=True, hrtf_az_sweep=8.0,
              use_monaural=True, monaural_vol=0.035,
              block_gain=0.55, use_comfort_eq=True,
              seed=55),

        Block(label='SLEEP — DESCENT 1', dur_s=300,
              c0=201, c1=200, b0=6.0, b1=2.0,
              carrier_type='soft', noise_pw=0.1, noise_bw=0.9,
              iso_layers=[(40.0, 200, 0.05, 8, 16)],
              infra_freq=0.033, infra_depth=0.12,
              use_respiratory=True, breath_bpm=4.0, breath_depth=0.14,
              use_monaural=True, monaural_vol=0.03,
              block_gain=0.52, use_comfort_eq=True,
              seed=56),

        Block(label='SLEEP — DEEP 2', dur_s=900,
              c0=200, c1=202, b0=2.0, b1=2.0,
              carrier_type='soft', noise_pw=0.0, noise_bw=1.0,
              iso_layers=[(40.0, 200, 0.05, 22, 22)],
              cfc_theta=5.0, cfc_strength=0.38,
              infra_freq=0.025, infra_depth=0.13,
              use_granular=True, granular_grain_ms=140.0,
              granular_density=5.0, granular_pitch_st=0.10,
              granular_scatter=0.65, granular_vol=0.045,
              use_respiratory=True, breath_bpm=4.0, breath_depth=0.14,
              use_focus_mix=True, focus_body_beat=1.5, focus_cortex_beat=8.0,
              block_gain=0.52, use_comfort_eq=True,
              seed=57),

        Block(label='SLEEP — WINDOW 2', dur_s=300,
              c0=202, c1=203, b0=2.0, b1=6.0,
              carrier_type='warm', noise_pw=0.2, noise_bw=0.8,
              iso_layers=[(40.0, 200, 0.07, 6, 8),
                          (33.0, 180, 0.045, 8, 8)],
              cfc_theta=6.0, cfc_strength=0.38, assr_80hz_vol=0.03,
              spatial_3d=True, itd_period=7.0, el_period=11.0, el_depth=0.40,
              use_hrtf=True, hrtf_az_sweep=7.0, hrtf_elevation=15.0,
              use_chaos=True, chaos_depth=0.15,
              use_drone=True, drone_vol=0.06,
              use_monaural=True, monaural_vol=0.035,
              block_gain=0.58, use_comfort_eq=True,
              quiet_before_s=45.0,
              seed=58),

        Block(label='SLEEP — HOLD 2', dur_s=120,
              c0=203, c1=203, b0=6.0, b1=6.0,
              carrier_type='warm',
              iso_layers=[(40.0, 200, 0.06, 6, 6)],
              cfc_theta=6.0, cfc_strength=0.40,
              use_hrtf=True,
              use_monaural=True, monaural_vol=0.035,
              block_gain=0.55, use_comfort_eq=True,
              seed=59),

        Block(label='SLEEP — DESCENT 2', dur_s=300,
              c0=203, c1=200, b0=6.0, b1=2.0,
              carrier_type='soft', noise_pw=0.1, noise_bw=0.9,
              infra_freq=0.033, infra_depth=0.12,
              use_respiratory=True, breath_bpm=4.0, breath_depth=0.14,
              use_monaural=True, monaural_vol=0.03,
              block_gain=0.52, use_comfort_eq=True,
              seed=60),

        Block(label='SLEEP — WINDOW 3', dur_s=300,
              c0=200, c1=204, b0=2.0, b1=7.83,
              carrier_type='warm', noise_pw=0.3, noise_bw=0.7,
              iso_layers=[(40.0, 200, 0.075, 6, 6),
                          (33.0, 180, 0.05, 6, 6)],
              cfc_theta=6.5, cfc_strength=0.42, assr_80hz_vol=0.035,
              spatial_3d=True, itd_period=6.0, el_period=11.0, el_depth=0.45,
              use_hrtf=True, hrtf_az_sweep=6.0, hrtf_elevation=20.0,
              use_chaos=True, chaos_depth=0.16,
              phase_lock=True, phase_lock_depth=0.16,
              use_drone=True, drone_vol=0.07,
              use_monaural=True, monaural_vol=0.035,
              block_gain=0.60, use_comfort_eq=True,
              quiet_before_s=60.0,
              seed=61),

        Block(label='SLEEP — HOLD 3', dur_s=180,
              c0=204, c1=204, b0=7.83, b1=7.83,
              carrier_type='warm',
              iso_layers=[(40.0, 200, 0.065, 6, 8),
                          (33.0, 180, 0.045, 6, 8)],
              cfc_theta=7.83, cfc_strength=0.35,
              use_hrtf=True, hrtf_az_sweep=8.0,
              use_monaural=True, monaural_vol=0.035,
              block_gain=0.56, use_comfort_eq=True,
              seed=62),

        Block(label='SLEEP — CLOSE', dur_s=300,
              c0=204, c1=200, b0=7.83, b1=2.5,
              carrier_type='soft', noise_pw=0.1, noise_bw=0.9,
              use_wind=True, wind_vol=0.04,
              infra_freq=0.025, infra_depth=0.13,
              use_respiratory=True, breath_bpm=4.0, breath_depth=0.14,
              use_monaural=True, monaural_vol=0.025,
              block_gain=0.48, use_comfort_eq=True,
              seed=63),
    ]


# ══════════════════════════════════════════════════════════
#  HEALER — ~64 min core
# ══════════════════════════════════════════════════════════

def _healer():
    return [
        Block(label='HEALER — OPEN', dur_s=480,
              c0=528, c1=528, b0=10.0, b1=6.0,
              carrier_type='rich', noise_pw=0.9, noise_bw=0.1,
              iso_layers=[(6.0, 264, 0.08, 10, 10)],
              cfc_theta=6.0, cfc_strength=0.28,
              infra_freq=0.10, infra_depth=0.10,
              use_phi=True, use_drone=True, drone_vol=0.08,
              use_wind=True, wind_vol=0.055,
              use_monaural=True, monaural_vol=0.04,
              use_formant=True, formant_intensity=0.18,
              use_saturate=True, saturate_drive=0.08,
              use_reverb=True, reverb_rt60=650.0, reverb_wet=0.09,
              use_respiratory=True, breath_bpm=6.0, breath_depth=0.12,
              block_gain=0.58, use_comfort_eq=True,
              seed=71),

        Block(label='HEALER — DESCENT', dur_s=720,
              c0=528, c1=528, b0=6.0, b1=2.0,
              carrier_type='rich', noise_pw=0.4, noise_bw=0.6,
              iso_layers=[(5.0, 264, 0.07, 12, 16),
                          (40.0, 200, 0.05, 14, 10)],
              cfc_theta=5.0, cfc_strength=0.42,
              infra_freq=0.067, infra_depth=0.12,
              use_phi=True, use_drone=True, drone_vol=0.08,
              use_wind=True, wind_vol=0.055,
              use_lfo_filter=True, lfo_fc=650.0, lfo_depth=280.0, lfo_rate=0.04,
              use_monaural=True, monaural_vol=0.04,
              use_formant=True, formant_intensity=0.17,
              use_saturate=True, saturate_drive=0.08,
              use_reverb=True, reverb_rt60=700.0, reverb_wet=0.09,
              use_respiratory=True, breath_bpm=5.5, breath_bpm_end=4.0,
              breath_depth=0.13,
              block_gain=0.56, use_comfort_eq=True,
              seed=72),

        Block(label='HEALER — VOID 1', dur_s=900,
              c0=528, c1=528, b0=1.5, b1=1.5,
              carrier_type='soft', noise_pw=0.0, noise_bw=1.0,
              iso_layers=[(40.0, 200, 0.05, 22, 22),
                          (33.0, 180, 0.04, 25, 25)],
              cfc_theta=5.0, cfc_strength=0.48, assr_80hz_vol=0.03,
              infra_freq=0.033, infra_depth=0.13,
              use_phi=True, use_wind=True, wind_vol=0.045,
              use_granular=True, granular_grain_ms=110.0,
              granular_density=8.0, granular_pitch_st=0.18,
              granular_scatter=0.55, granular_vol=0.065,
              use_formant=True, formant_intensity=0.16,
              use_respiratory=True, breath_bpm=4.5, breath_bpm_end=4.0,
              breath_depth=0.14,
              use_focus_mix=True, focus_body_beat=1.5, focus_cortex_beat=8.0,
              block_gain=0.52, use_comfort_eq=True,
              quiet_before_s=60.0,
              seed=73),

        Block(label='HEALER — VOID 2', dur_s=900,
              c0=528, c1=528, b0=1.5, b1=1.5,
              carrier_type='soft', noise_pw=0.0, noise_bw=1.0,
              iso_layers=[(40.0, 200, 0.05, 22, 22)],
              cfc_theta=4.5, cfc_strength=0.50, assr_80hz_vol=0.03,
              infra_freq=0.025, infra_depth=0.13,
              use_phi=True,
              use_granular=True, granular_grain_ms=130.0,
              granular_density=6.0, granular_pitch_st=0.14,
              granular_scatter=0.60, granular_vol=0.055,
              use_formant=True, formant_intensity=0.16,
              use_respiratory=True, breath_bpm=4.0, breath_depth=0.14,
              use_focus_mix=True, focus_body_beat=1.5, focus_cortex_beat=7.5,
              block_gain=0.52, use_comfort_eq=True,
              quiet_before_s=45.0,
              seed=74),

        Block(label='HEALER — RETURN', dur_s=480,
              c0=528, c1=432, b0=1.5, b1=8.0,
              carrier_type='rich', noise_pw=0.8, noise_bw=0.2,
              iso_layers=[(40.0, 200, 0.07, 8, 8)],
              cfc_theta=6.0, cfc_strength=0.28,
              infra_freq=0.083, infra_depth=0.10,
              use_drone=True, drone_vol=0.07,
              use_monaural=True, monaural_vol=0.04,
              use_formant=True, formant_intensity=0.17,
              use_saturate=True, saturate_drive=0.08,
              use_reverb=True, reverb_rt60=650.0, reverb_wet=0.09,
              use_respiratory=True, breath_bpm=5.0, breath_depth=0.12,
              block_gain=0.60, use_comfort_eq=True,
              seed=75),

        Block(label='HEALER — INTEGRATE', dur_s=270,
              c0=432, c1=432, b0=8.0, b1=12.0,
              carrier_type='rich', noise_pw=1.0, noise_bw=0.0,
              iso_layers=[(40.0, 200, 0.075, 6, 5)],
              assr_80hz_vol=0.03,
              use_formant=True, formant_intensity=0.16,
              use_saturate=True, saturate_drive=0.08,
              use_reverb=True, reverb_rt60=550.0, reverb_wet=0.08,
              use_monaural=True, monaural_vol=0.035,
              block_gain=0.62, use_comfort_eq=True,
              seed=76),
    ]


# ══════════════════════════════════════════════════════════
#  ORACLE — ~57 min core
# ══════════════════════════════════════════════════════════

def _oracle():
    return [
        Block(label='ORACLE — EARTH OPEN', dur_s=600,
              c0=432, c1=432, b0=10.0, b1=7.83,
              carrier_type='organ', schumann_mode=True,
              iso_layers=[(7.83, 432, 0.065, 12, 12)],
              cfc_theta=7.83, cfc_strength=0.28,
              infra_freq=0.083, infra_depth=0.10,
              use_hrtf=True, itd_period=14.0,
              use_wind=True, wind_vol=0.055,
              use_monaural=True, monaural_vol=0.04,
              use_formant=True, formant_intensity=0.18,
              use_saturate=True, saturate_drive=0.08,
              use_reverb=True, reverb_rt60=700.0, reverb_wet=0.09,
              use_respiratory=True, breath_bpm=6.0, breath_depth=0.12,
              block_gain=0.72, use_comfort_eq=True,
              seed=81),

        Block(label='ORACLE — THETA 1', dur_s=720,
              c0=432, c1=432, b0=7.83, b1=5.5,
              carrier_type='warm', noise_pw=0.7, noise_bw=0.3,
              iso_layers=[(6.0,  216, 0.08, 14, 12),
                          (40.0, 200, 0.05, 16, 10)],
              cfc_theta=6.5, cfc_strength=0.40,
              itd_period=16.0, use_hrtf=True,
              infra_freq=0.067, infra_depth=0.11,
              use_drone=True, drone_vol=0.07,
              use_lfo_filter=True, lfo_fc=700.0, lfo_depth=320.0, lfo_rate=0.05,
              use_monaural=True, monaural_vol=0.04,
              use_formant=True, formant_intensity=0.18,
              use_saturate=True, saturate_drive=0.08,
              use_reverb=True, reverb_rt60=750.0, reverb_wet=0.09,
              use_respiratory=True, breath_bpm=6.0, breath_bpm_end=5.0,
              breath_depth=0.12,
              block_gain=0.72, use_comfort_eq=True,
              seed=82),

        Block(label='ORACLE — THETA 2 CHAOS', dur_s=720,
              c0=432, c1=432, b0=5.5, b1=4.5,
              carrier_type='warm', noise_pw=0.5, noise_bw=0.5,
              iso_layers=[(5.5,  216, 0.075, 12, 12),
                          (40.0, 200, 0.055, 14, 10)],
              cfc_theta=5.5, cfc_strength=0.45, assr_80hz_vol=0.03,
              itd_period=18.0, use_hrtf=True,
              infra_freq=0.05, infra_depth=0.11,
              use_chaos=True, chaos_depth=0.16,
              phase_lock=True, phase_lock_depth=0.14,
              use_drone=True, drone_vol=0.07,
              use_monaural=True, monaural_vol=0.04,
              use_formant=True, formant_intensity=0.18,
              use_saturate=True, saturate_drive=0.08,
              use_reverb=True, reverb_rt60=800.0, reverb_wet=0.09,
              use_respiratory=True, breath_bpm=5.5, breath_bpm_end=4.5,
              breath_depth=0.13,
              block_gain=0.70, use_comfort_eq=True,
              seed=83),

        Block(label='ORACLE — VISION HOLD', dur_s=480,
              c0=432, c1=432, b0=4.5, b1=4.5,
              carrier_type='organ', noise_pw=0.4, noise_bw=0.6,
              iso_layers=[(40.0, 200, 0.055, 12, 12),
                          (33.0, 180, 0.04, 14, 14)],
              cfc_theta=4.5, cfc_strength=0.48, assr_80hz_vol=0.03,
              spatial_3d=True, itd_period=14.0, el_period=23.0, el_depth=0.35,
              infra_freq=0.05, infra_depth=0.12,
              use_phi=True, use_hrtf=True, hrtf_az_sweep=14.0,
              use_wind=True, wind_vol=0.055,
              use_formant=True, formant_intensity=0.18,
              use_reverb=True, reverb_rt60=1000.0, reverb_wet=0.10,
              use_respiratory=True, breath_bpm=5.0, breath_bpm_end=4.0,
              breath_depth=0.13,
              use_focus_mix=True, focus_body_beat=2.0, focus_cortex_beat=9.0,
              block_gain=0.70, use_comfort_eq=True,
              quiet_before_s=60.0,
              seed=84),

        Block(label='ORACLE — SCHUMANN RETURN', dur_s=480,
              c0=432, c1=432, b0=4.5, b1=7.83,
              carrier_type='organ', schumann_mode=True,
              iso_layers=[(7.83, 432, 0.07, 10, 10),
                          (40.0, 200, 0.055, 10, 8)],
              cfc_theta=7.83, cfc_strength=0.32,
              itd_period=12.0, use_hrtf=True, hrtf_az_sweep=12.0,
              infra_freq=0.083, infra_depth=0.10,
              use_wind=True, wind_vol=0.05,
              use_monaural=True, monaural_vol=0.04,
              use_formant=True, formant_intensity=0.16,
              use_saturate=True, saturate_drive=0.08,
              use_reverb=True, reverb_rt60=700.0, reverb_wet=0.09,
              use_respiratory=True, breath_bpm=6.0, breath_depth=0.11,
              block_gain=0.72, use_comfort_eq=True,
              seed=85),

        Block(label='ORACLE — SEAL', dur_s=360,
              c0=432, c1=432, b0=7.83, b1=14.0,
              carrier_type='warm', noise_pw=1.0, noise_bw=0.0,
              iso_layers=[(40.0, 200, 0.08, 6, 5),
                          (14.0, 216, 0.06, 10, 5)],
              assr_80hz_vol=0.035,
              use_drone=True, drone_vol=0.07,
              use_monaural=True, monaural_vol=0.04,
              use_formant=True, formant_intensity=0.16,
              use_saturate=True, saturate_drive=0.08,
              block_gain=0.74, use_comfort_eq=True,
              seed=86),
    ]


# ══════════════════════════════════════════════════════════
#  WARRIOR — sharp-safe (~51 min core)
#  Higher energy, soft edges, no comfort EQ on peak blocks.
# ══════════════════════════════════════════════════════════

def _warrior():
    return [
        Block(label='WARRIOR — CHARGE', dur_s=300,
              c0=200, c1=200, b0=30.0, b1=40.0,
              carrier_type='sine', noise_pw=1.0, noise_bw=0.0,
              iso_layers=[(40.0, 200, 0.11, 5, 6)],
              assr_80hz_vol=0.06, itd_period=8.0,
              use_hrtf=True,
              use_monaural=True, monaural_vol=0.055, monaural_beat_hz=40.0,
              use_saturate=True, saturate_drive=0.08,
              use_underbed=True, underbed_vol=0.010,
              soft_ceiling_fs=0.52, block_gain=0.95,
              am_depth_cap=0.30,
              allow_sharp_iso=True, use_silk=True, silk_cutoff_hz=6000.0,
              organic_style='minimal', organic_intensity=0.40,
              carrier_drift_hz=0.45, spectral_breath_mix=0.05,
              intro_fade_s=6.0,
              seed=91),

        Block(label='WARRIOR — PEAK', dur_s=600,
              c0=200, c1=432, b0=40.0, b1=40.0,
              carrier_type='sine', noise_pw=1.0, noise_bw=0.0,
              iso_layers=[(40.0, 200, 0.12, 5, 6)],
              assr_80hz_vol=0.07, itd_period=6.0,
              use_hrtf=True,
              use_chaos=True, chaos_depth=0.12,
              use_monaural=True, monaural_vol=0.055, monaural_beat_hz=40.0,
              use_saturate=True, saturate_drive=0.08,
              use_underbed=True, underbed_vol=0.010,
              soft_ceiling_fs=0.52, block_gain=0.95,
              am_depth_cap=0.30,
              allow_sharp_iso=True, use_silk=True, silk_cutoff_hz=6000.0,
              organic_style='minimal', organic_intensity=0.35,
              carrier_drift_hz=0.40, spectral_breath_mix=0.04,
              intro_fade_s=6.0,
              seed=92),

        Block(label='WARRIOR — DESCENT', dur_s=480,
              c0=432, c1=432, b0=40.0, b1=12.0,
              carrier_type='warm', noise_pw=0.8, noise_bw=0.2,
              iso_layers=[(40.0, 200, 0.09, 6, 10),
                          (33.0, 216, 0.055, 6, 10)],
              cfc_theta=8.0, cfc_strength=0.25,
              assr_80hz_vol=0.045, itd_period=8.0,
              use_hrtf=True,
              use_monaural=True, monaural_vol=0.045,
              use_saturate=True, saturate_drive=0.08,
              use_comfort_eq=True, block_gain=0.88,
              organic_style='focus', organic_intensity=0.70,
              seed=93),

        Block(label='WARRIOR — THETA TOUCH', dur_s=480,
              c0=432, c1=432, b0=12.0, b1=7.83,
              carrier_type='warm', noise_pw=0.7, noise_bw=0.3,
              iso_layers=[(40.0, 200, 0.075, 8, 10)],
              cfc_theta=7.83, cfc_strength=0.32, assr_80hz_vol=0.04,
              infra_freq=0.083, infra_depth=0.09,
              use_monaural=True, monaural_vol=0.04,
              use_formant=True, formant_intensity=0.15,
              use_saturate=True, saturate_drive=0.08,
              use_comfort_eq=True, block_gain=0.85,
              organic_style='rest', organic_intensity=0.85,
              seed=94),

        Block(label='WARRIOR — RELOAD', dur_s=600,
              c0=432, c1=200, b0=7.83, b1=35.0,
              carrier_type='sine', noise_pw=1.0, noise_bw=0.0,
              iso_layers=[(40.0, 200, 0.11, 5, 5),
                          (35.0, 216, 0.075, 5, 5)],
              assr_80hz_vol=0.06, itd_period=6.0,
              use_hrtf=True,
              use_chaos=True, chaos_depth=0.10,
              use_monaural=True, monaural_vol=0.055, monaural_beat_hz=35.0,
              use_saturate=True, saturate_drive=0.08,
              soft_ceiling_fs=0.52, block_gain=0.95,
              am_depth_cap=0.30,
              allow_sharp_iso=True, use_silk=True, silk_cutoff_hz=6000.0,
              organic_style='minimal', organic_intensity=0.38,
              carrier_drift_hz=0.45, spectral_breath_mix=0.05,
              intro_fade_s=6.0,
              seed=95),

        Block(label='WARRIOR — LOCK', dur_s=540,
              c0=200, c1=200, b0=35.0, b1=40.0,
              carrier_type='sine', noise_pw=1.0, noise_bw=0.0,
              iso_layers=[(40.0, 200, 0.12, 5, 5)],
              assr_80hz_vol=0.07, itd_period=5.0,
              use_hrtf=True,
              use_monaural=True, monaural_vol=0.055, monaural_beat_hz=40.0,
              use_saturate=True, saturate_drive=0.08,
              soft_ceiling_fs=0.52, block_gain=0.95,
              am_depth_cap=0.30,
              allow_sharp_iso=True, use_silk=True, silk_cutoff_hz=6000.0,
              organic_style='minimal', organic_intensity=0.35,
              carrier_drift_hz=0.40, spectral_breath_mix=0.04,
              intro_fade_s=6.0,
              seed=96),
    ]

# ══════════════════════════════════════════════════════════
#  GATEWAY EDGE — ~29–31 min
#  Monroe-inspired ladder for practitioners with F10 automation:
#  F10 lock → F12 expand → F15 no-time → interrupt → F21 touch → seal
#  Rare-use edge session; not nightly. Permanent levels, exotic map.
# ══════════════════════════════════════════════════════════

def _gateway_edge():
    return [
        # ── F10: mind awake / body asleep (FocusMix dual-state)
        Block(
            label='EDGE — F10 LOCK', dur_s=300,
            c0=200, c1=200, b0=10.0, b1=4.0,
            carrier_type='soft',
            carrier_jitter=0.6, beat_jitter=0.06,
            noise_pw=0.5, noise_bw=0.5,
            use_focus_mix=True,
            focus_body_beat=2.0, focus_cortex_beat=12.0,
            focus_vol_body=0.08, focus_vol_cortex=0.055,
            use_monaural=True, monaural_vol=0.035,
            use_drone=True, drone_vol=0.07, drone_detune=0.12,
            use_wind=True, wind_vol=0.04, wind_bw=14.0,
            infra_freq=0.083, infra_depth=0.09,
            use_respiratory=True, breath_bpm=6.0, breath_bpm_end=5.0,
            breath_depth=0.12,
            use_formant=True, formant_intensity=0.14,
            use_saturate=True, saturate_drive=0.07,
            use_comfort_eq=True, block_gain=0.68,
            underbed_vol=0.016,
            seed=201
        ),
        # ── F12: expanded awareness
        Block(
            label='EDGE — F12 EXPAND', dur_s=420,
            c0=200, c1=432, b0=4.0, b1=7.83,
            carrier_type='warm',
            carrier_jitter=1.2, beat_jitter=0.10,
            noise_pw=0.7, noise_bw=0.3,
            iso_layers=[(7.83, 216, 0.06, 12, 12),
                        (40.0, 200, 0.045, 14, 10)],
            cfc_theta=7.83, cfc_strength=0.32,
            use_phi=True,
            schumann_mode=True,
            use_hrtf=True, hrtf_az_sweep=14.0, hrtf_elevation=8.0,
            itd_period=14.0,
            use_monaural=True, monaural_vol=0.04,
            use_drone=True, drone_vol=0.07,
            use_lfo_filter=True, lfo_fc=720.0, lfo_depth=280.0, lfo_rate=0.04,
            infra_freq=0.067, infra_depth=0.10,
            use_respiratory=True, breath_bpm=5.5, breath_bpm_end=4.5,
            breath_depth=0.12,
            use_formant=True, formant_intensity=0.16,
            use_saturate=True, saturate_drive=0.08,
            use_reverb=True, reverb_rt60=750.0, reverb_wet=0.09,
            use_comfort_eq=True, block_gain=0.70,
            seed=202
        ),
        # ── F15: no-time / void (quiet before = internalization)
        Block(
            label='EDGE — F15 NO-TIME', dur_s=480,
            c0=432, c1=432, b0=7.83, b1=1.5,
            carrier_type='soft',
            carrier_jitter=2.0, beat_jitter=0.10,
            noise_pw=0.0, noise_bw=1.0,
            iso_layers=[(4.5, 216, 0.045, 20, 24),
                        (40.0, 200, 0.028, 24, 24)],
            cfc_theta=5.0, cfc_strength=0.35,
            use_focus_mix=True,
            focus_body_beat=1.5, focus_cortex_beat=8.0,
            focus_vol_body=0.06, focus_vol_cortex=0.04,
            use_chaos=True, chaos_depth=0.10,
            use_granular=True, granular_grain_ms=140.0,
            granular_density=5.0, granular_pitch_st=0.08,
            granular_scatter=0.55, granular_vol=0.04,
            use_wind=True, wind_vol=0.05, wind_bw=11.0,
            infra_freq=0.033, infra_depth=0.11,
            phase_lock=True, phase_lock_depth=0.12,
            use_respiratory=True, breath_bpm=4.5, breath_bpm_end=4.0,
            breath_depth=0.13,
            use_formant=True, formant_intensity=0.10, formant_vowel='O',
            use_reverb=True, reverb_rt60=900.0, reverb_wet=0.08,
            use_comfort_eq=True, block_gain=0.55,
            quiet_before_s=40.0,
            underbed_vol=0.018,
            intro_fade_s=14.0, outro_fade_s=12.0,
            silk_cutoff_hz=4800.0,
            seed=203
        ),
        # ── Soft pattern interrupt: texture/beat shift — NOT a whistle slam
        Block(
            label='EDGE — INTERRUPT', dur_s=60,
            c0=432, c1=440, b0=1.5, b1=5.5,
            carrier_type='soft',
            carrier_jitter=0.8, beat_jitter=0.06,
            noise_pw=0.35, noise_bw=0.65,
            iso_layers=[(5.5, 200, 0.04, 16, 16)],
            use_phi=True,
            use_monaural=True, monaural_vol=0.03,
            use_drone=True, drone_vol=0.05,
            use_wind=True, wind_vol=0.045,
            spatial_3d=True, itd_period=9.0, el_period=15.0, el_depth=0.28,
            use_hrtf=True, hrtf_az_sweep=10.0, hrtf_elevation=12.0,
            use_formant=True, formant_intensity=0.08, formant_vowel='U',
            use_saturate=True, saturate_drive=0.06,
            use_comfort_eq=True, block_gain=0.52,
            use_underbed=True, underbed_vol=0.016,
            quiet_before_s=25.0,
            intro_fade_s=18.0, outro_fade_s=14.0,
            silk_cutoff_hz=4500.0,
            seed=204
        ),
        # ── F21 touch: brief edge (soft exotic — no ASSR scream)
        Block(
            label='EDGE — F21 TOUCH', dur_s=210,
            c0=396, c1=432, b0=5.5, b1=4.5,
            carrier_type='warm',
            carrier_jitter=1.5, beat_jitter=0.10,
            noise_pw=0.4, noise_bw=0.6,
            iso_layers=[(40.0, 200, 0.035, 14, 14),
                        (7.83, 216, 0.04, 14, 14)],
            cfc_theta=4.5, cfc_strength=0.38,
            use_chaos=True, chaos_depth=0.12,
            use_phi=True,
            use_focus_mix=True,
            focus_body_beat=2.0, focus_cortex_beat=10.0,
            focus_vol_body=0.05, focus_vol_cortex=0.04,
            spatial_3d=True, itd_period=12.0, el_period=19.0, el_depth=0.35,
            use_hrtf=True, hrtf_az_sweep=10.0, hrtf_elevation=18.0,
            use_monaural=True, monaural_vol=0.03,
            infra_freq=0.05, infra_depth=0.10,
            use_respiratory=True, breath_bpm=4.0, breath_depth=0.12,
            use_formant=True, formant_intensity=0.10, formant_vowel='O',
            use_reverb=True, reverb_rt60=1000.0, reverb_wet=0.09,
            use_comfort_eq=True, block_gain=0.58,
            quiet_before_s=25.0,
            intro_fade_s=14.0, outro_fade_s=12.0,
            silk_cutoff_hz=4800.0,
            seed=205
        ),
        # ── Seal: F10 / body return — session "counts"
        Block(
            label='EDGE — SEAL', dur_s=300,
            c0=432, c1=200, b0=4.5, b1=10.0,
            carrier_type='soft',
            carrier_jitter=0.8, beat_jitter=0.06,
            noise_pw=0.8, noise_bw=0.2,
            use_focus_mix=True,
            focus_body_beat=2.5, focus_cortex_beat=11.0,
            focus_vol_body=0.06, focus_vol_cortex=0.045,
            iso_layers=[(10.0, 200, 0.04, 12, 12)],
            use_drone=True, drone_vol=0.07, drone_detune=0.10,
            use_monaural=True, monaural_vol=0.03,
            use_hrtf=True, itd_period=12.0,
            infra_freq=0.083, infra_depth=0.09,
            use_respiratory=True, breath_bpm=5.0, breath_bpm_end=6.0,
            breath_depth=0.11,
            use_formant=True, formant_intensity=0.10, formant_vowel='A',
            use_saturate=True, saturate_drive=0.06,
            use_comfort_eq=True, block_gain=0.66,
            underbed_vol=0.015,
            intro_fade_s=12.0, outro_fade_s=14.0,
            seed=206
        ),
    ]


# ══════════════════════════════════════════════════════════
#  CHAKRA ASCENT — ~35 min
#  Symbolic solfeggio ladder (Puleo/Horowitz tradition) + elevation rise.
#  Not physiology — intentional / harmonic layer like φ.
# ══════════════════════════════════════════════════════════

def _chakra_ascent():
    # (label, carrier, b0, b1, elev, vowel, morph, morph_s, breath)
    CH = [
        ('CHAKRA — ROOT',       396, 8.0, 6.0, -20, 'A', None, 0.0, 6.0),
        ('CHAKRA — SACRAL',     417, 6.0, 5.0, -12, 'A', None, 0.0, 5.5),
        ('CHAKRA — PLEXUS',     528, 5.0, 4.5,  -5, 'A', None, 0.0, 5.0),
        ('CHAKRA — HEART',      639, 4.5, 4.0,   0, 'E', None, 0.0, 4.5),
        ('CHAKRA — THROAT',     741, 4.0, 3.5,  10, 'A', None, 0.0, 4.5),
        ('CHAKRA — THIRD EYE',  852, 3.5, 2.0,  20, 'O', 'U', 25.0, 4.0),
        ('CHAKRA — CROWN',      963, 2.0, 0.5,  28, 'U', 'M', 30.0, 4.0),
    ]
    blocks = []
    for i, (label, c, b0, b1, el, vow, morph, ms, bpm) in enumerate(CH):
        high = c >= 700
        blocks.append(Block(
            label=label, dur_s=300,
            c0=c, c1=c, b0=b0, b1=b1,
            carrier_type='soft' if high else 'warm',
            carrier_jitter=0.5, beat_jitter=0.05,
            noise_pw=0.55 if not high else 0.25,
            noise_bw=0.45 if not high else 0.75,
            iso_layers=[] if high else (
                [(b0, min(c * 0.5, 220), 0.04, 14, 14)] if i < 3 else []
            ),
            use_hrtf=True, hrtf_elevation=el, hrtf_az_sweep=0.0,
            use_formant=True,
            formant_intensity=0.12 if not high else 0.07,
            formant_vowel=vow,
            formant_morph_vowel=morph,
            formant_morph_s=ms,
            use_phi=(i >= 5),
            use_drone=True, drone_vol=0.06 if not high else 0.04,
            use_wind=True, wind_vol=0.045,
            use_monaural=True, monaural_vol=0.03,
            use_respiratory=True, breath_bpm=bpm,
            breath_bpm_end=max(4.0, bpm - 0.5),
            breath_depth=0.11,
            infra_freq=0.06, infra_depth=0.09,
            use_saturate=True, saturate_drive=0.06,
            use_reverb=(i >= 3),
            reverb_rt60=700.0 + i * 60, reverb_wet=0.07,
            use_comfort_eq=True,
            block_gain=0.70 if not high else (0.58 if c < 900 else 0.48),
            silk_cutoff_hz=5000.0 if not high else (4000.0 if c < 900 else 3600.0),
            intro_fade_s=14.0, outro_fade_s=12.0,
            underbed_vol=0.014,
            quiet_before_s=20.0 if i == 5 else (25.0 if i == 6 else 0.0),
            seed=300 + i,
        ))
    return blocks


# ══════════════════════════════════════════════════════════
#  DEEP DIVE PRO NIGHT — ~121 min
#
#  Habituation-resistant descent past the GATEWAY_EDGE ladder:
#    PREP → BODY OFF → STABLE THETA → DEEP THETA → LIMINAL → AUTO/VOID
#
#  · Single fixed 200 Hz carrier for the WHOLE session — no carrier jump
#    anywhere, so every join is equal-power (renderer._carrier_jump never
#    fires) instead of fade-through-silence. That is the actual mechanism
#    behind "no sudden sounds," not a volume rule layered on top.
#  · Beat path is 100% beat_ctrl → adaptive_drift_envelope, never log_sweep:
#    long dwell plateaus connected by short (~1 min) glides, plus
#    independent multi-rate micro-wander. Never a metronomic ramp.
#  · organic_style='void': continuous river/ghost bed stays, bowl/bell
#    EVENTS are hard-zeroed (events-mix = 0.0 in _STYLE_MIX). A session
#    whose entire premise is "nothing happens" cannot also schedule
#    occasional bowl strikes — those are exactly the discrete, attention-
#    grabbing events Phase 4/5 of the design brief rules out.
#  · No iso layers, no formant/vowel, no schumann stack. use_focus_mix only
#    in BODY OFF (the one phase that is actually Monroe F10's body/cortex
#    duality) — structure is deliberately stripped phase by phase, mirroring
#    "не вести пользователя вообще" for LIMINAL/AUTO.
#  · skip_ambient_bridge=True on every block: this is one unbroken descent,
#    not GENESIS/EDGE-style movements separated by 20s ambient bridges.
#  · quiet_before_s placed before DEEP THETA / LIMINAL / AUTO — structured
#    near-silence before each further descent (same convention as
#    GATEWAY_EDGE's F15/INTERRUPT/F21, README's "quiet before void/OBE").
#  · AUTO/VOID's outro_fade_s=240 is a real 4-minute exit ramp to silence —
#    a night session should end IN sleep, not stop abruptly.
#
#  Honest framing (see README): this is NOT validated to reach any specific
#  numbered "Focus level," and going "past F21/27" is understood here as
#  engineering — longer uninterrupted time-on-target at a lower, steadier
#  beat frequency with zero external redirection — not a claim about
#  reaching a specific verified state of consciousness.
# ══════════════════════════════════════════════════════════

def _deep_dive_pro_night():
    return [
        # ── PREP — settle: alpha → alpha/theta border. Nothing structured
        #    yet; just less internal noise.
        Block(
            label='DEEP DIVE — PREP', dur_s=480,
            c0=200, c1=200, b0=11.2, b1=9.4,
            carrier_type='soft', carrier_jitter=0.8, beat_jitter=0.05,
            noise_pw=0.85, noise_bw=0.15,
            beat_ctrl=[(0.0, 11.2), (1.0, 9.4)],
            beat_micro_amp=0.05, beat_micro_rate=0.012,
            use_monaural=True, monaural_vol=0.030,
            use_respiratory=True, breath_bpm=6.0, breath_bpm_end=5.6,
            breath_depth=0.10,
            infra_freq=0.030, infra_depth=0.080,
            itd_period=100.0,
            use_carrier_drift=True, carrier_drift_hz=0.60,
            use_underbed=True, underbed_vol=0.014,
            use_organic=True, organic_style='void', organic_intensity=0.85,
            use_granular=True, granular_grain_ms=220.0, granular_density=3.0,
            granular_pitch_st=0.2, granular_scatter=0.6, granular_vol=0.035,
            use_saturate=True, saturate_drive=0.050,
            use_reverb=True, reverb_wet=0.050, reverb_rt60=700.0,
            use_comfort_eq=True, block_gain=0.58,
            intro_fade_s=20.0, outro_fade_s=30.0,
            skip_ambient_bridge=True,
            seed=501
        ),
        # ── BODY OFF — analog Focus 10: body/cortex duality, then let it go
        Block(
            label='DEEP DIVE — BODY OFF', dur_s=1080,
            c0=200, c1=200, b0=9.4, b1=6.4,
            carrier_type='soft', carrier_jitter=0.7, beat_jitter=0.06,
            noise_pw=0.75, noise_bw=0.25,
            beat_ctrl=[(0.0, 9.4), (1.0, 6.4)],
            beat_micro_amp=0.06, beat_micro_rate=0.011,
            use_focus_mix=True, focus_body_beat=2.2, focus_cortex_beat=8.5,
            focus_vol_body=0.07, focus_vol_cortex=0.05,
            use_monaural=True, monaural_vol=0.035,
            use_respiratory=True, breath_bpm=5.6, breath_bpm_end=5.0,
            breath_depth=0.11,
            infra_freq=0.035, infra_depth=0.090,
            itd_period=120.0,
            use_carrier_drift=True, carrier_drift_hz=0.55,
            use_underbed=True, underbed_vol=0.015,
            use_organic=True, organic_style='void', organic_intensity=0.70,
            use_granular=True, granular_grain_ms=200.0, granular_density=2.6,
            granular_pitch_st=0.2, granular_scatter=0.6, granular_vol=0.032,
            use_saturate=True, saturate_drive=0.055,
            use_reverb=True, reverb_wet=0.060, reverb_rt60=750.0,
            use_comfort_eq=True, block_gain=0.55,
            intro_fade_s=25.0, outro_fade_s=30.0,
            skip_ambient_bridge=True,
            seed=502
        ),
        # ── STABLE THETA — analog Focus 12: hold. No focus_mix, no motion
        #    beyond the drift floor — nothing to re-orient toward.
        Block(
            label='DEEP DIVE — STABLE THETA', dur_s=1500,
            c0=200, c1=200, b0=6.4, b1=6.0,
            carrier_type='soft', carrier_jitter=0.5, beat_jitter=0.04,
            noise_pw=0.65, noise_bw=0.35,
            beat_ctrl=[(0.0, 6.4), (1.0, 6.0)],
            beat_micro_amp=0.045, beat_micro_rate=0.010,
            use_monaural=True, monaural_vol=0.035,
            use_respiratory=True, breath_bpm=5.0, breath_bpm_end=4.6,
            breath_depth=0.12,
            infra_freq=0.040, infra_depth=0.095,
            itd_period=140.0,
            use_carrier_drift=True, carrier_drift_hz=0.50,
            use_underbed=True, underbed_vol=0.015,
            use_organic=True, organic_style='void', organic_intensity=0.55,
            use_granular=True, granular_grain_ms=180.0, granular_density=2.0,
            granular_pitch_st=0.15, granular_scatter=0.6, granular_vol=0.028,
            use_saturate=True, saturate_drive=0.050,
            use_reverb=True, reverb_wet=0.060, reverb_rt60=800.0,
            use_comfort_eq=True, block_gain=0.50,
            intro_fade_s=30.0, outro_fade_s=30.0,
            skip_ambient_bridge=True,
            seed=503
        ),
        # ── DEEP THETA — analog Focus 15: "living stillness" — ~7-8 min
        #    dwell plateaus connected by ~1 min glides. Never a metronome.
        Block(
            label='DEEP DIVE — DEEP THETA', dur_s=1800,
            c0=200, c1=200, b0=6.0, b1=4.5,
            carrier_type='soft', carrier_jitter=0.4, beat_jitter=0.04,
            noise_pw=0.55, noise_bw=0.45,
            beat_ctrl=[(0.0, 6.0), (0.24, 6.0), (0.27, 5.5), (0.51, 5.5),
                      (0.54, 5.0), (0.78, 5.0), (0.81, 4.5), (1.0, 4.5)],
            beat_micro_amp=0.07, beat_micro_rate=0.009,
            use_monaural=True, monaural_vol=0.035,
            use_respiratory=True, breath_bpm=4.6, breath_bpm_end=4.2,
            breath_depth=0.12,
            infra_freq=0.045, infra_depth=0.100,
            itd_period=160.0,
            use_carrier_drift=True, carrier_drift_hz=0.45,
            use_underbed=True, underbed_vol=0.016,
            use_organic=True, organic_style='void', organic_intensity=0.42,
            use_saturate=True, saturate_drive=0.045,
            use_reverb=True, reverb_wet=0.055, reverb_rt60=850.0,
            use_comfort_eq=True, block_gain=0.46,
            quiet_before_s=20.0,
            intro_fade_s=35.0, outro_fade_s=35.0,
            skip_ambient_bridge=True,
            seed=504
        ),
        # ── LIMINAL — past what Monroe-style ladders script: no voice, no
        #    focus_mix, no further guidance. One small step at the midpoint;
        #    otherwise hold. Largest micro-wander of the session on purpose —
        #    it is the only thing still "alive" here.
        Block(
            label='DEEP DIVE — LIMINAL', dur_s=1500,
            c0=200, c1=200, b0=4.5, b1=4.1,
            carrier_type='soft', carrier_jitter=0.35, beat_jitter=0.03,
            noise_pw=0.50, noise_bw=0.50,
            beat_ctrl=[(0.0, 4.5), (0.46, 4.5), (0.50, 4.1), (1.0, 4.1)],
            beat_micro_amp=0.10, beat_micro_rate=0.008,
            use_monaural=True, monaural_vol=0.030,
            use_respiratory=True, breath_bpm=4.2, breath_bpm_end=4.0,
            breath_depth=0.11,
            infra_freq=0.050, infra_depth=0.090,
            itd_period=180.0,
            use_carrier_drift=True, carrier_drift_hz=0.40,
            use_underbed=True, underbed_vol=0.015,
            use_organic=True, organic_style='void', organic_intensity=0.30,
            use_saturate=True, saturate_drive=0.040,
            use_reverb=True, reverb_wet=0.050, reverb_rt60=900.0,
            use_comfort_eq=True, block_gain=0.42,
            quiet_before_s=40.0,
            intro_fade_s=40.0, outro_fade_s=35.0,
            skip_ambient_bridge=True,
            seed=505
        ),
        # ── AUTO / VOID — flat floor, then a genuine taper into silence.
        #    outro_fade_s=240 (4 min, clamped to n//3=280s) is the real exit
        #    ramp — a night session should end IN sleep, not stop abruptly.
        Block(
            label='DEEP DIVE — AUTO / VOID', dur_s=840,
            c0=200, c1=200, b0=3.8, b1=3.8,
            carrier_type='soft', carrier_jitter=0.3, beat_jitter=0.03,
            noise_pw=0.50, noise_bw=0.50,
            beat_ctrl=[(0.0, 3.8), (1.0, 3.8)],
            beat_micro_amp=0.06, beat_micro_rate=0.007,
            use_monaural=True, monaural_vol=0.025,
            use_respiratory=True, breath_bpm=4.0, breath_depth=0.10,
            infra_freq=0.050, infra_depth=0.080,
            itd_period=200.0,
            use_carrier_drift=True, carrier_drift_hz=0.35,
            use_underbed=True, underbed_vol=0.013,
            use_organic=True, organic_style='void', organic_intensity=0.18,
            use_saturate=True, saturate_drive=0.035,
            use_reverb=True, reverb_wet=0.045, reverb_rt60=950.0,
            use_comfort_eq=True, block_gain=0.38,
            quiet_before_s=35.0,
            intro_fade_s=40.0, outro_fade_s=240.0,
            skip_ambient_bridge=True,
            seed=506
        ),
    ]
