import numpy as np


def lorenz_trajectory(n_samples, steps=50000, seed=0):
    """
    Integrates Lorenz system (σ=10, ρ=28, β=8/3) — canonical chaotic regime.
    Returns x-coordinate normalized to [-1, 1], resampled to n_samples.

    Key property: deterministic but aperiodic — the brain cannot build
    a stable prediction model, forcing sustained cortical response.
    """
    rng = np.random.RandomState(seed)
    s, r, b = 10.0, 28.0, 8.0/3.0
    dt = 0.005
    x = rng.randn() * 0.5
    y = rng.randn() * 0.5
    z = 20.0 + rng.randn() * 0.3

    xs = np.empty(steps, dtype=np.float64)
    for i in range(steps):
        dx = s * (y - x) * dt
        dy = (x * (r - z) - y) * dt
        dz = (x * y - b * z) * dt
        x += dx; y += dy; z += dz
        xs[i] = x

    t_src = np.linspace(0, 1, steps)
    t_dst = np.linspace(0, 1, n_samples)
    out = np.interp(t_dst, t_src, xs)
    out -= out.mean()
    out /= np.max(np.abs(out)) + 1e-9
    return out.astype(np.float64)


def chaos_modulate(beat_sweep, depth=0.25, seed=0):
    """
    Replace 1/f beat jitter with Lorenz chaos.
    Richer long-range unpredictability vs pink noise jitter.
    depth=0.25 → beat oscillates ±25% around sweep value.
    """
    chaos = lorenz_trajectory(len(beat_sweep), seed=seed)
    return (beat_sweep * (1.0 + depth * chaos)).astype(np.float64)
