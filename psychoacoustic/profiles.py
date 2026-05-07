"""
Профили сессий.
Каждый профиль — список Block объектов.
carrier_type, use_drone, use_wind, use_lfo_filter задают тембральный характер.
"""

from .block import Block


def build_profile(name: str):
    n = name.upper()
    if   n == 'GENESIS':  return _genesis()
    elif n == 'WALK':     return _walk()
    elif n == 'SLEEP':    return _sleep()
    elif n == 'HEALER':   return _healer()
    elif n == 'ORACLE':   return _oracle()
    elif n == 'WARRIOR':  return _warrior()
    else:
        raise ValueError(
            f"Unknown profile '{name}'. "
            f"Use: GENESIS WALK SLEEP HEALER ORACLE WARRIOR")


# ══════════════════════════════════════════════════════════
#  GENESIS — 63 min
#  Тембр: warm (FM) → soft в void. Drone + wind в ключевых блоках.
# ══════════════════════════════════════════════════════════

def _genesis():
    return [
        Block(
            label='IGNITION', dur_s=300,
            c0=200, c1=432, b0=36.0, b1=40.0,
            carrier_type='warm',
            carrier_jitter=0.8, beat_jitter=0.08,
            noise_pw=1.0, noise_bw=0.0,
            iso_layers=[(40.0, 200, 0.11, 5, 6)],
            assr_80hz_vol=0.05,
            itd_period=12.0, use_hrtf=True, hrtf_az_sweep=0,
            use_drone=True, drone_vol=0.08,
            seed=1
        ),
        Block(
            label='EARTH SYNC', dur_s=480,
            c0=432, c1=432, b0=7.83, b1=7.83,
            carrier_type='warm',
            carrier_jitter=0.3, beat_jitter=0.06,
            noise_pw=0.8, noise_bw=0.2,
            iso_layers=[(14.3, 216, 0.07, 10, 10),
                        (40.0, 200, 0.06, 12,  8)],
            cfc_theta=7.83, cfc_strength=0.30,
            assr_80hz_vol=0.04,
            infra_freq=0.10, infra_depth=0.12,
            schumann_mode=True,
            use_hrtf=True, hrtf_az_sweep=16.0,
            use_wind=True, wind_vol=0.06, wind_bw=14.0,
            use_lfo_filter=True, lfo_fc=800.0, lfo_depth=350.0, lfo_rate=0.04,
            seed=2
        ),
        Block(
            label='THETA GATEWAY', dur_s=540,
            c0=432, c1=528, b0=7.83, b1=4.5,
            carrier_type='warm',
            carrier_jitter=1.8, beat_jitter=0.20,
            noise_pw=0.6, noise_bw=0.4,
            iso_layers=[(6.0,  264, 0.12, 12, 10),
                        (40.0, 200, 0.07, 15,  5)],
            cfc_theta=6.0, cfc_strength=0.45,
            assr_80hz_vol=0.04,
            itd_period=15.0, use_hrtf=True, hrtf_az_sweep=0,
            infra_freq=0.08, infra_depth=0.13,
            use_chaos=True, chaos_depth=0.18,
            use_drone=True, drone_vol=0.09, drone_detune=0.12,
            use_lfo_filter=True, lfo_fc=700.0, lfo_depth=300.0, lfo_rate=0.05,
            seed=3
        ),
        Block(
            label='DELTA APPROACH', dur_s=540,
            c0=528, c1=528, b0=4.5, b1=2.0,
            carrier_type='soft',
            carrier_jitter=2.5, beat_jitter=0.22,
            noise_pw=0.2, noise_bw=0.8,
            iso_layers=[(4.5,  264, 0.10,  5, 25),
                        (40.0, 200, 0.07,  5,  8)],
            cfc_theta=5.5, cfc_strength=0.50,
            assr_80hz_vol=0.05,
            infra_freq=0.067, infra_depth=0.14,
            phase_lock=True, phase_lock_depth=0.18,
            use_wind=True, wind_vol=0.07, wind_bw=12.0,
            seed=4
        ),
        Block(
            label='VOID CORE', dur_s=720,
            c0=528, c1=528, b0=1.5, b1=1.5,
            carrier_type='soft',
            carrier_jitter=3.0, beat_jitter=0.10,
            noise_pw=0.0, noise_bw=1.0,
            iso_layers=[(33.0, 180, 0.06, 20, 20),
                        (40.0, 200, 0.08, 20, 20)],
            cfc_theta=5.0, cfc_strength=0.55,
            assr_80hz_vol=0.05,
            spatial_3d=True, itd_period=18.0, el_period=29.0,
            infra_freq=0.033, infra_depth=0.15,
            use_chaos=True, chaos_depth=0.22,
            use_wind=True, wind_vol=0.06, wind_bw=10.0,
            seed=5
        ),
        Block(
            label='ASCENT SURGE', dur_s=360,
            c0=528, c1=639, b0=1.5, b1=12.0,
            carrier_type='warm',
            carrier_jitter=1.5, beat_jitter=0.18,
            noise_pw=0.9, noise_bw=0.1,
            iso_layers=[(40.0, 200, 0.13, 3, 5),
                        (33.0, 216, 0.08, 3, 5)],
            cfc_theta=6.0, cfc_strength=0.35,
            assr_80hz_vol=0.06,
            spatial_3d=True, itd_period=6.0, el_period=11.0,
            infra_freq=0.10, infra_depth=0.10,
            use_hrtf=True, hrtf_az_sweep=6.0, hrtf_elevation=15.0,
            use_drone=True, drone_vol=0.09,
            seed=6
        ),
        Block(
            label='SCHUMANN INTEGRATION', dur_s=480,
            c0=639, c1=432, b0=12.0, b1=7.83,
            carrier_type='warm',
            carrier_jitter=1.2, beat_jitter=0.12,
            noise_pw=0.85, noise_bw=0.15,
            iso_layers=[(7.83, 432, 0.09,  6,  6),
                        (40.0, 200, 0.09,  6, 10)],
            cfc_theta=7.83, cfc_strength=0.40,
            assr_80hz_vol=0.05,
            itd_period=12.0, use_hrtf=True, hrtf_az_sweep=12.0,
            infra_freq=0.083, infra_depth=0.11,
            schumann_mode=True,
            use_wind=True, wind_vol=0.06,
            use_lfo_filter=True, lfo_fc=850.0, lfo_depth=380.0, lfo_rate=0.04,
            seed=7
        ),
        Block(
            label='ACTIVATION LOCK', dur_s=360,
            c0=432, c1=200, b0=7.83, b1=30.0,
            carrier_type='warm',
            carrier_jitter=0.8, beat_jitter=0.10,
            noise_pw=1.0, noise_bw=0.0,
            iso_layers=[(40.0, 200, 0.13, 5, 3),
                        (30.0, 216, 0.09, 8, 3)],
            assr_80hz_vol=0.07,
            itd_period=9.0, use_hrtf=True, hrtf_az_sweep=0,
            use_drone=True, drone_vol=0.08,
            seed=8
        ),
    ]


# ══════════════════════════════════════════════════════════
#  WALK — 30 min
#  Тембр: warm. Drone + HRTF для пространственного расширения.
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
            seed=41
        ),
        Block(
            label='WALK — EXPAND', dur_s=600,
            c0=200, c1=204, b0=10.0, b1=8.0,
            carrier_type='warm',
            carrier_jitter=1.2, beat_jitter=0.10,
            noise_pw=1.0, noise_bw=0.0,
            iso_layers=[(40.0, 200, 0.06, 10, 8)],
            cfc_theta=8.0, cfc_strength=0.25,
            itd_period=12.0, use_hrtf=True,
            infra_freq=0.10, infra_depth=0.10,
            use_drone=True, drone_vol=0.09, drone_detune=0.12,
            use_wind=True,  wind_vol=0.05,
            seed=42
        ),
        Block(
            label='WALK — OPERATOR', dur_s=600,
            c0=204, c1=206, b0=8.0, b1=7.5,
            carrier_type='warm',
            carrier_jitter=1.8, beat_jitter=0.14,
            noise_pw=0.9, noise_bw=0.1,
            iso_layers=[(40.0, 200, 0.07, 8, 6)],
            cfc_theta=7.5, cfc_strength=0.30,
            assr_80hz_vol=0.04,
            itd_period=14.0, use_hrtf=True,
            infra_freq=0.083, infra_depth=0.10,
            use_drone=True, drone_vol=0.10, drone_detune=0.14,
            use_phi=True,
            use_lfo_filter=True, lfo_fc=750.0, lfo_depth=300.0, lfo_rate=0.04,
            seed=43
        ),
        Block(
            label='WALK — RETURN', dur_s=300,
            c0=206, c1=200, b0=7.5, b1=10.0,
            carrier_type='warm',
            carrier_jitter=0.8, beat_jitter=0.08,
            noise_pw=1.0, noise_bw=0.0,
            iso_layers=[(40.0, 200, 0.06, 5, 5)],
            itd_period=10.0, use_hrtf=True,
            use_drone=True, drone_vol=0.07,
            seed=44
        ),
    ]


# ══════════════════════════════════════════════════════════
#  SLEEP — 90 min  (3x OBE windows)
#  Тембр: soft для сна. 3D-orbit в OBE-триггерах.
# ══════════════════════════════════════════════════════════

def _sleep():
    return [
        Block(label='SLEEP — SETTLE', dur_s=600,
              c0=200, c1=200, b0=10.0, b1=5.5,
              carrier_type='soft', noise_pw=1.0, noise_bw=0.0,
              infra_freq=0.10, infra_depth=0.10,
              use_wind=True, wind_vol=0.05,
              seed=51),
        Block(label='SLEEP — DRIFT', dur_s=600,
              c0=200, c1=200, b0=5.5, b1=3.0,
              carrier_type='soft', noise_pw=0.4, noise_bw=0.6,
              infra_freq=0.067, infra_depth=0.12,
              use_wind=True, wind_vol=0.05,
              seed=52),
        Block(label='SLEEP — DEEP 1', dur_s=900,
              c0=200, c1=200, b0=3.0, b1=2.0,
              carrier_type='soft', noise_pw=0.0, noise_bw=1.0,
              infra_freq=0.033, infra_depth=0.14, seed=53),
        # OBE window 1
        Block(label='SLEEP — WINDOW 1', dur_s=300,
              c0=200, c1=201, b0=2.0, b1=6.0,
              carrier_type='warm', noise_pw=0.2, noise_bw=0.8,
              iso_layers=[(40.0, 200, 0.09, 3, 5)],
              cfc_theta=6.0, cfc_strength=0.40, assr_80hz_vol=0.05,
              spatial_3d=True, itd_period=8.0, el_period=13.0, el_depth=0.40,
              use_hrtf=True, hrtf_az_sweep=8.0, hrtf_elevation=10.0,
              use_chaos=True, chaos_depth=0.20,
              use_drone=True, drone_vol=0.07,
              seed=54),
        Block(label='SLEEP — HOLD 1', dur_s=120,
              c0=201, c1=201, b0=6.0, b1=6.0,
              carrier_type='warm', noise_pw=0.3, noise_bw=0.7,
              iso_layers=[(40.0, 200, 0.09, 5, 5)],
              cfc_theta=6.0, cfc_strength=0.45,
              use_hrtf=True, hrtf_az_sweep=8.0, seed=55),
        Block(label='SLEEP — DESCENT 1', dur_s=300,
              c0=201, c1=200, b0=6.0, b1=2.0,
              carrier_type='soft', noise_pw=0.1, noise_bw=0.9,
              iso_layers=[(40.0, 200, 0.07, 5, 15)],
              infra_freq=0.033, infra_depth=0.14, seed=56),
        Block(label='SLEEP — DEEP 2', dur_s=900,
              c0=200, c1=202, b0=2.0, b1=2.0,
              carrier_type='soft', noise_pw=0.0, noise_bw=1.0,
              iso_layers=[(40.0, 200, 0.07, 20, 20)],
              cfc_theta=5.0, cfc_strength=0.45,
              infra_freq=0.025, infra_depth=0.15, seed=57),
        # OBE window 2
        Block(label='SLEEP — WINDOW 2', dur_s=300,
              c0=202, c1=203, b0=2.0, b1=6.0,
              carrier_type='warm', noise_pw=0.2, noise_bw=0.8,
              iso_layers=[(40.0, 200, 0.10, 3, 5),
                          (33.0, 180, 0.06, 5, 5)],
              cfc_theta=6.0, cfc_strength=0.45, assr_80hz_vol=0.05,
              spatial_3d=True, itd_period=7.0, el_period=11.0, el_depth=0.45,
              use_hrtf=True, hrtf_az_sweep=7.0, hrtf_elevation=15.0,
              use_chaos=True, chaos_depth=0.22,
              use_drone=True, drone_vol=0.07,
              seed=58),
        Block(label='SLEEP — HOLD 2', dur_s=120,
              c0=203, c1=203, b0=6.0, b1=6.0,
              carrier_type='warm',
              iso_layers=[(40.0, 200, 0.09, 5, 5)],
              cfc_theta=6.0, cfc_strength=0.50,
              use_hrtf=True, seed=59),
        Block(label='SLEEP — DESCENT 2', dur_s=300,
              c0=203, c1=200, b0=6.0, b1=2.0,
              carrier_type='soft', noise_pw=0.1, noise_bw=0.9,
              infra_freq=0.033, infra_depth=0.14, seed=60),
        # OBE window 3 — самое глубокое
        Block(label='SLEEP — WINDOW 3', dur_s=300,
              c0=200, c1=204, b0=2.0, b1=7.83,
              carrier_type='warm', noise_pw=0.3, noise_bw=0.7,
              iso_layers=[(40.0, 200, 0.11, 3, 4),
                          (33.0, 180, 0.07, 3, 4)],
              cfc_theta=6.5, cfc_strength=0.50, assr_80hz_vol=0.06,
              spatial_3d=True, itd_period=6.0, el_period=11.0, el_depth=0.50,
              use_hrtf=True, hrtf_az_sweep=6.0, hrtf_elevation=20.0,
              use_chaos=True, chaos_depth=0.25,
              phase_lock=True, phase_lock_depth=0.22,
              use_drone=True, drone_vol=0.08,
              seed=61),
        Block(label='SLEEP — HOLD 3', dur_s=180,
              c0=204, c1=204, b0=7.83, b1=7.83,
              carrier_type='warm',
              iso_layers=[(40.0, 200, 0.09, 5, 8),
                          (33.0, 180, 0.06, 5, 8)],
              cfc_theta=7.83, cfc_strength=0.40,
              use_hrtf=True, hrtf_az_sweep=8.0, seed=62),
        Block(label='SLEEP — CLOSE', dur_s=300,
              c0=204, c1=200, b0=7.83, b1=2.5,
              carrier_type='soft', noise_pw=0.1, noise_bw=0.9,
              use_wind=True, wind_vol=0.04,
              infra_freq=0.025, infra_depth=0.15, seed=63),
    ]


# ══════════════════════════════════════════════════════════
#  HEALER — 75 min
#  Тембр: rich (аддитивный, 5 гармоник). Phi-layers. 528 Hz.
# ══════════════════════════════════════════════════════════

def _healer():
    return [
        Block(label='HEALER — OPEN', dur_s=480,
              c0=528, c1=528, b0=10.0, b1=6.0,
              carrier_type='rich', noise_pw=0.9, noise_bw=0.1,
              iso_layers=[(6.0, 264, 0.10, 8, 8)],
              cfc_theta=6.0, cfc_strength=0.30,
              infra_freq=0.10, infra_depth=0.12,
              use_phi=True, use_drone=True, drone_vol=0.09,
              use_wind=True, wind_vol=0.06,
              seed=71),
        Block(label='HEALER — DESCENT', dur_s=720,
              c0=528, c1=528, b0=6.0, b1=2.0,
              carrier_type='rich', noise_pw=0.4, noise_bw=0.6,
              iso_layers=[(5.0, 264, 0.09, 10, 15),
                          (40.0, 200, 0.06, 12,  8)],
              cfc_theta=5.0, cfc_strength=0.50,
              infra_freq=0.067, infra_depth=0.14,
              use_phi=True, use_drone=True, drone_vol=0.09,
              use_wind=True, wind_vol=0.06,
              use_lfo_filter=True, lfo_fc=650.0, lfo_depth=280.0, lfo_rate=0.04,
              seed=72),
        Block(label='HEALER — VOID 1', dur_s=900,
              c0=528, c1=528, b0=1.5, b1=1.5,
              carrier_type='soft', noise_pw=0.0, noise_bw=1.0,
              iso_layers=[(40.0, 200, 0.07, 20, 20),
                          (33.0, 180, 0.05, 25, 25)],
              cfc_theta=5.0, cfc_strength=0.60, assr_80hz_vol=0.04,
              infra_freq=0.033, infra_depth=0.16,
              use_phi=True, use_wind=True, wind_vol=0.05,
              seed=73),
        Block(label='HEALER — VOID 2', dur_s=900,
              c0=528, c1=528, b0=1.5, b1=1.5,
              carrier_type='soft', noise_pw=0.0, noise_bw=1.0,
              iso_layers=[(40.0, 200, 0.07, 20, 20)],
              cfc_theta=4.5, cfc_strength=0.65, assr_80hz_vol=0.04,
              infra_freq=0.025, infra_depth=0.16,
              use_phi=True, seed=74),
        Block(label='HEALER — RETURN', dur_s=480,
              c0=528, c1=432, b0=1.5, b1=8.0,
              carrier_type='rich', noise_pw=0.8, noise_bw=0.2,
              iso_layers=[(40.0, 200, 0.10, 5, 5)],
              cfc_theta=6.0, cfc_strength=0.30,
              infra_freq=0.083, infra_depth=0.11,
              use_drone=True, drone_vol=0.08, seed=75),
        Block(label='HEALER — INTEGRATE', dur_s=270,
              c0=432, c1=432, b0=8.0, b1=12.0,
              carrier_type='rich', noise_pw=1.0, noise_bw=0.0,
              iso_layers=[(40.0, 200, 0.11, 5, 3)],
              assr_80hz_vol=0.05, seed=76),
    ]


# ══════════════════════════════════════════════════════════
#  ORACLE — 60 min
#  Тембр: warm/organ. Chaos в theta-2. 3D в vision-hold.
# ══════════════════════════════════════════════════════════

def _oracle():
    return [
        Block(label='ORACLE — EARTH OPEN', dur_s=600,
              c0=432, c1=432, b0=10.0, b1=7.83,
              carrier_type='organ', schumann_mode=True,
              iso_layers=[(7.83, 432, 0.08, 10, 10)],
              cfc_theta=7.83, cfc_strength=0.30,
              infra_freq=0.083, infra_depth=0.11,
              use_hrtf=True, itd_period=14.0,
              use_wind=True, wind_vol=0.06,
              seed=81),
        Block(label='ORACLE — THETA 1', dur_s=720,
              c0=432, c1=432, b0=7.83, b1=5.5,
              carrier_type='warm', noise_pw=0.7, noise_bw=0.3,
              iso_layers=[(6.0,  216, 0.11, 12, 10),
                          (40.0, 200, 0.06, 15,  8)],
              cfc_theta=6.5, cfc_strength=0.48,
              itd_period=16.0, use_hrtf=True,
              infra_freq=0.067, infra_depth=0.12,
              use_drone=True, drone_vol=0.08,
              use_lfo_filter=True, lfo_fc=700.0, lfo_depth=320.0, lfo_rate=0.05,
              seed=82),
        Block(label='ORACLE — THETA 2 CHAOS', dur_s=720,
              c0=432, c1=432, b0=5.5, b1=4.5,
              carrier_type='warm', noise_pw=0.5, noise_bw=0.5,
              iso_layers=[(5.5,  216, 0.10, 10, 10),
                          (40.0, 200, 0.07, 12,  8)],
              cfc_theta=5.5, cfc_strength=0.55, assr_80hz_vol=0.04,
              itd_period=18.0, use_hrtf=True,
              infra_freq=0.05, infra_depth=0.13,
              use_chaos=True, chaos_depth=0.25,
              phase_lock=True, phase_lock_depth=0.18,
              use_drone=True, drone_vol=0.08,
              seed=83),
        Block(label='ORACLE — VISION HOLD', dur_s=480,
              c0=432, c1=432, b0=4.5, b1=4.5,
              carrier_type='organ', noise_pw=0.4, noise_bw=0.6,
              iso_layers=[(40.0, 200, 0.08, 10, 10),
                          (33.0, 180, 0.05, 12, 12)],
              cfc_theta=4.5, cfc_strength=0.60, assr_80hz_vol=0.05,
              spatial_3d=True, itd_period=14.0, el_period=23.0, el_depth=0.40,
              infra_freq=0.05, infra_depth=0.14,
              use_phi=True, use_hrtf=True, hrtf_az_sweep=14.0,
              use_wind=True, wind_vol=0.06,
              seed=84),
        Block(label='ORACLE — SCHUMANN RETURN', dur_s=480,
              c0=432, c1=432, b0=4.5, b1=7.83,
              carrier_type='organ', schumann_mode=True,
              iso_layers=[(7.83, 432, 0.09, 8, 8),
                          (40.0, 200, 0.08, 8, 6)],
              cfc_theta=7.83, cfc_strength=0.35,
              itd_period=12.0, use_hrtf=True, hrtf_az_sweep=12.0,
              infra_freq=0.083,
              use_wind=True, wind_vol=0.05,
              seed=85),
        Block(label='ORACLE — SEAL', dur_s=360,
              c0=432, c1=432, b0=7.83, b1=14.0,
              carrier_type='warm', noise_pw=1.0, noise_bw=0.0,
              iso_layers=[(40.0, 200, 0.12, 5, 3),
                          (14.0, 216, 0.08, 8, 3)],
              assr_80hz_vol=0.05,
              use_drone=True, drone_vol=0.08, seed=86),
    ]


# ══════════════════════════════════════════════════════════
#  WARRIOR — 50 min
#  Тембр: sine (чистый, острый). Максимальный ASSR-80.
# ══════════════════════════════════════════════════════════

def _warrior():
    return [
        Block(label='WARRIOR — CHARGE', dur_s=300,
              c0=200, c1=200, b0=30.0, b1=40.0,
              carrier_type='sine', noise_pw=1.0, noise_bw=0.0,
              iso_layers=[(40.0, 200, 0.13, 4, 5)],
              assr_80hz_vol=0.07, itd_period=8.0,
              use_hrtf=True, seed=91),
        Block(label='WARRIOR — PEAK', dur_s=600,
              c0=200, c1=432, b0=40.0, b1=40.0,
              carrier_type='sine', noise_pw=1.0, noise_bw=0.0,
              iso_layers=[(40.0, 200, 0.13, 5, 5)],
              assr_80hz_vol=0.08, itd_period=6.0,
              use_hrtf=True, use_chaos=True, chaos_depth=0.15, seed=92),
        Block(label='WARRIOR — DESCENT', dur_s=480,
              c0=432, c1=432, b0=40.0, b1=12.0,
              carrier_type='warm', noise_pw=0.8, noise_bw=0.2,
              iso_layers=[(40.0, 200, 0.12, 5, 8),
                          (33.0, 216, 0.07, 5, 8)],
              cfc_theta=8.0, cfc_strength=0.28,
              assr_80hz_vol=0.06, itd_period=8.0,
              use_hrtf=True, seed=93),
        Block(label='WARRIOR — THETA TOUCH', dur_s=480,
              c0=432, c1=432, b0=12.0, b1=7.83,
              carrier_type='warm', noise_pw=0.7, noise_bw=0.3,
              iso_layers=[(40.0, 200, 0.10, 8, 8)],
              cfc_theta=7.83, cfc_strength=0.38, assr_80hz_vol=0.05,
              infra_freq=0.083, infra_depth=0.10, seed=94),
        Block(label='WARRIOR — RELOAD', dur_s=600,
              c0=432, c1=200, b0=7.83, b1=35.0,
              carrier_type='sine', noise_pw=1.0, noise_bw=0.0,
              iso_layers=[(40.0, 200, 0.13, 5, 3),
                          (35.0, 216, 0.09, 5, 3)],
              assr_80hz_vol=0.07, itd_period=6.0,
              use_hrtf=True, use_chaos=True, chaos_depth=0.12, seed=95),
        Block(label='WARRIOR — LOCK', dur_s=540,
              c0=200, c1=200, b0=35.0, b1=40.0,
              carrier_type='sine', noise_pw=1.0, noise_bw=0.0,
              iso_layers=[(40.0, 200, 0.14, 3, 2)],
              assr_80hz_vol=0.08, itd_period=5.0,
              use_hrtf=True, seed=96),
    ]
