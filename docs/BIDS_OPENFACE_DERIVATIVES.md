# OpenFace outputs as BIDS derivatives (`of2bids`)

**Start here for time base + LSL together:** [INTEGRATION_LSL_BIDS.md](INTEGRATION_LSL_BIDS.md).

This repository adds a small Python tool under `tools/of2bids/` that converts **OpenFace `FeatureExtraction` sequence CSV** files (plus matching `*_of_details.txt`) into **tabular derivatives** next to a BIDS dataset: UTF-8 **TSV** time series and a **JSON sidecar** with column semantics, sampling metadata, and provenance. **Source CSV files are never modified.**

## Rationale

- **BIDS** standardizes neuroimaging datasets; **BIDS derivatives** document processed data under `derivatives/<tool>/` with machine-readable metadata.
- OpenFace already emits rich per-frame features in CSV. Exporting **TSV + JSON** aligns facial time series with BIDS-style tabular conventions used elsewhere (e.g. physiological recordings), improves interoperability with EEG/fMRI pipelines, and preserves a clear **audit trail** (`Sources`, `AssociatedEvents`).

## Layout

Under the BIDS root you specify, the tool writes:

```text
derivatives/openface/
  dataset_description.json          # created once if missing (minimal derivative record)
  sub-<label>/func/
    sub-<label>_task-<task>[_recording-<rec>][_run-<NN>]_desc-openface_timeseries.tsv
    sub-<label>_task-<task>[_recording-<rec>][_run-<NN>]_desc-openface_timeseries.json
```

Optional, when `--merge-events` is used alongside `--events-tsv`:

```text
    sub-<label>_task-<task>_..._desc-openfacewithevents_timeseries.tsv
    sub-<label>_task-<task>_..._desc-openfacewithevents_timeseries.json
```

**Why `func/`?** OpenFace features are time series aligned to a **dynamic stimulus / video timeline** (seconds in the source media). Placing them under `func/` matches common practice for stimulus-aligned continuous measures; if your institution prefers `beh/` or a custom `derivatives/openface/.../recording/`, you can copy or symlink after export—the JSON `Description` field states the OpenFace origin.

## Column names

TSV column headers are **preserved from OpenFace** (e.g. `timestamp`, `AU01_r`, `success`) so results stay comparable to upstream OpenFace documentation. The JSON sidecar `Columns` array gives **BIDS-style** `Description` / `Units` hints per column.

## Sampling frequency (`SamplingFrequency`)

Stock OpenFace `*_of_details.txt` **does not** record container FPS. The exporter therefore:

1. **Infers** `SamplingFrequency` as `1 / median(positive delta timestamp)` from the CSV when possible.
2. Optionally reads an **`FPS:`** line if present in `_of_details.txt` (not produced by stock OpenFace; you may inject it for provenance).
3. With `--prefer-details-fps`, prefers the `FPS:` line over inference when both exist.

The JSON field `SamplingFrequencyProvenance` records which branch was used.

## EEG / `events.tsv` coupling

Two mechanisms are implemented; both can coexist:

1. **Provenance link (default when `--events-tsv` is passed):** the sidecar includes `AssociatedEvents` with a `path` to the events file (relative to the BIDS root when the file lies inside it, otherwise absolute). This is the **safest** default: it documents alignment intent without inventing merged columns.
2. **Optional merged derivative (`--merge-events`):** writes `*_desc-openfacewithevents_timeseries.tsv` where each OpenFace row is augmented with **event columns** using **as-of backward** selection: for OpenFace `timestamp` \(t\), take the **last** event row whose BIDS `onset` ≤ \(t\). This matches “state carried forward” when events mark piecewise-constant experimental conditions.

**Time base assumption (critical):** by default we assume OpenFace `timestamp` (seconds) is **comparable to BIDS `onset` in `events.tsv`** (same media / task clock). If you use **LSL**, **hardware triggers**, or **separate AV vs EEG clocks**, you must document offsets or resample—see **[INTEGRATION_LSL_BIDS.md](INTEGRATION_LSL_BIDS.md)** and the **`TimeAlignment`** object in each derivative JSON.

## CLI

Requires `PYTHONPATH` to include the `tools` directory (repository root), **or** use the wrappers (set paths for you):

- **Windows:** `.\tools\run_of2bids.ps1 --bids-root ...` (from repo root; same arguments as `python -m of2bids`).
- **Linux / WSL:** `./tools/run_of2bids.sh --bids-root ...` (executable bit: `chmod +x tools/run_of2bids.sh` once).

Manual `PYTHONPATH`:

```powershell
cd OpenFace-2.2.0
$env:PYTHONPATH = "tools"
python -m of2bids --bids-root D:\bids_dataset --subject 01 --task rest `
  --csv D:\openface_out\run1.csv --of-details D:\openface_out\run1_of_details.txt
```

Directory scan (pairs `stem.csv` + `stem_of_details.txt` in the same folder):

```powershell
python -m of2bids --bids-root D:\bids_dataset --subject 01 --task faces `
  --scan-dir D:\openface_out --recursive
```

Multiple pairs from `--scan-dir` automatically receive `_run-01`, `_run-02`, … entity labels.

With BIDS events and merged export:

```powershell
python -m of2bids --bids-root D:\bids_dataset --subject 01 --task rest `
  --csv D:\openface_out\run1.csv --of-details D:\openface_out\run1_of_details.txt `
  --events-tsv D:\bids_dataset\sub-01\func\sub-01_task-rest_events.tsv `
  --events-json D:\bids_dataset\sub-01\func\sub-01_task-rest_events.json `
  --merge-events
```

Validation flags:

- `--strict-timestamps` — fail on **duplicate** timestamps (non-strict mode only warns).
- Non-monotonic **decreasing** timestamps always fail.

## Limitations

- **Image / single-frame mode** CSV (header `face,confidence,...` without `timestamp`) is **not** exported as a continuous BIDS time series; the tool raises a clear error.
- Merged events require a BIDS **`onset`** column in `events.tsv`.

## Multi-face, fMRI / TR, and LSL (resolved at repo level)

Design choices and extension points are documented in **[INTEGRATION_LSL_BIDS.md](INTEGRATION_LSL_BIDS.md)** (`face_id`, TR vs video, LSL vs BIDS `onset`).

## Tests

Synthetic fixtures live under `tests/of2bids_fixtures/`. From the repository root:

```powershell
$env:PYTHONPATH = "tools"
python -m unittest tests.test_of2bids -v
```
