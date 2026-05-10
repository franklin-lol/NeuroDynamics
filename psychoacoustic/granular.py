"""
granular.py — ATMOSPHERE Granular Engine v0.1
Stochastic grain cloud synthesis. Pure numpy/scipy, zero extra deps.

API
───
granular_cloud(dur_s, carrier_freq, ...) → mono float32 ndarray

Algorithm
─────────
1. Schedule N = int(dur_s * density) grain onsets uniformly across the
   output buffer, then apply ±scatter jitter in the time domain.
2. Per grain: synthesize carrier_type waveform at a pitch-scattered
   frequency (±pitch_scatter_st semitones via 2^(st/12) ratio).
3. Apply Hann window to each grain (zero-crossing, click-free).
4. Accumulate all grains → peak-normalize → apply vol.

L/R stereo width: caller requests two instances with seeds +900 / +901.
The differing RNG seeds produce independent grain onset/pitch schedules,
creating subtle inter-channel decorrelation without explicit pan law.

Performance: N grains × grain_n samples per grain.
Worst case: density=12, dur_s=900, grain_ms=140 → ~10 800 grains × 6174
samples = ~67 M float64 ops. Runs in <3 s on a modern CPU (numpy BLAS).
"""

import numpy as np
from .core import SR


# ──────────────────────────────────────────────────────────────────────────
#  Internal: carrier waveform from phase array (mirrors dsp._apply_carrier_type
#  without creating a circular import — dsp imports from core, granular imports
#  from core only).
# ──────────────────────────────────────────────────────────────────────────

def _grain_carrier(phase: np.ndarray, ctype: str) -> np.ndarray:
    """
    Synthesize one grain waveform from a phase vector.
    Matches dsp._apply_carrier_type exactly — kept local to avoid circular deps.
    """
    if ctype == 'warm':
        return np.sin(phase + 0.28 * np.sin(1.5 * phase))
    elif ctype == 'rich':
        return (0.600 * np.sin(phase)
              + 0.240 * np.sin(2 * phase)
              + 0.100 * np.sin(3 * phase)
              + 0.040 * np.sin(4 * phase)
              + 0.020 * np.sin(5 * phase))
    elif ctype == 'soft':
        return (0.88 * np.sin(phase)
              + 0.10 * np.sin(2 * phase)
              + 0.02 * np.sin(3 * phase))
    elif ctype == 'organ':
        return (0.55 * np.sin(phase)
              + 0.30 * np.sin(2 * phase)
              + 0.12 * np.sin(3 * phase)
              + 0.03 * np.sin(4 * phase))
    else:  # 'sine' and fallback
        return np.sin(phase)


# ──────────────────────────────────────────────────────────────────────────
#  Public API
# ──────────────────────────────────────────────────────────────────────────

def granular_cloud(
    dur_s:            float,
    carrier_freq:     float,
    grain_size_ms:    float = 80.0,
    density:          float = 12.0,
    pitch_scatter_st: float = 0.30,
    time_scatter:     float = 0.50,
    vol:              float = 0.11,
    ctype:            str   = 'warm',
    seed:             int   = 0,
) -> np.ndarray:
    """
    Stochastic grain cloud over a psychoacoustic carrier.

    Parameters
    ----------
    dur_s            : total output duration (seconds)
    carrier_freq     : fundamental frequency Hz — grain pitch center
    grain_size_ms    : grain window duration ms, typ. 40–200
    density          : average grains per second, typ. 5–20
    pitch_scatter_st : ±semitones pitch randomization per grain (0 = no scatter)
    time_scatter     : time jitter as fraction of grain_size_ms (0–1)
    vol              : output amplitude after internal peak-normalize
    ctype            : carrier type 'sine'|'warm'|'rich'|'soft'|'organ'
    seed             : deterministic RNG seed

    Returns
    -------
    np.ndarray, dtype=float32, shape=(int(dur_s * SR),)  — mono
    """
    n_out   = int(dur_s * SR)
    # Clamp grain length: minimum 64 samples to avoid spectral smear
    grain_n = max(64, int(grain_size_ms * 1e-3 * SR))
    n_grains = max(1, int(dur_s * density))

    rng = np.random.RandomState(seed)
    out = np.zeros(n_out, dtype=np.float64)

    # Hann window — smooth amplitude envelope, zero at grain edges
    window = np.hanning(grain_n)  # float64

    # ── Grain onset schedule ──────────────────────────────────────────────
    # Uniform base spacing across the full buffer, converted to sample indices
    base_onsets_s = np.linspace(0.0,
                                dur_s - grain_size_ms * 1e-3,
                                n_grains)

    # Time scatter: ±(time_scatter * grain_duration) seconds
    jitter_s = time_scatter * (grain_size_ms * 1e-3)
    if jitter_s > 0.0:
        base_onsets_s = base_onsets_s + rng.uniform(
            -jitter_s, jitter_s, size=n_grains
        )

    onset_samples = np.round(base_onsets_s * SR).astype(np.int64)

    # ── Pitch scatter ─────────────────────────────────────────────────────
    if pitch_scatter_st > 0.0:
        st_offsets = rng.uniform(-pitch_scatter_st, pitch_scatter_st,
                                  size=n_grains)
    else:
        st_offsets = np.zeros(n_grains)
    freqs = carrier_freq * (2.0 ** (st_offsets / 12.0))

    # ── Reusable time axis for a single grain at SR ───────────────────────
    t_base = np.arange(grain_n, dtype=np.float64) / SR

    # ── Grain accumulation ────────────────────────────────────────────────
    for i in range(n_grains):
        pos = int(onset_samples[i])

        # Skip grains that start before the buffer
        if pos < 0:
            continue

        end = pos + grain_n

        if end <= n_out:
            # Full grain fits in buffer
            phase = 2.0 * np.pi * freqs[i] * t_base
            grain = _grain_carrier(phase, ctype) * window
            out[pos:end] += grain
        else:
            # Partial grain at tail — crop to remaining samples
            crop = n_out - pos
            if crop < 16:
                continue
            phase = 2.0 * np.pi * freqs[i] * t_base[:crop]
            grain = _grain_carrier(phase, ctype) * window[:crop]
            out[pos:n_out] += grain

    # ── Output normalisation + vol ────────────────────────────────────────
    peak = np.max(np.abs(out)) + 1e-9
    return (out / peak * vol).astype(np.float32)