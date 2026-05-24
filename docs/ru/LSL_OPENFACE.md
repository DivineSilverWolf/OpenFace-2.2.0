# OpenFace и Lab Streaming Layer (LSL)

**Как это связано с BIDS / EEG clock:** сначала прочитайте **[INTEGRATION_LSL_BIDS.md](INTEGRATION_LSL_BIDS.md)**.

Этот документ описывает интеграцию **Mode A** в данном форке: воспроизведение CSV-файлов OpenFace `FeatureExtraction` в **LSL outlets** для синхронизируемых временных рядов (например, вместе с EEG или eye-tracking потоками, записанными через LSL).

LSL (Lab Streaming Layer) предоставляет сетевые потоки с временными метаданными. **XDF** — распространённый контейнер для multi-stream записей; stream headers приходят из LSL, а дополнительные метаданные могут храниться в sidecar JSON в BIDS/companion стиле.

## Mode A (реализован): post-hoc CSV → LSL

OpenFace пишет одну строку на каждый обработанный кадр со столбцом `timestamp` (секунды, когда доступны из источника), а также `frame`, `face_id` и большое число feature-колонок. Утилита в `tools/lsl_streamer/`:

- Читает CSV, сохраняя **OpenFace column names**, как их выдаёт `FeatureExtraction`.
- Оценивает **nominal sampling rate** по последовательным `timestamp` (или использует `--fps`).
- Создаёт один или два **float32** continuous stream:
  - **split** (по умолчанию): `\<stream-name\>-AU` (все найденные `AU*_r` и `AU*_c`) и `\<stream-name\>-core` (confidence, success, gaze vectors/angles, head pose).
  - **single**: один поток AU + core в фиксированном порядке колонок (AU intensities, затем AU presence, затем core).
- Публикует каждую строку с LSL timestamp, выровненным по **`local_clock()`**, чтобы **относительный** тайминг соответствовал CSV: `lsl_t = t0_lsl + (csv_timestamp - csv_timestamp_first)`.

### Установка

1. Установите **liblsl** для вашей ОС (см. [LabStreamingLayer releases](https://github.com/sccn/liblsl/releases)).
2. Установите Python bindings:

```bash
pip install -r tools/lsl_streamer/requirements.txt
```

Опционально: `tools/lsl_streamer/pyproject.toml` перечисляет ту же зависимость для инструментов, читающих PEP 621 metadata.

### CLI (из корня репозитория)

```bash
python -m tools.lsl_streamer path/to/video_of.csv --stream-name OpenFace --subject-id S01 --run-id 001
```

Полезные флаги:

- `--layout split|single` — default `split`.
- `--fps 30` — переопределяет nominal rate, если timestamps отсутствуют или ненадёжны.
- `--openface-version 2.2.0` — сохраняется в LSL `desc` и JSON sidecar.
- `--sidecar-dir ./meta` — пишет по одному JSON на поток с **XDF-oriented** полями (stream name, nominal rate, channel labels, версия OpenFace, путь CSV).
- `--realtime` — добавляет sleep между samples для приближения к real-time delivery (по умолчанию push происходит максимально быстро).

### XDF-oriented metadata

LSL `StreamInfo` содержит небольшое XML-дерево `desc`. Инструмент добавляет key/value пары (`source`, `openface_version`, `csv_path`, `stream_role`, опциональные `subject_id` / `run_id`) и channel `<label>` под `<channels>`.

Для более богатых метаданных, удобных для архивирования, опциональный **JSON sidecar** добавляет:

- `SoftwareFilters.OpenFace.Version` — задаётся через `--openface-version`.
- `LSL.channel_labels` — тот же порядок, что и у LSL-каналов.
- `OpenFace.column_map` — канонические колонки OpenFace (`timestamp`, `frame`, `face_id`).

При объединении с другими модальностями в XDF сопоставляйте эти sidecar с метаданными записи и соблюдайте семантику времени из [INTEGRATION_LSL_BIDS.md](INTEGRATION_LSL_BIDS.md).

## Ограничения

- **Landmarks / full mesh columns** по умолчанию не стримятся (сотни каналов). Если это нужно исследованию, расширяйте списки в `tools/lsl_streamer/columns.py` (разрешённая зона: `tools/**`).
- В режиме **post-hoc burst** сэмплы могут иметь timestamps «в прошлом» относительно текущего времени; некоторые приёмники ожидают метки, близкие к now. Для интерактивных демо используйте `--realtime`.
- **Multiple faces** (`face_id`): строки отправляются в порядке файла; downstream фильтрует по `face_id`, если вы добавляете его как канал (в default-стримы он не включён).

## Mode B (будущая работа): near real-time from webcam

Near real-time LSL с веб-камеры потребует отправки сэмплов внутри/рядом с `FeatureExtraction` по мере обработки кадров, либо IPC bridge из C++ executable. Это затрагивает `exe/FeatureExtraction` и здесь **не реализовано**.

Практичный путь:

1. Добавить optional compile-time/runtime hook на уровне **`exe/**`** для сериализации компактного feature-вектора по кадру в stdout, named pipe или ZeroMQ.
2. Держать LSL-специфику в **Python** под `tools/lsl_streamer/`, читая этот поток и вызывая `push_sample` с timestamp из `local_clock()`.

Это позволяет не менять `lib/local/**` (алгоритмическое ядро), но при этом добавить live-fusion в отдельном процессе.

## Связанные инструменты

- **BIDS derivatives:** `tools/of2bids/` — см. [BIDS_OPENFACE_DERIVATIVES.md](BIDS_OPENFACE_DERIVATIVES.md).
- **Единая time model (LSL + BIDS + events):** [INTEGRATION_LSL_BIDS.md](INTEGRATION_LSL_BIDS.md).

## Тесты

Из корня репозитория:

```bash
python -m unittest discover -s tests -p "test_lsl_streamer*.py" -v
```

Тесты используют **synthetic CSV** в `tests/fixtures/lsl_streamer/` и **fake pylsl** module, поэтому CI не требует liblsl. Если установлен `pylsl`, дополнительный тест проверяет флаг `HAS_PYLSL`.

### Локальный интеграционный тест (реальный LSL)

При установленном liblsl и запущенном LSL viewer (например, LabRecorder или другой inlet):

```bash
python -m tools.lsl_streamer tests/fixtures/lsl_streamer/minimal_openface.csv --stream-name DemoOF --sidecar-dir ./lsl_meta_out
```

Проверьте, что потоки видны и sample count соответствует количеству строк CSV для выбранного layout.
