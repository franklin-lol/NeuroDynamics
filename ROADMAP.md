# NeuroDynamics Roadmap

Стратегический план развития экосистемы высокотехнологичного психоакустического ПО.

## [DONE] Phase: GENESIS (Organic & Scientific)
*   **Core Engine:** Разработка ядра `psychoacoustic/` с поддержкой 4 тембральных режимов.
*   **Spatial Model:** Интеграция аналитической модели HRTF Брауна-Дуды и задержек Woodworth ITD.
*   **Chaos Dynamics:** Реализация стабилизированного аттрактора Лоренца (0.5–3 Hz) для деактивации DMN.
*   **Geometry:** Слой Phi-пропорций (1.618) для снижения когнитивного сопротивления.
*   **Smart Rendering:** Автоматическая генерация CUE-sheets и рендеринг в PCM-24.
*   **Interactive CLI:** Полнофункциональный Dashboard для управления генерацией.

## [DONE] Phase: ATMOSPHERE (Texture & Synthesis)
*   **Granular Engine:** Стохастический синтез зернистых облаков (granular clouds) для создания живых органических текстур.
*   **Spectral Morphing:** Плавные переходы между тембральными состояниями через STFT Overlap-Add интерполяцию.
*   **Loudness Optimization:** Пересмотр системы нормализации (-3.1 dBFS) и внедрение `block_gain` для комфортного прослушивания.

## [PLANNED] Phase: NEUROSYNC (Biofeedback & Adaptation)
*   **EEG Integration:** Поддержка OpenBCI и Muse для сбора данных в реальном времени.
*   **Adaptive Entrainment:** Динамическая подстройка частоты биений под текущий ритм мозга пользователя.
*   **Neural Fingerprinting:** Генерация уникальных сессий на основе спектрального анализа ЭЭГ.

## [PLANNED] Phase: ATMOSPHERE (Advanced)
*   **Field Recordings:** Интеграция алгоритмически обработанных природных ландшафтов.
*   **Spectral Morphing (Advanced):** Более сложные алгоритмы морфинга для нелинейных переходов.

## [PLANNED] Phase: ECOSYSTEM (Platform Expansion)
*   **Web Renderer:** Портирование ядра на WebAudio + WebAssembly для запуска в браузере.
*   **Mobile App:** Нативное приложение (Flutter/Compose) с локальным рендерингом.
*   **VST/AU Plugin:** Интеграция движка в DAW для профессиональной работы со звуком.
*   **API Service:** Облачный рендеринг сессий и хранилище пресетов.
