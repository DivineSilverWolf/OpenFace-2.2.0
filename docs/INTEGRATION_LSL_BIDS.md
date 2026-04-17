# LSL + BIDS derivatives around OpenFace: one time model

This document **ties together** [`tools/lsl_streamer/`](LSL_OPENFACE.md) (Lab Streaming Layer, post-hoc replay) and [`tools/of2bids/`](BIDS_OPENFACE_DERIVATIVES.md) (BIDS derivatives). Any developer should be able to follow the steps below from a clean checkout.

## Three time bases (do not confuse them)

| Name | Where it appears | Meaning |
|------|------------------|---------|
| **OpenFace `timestamp`** | `FeatureExtraction` CSV, of2bids TSV | Seconds on the **video / processing** timeline (feature rows). This is the **canonical** time column for derivatives in this repo. |
| **BIDS `events.tsv` `onset`** | Raw BIDS dataset | Seconds (or dataset-defined unit) relative to the **BIDS recording anchor** for that run. Must match OpenFace only if your pipeline defines it that way. |
| **LSL timestamps (Mode A replay)** | `python -m tools.lsl_streamer …` | `local_clock()` shifted so **inter-sample spacing** matches CSV deltas. **Not** automatically the same as EEG wall clock; use LabRecorder + triggers or a post-hoc map. |

**Project policy:** treat **OpenFace `timestamp`** as the shared reference for **of2bids** files and for **comparing** to `events.tsv` **only after** you have verified (or documented) that both clocks share one anchor. If you use LSL during acquisition, store alignment metadata (offsets, trigger sample indices) in your dataset `dataset_description.json` or a companion JSON.

The derivative sidecar JSON now includes a machine-readable **`TimeAlignment`** block (same text as this table, refined) so downstream tools do not depend on this Markdown alone.

## Recommended pipelines

### A. Archival / publication (no LSL required)

1. Run OpenFace `FeatureExtraction` on video → `*.csv` + `*_of_details.txt`.
2. Export BIDS derivatives (from **repository root**):

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

Or manually:

```powershell
$env:PYTHONPATH = "$PWD\tools"
python -m of2bids --bids-root D:\bids_dataset --subject 01 --task rest `
  --csv D:\openface\run.csv --of-details D:\openface\run_of_details.txt
```

3. Optional: `--events-tsv` / `--merge-events` as in [BIDS_OPENFACE_DERIVATIVES.md](BIDS_OPENFACE_DERIVATIVES.md).

### B. Same data into LSL (e.g. demo with LabRecorder)

1. Install **liblsl** + `pip install -r tools/lsl_streamer/requirements.txt` (see [LSL_OPENFACE.md](LSL_OPENFACE.md)).
2. From **repository root**:

```bash
python -m tools.lsl_streamer path/to/run.csv --stream-name OpenFace --sidecar-dir ./lsl_meta
```

3. Record with **LabRecorder** (or your inlet). Remember: **LSL clock ≠ OpenFace CSV clock** unless you explicitly align; the replay only preserves **relative** timing within the file.

### C. EEG + video + OpenFace (high level)

1. During acquisition: EEG → BIDS/EEG; optional LSL stream from acquisition software; optional video.
2. Post-process video with OpenFace → CSV.
3. Run **of2bids** with `--events-tsv` pointing at the BIDS run’s events.
4. If `onset` and OpenFace `timestamp` are **not** on the same anchor, **do not** use `--merge-events` blindly: first apply a documented offset or resampling step, or keep only `AssociatedEvents` provenance without merge.

## `face_id` and multi-face CSV

If the CSV interleaves multiple `face_id` values, **filter or split upstream** before export, or export as-is and document in `dataset_description.json` that downstream must stratify by `face_id`. Automatic per-face split is a possible future enhancement (see [BIDS_OPENFACE_DERIVATIVES.md](BIDS_OPENFACE_DERIVATIVES.md)).

## fMRI / TR and video

If stimulus timing is already in `events.tsv` (onsets in TR or seconds from scan start), use **`AssociatedEvents`** and/or `--merge-events` only when OpenFace `timestamp` is expressed on **that same** timeline. Otherwise link files via metadata and perform alignment in your analysis code.

## Verification commands (from repository root)

```bash
# Static tests (no liblsl required for LSL tests)
python3 -m unittest discover -s tests -p "test_lsl_streamer*.py" -v
PYTHONPATH=tools python3 -m unittest tests.test_of2bids -v
```

**Dry-run of2bids** (no files written):

```bash
export PYTHONPATH="$(pwd)/tools"
python -m of2bids --bids-root /tmp/of2bids_dry --subject 01 --task rest \
  --csv tests/of2bids_fixtures/synthetic.csv \
  --of-details tests/of2bids_fixtures/synthetic_of_details.txt \
  --dry-run
```

**LSL CLI help** (does not require liblsl for `--help`):

```bash
python -m tools.lsl_streamer --help
```

Full Docker smoke (optional, per `AGENTS.md`):

```bash
./tools/run_smoke_and_compare.sh
```

## Further reading

- [LSL_OPENFACE.md](LSL_OPENFACE.md) — install, CLI flags, XDF sidecars, Mode B roadmap.
- [BIDS_OPENFACE_DERIVATIVES.md](BIDS_OPENFACE_DERIVATIVES.md) — layout, validation, events coupling, scan mode.
