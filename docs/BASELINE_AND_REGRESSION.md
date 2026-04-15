# Smoke Baseline and Regression

This document describes a reproducible smoke regression workflow from zero.

## Roles of directories

- `smoke_test/data/` - source inputs for smoke (images/videos).
- `smoke_test/baseline_output/` - frozen reference outputs used as baseline.
- `smoke_test/output/` - outputs of the current run under test.

`tools/run_smoke_and_compare.sh` always cleans `smoke_test/output/{img,video}` before a run.  
`smoke_test/baseline_output/` is not touched by this script.

## What happens before compare (important)

`./tools/run_smoke_and_compare.sh` is not just "compare"; it also does:

1. normalizes `DATA_MOUNT` path (Windows path -> Linux mount path when needed);
2. validates that baseline exists and contains regression files;
3. validates `ACTUAL_DIR != BASELINE_DIR`;
4. cleans `smoke_test/output/img` and `smoke_test/output/video`;
5. runs `docker compose build`;
6. runs `docker compose up -d --force-recreate openface`;
7. runs `./smoke_test/run_smoke.sh`;
8. runs `compare_smoke_outputs.py`.

So yes, there are required actions before the actual compare, and they are intentional for reproducibility.

## Step 0: Prepare baseline once (before reengineering, when baseline is empty)

Use existing `smoke_test/data/` inputs to generate a golden run and then freeze it to `baseline_output`.

1) Build/start container and run smoke once (writes to `smoke_test/output/`):

```bash
docker compose up -d --force-recreate openface
./smoke_test/run_smoke.sh
```

2) Snapshot `output/` into baseline:

```bash
./tools/regression/bootstrap_smoke_baseline.sh
```

If you need to refresh baseline intentionally (for example after toolchain/build change), use:

```bash
FORCE=1 ./tools/regression/bootstrap_smoke_baseline.sh
```

`bootstrap_smoke_baseline.sh` copies only files from the current `output/` tree to `baseline_output/`.

## Step 1: Make your code changes

Do your reengineering changes in allowed areas.

## Step 2: Validate against baseline after changes

Run the full pipeline:

```bash
./tools/run_smoke_and_compare.sh
```

This executes:
- `docker compose build`
- smoke run on `smoke_test/data/` into `smoke_test/output/`
- compare `smoke_test/output/` vs `smoke_test/baseline_output/`

## Real "from empty baseline" example

If `smoke_test/baseline_output/` is empty, the first run fails fast with:

- `ERROR: baseline has no *.csv under .../smoke_test/baseline_output`

This is expected. The correct flow is:

1) create baseline from `smoke_test/data/` via `run_smoke.sh` + `bootstrap_smoke_baseline.sh`;
2) make changes;
3) run `run_smoke_and_compare.sh`.

## Comparison modes

### Strict (byte-for-byte)

Default mode (`MODE=strict`):

```bash
MODE=strict ./tools/run_smoke_and_compare.sh
```

### Tolerant numeric mode

For micro-differences from compiler/libs:

```bash
MODE=tolerant ABS_TOL=1e-6 ./tools/run_smoke_and_compare.sh
```

In tolerant mode:
- `.csv` and `*_of_details.txt` are compared numerically with `abs(a-b) <= ABS_TOL`.
- `.hog` remains strict (binary file).

## `baseline_manifest.json`: what it is and how to use it

File: `smoke_test/baseline_manifest.json`

Purpose:
- controls **which file types/patterns** are included in regression compare;
- optionally pins baseline file hashes (`sha256`) to detect baseline tampering.

Current schema:

```json
{
  "version": 1,
  "description": "Smoke regression baseline manifest.",
  "patterns": ["**/*.csv", "**/*.hog", "**/*_of_details.txt"],
  "sha256": {}
}
```

How fields work:
- `patterns` - glob patterns for target files to compare.
- `sha256` - optional map `relative/path -> sha256`.
  - empty `{}` means "do not enforce hash pinning".
  - non-empty map enforces that baseline files match declared hashes before compare starts.

## `compare_smoke_outputs.py` parameters

Script: `tools/regression/compare_smoke_outputs.py`

Required:
- `--actual-dir PATH` - tested outputs (usually `smoke_test/output`).
- `--baseline-dir PATH` - baseline outputs (usually `smoke_test/baseline_output`).
- `--manifest PATH` - manifest JSON (`smoke_test/baseline_manifest.json`).

Optional:
- `--mode strict|tolerant` (default: `strict`).
- `--abs-tol FLOAT` (default: `1e-6`, used in tolerant mode).

Examples:

```bash
python3 ./tools/regression/compare_smoke_outputs.py \
  --actual-dir ./smoke_test/output \
  --baseline-dir ./smoke_test/baseline_output \
  --manifest ./smoke_test/baseline_manifest.json \
  --mode strict
```

```bash
python3 ./tools/regression/compare_smoke_outputs.py \
  --actual-dir ./smoke_test/output \
  --baseline-dir ./smoke_test/baseline_output \
  --manifest ./smoke_test/baseline_manifest.json \
  --mode tolerant \
  --abs-tol 1e-6
```
