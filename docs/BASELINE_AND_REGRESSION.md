# Smoke Baseline and Regression

This document describes a reproducible smoke regression workflow from zero.

**See also:** [WINDOWS_VERIFICATION.md](WINDOWS_VERIFICATION.md) (PowerShell asset tests, `log/` for thesis), [NATIVE_BUILD_VCPKG.md](NATIVE_BUILD_VCPKG.md) (Windows native CMake + vcpkg), [tests/README.md](../tests/README.md) (test index).

## Roles of directories

- `smoke_test/data/` - source inputs for smoke (images/videos).
- `smoke_test/baseline_output/` - **CI / git baseline:** lean regression files committed to the repository; GitHub Actions compares a **subset** via `tools/regression/baseline_manifest_ci.json` (currently `*_of_details.txt` only; see docs below).
- `smoke_test/baseline_output_local/` - **machine-local golden:** same layout as `baseline_output/`, but **not committed** (see `.gitignore`). Used to compare a fresh smoke run against outputs produced on **your** hardware without overwriting the CI baseline.
- `smoke_test/output/` - outputs of the current run under test.
- `smoke-output-for-baseline/` (optional, repo root) - unpacked artifact from workflow **Smoke baseline capture**; **gitignored** so heavy media is never committed.

`tools/run_smoke_and_compare.sh` always cleans `smoke_test/output/{img,video}` before a run.  
`smoke_test/baseline_output/` and `smoke_test/baseline_output_local/` are not modified by that script (only read for compare).

## Baseline in git and CI (preferred policy)

Regression compares only the file kinds under `smoke_test/baseline_manifest.json` (today: `*.csv`, `*.hog`, `*_of_details.txt`). Those are enough for `compare_smoke_outputs.py`; aligned bitmaps, preview images, and rendered videos are **not** part of the regression gate.

**Preferred approach:** keep a **lean** `smoke_test/baseline_output/` in the repository (paths mirror `output/`, but only the compared artifacts). This gives reproducible GitHub Actions without external downloads and avoids committing large media trees.

### Dual baseline (CI vs local machine)

| Path | Purpose | In git |
|------|---------|--------|
| `smoke_test/baseline_output/` | Gate for **merge / GitHub Actions** (aligned with `ubuntu-latest` capture when refreshed) | yes (lean) |
| `smoke_test/baseline_output_local/` | Optional **developer golden** on your CPU/Docker host | no |

- **Same gate as CI locally:** `./tools/run_smoke_and_compare.sh` with the same `MODE`, `MANIFEST`, and `ABS_TOL` as `.github/workflows/ci.yml` (defaults target `baseline_output/`).
- **Compare against your saved golden:** `./tools/run_smoke_compare_local_baseline.sh` (defaults: `BASELINE_DIR=smoke_test/baseline_output_local`, full `baseline_manifest.json`, tolerant). Refresh local golden after a good local run:

```bash
SRC=smoke_test/output DST=smoke_test/baseline_output_local ./tools/regression/sync_smoke_baseline_git.sh
```

When ingesting a CI artifact into `baseline_output/`, snapshot the **previous** lean baseline into `baseline_output_local/` first if you still want that machine as reference:

```bash
SRC=smoke_test/baseline_output DST=smoke_test/baseline_output_local ./tools/regression/sync_smoke_baseline_git.sh
SRC=smoke-output-for-baseline DST=smoke_test/baseline_output ./tools/regression/sync_smoke_baseline_git.sh
```

(Or use `./tools/regression/refresh_git_baseline_from_ci_output.sh` for the second line only.)

- **Full local snapshot** (everything under `output/`, for human inspection): `./tools/regression/bootstrap_smoke_baseline.sh`
- **Git- and CI-sized baseline** (compared files only): `./tools/regression/sync_smoke_baseline_git.sh` after a golden `./smoke_test/run_smoke.sh`

When outputs change intentionally (toolchain, model, or OpenFace behavior), regenerate smoke output, run `sync_smoke_baseline_git.sh`, and commit the updated `smoke_test/baseline_output/`.

**Drift note:** if the repository still tracks a large `smoke_test/output/` tree for convenience, its regression files can get out of date versus what the current Docker image produces. The gate compares **fresh** `output/` from `run_smoke.sh` against `baseline_output/`. After refreshing the baseline, run `./tools/run_smoke_and_compare.sh` once to confirm strict mode passes before committing.

## CI-aligned baseline (`ubuntu-latest`)

The lean files in `smoke_test/baseline_output/` are compared on GitHub Actions using `tools/regression/baseline_manifest_ci.json` and tolerant mode (see `.github/workflows/ci.yml`).

### Windows native (MSVC + vcpkg)

The **Windows native vcpkg proof** workflow (`.github/workflows/windows-native-vcpkg-proof.yml`) runs the **same Python static/unit checks** as the Linux job `native-manifest-presets`, then **native** `FaceLandmarkImg` / `FeatureExtraction` on `smoke_test/data/` and the **same** `compare_smoke_outputs.py` invocation with **`baseline_manifest_ci.json`** (no Docker). Dense `*.csv` / `*.hog` still **differ vs the Linux baseline** on Windows; the **contract** is the same as merge CI: summary `*_of_details.txt` within **`ABS_TOL`**. Entry points: `tools/windows/Run-NativeSmokeAndCompare.ps1` and `tools/windows/Run-WindowsNativeTestSuite.ps1` (see [NATIVE_BUILD_VCPKG.md](NATIVE_BUILD_VCPKG.md), [WINDOWS_VERIFICATION.md](WINDOWS_VERIFICATION.md)).

### Why `*.csv` was removed from the GitHub Actions compare

The Docker smoke job **already proves** that the image builds, the container starts, and OpenFace runs end-to-end on `smoke_test/data/` (images + short videos). The fragile part was the **next** step: treating dense **`*.csv`** as a byte-stable or `1e-5`-stable contract **across different machines in the `ubuntu-latest` pool**.

In practice we saw:

- **Smoke logs green** (models load, tracking runs, files written), but **compare red** on `*.csv` only: thousands of numeric tokens differed, with **`max_abs` far above `1e-5`** (including on video), even after refreshing the committed baseline from a **Smoke baseline capture** artifact produced on GitHub. So the failure was not “baseline forgot to update”, but **run-to-run / runner-to-runner numeric drift** on the same workflow image.
- **`*_of_details.txt` still passed** the same tolerant compare in those failures: the summary side of the run stayed aligned within `ABS_TOL` while the huge per-frame CSV streams did not.

Keeping **`*.csv`** in `baseline_manifest_ci.json` would therefore mean either **constant false reds** on CI, or **raising `ABS_TOL` to huge values** so that the gate stops meaning anything for mixed-scale columns (see [Tolerance knob (ABS_TOL)](#tolerance-knob-abstol)).

**Current CI contract:** `tools/regression/baseline_manifest_ci.json` lists **`**/*_of_details.txt` only** — CI still enforces a **numeric regression** on those summary files, which has been stable across runners, while the full **`*.csv` (+ `.hog` if desired)** regression remains **local**: `smoke_test/baseline_manifest.json`, `./tools/run_smoke_compare_local_baseline.sh`, and/or `smoke_test/baseline_output_local/` (see [Dual baseline](#dual-baseline-ci-vs-local-machine)).

**`*_of_details.txt` path lines (tolerant mode):** the first lines contain absolute `Input:` / `Input full path:` values. A git baseline captured on GitHub (`/home/runner/...`) will not byte-match a laptop or WSL run (`/mnt/c/...`), and the numeric-token stream used to include **different counts** of digits embedded in those paths. In **tolerant** mode, `tools/regression/compare_smoke_outputs.py` **replaces each such line with the same prefix plus only the path basename** before extracting numbers, so local Docker smoke can compare cleanly against the committed CI baseline. **`strict` mode is unchanged** (full-file SHA256), so path-dependent baselines still differ across machines in strict mode by design.

A baseline captured on a **different** machine than the one that produced `baseline_output/` can still fail locally on CSV strict/tolerant checks; refresh the committed baseline from a GA artifact when you intentionally change outputs (see below).

**Preferred refresh when CI compare fails but the pipeline is correct:** treat the GitHub-hosted runner as the source of truth for the committed baseline.

1. Run **Smoke baseline capture** on GitHub (`.github/workflows/smoke-baseline-artifact.yml`) manually via **Actions → Smoke baseline capture → Run workflow** (`workflow_dispatch` only; it does not run on push). The workflow file must exist on the **default branch** for that button to appear. It builds the same Docker image as CI, starts `openface`, runs `./smoke_test/run_smoke.sh`, and uploads an artifact named **`smoke-output-for-baseline`** with the `smoke_test/output/` tree (`img/`, `video/` at the zip root).

2. **Download the artifact:** open the successful workflow run → scroll to **Artifacts** at the bottom of the summary page → click **`smoke-output-for-baseline`** (downloads a zip). Unzip locally; you should see top-level folders `img/` and `video/`.

3. From the repository root, apply it to the git-oriented baseline (copies only `*.csv`, `*.hog`, `*_of_details.txt` into `smoke_test/baseline_output/`):

```bash
./tools/regression/refresh_git_baseline_from_ci_output.sh /path/to/unzipped/dir
# If the artifact is unpacked at repo root as ./smoke-output-for-baseline/ (gitignored):
#   SRC=smoke-output-for-baseline DST=smoke_test/baseline_output ./tools/regression/sync_smoke_baseline_git.sh
```

   Equivalent: `SRC=/path/to/unzipped/dir ./tools/regression/sync_smoke_baseline_git.sh`

4. Review `git diff smoke_test/baseline_output`, then commit the updated files.

5. Optional local sanity check using the **same** compare settings as CI:

```bash
export MODE=tolerant ABS_TOL=1e-5
export MANIFEST="$(pwd)/tools/regression/baseline_manifest_ci.json"
./tools/run_smoke_and_compare.sh
```

   A pass on your machine is not guaranteed after a CI-only baseline refresh (your Docker host may still differ slightly), but **GitHub Actions** should go green once the baseline matches the runner that produced the artifact.

## Native toolchain (vcpkg / MSVC) vs Docker baseline

If you rebuild OpenFace **natively** on Windows with **vcpkg** (see [NATIVE_BUILD_VCPKG.md](NATIVE_BUILD_VCPKG.md)), treat regression the same way as after any compiler/OpenCV change: run smoke, then compare with **`ABS_TOL`** and refresh **`baseline_output_local/`** (or the git baseline if you intentionally adopt new golden numbers). Dense **`*.csv`** may drift slightly while **`*_of_details.txt`** stays within tolerance; **`compare_smoke_outputs.py`** compares CSVs as **numeric token streams** (not yet column-keyed by header). For **`*_of_details.txt`**, tolerant mode also **normalizes `Input:` / `Input full path:`** to basename-only so CI vs WSL paths do not false-fail the gate (see note under [CI-aligned baseline](#ci-aligned-baseline-ubuntu-latest)).

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

### Tolerance knob (ABS_TOL)

`compare_smoke_outputs.py` in tolerant mode walks each file, extracts **every numeric token** (integers and floats) in **file order**, pairs them with the baseline token stream, and requires `abs(actual - baseline) <= ABS_TOL` (with a paired NaN exception). There is **one** threshold for **all** tokens in that file — no per-column logic. The environment variable `ABS_TOL` is passed through from `run_smoke_and_compare.sh` to `compare_smoke_outputs.py --abs-tol` (GitHub Actions sets it in `.github/workflows/ci.yml`).

**When raising `ABS_TOL` helps:** tiny platform drift (for example `1e-6` vs `1e-5` vs `1e-4`) on **small-magnitude** numbers, or on summary files where all quantities stay in a similar range.

**When a larger `ABS_TOL` is a poor fix for full `FeatureExtraction` / `FaceLandmarkImg` CSV:** those CSVs mix **very different scales** in one stream (for example AU-like values near 0…1, pixel coordinates in the hundreds, pose translation in hundreds or more). A single absolute tolerance either stays tight and **fails on large columns** when runners differ slightly, or becomes huge and **stops protecting small columns** (you accept large silent errors in AU-like fields).

Empirically, on **GitHub-hosted `ubuntu-latest`**, two runs with the **same** Docker image can still yield **large** `max_abs` on dense CSV (for example order **1** on still images and **10+** on video rows) because of **runner / CPU / math library variability**, not necessarily because smoke is broken.

**Policy in this repository:** CI uses `tools/regression/baseline_manifest_ci.json`, which compares **`*_of_details.txt` only** with `ABS_TOL=1e-5` (see `.github/workflows/ci.yml`). That keeps the gate meaningful across the runner pool. **Full CSV (+ optional `.hog`) regression** stays a **local** concern: use `smoke_test/baseline_manifest.json` and/or `./tools/run_smoke_compare_local_baseline.sh` against `smoke_test/baseline_output_local/` (see [Dual baseline](#dual-baseline-ci-vs-local-machine) above).

**If CI ever flakes on `*_of_details.txt` only:** increase `ABS_TOL` in small steps (for example `1e-4`, then `1e-3`) in `ci.yml` and mirror the same values when you run the optional local sanity command in [CI-aligned baseline](#ci-aligned-baseline-ubuntu-latest). Do **not** expect a single larger `ABS_TOL` to make dense per-frame CSV reliable on CI without also changing compare logic (for example column-aware or relative tolerance — not implemented today).

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
