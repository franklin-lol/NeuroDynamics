import numpy as np
import pytest
from psychoacoustic.core import SR, pink_noise, calibrated_noise, crossfade_write
from psychoacoustic.block import Block
from psychoacoustic.dsp import (tube_saturate, formant_resonator, isochronic, 
                                 schumann_stack, comfort_filter, ambient_bridge,
                                 _SCHUMANN_TAPER)

def test_normalization_limit():
    """Проверка жесткого лимита 0.56 FS."""
    # Создаем блок с избыточной громкостью
    b = Block(label="Test", dur_s=1.0, c0=200.0, b0=10.0, use_drone=True, drone_vol=1.0)
    L, R = b.render()
    peak = max(np.max(np.abs(L)), np.max(np.abs(R)))
    # Допуск 0.561 из-за особенностей float32 и возможных пиков после фильтрации
    assert peak <= 0.561

def test_no_nan_values():
    """Проверка на отсутствие NaN в выходном сигнале."""
    b = Block(label="Test", dur_s=1.0, use_chaos=True, use_hrtf=True, use_reverb=True, 
              use_formant=True, use_comfort_eq=True)
    L, R = b.render()
    assert not np.any(np.isnan(L))
    assert not np.any(np.isnan(R))

def test_isochronic_smoothness():
    """Проверка адаптивного сглаживания в isochronic (FIX 1)."""
    # Тестируем Gamma (40Hz) - самый критичный случай
    freq = 40.0
    sig = isochronic(dur_s=1.0, freq=freq, carrier=200.0)
    
    # Считаем производную (разницу между соседними семплами)
    diffs = np.abs(np.diff(sig))
    max_jump = np.max(diffs)
    
    # При 40Hz и 18ms сглаживании скачок должен быть очень малым
    # До фикса он был порядка 0.05-0.1, после должен быть < 0.01
    assert max_jump < 0.005, f"Too harsh jump in Gamma gate: {max_jump}"

def test_schumann_taper():
    """Проверка тейпера резонансов Шумана (FIX 2)."""
    # Проверяем что глобальный тейпер соответствует новым значениям
    expected = [1.0, 0.45, 0.12, 0.04, 0.01]
    assert np.allclose(_SCHUMANN_TAPER, expected)
    
    # Проверяем рендер стека
    L, R = schumann_stack(dur_s=1.0, carrier=432.0, base_vol=0.20)
    # Максимальная амплитуда не должна зашкаливать
    assert np.max(np.abs(L)) < 0.8  # 0.2 * sum(taper) ~ 0.2 * 1.62 = 0.324 + бинауральные биения

def test_ambient_bridge_levels():
    """Проверка уровней в ambient_bridge (FIX 3)."""
    L, R = ambient_bridge(carrier=432.0, dur_s=2.0)
    peak = max(np.max(np.abs(L)), np.max(np.abs(R)))
    
    # Целевой уровень -18 dBFS ~ 0.126
    # Должен быть в районе 0.126 (с учетом фейдов может быть меньше)
    assert peak <= 0.13
    assert peak > 0.05 # Но не тишина

def test_comfort_filter_response():
    """Проверка работы comfort_filter (FIX 4)."""
    # Создаем белый шум для теста АЧХ
    n = int(SR * 2)
    noise = np.random.normal(0, 0.1, n).astype(np.float32)
    
    # Применяем фильтр
    low_db = 6.0 # Усилим для теста
    high_db = -6.0
    fL, fR = comfort_filter(noise, noise, low_db=low_db, high_db=high_db)
    
    # Считаем RMS в разных полосах
    def get_rms(sig, f_min, f_max):
        from scipy.signal import butter, sosfilt
        sos = butter(4, [f_min/(SR/2), f_max/(SR/2)], btype='band', output='sos')
        return np.sqrt(np.mean(sosfilt(sos, sig)**2))
    
    rms_low_orig = get_rms(noise, 20, 80)
    rms_low_filt = get_rms(fL, 20, 80)
    
    rms_hi_orig = get_rms(noise, 10000, 15000)
    rms_hi_filt = get_rms(fL, 10000, 15000)
    
    # Низкие должны быть громче
    assert rms_low_filt > rms_low_orig
    # Высокие должны быть тише
    assert rms_hi_filt < rms_hi_orig

def test_crossfade_logic():
    """Проверка кроссфейда."""
    class FakeFile:
        def __init__(self): self.data = []
        def write(self, x): self.data.append(x)
    
    fh = FakeFile()
    prev_tail = (np.ones(int(SR), dtype=np.float32), np.ones(int(SR), dtype=np.float32))
    new_L, new_R = np.ones(int(5*SR), dtype=np.float32), np.ones(int(5*SR), dtype=np.float32)
    
    crossfade_write(fh, prev_tail, new_L, new_R, fade_s=1.0, silence_s=0.5)
    
    # fh.data[1] - пауза
    assert len(fh.data[1]) == int(0.5 * SR)
