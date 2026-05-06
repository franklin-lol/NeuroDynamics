import numpy as np
import soundfile as sf
import os, sys
from typing import List
from .block import Block
from .core import SR, crossfade_write
from .dsp import pattern_break


def export_map(blocks: List[Block], profile: str, out_path: str):
    lines = [
        "═" * 72,
        f"  GENESIS — SESSION MAP  |  Profile: {profile}",
        "═" * 72, ""
    ]
    t = 0.0
    for i, b in enumerate(blocks):
        end = t + b.dur_s
        lines.append(f"  [{i+1:02d}]  {b.label}")
        lines.append(f"        {t/60:.2f} → {end/60:.2f} min")
        lines.append(f"        Carrier {b.c0}→{b.c1} Hz   Beat {b.b0}→{b.b1} Hz (log)")
        lines.append(f"        Noise  pink={b.noise_pw:.1f} brown={b.noise_bw:.1f} (SR-cal)")
        for (fv, cv, vv, atk, dec) in b.iso_layers:
            lines.append(f"        ISO    {fv} Hz  carr={cv}  vol={vv}  atk={atk}s dec={dec}s")
        if b.cfc_theta:    lines.append(f"        CFC    θ={b.cfc_theta} Hz → γ  str={b.cfc_strength}")
        if b.assr_80hz_vol: lines.append(f"        ASSR-80  vol={b.assr_80hz_vol}")
        if b.itd_period:   lines.append(f"        ITD-rot  period={b.itd_period}s")
        if b.infra_freq:   lines.append(f"        Infra    {b.infra_freq} Hz  depth={b.infra_depth}")
        if b.schumann_mode: lines.append(f"        MODE     Schumann stack (7.83+14.3+20.8+27.3+33.8 Hz)")
        if b.use_chaos:    lines.append(f"        CHAOS    Lorenz beat  depth={b.chaos_depth}")
        if b.use_hrtf:     lines.append(f"        HRTF     pinna externalization")
        if b.use_phi:      lines.append(f"        PHI      φ-ratio 3rd binaural layer")
        if b.phase_lock:   lines.append(f"        LOCK     infra→beat phase coupling  depth={b.phase_lock_depth}")
        lines.append("")
        t = end

    lines += [
        "═" * 72,
        "  LAYER LEGEND",
        "  Binaural    phase-accurate dual-octave pair + beat/carrier jitter",
        "  Isochronic  hard-gated AM > cortical evoked response",
        "  CFC         theta→gamma PAC (hippocampal working memory coupling)",
        "  ASSR-80     80 Hz brainstem pathway, independent of 40 Hz cortical",
        "  ITD-rot     inter-aural rotation, vestibular + spatial circuits",
        "  Infra       ultra-slow AM, ANS + respiratory entrainment",
        "  SR noise    stochastic-resonance calibrated to 15% signal RMS",
        "  Lorenz      deterministic chaos beat modulation, DMN deactivation",
        "  HRTF        pinna reflection + head shadow, partial externalization",
        "  PHI         φ=1.618 ratio 3rd binaural layer, minimal cog. friction",
        "  PhLock      infra envelope drives beat frequency (breath=master clock)",
        "═" * 72,
    ]
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f"  Map → {out_path}")


def render_session(blocks: List[Block], out_flac: str,
                   author: str = 'franklin-sys',
                   url: str = 'https://franklin-sys.vercel.app/',
                   fade_s: float = 8.0,
                   break_min_dur: float = 600.0):
    """
    Render blocks to FLAC PCM-24.
    Inserts 20s pattern-break after: first block + any block ≥ break_min_dur.
    Uses equal-power crossfades throughout.
    """
    BREAK_AFTER = {i for i, b in enumerate(blocks) if b.dur_s >= break_min_dur}
    BREAK_AFTER.add(0)

    total_core   = sum(b.dur_s for b in blocks)
    total_breaks = len(BREAK_AFTER) * 20
    total_s      = total_core + total_breaks

    print(f"  {len(blocks)} blocks | {len(BREAK_AFTER)} breaks | {total_s/60:.1f} min total")
    print(f"  → {out_flac}")

    with sf.SoundFile(out_flac, 'w', samplerate=SR,
                      channels=2, format='FLAC', subtype='PCM_24') as fh:
        # Metadata
        try:
            fh.artist    = author
            fh.date      = '2026'
            fh.copyright = f'{author} (2026) | {url}'
            fh.license   = url
        except Exception:
            pass  # SoundFile metadata not always writable

        prev_tail = None

        for i, block in enumerate(blocks):
            done = sum(b.dur_s for b in blocks[:i])
            pct  = done / total_core * 100
            bar  = '█' * int(pct/5) + '░' * (20 - int(pct/5))
            sys.stdout.write(f"\r  [{bar}] {pct:4.0f}%  {block.label[:36]:<36s}")
            sys.stdout.flush()

            L, R = block.render()

            if i == 0:
                fn = int(5 * SR)
                ramp = np.linspace(0, 1, fn, np.float32)
                L[:fn] *= ramp; R[:fn] *= ramp

            prev_tail = crossfade_write(fh, prev_tail, L, R, fade_s=fade_s)
            del L, R

            if i in BREAK_AFTER:
                bL, bR = pattern_break(carrier=float(block.c1))
                prev_tail = crossfade_write(fh, prev_tail, bL, bR, fade_s=3.0)
                del bL, bR

        if prev_tail and prev_tail[0] is not None and len(prev_tail[0]):
            tL, tR = prev_tail
            fn = min(int(6*SR), len(tL))
            ramp = np.linspace(1, 0, fn, np.float32)
            tL[-fn:] *= ramp; tR[-fn:] *= ramp
            fh.write(np.stack([tL, tR], axis=1))

    size_mb = os.path.getsize(out_flac) / 1024 / 1024
    print(f"\r  {'█'*20}  100%  {total_s/60:.1f} min | {size_mb:.1f} MB{' '*20}")
    return out_flac
