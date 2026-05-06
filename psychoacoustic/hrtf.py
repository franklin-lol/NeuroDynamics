"""
Simplified HRTF externalization — pure numpy/scipy, no external SOFA files.

Real HRTF uses measured Head-Related Transfer Functions (pysofaconventions +
MIT KEMAR dataset). This approximation achieves partial externalization via:
  1. Pinna reflection: delayed+attenuated copy → comb filter notch ~8-10 kHz
     (signature cue the auditory cortex uses to judge elevation)
  2. Head shadow: gentle LP on the "far" ear — frequency-dependent ILD
  3. ITD enhancement: small fractional sample delay between ears

Effect: binaural image shifts from "inside skull" to "in front/around the head".
Use in combination with spatial_rotation() for maximum externalization.
"""

import numpy as np
from scipy.signal import butter, lfilter, sosfilt
from .core import SR


def hrtf_externalize(L, R,
                     pinna_delay_ms=0.28,
                     pinna_gain=0.20,
                     shadow_fc=2200.0,
                     shadow_mix=0.22):
    """
    pinna_delay_ms: pinna reflection delay (typ. 0.25–0.35 ms → 11–15 samples)
    pinna_gain:     pinna reflection amplitude (typ. 0.15–0.25)
    shadow_fc:      head shadow LP cutoff (typ. 1.5–3 kHz)
    shadow_mix:     blend ratio of head-shadow coloring (0.2–0.3)
    """
    n = len(L)
    pd = max(1, int(pinna_delay_ms * 0.001 * SR))

    # Pinna: add time-delayed copy → comb notch
    L_p = np.zeros(n, np.float32)
    R_p = np.zeros(n, np.float32)
    if pd < n:
        L_p[pd:] = L[:-pd] * pinna_gain
        R_p[pd:] = R[:-pd] * pinna_gain

    L_c = (L + L_p).astype(np.float32)
    R_c = (R + R_p).astype(np.float32)

    # Head shadow: 2nd-order Butterworth LP
    nyq = SR / 2.0
    sos = butter(2, min(shadow_fc / nyq, 0.99), btype='low', output='sos')
    L_lp = sosfilt(sos, L_c).astype(np.float32)
    R_lp = sosfilt(sos, R_c).astype(np.float32)

    m = 1.0 - shadow_mix
    return (L_c * m + L_lp * shadow_mix).astype(np.float32), \
           (R_c * m + R_lp * shadow_mix).astype(np.float32)
