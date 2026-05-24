# Выходы OpenFace как BIDS derivatives (`of2bids`)

**Начните с этого документа для единой временной модели вместе с LSL:** [INTEGRATION_LSL_BIDS.md](INTEGRATION_LSL_BIDS.md).

В репозитории есть инструмент `tools/of2bids/`, который преобразует **CSV последовательностей OpenFace `FeatureExtraction`** (и соответствующие `*_of_details.txt`) в **табличные derivatives** рядом с BIDS-датасетом: UTF-8 **TSV** временные ряды и **JSON sidecar** с описанием колонок, параметрами дискретизации и provenance. **Исходные CSV не изменяются.**

## Обоснование

- **BIDS** стандартизирует структуру нейровизуализационных датасетов; **BIDS derivatives** фиксируют обработанные данные в `derivatives/<tool>/` с машиночитаемыми метаданными.
- OpenFace уже выдаёт детальные признаки по каждому кадру в CSV. Экспорт в **TSV + JSON** делает лицевые временные ряды совместимыми с BIDS-подходом к табличным данным (включая физиологические серии), упрощает интеграцию с EEG/fMRI пайплайнами и сохраняет прозрачный **audit trail** (`Sources`, `AssociatedEvents`).

## Структура выходных файлов

Под указанным BIDS root инструмент создаёт:

```text
derivatives/openface/
  dataset_description.json          # created once if missing (minimal derivative record)
  sub-<label>/func/
    sub-<label>_task-<task>[_recording-<rec>][_run-<NN>]_desc-openface_timeseries.tsv
    sub-<label>_task-<task>[_recording-<rec>][_run-<NN>]_desc-openface_timeseries.json
```

Опционально, если одновременно переданы `--events-tsv` и `--merge-events`:

```text
    sub-<label>_task-<task>_..._desc-openfacewithevents_timeseries.tsv
    sub-<label>_task-<task>_..._desc-openfacewithevents_timeseries.json
```

**Почему используется `func/`?** Признаки OpenFace — это временные ряды, привязанные к **динамическому стимулу / таймлайну видео** (секунды в исходном медиафайле). Размещение в `func/` соответствует общепринятой практике для stimulus-aligned continuous measures. Если внутри вашей организации принят `beh/` или кастомный `derivatives/openface/.../recording/`, после экспорта можно использовать копирование или symlink — поле `Description` в JSON явно показывает происхождение данных из OpenFace.

## Имена колонок

Заголовки TSV **сохраняются в формате OpenFace** (например, `timestamp`, `AU01_r`, `success`), чтобы результаты были сопоставимы с upstream-документацией. В JSON sidecar массив `Columns` добавляет BIDS-style подсказки `Description` / `Units` для каждой колонки.

## Частота дискретизации (`SamplingFrequency`)

Стандартный `*_of_details.txt` OpenFace **не содержит** FPS контейнера. Поэтому экспортёр:

1. **Оценивает** `SamplingFrequency` как `1 / median(positive delta timestamp)` по CSV (когда это возможно).
2. Опционально читает строку **`FPS:`** из `_of_details.txt` (в stock OpenFace такой строки нет; её можно добавить вручную для provenance).
3. При `--prefer-details-fps` выбирает `FPS:` из details-файла вместо оценки по CSV, если доступны оба источника.

Поле JSON `SamplingFrequencyProvenance` фиксирует, какая ветка расчёта использовалась.

## Связка с EEG / `events.tsv`

Реализованы два механизма, и они могут использоваться вместе:

1. **Provenance link (по умолчанию при `--events-tsv`):** в sidecar записывается `AssociatedEvents` с `path` к файлу событий (relative к BIDS root, если файл внутри датасета; иначе absolute). Это самый безопасный default: связь задокументирована, но merge-колонки не придумываются.
2. **Опциональный merged derivative (`--merge-events`):** создаётся `*_desc-openfacewithevents_timeseries.tsv`, где каждая строка OpenFace дополняется **event columns** через **as-of backward**: для OpenFace `timestamp` \(t\) берётся **последняя** строка событий с BIDS `onset` ≤ \(t\). Такой подход соответствует модели «состояние переносится вперёд» для piecewise-constant условий.

**Критичное предположение о времени:** по умолчанию считается, что OpenFace `timestamp` (секунды) **сопоставим** с BIDS `onset` в `events.tsv` (одни и те же media/task часы). Если у вас используются **LSL**, **hardware triggers** или раздельные AV и EEG часы, нужно явно документировать offsets или выполнять ресэмплинг — см. **[INTEGRATION_LSL_BIDS.md](INTEGRATION_LSL_BIDS.md)** и объект **`TimeAlignment`** в каждом JSON derivative.

## CLI

Нужно, чтобы `PYTHONPATH` включал каталог `tools` (корень репозитория), **или** используйте wrappers (они выставляют путь автоматически):

- **Windows:** `.\tools\run_of2bids.ps1 --bids-root ...` (из корня репозитория; аргументы те же, что у `python -m of2bids`).
- **Linux / WSL:** `./tools/run_of2bids.sh --bids-root ...` (один раз выставьте executable bit: `chmod +x tools/run_of2bids.sh`).

Ручной вариант с `PYTHONPATH`:

```powershell
cd OpenFace-2.2.0
$env:PYTHONPATH = "tools"
python -m of2bids --bids-root D:\bids_dataset --subject 01 --task rest `
  --csv D:\openface_out\run1.csv --of-details D:\openface_out\run1_of_details.txt
```

Скан директории (пары `stem.csv` + `stem_of_details.txt` в одной папке):

```powershell
python -m of2bids --bids-root D:\bids_dataset --subject 01 --task faces `
  --scan-dir D:\openface_out --recursive
```

При нескольких парах из `--scan-dir` автоматически добавляются entity-метки `_run-01`, `_run-02`, ….

С BIDS events и merged export:

```powershell
python -m of2bids --bids-root D:\bids_dataset --subject 01 --task rest `
  --csv D:\openface_out\run1.csv --of-details D:\openface_out\run1_of_details.txt `
  --events-tsv D:\bids_dataset\sub-01\func\sub-01_task-rest_events.tsv `
  --events-json D:\bids_dataset\sub-01\func\sub-01_task-rest_events.json `
  --merge-events
```

Флаги валидации:

- `--strict-timestamps` — завершает работу с ошибкой при **дубликатах** timestamps (в нестрогом режиме только warning).
- Немонотонные **убывающие** timestamps всегда приводят к ошибке.

## Ограничения

- CSV режима **image / single-frame** (заголовок `face,confidence,...` без `timestamp`) **не** экспортируется как непрерывный BIDS time series; инструмент выдаёт явную ошибку.
- Для merged events требуется колонка BIDS **`onset`** в `events.tsv`.

## Multi-face, fMRI / TR и LSL (решения на уровне репозитория)

Дизайн-решения и точки расширения описаны в **[INTEGRATION_LSL_BIDS.md](INTEGRATION_LSL_BIDS.md)** (`face_id`, TR vs video, LSL vs BIDS `onset`).

## Тесты

Синтетические fixtures лежат в `tests/of2bids_fixtures/`. Запуск из корня репозитория:

```powershell
$env:PYTHONPATH = "tools"
python -m unittest tests.test_of2bids -v
```
