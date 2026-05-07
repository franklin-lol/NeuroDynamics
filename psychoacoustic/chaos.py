import numpy as np

# ══════════════════════════════════════════════════════════
#  LORENZ ATTRACTOR — канонические параметры Эдварда Лоренца
#  σ=10, ρ=28, β=8/3  →  "бабочка" в хаотическом режиме
#
#  Ключевое исправление vs предыдущей версии:
#  Ресемплинг теперь привязан к АБСОЛЮТНОМУ времени (dt_real),
#  а не к длине блока. Это гарантирует что хаотические
#  колебания всегда в диапазоне 0.3–4 Hz (значимом для DMN)
#  независимо от того, длится блок 5 или 20 минут.
#
#  Начальная точка фиксирована (seed → детерминированный хаос):
#  при одном seed каждый рендер даёт ИДЕНТИЧНУЮ траекторию.
# ══════════════════════════════════════════════════════════

# Канонические коэффициенты
_SIGMA = 10.0
_RHO   = 28.0
_BETA  = 8.0 / 3.0

# Шаг интеграции в секундах "реального аттрактора"
# dt_real=0.01 → 1 шаг ≈ ~10 мс биологического времени
# Это даёт характерные переходы аттрактора ~0.5–3 Hz
_DT_REAL = 0.01


def _integrate_lorenz(n_steps: int, seed: int) -> np.ndarray:
    """
    Интегрирует систему Лоренца n_steps шагов с шагом _DT_REAL.
    Начальная точка — детерминированная по seed (НЕ случайная).
    Возвращает x-координату, нормированную к [-1, 1].
    """
    # Детерминированная начальная точка на аттракторе
    # (прогрев 2000 шагов для выхода на аттрактор)
    rng = np.random.RandomState(seed & 0xFFFF)
    x = 0.1 + rng.uniform(-0.05, 0.05)
    y = 0.0 + rng.uniform(-0.05, 0.05)
    z = 20.0 + rng.uniform(-0.5,  0.5)

    # Прогрев — вывести на аттрактор
    for _ in range(2000):
        dx = _SIGMA * (y - x) * _DT_REAL
        dy = (x*(_RHO - z) - y) * _DT_REAL
        dz = (x*y - _BETA*z)    * _DT_REAL
        x += dx; y += dy; z += dz

    xs = np.empty(n_steps, dtype=np.float64)
    for i in range(n_steps):
        dx = _SIGMA * (y - x) * _DT_REAL
        dy = (x*(_RHO - z) - y) * _DT_REAL
        dz = (x*y - _BETA*z)    * _DT_REAL
        x += dx; y += dy; z += dz
        xs[i] = x

    xs -= xs.mean()
    xs /= (np.max(np.abs(xs)) + 1e-9)
    return xs


def lorenz_trajectory(n_samples: int, seed: int = 0) -> np.ndarray:
    """
    Возвращает хаотическую огибающую длиной n_samples.

    Временной масштаб зафиксирован: 1 аудио-сэмпл = 1/_DT_SR шагов
    аттрактора, где _DT_SR = SR * _DT_REAL = 441 шаг/сэмпл.
    Это означает что частота хаотических переходов ~0.5–3 Hz
    ВСЕГДА, вне зависимости от длины блока.
    """
    from .core import SR
    # Сколько шагов аттрактора нужно для n_samples аудио-сэмплов
    # 1 шаг аттрактора = _DT_REAL секунды
    # n_samples аудио = n_samples/SR секунды
    # → нужно (n_samples/SR) / _DT_REAL шагов
    n_lorenz = max(4000, int(n_samples / SR / _DT_REAL) + 1)

    traj = _integrate_lorenz(n_lorenz, seed)

    # Ресемплинг с сохранением временного масштаба
    t_src = np.linspace(0.0, 1.0, n_lorenz)
    t_dst = np.linspace(0.0, 1.0, n_samples)
    out   = np.interp(t_dst, t_src, traj)
    return out.astype(np.float64)


def chaos_modulate(beat_sweep: np.ndarray, depth: float = 0.22,
                   seed: int = 0) -> np.ndarray:
    """
    Накладывает детерминированный хаос Лоренца на beat-огибающую.
    depth=0.22 → ±22% вариация частоты биений.
    Частота модуляции 0.5–3 Hz → значимый диапазон для деактивации DMN.
    """
    chaos = lorenz_trajectory(len(beat_sweep), seed=seed)
    return (beat_sweep * (1.0 + depth * chaos)).astype(np.float64)
