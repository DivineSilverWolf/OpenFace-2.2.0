# LSL + BIDS derivatives вокруг OpenFace: единая модель времени

Этот документ **связывает** [`tools/lsl_streamer/`](LSL_OPENFACE.md) (Lab Streaming Layer, post-hoc replay) и [`tools/of2bids/`](BIDS_OPENFACE_DERIVATIVES.md) (BIDS derivatives). Ниже описан единый time model, который можно воспроизвести из чистого checkout.

## Три временные базы (не путайте их)

| Name | Where it appears | Meaning |
|------|------------------|---------|
| **OpenFace `timestamp`** | `FeatureExtraction` CSV, of2bids TSV | Секунды на таймлайне **video / processing** (строки признаков). Это **каноническая** временная колонка derivatives в этом репозитории. |
| **BIDS `events.tsv` `onset`** | Raw BIDS dataset | Секунды (или единицы, заданные датасетом) относительно **BIDS recording anchor** для этого run. Должно совпадать с OpenFace только если ваш pipeline так определяет. |
| **LSL timestamps (Mode A replay)** | `python -m tools.lsl_streamer …` | `local_clock()`, сдвинутый так, чтобы **межсэмпловые интервалы** совпадали с дельтами CSV. Это **не** автоматически тот же clock, что в EEG; используйте LabRecorder + triggers или post-hoc mapping. |

**Политика проекта:** используйте **OpenFace `timestamp`** как общую reference-точку для файлов **of2bids** и для сравнения с `events.tsv` **только после** проверки (или документирования), что обе шкалы времени разделяют один anchor. Если при записи используется LSL, сохраняйте метаданные выравнивания (offsets, trigger sample indices) в `dataset_description.json` или companion JSON.

В JSON sidecar derivatives включается машиночитаемый блок **`TimeAlignment`**, чтобы downstream-инструменты не зависели только от Markdown.

## Рекомендуемые пайплайны

### A. Архивирование / публикация (LSL не обязателен)

1. Запустите OpenFace `FeatureExtraction` на видео → `*.csv` + `*_of_details.txt`.
2. Экспортируйте BIDS derivatives (из **корня репозитория**):

**Linux / macOS / Git Bash**

```bash
export PYTHONPATH="$(pwd)/tools"
python -m of2bids --bids-root /path/to/bids_dataset --subject 01 --task rest \
  --csv /path/to/run.csv --of-details /path/to/run_of_details.txt
```

**Windows PowerShell**

```powershell
cd C:\path\to\OpenFace-2.2.0
.\tools\run_of2bids.ps1 --bids-root D:\bids_dataset --subject 01 --task rest `
  --csv D:\openface\run.csv --of-details D:\openface\run_of_details.txt
```

Или вручную:

```powershell
$env:PYTHONPATH = "$PWD\tools"
python -m of2bids --bids-root D:\bids_dataset --subject 01 --task rest `
  --csv D:\openface\run.csv --of-details D:\openface\run_of_details.txt
```

3. Опционально: `--events-tsv` / `--merge-events`, как в [BIDS_OPENFACE_DERIVATIVES.md](BIDS_OPENFACE_DERIVATIVES.md).

### B. Те же данные в LSL (например, демо с LabRecorder)

1. Установите **liblsl** + `pip install -r tools/lsl_streamer/requirements.txt` (см. [LSL_OPENFACE.md](LSL_OPENFACE.md)).
2. Из **корня репозитория**:

```bash
python -m tools.lsl_streamer path/to/run.csv --stream-name OpenFace --sidecar-dir ./lsl_meta
```

3. Пишите через **LabRecorder** (или ваш inlet). Помните: **LSL clock ≠ OpenFace CSV clock**, если вы явно не выполнили выравнивание; replay сохраняет только **относительный** тайминг внутри файла.

### C. EEG + video + OpenFace (high level)

1. Во время записи: EEG → BIDS/EEG; опционально LSL stream от acquisition software; опционально video.
2. Постобработайте video в OpenFace → CSV.
3. Запустите **of2bids** с `--events-tsv`, указывающим на events соответствующего BIDS run.
4. Если `onset` и OpenFace `timestamp` **не** находятся на одном anchor, **не** используйте `--merge-events` вслепую: сначала примените документированный offset/resampling или оставьте только provenance-связь `AssociatedEvents` без merge.

## `face_id` и multi-face CSV

Если CSV чередует несколько `face_id`, **фильтруйте или разбивайте upstream** до экспорта, либо экспортируйте как есть и документируйте в `dataset_description.json`, что downstream должен стратифицировать по `face_id`. Автоматическое per-face разбиение — возможное будущее расширение (см. [BIDS_OPENFACE_DERIVATIVES.md](BIDS_OPENFACE_DERIVATIVES.md)).

## fMRI / TR и video

Если stimulus timing уже задан в `events.tsv` (onset в TR или секундах от начала сканирования), используйте **`AssociatedEvents`** и/или `--merge-events` только если OpenFace `timestamp` выражен в **той же** шкале времени. Иначе связывайте файлы через metadata и выполняйте выравнивание в аналитическом коде.

## Команды верификации (из корня репозитория)

```bash
# Static tests (no liblsl required for LSL tests)
python3 -m unittest discover -s tests -p "test_lsl_streamer*.py" -v
PYTHONPATH=tools python3 -m unittest tests.test_of2bids -v
```

**Dry-run of2bids** (без записи файлов):

```bash
export PYTHONPATH="$(pwd)/tools"
python -m of2bids --bids-root /tmp/of2bids_dry --subject 01 --task rest \
  --csv tests/of2bids_fixtures/synthetic.csv \
  --of-details tests/of2bids_fixtures/synthetic_of_details.txt \
  --dry-run
```

**LSL CLI help** (для `--help` liblsl не требуется):

```bash
python -m tools.lsl_streamer --help
```

Полный Docker smoke (опционально, согласно `AGENTS.md`):

```bash
./tools/run_smoke_and_compare.sh
```

## Дополнительные материалы

- [LSL_OPENFACE.md](LSL_OPENFACE.md) — установка, CLI flags, XDF sidecars, roadmap Mode B.
- [BIDS_OPENFACE_DERIVATIVES.md](BIDS_OPENFACE_DERIVATIVES.md) — layout, validation, events coupling, scan mode.
