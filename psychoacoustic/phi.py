"""
Phi-geometry carrier architecture.

φ = 1.6180339887... (golden ratio) appears in:
  — Fibonacci spirals, DNA double helix pitch ratio
  — Dendritic branching ratios in neurons
  — Cochlear frequency mapping (~logarithmic with φ-ratio octaves)

Using φ-ratio intervals between concurrent signal layers creates
a "minimum cognitive resistance" frequency structure — the brain
recognises these ratios as self-similar, reducing entrainment friction.

Practically: adds a 3rd binaural layer at carrier×φ with beat×φ,
at reduced volume, alongside the existing dual octave pair.
"""

PHI = 1.6180339887498948482


def phi_beat_layer(dur_s, base_carrier, beat_array, vol=0.18, seed=0):
    """
    Additional binaural layer at carrier×φ with beat×φ.
    Import here to avoid circular dependency.
    """
    from .dsp import dual_binaural
    from .core import log_sweep
    import numpy as np

    n = int(dur_s * 44100)
    c_phi = base_carrier * PHI
    b_phi = np.clip(beat_array * PHI, 0.3, 120.0).astype(np.float64)

    return dual_binaural(dur_s, c_phi, c_phi,
                         float(b_phi[0]), float(b_phi[-1]),
                         vol_p=vol, vol_s=vol*0.4,
                         carrier_jitter=0.8, beat_jitter=0.08,
                         seed=seed + 700, beat_array=b_phi)


def phi_cascade(base, n=4):
    """Returns list of n carriers in φ-ratio sequence: base, base×φ, base×φ², ..."""
    return [base * (PHI ** i) for i in range(n)]
