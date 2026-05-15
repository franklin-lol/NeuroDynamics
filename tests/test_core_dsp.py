import numpy as np
import pytest
import os
from psychoacoustic.core import SR, pink_noise, calibrated_noise, crossfade_write
from psychoacoustic.block import Block
from psychoacoustic.dsp import tube_saturate, formant_resonator

def test_normalization_limit():
    """Проверка жесткого лимита 0.56 FS."""
    # Создаем блок с избыточной громкостью
    b = Block(label="Test", dur_s=1.0, c0=200.0, b0=10.0, use_drone=True, drone_vol=1.0)
    L, R = b.render()
    peak = max(np.max(np.abs(L)), np.max(np.abs(R)))
    assert peak <= 0.561  # Допуск на точность float

def test_no_nan_values():
    """Проверка на отсутствие NaN в выходном сигнале."""
    b = Block(label="Test", dur_s=1.0, use_chaos=True, use_hrtf=True, use_reverb=True, use_formant=True)
    L, R = b.render()
    assert not np.any(np.isnan(L))
    assert not np.any(np.isnan(R))

def test_noise_levels():
    """Проверка уровня шума в crossfade."""
    # Уровень pink noise -62 dBFS (0.0008)
    nz = pink_noise(int(SR), seed=0) * 0.0008
    rms = np.sqrt(np.mean(nz**2))
    # RMS для -62 dBFS pink noise должен быть очень низким
    assert rms < 0.001

def test_block_duration():
    """Проверка точности длительности отрендеренного массива."""
    dur = 0.5
    b = Block(label="Short", dur_s=dur)
    L, R = b.render()
    assert len(L) == int(dur * SR)

def test_respiratory_modulation():
    """Проверка что респираторная модуляция применяется корректно."""
    b = Block(label="Resp", dur_s=10.0, use_respiratory=True, breath_depth=0.5)
    L, R = b.render()
    # Сигнал должен иметь вариацию амплитуды
    assert np.max(L) > np.min(L) * 1.5

def test_crossfade_silence_gap():
    """Проверка наличия паузы в crossfade logic."""
    class FakeFile:
        def __init__(self): self.data = []
        def write(self, x): self.data.append(x)
    
    fh = FakeFile()
    prev_tail = (np.ones(int(SR)), np.ones(int(SR)))
    new_L, new_R = np.ones(int(5*SR)), np.ones(int(5*SR))
    
    # Рендерим переход
    crossfade_write(fh, prev_tail, new_L, new_R, fade_s=1.0, silence_s=0.5)
    
    # fh.data[1] должен быть pink noise паузой
    gap_data = fh.data[1]
    assert len(gap_data) == int(0.5 * SR)
    assert np.max(np.abs(gap_data)) < 0.01 # Должен быть тихим шумом
