import numpy as np
import soundfile as sf
import os, sys, time
from typing import List, Callable, Optional
from .block import Block
from .core  import SR, crossfade_write
from .dsp   import pattern_break, ffr_prime_burst


# ══════════════════════════════════════════════════════════
#  CUE SHEET EXPORT
# ══════════════════════════════════════════════════════════

def _sec_to_cue(seconds: float) -> str:
    """Конвертирует секунды в формат CUE MM:SS:FF (75 frames/sec)."""
    total_frames = int(round(seconds * 75))
    ff  = total_frames % 75
    ss  = (total_frames // 75) % 60
    mm  = total_frames // 75 // 60
    return f"{mm:02d}:{ss:02d}:{ff:02d}"


def export_cue(blocks: List[Block], out_path: str, flac_filename: str,
               artist: str = 'franklin-sys',
               break_min_dur: float = 600.0):
    """
    Генерирует .cue файл с треком для каждого блока.
    Плееры (foobar2000, VLC, mpv) показывают название текущей фазы.
    """
    BREAK_AFTER = {i for i, b in enumerate(blocks) if b.dur_s >= break_min_dur}
    BREAK_AFTER.add(0)

    lines = [
        f'PERFORMER "{artist}"',
        f'FILE "{flac_filename}" FLAC',
    ]

    t     = 0.0
    track = 1
    for i, b in enumerate(blocks):
        lines.append(f'  TRACK {track:02d} AUDIO')
        lines.append(f'    TITLE "{b.label}"')
        lines.append(f'    PERFORMER "{artist}"')
        lines.append(f'    INDEX 01 {_sec_to_cue(t)}')
        track += 1
        t += b.dur_s
        if i in BREAK_AFTER:
            t += 20.0   # pattern break

    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print(f"  Cue  → {out_path}")


# ══════════════════════════════════════════════════════════
#  SESSION MAP (text)
# ══════════════════════════════════════════════════════════

def export_map(blocks: List[Block], profile: str, out_path: str,
               break_min_dur: float = 600.0):
    BREAK_AFTER = {i for i, b in enumerate(blocks) if b.dur_s >= break_min_dur}
    BREAK_AFTER.add(0)

    lines = ["═" * 72,
             f"  GENESIS — SESSION MAP  |  Profile: {profile}", "═" * 72, ""]
    t = 0.0
    for i, b in enumerate(blocks):
        end = t + b.dur_s
        lines.append(f"  [{i+1:02d}]  {b.label}")
        lines.append(f"        {t/60:.2f} → {end/60:.2f} min")
        lines.append(f"        Carrier {b.c0}→{b.c1} Hz   Beat {b.b0}→{b.b1} Hz")
        lines.append(f"        Timbre: {b.carrier_type}   "
                     f"Noise pink={b.noise_pw:.1f} brown={b.noise_bw:.1f}")
        for (fv, cv, vv, atk, dec) in b.iso_layers:
            lines.append(f"        ISO {fv} Hz  carr={cv}  vol={vv}")
        flags = []
        if b.cfc_theta:       flags.append(f"CFC θ={b.cfc_theta}Hz str={b.cfc_strength}")
        if b.assr_80hz_vol:   flags.append(f"ASSR-80 vol={b.assr_80hz_vol}")
        if b.use_chaos:       flags.append(f"Lorenz depth={b.chaos_depth}")
        if b.use_hrtf:        flags.append(f"HRTF az={b.hrtf_az_sweep}s el={b.hrtf_elevation}°")
        if b.spatial_3d:      flags.append(f"3D-orbit az={b.itd_period}s el={b.el_period}s")
        elif b.itd_period:    flags.append(f"ITD-2D period={b.itd_period}s")
        if b.infra_freq:      flags.append(f"Infra {b.infra_freq}Hz d={b.infra_depth}")
        if b.use_drone:       flags.append(f"Drone vol={b.drone_vol} det={b.drone_detune}Hz")
        if b.use_granular:    flags.append(f"Granular dens={b.granular_density} size={b.granular_grain_ms}ms")
        if b.use_wind:        flags.append(f"Wind vol={b.wind_vol} bw={b.wind_bw}Hz")
        if b.use_lfo_filter:  flags.append(f"LFO-filt fc={b.lfo_fc}Hz")
        if b.schumann_mode:   flags.append("Schumann-stack")
        if b.use_phi:         flags.append("φ-layer")
        if b.phase_lock:      flags.append(f"PhLock d={b.phase_lock_depth}")
        if b.use_monaural:    flags.append(f"MonoBeat vol={b.monaural_vol}")
        if b.use_formant:     flags.append(f"Formant intensity={b.formant_intensity}")
        if b.use_saturate:    flags.append(f"Saturate drive={b.saturate_drive}")
        if b.use_reverb:      flags.append(f"Reverb wet={b.reverb_wet} rt60={b.reverb_rt60}")
        if b.use_respiratory: flags.append(f"Resp bpm={b.breath_bpm} d={b.breath_depth}")
        if flags:
            lines.append("        " + "  ·  ".join(flags))
        lines.append("")
        t = end
        if i in BREAK_AFTER:
            t += 20.0

    lines += ["═" * 72,
              "  LAYER LEGEND",
              "  carrier:  sine|warm(FM β=0.28)|rich(5harm)|soft|organ",
              "  drone:    detuned 3-voice pad с micro-LFO детюнингом",
              "  wind:     розовый шум → узкополосный BP @ carrier freq",
              "  lfo-filt: медленный LP-sweep → живое дыхание сигнала",
              "  CFC:      theta→gamma PAC (hippocampal coupling)",
              "  ASSR-80:  brainstem 80Hz pathway",
              "  Lorenz:   детерминированный хаос (solve_ivp RK45), t-scale фиксирован",
              "  HRTF:     Brown-Duda spherical head (Woodworth ITD + IIR ILD)",
              "  3D-orbit: azimuth circle + elevation Lissajous",
              "  Infra:    ultra-slow AM → ANS sync",
              "  MonoBeat: monaural AM pathway (brainstem)",
              "  Formant:  F1/F2/F3 vocal resonator",
              "  Saturate: arctan tube-warmth (soft-clip)",
              "  Reverb:   synthetic IR room reverb",
              "  Resp:     respiratory-sync AM (HRV coherence)",
              "  SR noise: stochastic-resonance optimal (15% signal RMS)",
              "  order:    spatial→infra→Resp→HRTF→Reverb→normalize",
              "═" * 72]

    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f"  Map  → {out_path}")


# ══════════════════════════════════════════════════════════
#  RENDER ENGINE
#
#  progress_cb: Optional callback для UI-отображения прогресса.
#  Сигнатура: progress_cb(block_idx: int, label: str,
#                         pct: float, elapsed_s: float) -> None
#  Если None — встроенный ASCII-бар.
# ══════════════════════════════════════════════════════════

def render_session(blocks: List[Block],
                   out_flac: str,
                   author:        str   = 'franklin-sys',
                   url:           str   = 'https://franklin-sys.vercel.app/',
                   fade_s:        float = 8.0,
                   break_min_dur: float = 600.0,
                   progress_cb:   Optional[Callable] = None):
    """
    Рендерит блоки в FLAC PCM-24 с равномощными кросс-фейдами.
    Автоматически генерирует .cue и _MAP.txt рядом с FLAC.

    progress_cb(idx, label, pct, elapsed_s) вызывается перед каждым блоком.
    Если не задан — выводит встроенный ASCII progress bar.
    """
    BREAK_AFTER = {i for i, b in enumerate(blocks) if b.dur_s >= break_min_dur}
    BREAK_AFTER.add(0)

    total_core   = sum(b.dur_s for b in blocks)
    total_breaks = len(BREAK_AFTER) * 20
    total_s      = total_core + total_breaks

    # CUE sheet рядом с FLAC
    cue_path = out_flac.replace('.flac', '.cue')
    export_cue(blocks, cue_path,
               flac_filename=os.path.basename(out_flac),
               artist=author,
               break_min_dur=break_min_dur)

    print(f"  {len(blocks)} blocks | {len(BREAK_AFTER)} breaks "
          f"| {total_s/60:.1f} min total")
    print(f"  → {out_flac}")

    t_start = time.time()

    with sf.SoundFile(out_flac, 'w', samplerate=SR,
                      channels=2, format='FLAC', subtype='PCM_24') as fh:
        try:
            fh.artist    = author
            fh.date      = '2026'
            fh.copyright = f'{author} (2026) | {url}'
            fh.license   = url
        except Exception:
            pass

        prev_tail = None

        for i, block in enumerate(blocks):
            done    = sum(b.dur_s for b in blocks[:i])
            pct     = done / total_core * 100
            elapsed = time.time() - t_start

            if progress_cb is not None:
                # UI-режим: внешний callback рисует прогресс
                progress_cb(i, block.label, pct, elapsed)
            else:
                # Fallback: встроенный ASCII bar
                bar = '█' * int(pct / 5) + '░' * (20 - int(pct / 5))
                sys.stdout.write(
                    f"\r  [{bar}] {pct:4.0f}%  {block.label[:36]:<36s}")
                sys.stdout.flush()

            # ── FFR Prime Burst (только перед первым блоком)
            if i == 0:
                pL, pR = ffr_prime_burst(carrier=block.c0,
                                         carrier_type=block.carrier_type)
                prev_tail = crossfade_write(fh, None, pL, pR,
                                            fade_s=4.0, silence_s=0.2)
                del pL, pR

            L, R = block.render()

            prev_tail = crossfade_write(fh, prev_tail, L, R,
                                        fade_s=fade_s, silence_s=0.5)
            del L, R

            if i in BREAK_AFTER:
                bL, bR = pattern_break(carrier=float(block.c1),
                                       carrier_type=block.carrier_type)
                prev_tail = crossfade_write(fh, prev_tail, bL, bR,
                                            fade_s=3.0, silence_s=0.2)
                del bL, bR

        # Финальный fade-out
        if prev_tail and prev_tail[0] is not None and len(prev_tail[0]):
            tL, tR = prev_tail
            fn   = min(int(6 * SR), len(tL))
            ramp = np.linspace(1, 0, fn, np.float32)
            tL[-fn:] *= ramp; tR[-fn:] *= ramp
            fh.write(np.stack([tL, tR], axis=1))

    size_mb = os.path.getsize(out_flac) / 1024 / 1024
    if progress_cb is None:
        print(f"\r  {'█'*20}  100%  "
              f"{total_s/60:.1f} min | {size_mb:.1f} MB{' '*25}")
    return out_flac
