import numpy as np
import soundfile as sf
import os, sys, time
from typing import List, Callable, Optional
from .block import Block
from .core  import SR, crossfade_write
from .dsp   import ffr_prime_burst, ambient_bridge, structured_quiet


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


def _carrier_jump(prev: Block, cur: Block, thresh_hz: float = 40.0) -> bool:
    """True when carriers differ enough to need fade-through-silence."""
    return abs(float(prev.c1) - float(cur.c0)) > thresh_hz


def export_cue(blocks: List[Block], out_path: str, flac_filename: str,
               artist: str = 'franklin-sys',
               break_min_dur: float = 600.0):
    """
    Генерирует .cue файл с треком для каждого блока.
    Плееры (foobar2000, VLC, mpv) показывают название текущей фазы.
    """
    BREAK_AFTER = {
        i for i, b in enumerate(blocks)
        if b.dur_s >= break_min_dur
        and not getattr(b, 'skip_ambient_bridge', False)
    }
    if blocks and not getattr(blocks[0], 'skip_ambient_bridge', False):
        BREAK_AFTER.add(0)

    lines = [
        f'PERFORMER "{artist}"',
        f'FILE "{flac_filename}" FLAC',
    ]

    t     = 0.0
    track = 1
    for i, b in enumerate(blocks):
        if getattr(b, 'quiet_before_s', 0) and b.quiet_before_s > 0:
            t += float(b.quiet_before_s)
        lines.append(f'  TRACK {track:02d} AUDIO')
        lines.append(f'    TITLE "{b.label}"')
        lines.append(f'    PERFORMER "{artist}"')
        lines.append(f'    INDEX 01 {_sec_to_cue(t)}')
        track += 1
        t += b.dur_s
        if i in BREAK_AFTER:
            t += 20.0

    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print(f"  Cue  → {out_path}")


# ══════════════════════════════════════════════════════════
#  SESSION MAP (text)
# ══════════════════════════════════════════════════════════

def export_map(blocks: List[Block], profile: str, out_path: str,
               break_min_dur: float = 600.0):
    BREAK_AFTER = {
        i for i, b in enumerate(blocks)
        if b.dur_s >= break_min_dur
        and not getattr(b, 'skip_ambient_bridge', False)
    }
    if blocks and not getattr(blocks[0], 'skip_ambient_bridge', False):
        BREAK_AFTER.add(0)

    lines = ["═" * 72,
             f"  NEURODYNAMICS — SESSION MAP  |  Profile: {profile}", "═" * 72, ""]
    t = 0.0
    for i, b in enumerate(blocks):
        if getattr(b, 'quiet_before_s', 0) and b.quiet_before_s > 0:
            lines.append(f"  [··]  STRUCTURED QUIET  {b.quiet_before_s:.0f}s")
            lines.append(f"        {t/60:.2f} → {(t+b.quiet_before_s)/60:.2f} min")
            lines.append("")
            t += float(b.quiet_before_s)
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
        if b.use_respiratory:
            end_bpm = getattr(b, 'breath_bpm_end', None)
            bpm_s = f"{b.breath_bpm}"
            if end_bpm: bpm_s += f"→{end_bpm}"
            flags.append(f"Resp bpm={bpm_s} d={b.breath_depth}")
        if getattr(b, 'use_focus_mix', False):
            flags.append(f"FocusMix body={b.focus_body_beat} cortex={b.focus_cortex_beat}")
        if b.use_comfort_eq:  flags.append("ComfortEQ")
        if getattr(b, 'use_harmonic_binaural', False):
            flags.append(f"HarmBinaural {b.harmonic_partials}p")
        if getattr(b, 'use_polyrhythmic_iso', False):
            flags.append(f"PolyISO {b.polyrhythmic_ratios}")
        if getattr(b, 'cfc_envelope_type', 'sine') == 'asymmetric':
            flags.append(f"AsymPAC a={b.cfc_asymmetry}")
        if getattr(b, 'use_signal_sr', False):
            flags.append(f"SignalSR {b.signal_sr_ratio}")
        if getattr(b, 'use_fm_carrier', False):
            flags.append(f"FMCarr idx={b.fm_mod_index}")
        if getattr(b, 'use_shepard_carrier', False):
            flags.append(f"Shepard {b.shepard_num_octaves}oct")
        if getattr(b, 'breath_golden_ratio', False):
            flags.append("GoldenBreath")
        if flags:
            lines.append("        " + "  ·  ".join(flags))
        lines.append("")
        t = end
        if i in BREAK_AFTER:
            t += 20.0

    lines += ["═" * 72,
              "  LAYER LEGEND",
              "  carrier:  sine|warm(FM β=0.28)|rich(5harm)|soft|organ",
              "  MonoBeat: monaural AM locked to binaural sweep",
              "  FocusMix: dual-frequency open-loop (body+cortex)",
              "  ComfortEQ→soft ceiling→block_gain master chain",
              "  Resp:     open-loop respiratory AM (optional bpm ramp)",
              "  Quiet:    structured near-silence before void/OBE",
              "  EDGE:     GATEWAY_EDGE Focus ladder + interrupt + seal",
              "═" * 72]

    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f"  Map  → {out_path}")


def estimate_session_duration(blocks: List[Block],
                              break_min_dur: float = 600.0,
                              ffr_s: float = 20.0) -> float:
    """Total rendered seconds including FFR, quiet, and ambient bridges."""
    BREAK_AFTER = {
        i for i, b in enumerate(blocks)
        if b.dur_s >= break_min_dur
        and not getattr(b, 'skip_ambient_bridge', False)
    }
    if blocks and not getattr(blocks[0], 'skip_ambient_bridge', False):
        BREAK_AFTER.add(0)
    total = ffr_s + sum(b.dur_s for b in blocks)
    total += sum(float(getattr(b, 'quiet_before_s', 0) or 0) for b in blocks)
    total += len(BREAK_AFTER) * 20.0
    return total


# ══════════════════════════════════════════════════════════
#  RENDER ENGINE
# ══════════════════════════════════════════════════════════

def render_session(blocks: List[Block],
                   out_flac: str,
                   author:        str   = 'franklin-sys',
                   url:           str   = 'https://franklin-sys.vercel.app/',
                   fade_s:        float = 8.0,
                   break_min_dur: float = 600.0,
                   progress_cb:   Optional[Callable] = None):
    """
    Рендерит блоки в FLAC PCM-24.
    Same-carrier joins use equal-power crossfade (no silence).
    Large carrier jumps keep fade-through-silence.
    Inserts structured quiet when block.quiet_before_s > 0.
    """
    BREAK_AFTER = {
        i for i, b in enumerate(blocks)
        if b.dur_s >= break_min_dur
        and not getattr(b, 'skip_ambient_bridge', False)
    }
    if blocks and not getattr(blocks[0], 'skip_ambient_bridge', False):
        BREAK_AFTER.add(0)

    total_s = estimate_session_duration(blocks, break_min_dur=break_min_dur)

    cue_path = out_flac.replace('.flac', '.cue')
    export_cue(blocks, cue_path,
               flac_filename=os.path.basename(out_flac),
               artist=author,
               break_min_dur=break_min_dur)

    print(f"  {len(blocks)} blocks | {len(BREAK_AFTER)} breaks "
          f"| {total_s/60:.1f} min total")
    print(f"  → {out_flac}")

    t_start = time.time()
    total_core = sum(b.dur_s for b in blocks)

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
        prev_block = None

        for i, block in enumerate(blocks):
            done    = sum(b.dur_s for b in blocks[:i])
            pct     = done / total_core * 100 if total_core else 0
            elapsed = time.time() - t_start

            if progress_cb is not None:
                progress_cb(i, block.label, pct, elapsed)
            else:
                bar = '█' * int(pct / 5) + '░' * (20 - int(pct / 5))
                sys.stdout.write(
                    f"\r  [{bar}] {pct:4.0f}%  {block.label[:36]:<36s}")
                sys.stdout.flush()

            if i == 0:
                pL, pR = ffr_prime_burst(carrier=block.c0,
                                         carrier_type=block.carrier_type)
                prev_tail = crossfade_write(fh, None, pL, pR,
                                            fade_s=6.0, silence_s=0.0,
                                            equal_power=False)
                del pL, pR

            # Structured quiet (Gateway internalization) before void/OBE
            qb = float(getattr(block, 'quiet_before_s', 0) or 0)
            if qb > 0:
                qL, qR = structured_quiet(dur_s=qb, seed=i * 31 + 7)
                prev_tail = crossfade_write(
                    fh, prev_tail, qL, qR,
                    fade_s=5.0, silence_s=0.2, equal_power=False)
                del qL, qR

            L, R = block.render()

            if prev_block is None:
                use_ep = False
                sil = 0.2
                fade = fade_s
            elif _carrier_jump(prev_block, block):
                use_ep = False
                sil = 0.35
                fade = max(fade_s, 12.0)  # longer ease across carrier jumps
            else:
                # Same carrier does NOT mean phase-aligned: two independently
                # -phased tonal blocks summed via equal-power weights can
                # destructively interfere (confirmed empirically — a real
                # multi-block render showed a 45s/-52dB dropout here that
                # vanished once this join used a short gap instead of an
                # amplitude sum). A short silence costs far less than an
                # unpredictable near-total dropout.
                use_ep = False
                sil = 0.30
                fade = fade_s

            # Extra-soft entry after structured quiet / into interrupt-like labels
            if qb > 0 or 'INTERRUPT' in block.label.upper():
                fade = max(fade, 14.0)
                use_ep = False
                sil = 0.25

            prev_tail = crossfade_write(
                fh, prev_tail, L, R,
                fade_s=fade, silence_s=sil, equal_power=use_ep)
            del L, R
            prev_block = block

            if i in BREAK_AFTER:
                bL, bR = ambient_bridge(carrier=float(block.c1),
                                        carrier_type='soft',
                                        dur_s=20.0,
                                        seed=i * 17 + 3)
                prev_tail = crossfade_write(
                    fh, prev_tail, bL, bR,
                    fade_s=6.0, silence_s=0.25, equal_power=False)
                del bL, bR

        if prev_tail and prev_tail[0] is not None and len(prev_tail[0]):
            tL, tR = prev_tail
            fn   = min(int(6 * SR), len(tL))
            ramp = np.linspace(1, 0, fn, np.float32)
            tL[-fn:] *= ramp; tR[-fn:] *= ramp
            fh.write(np.stack([tL, tR], axis=1))

    elapsed = time.time() - t_start
    print(f"\n  Done in {elapsed:.1f}s → {out_flac}")
    return out_flac
