# Smoke Baseline and Regression

This document describes a reproducible smoke regression workflow from zero.

## Roles of directories

- `smoke_test/data/` - source inputs for smoke (images/videos).
- `smoke_test/baseline_output/` - frozen reference outputs used as baseline.
- `smoke_test/output/` - outputs of the current run under test.

`tools/run_smoke_and_compare.sh` always cleans `smoke_test/output/{img,video}` before a run.  
`smoke_test/baseline_output/` is not touched by this script.

## Baseline in git and CI (preferred policy)

Regression compares only the file kinds under `smoke_test/baseline_manifest.json` (today: `*.csv`, `*.hog`, `*_of_details.txt`). Those are enough for `compare_smoke_outputs.py`; aligned bitmaps, preview images, and rendered videos are **not** part of the regression gate.

**Preferred approach:** keep a **lean** `smoke_test/baseline_output/` in the repository (paths mirror `output/`, but only the compared artifacts). This gives reproducible GitHub Actions without external downloads and avoids committing large media trees.

- **Full local snapshot** (everything under `output/`, for human inspection): `./tools/regression/bootstrap_smoke_baseline.sh`
- **Git- and CI-sized baseline** (compared files only): `./tools/regression/sync_smoke_baseline_git.sh` after a golden `./smoke_test/run_smoke.sh`

When outputs change intentionally (toolchain, model, or OpenFace behavior), regenerate smoke output, run `sync_smoke_baseline_git.sh`, and commit the updated `smoke_test/baseline_output/`.

**Drift note:** if the repository still tracks a large `smoke_test/output/` tree for convenience, its regression files can get out of date versus what the current Docker image produces. The gate compares **fresh** `output/` from `run_smoke.sh` against `baseline_output/`. After refreshing the baseline, run `./tools/run_smoke_and_compare.sh` once to confirm strict mode passes before committing.

## What happens before compare (important)

`./tools/run_smoke_and_compare.sh` is not just "compare"; it also does:

1. normalizes `DATA_MOUNT` via `tools/smoke_data_mount.sh` (Windows-style path → path Docker accepts, when `cygpath`/`wslpath` is available);
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
export DATA_MOUNT="$(pwd)/smoke_test"
./tools/smoke_docker_up.sh
./smoke_test/run_smoke.sh
```

`DATA_MOUNT` must be the same when the container is created and when `run_smoke.sh` runs. Using `./tools/smoke_docker_up.sh` (instead of raw `docker compose up`) applies the same path normalization as `run_smoke.sh`, which avoids **invalid volume specification** when the shell accidentally passes a `C:\...` path (for example PowerShell expanding `$(pwd)` before bash).

If they still differ (for example, compose was started with a different `.env` value), `run_smoke.sh` fails fast with a clear mismatch error.

More detail (including PowerShell + WSL): `docs/SETUP_WINDOWS11_WSL2.md`.

2) Snapshot `output/` into baseline:

```bash
./tools/regression/bootstrap_smoke_baseline.sh
```

If you need to refresh baseline intentionally (for example after toolchain/build change), use:

```bash
FORCE=1 ./tools/regression/bootstrap_smoke_baseline.sh
```

`bootstrap_smoke_baseline.sh` copies the entire current `output/` tree to `baseline_output/` (large; useful locally).

For commits and CI, prefer `./tools/regression/sync_smoke_baseline_git.sh` instead (see [Baseline in git and CI](#baseline-in-git-and-ci-preferred-policy)).

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

1) create baseline from `smoke_test/data/` via `run_smoke.sh`, then either `bootstrap_smoke_baseline.sh` (full tree) or `sync_smoke_baseline_git.sh` (compared files only, for git/CI);
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
