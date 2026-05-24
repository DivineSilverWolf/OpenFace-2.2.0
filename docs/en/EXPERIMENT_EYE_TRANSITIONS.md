# Experiment: sustained eye open / closed detection

This document describes the `Experiment/` workflow: videos where a participant alternates **sustained** eye-closed and eye-open phases (~2 minutes each), and the tool that predicts transition timestamps from OpenFace CSV.

## Experiment protocol

- Recording begins with **eyes open**.
- Six labelled transitions per session (see manual `Experiment/*.txt`):
  - **S1** — eyes closed (start of a long closed phase)
  - **S2** — eyes open (start of a long open phase)
- Phases last about **119–121 seconds**. Brief blinks (1–2 s) are **not** annotated.

Example manual file:

```text
# S1 - закрыл глаза
# S2 - открыл глаза
00:26 - S1
02:25 - S2
...
```

## OpenFace inputs

Run `FeatureExtraction` on each `.mp4` (Docker smoke setup or `tools/experiment/run_experiment_extraction.sh`).  
Outputs live in `Experiment/<video_basename>/`.

Recommended lean flags (landmarks + AUs only):

```bash
FeatureExtraction -f <video.mp4> -out_dir <out_dir> -quiet -2Dfp -aus
```

## CSV columns used by the detector

The Python tool reads the sequence CSV produced by `FeatureExtraction`:

| Column(s) | Meaning |
|-----------|---------|
| `timestamp` | Time in seconds (video timeline) |
| `success` | `1` = face tracked; other rows are skipped |
| `x_37`, `y_37`, `x_41`, `y_41` | Left eye corners (68-point model) |
| `x_43`, `y_43`, `x_47`, `y_47` | Right eye corners |
| `AU45_r` | AU45 intensity (blink); peaks mark closure onset |

**Derived signals**

1. **Eyelid opening** — mean of vertical distances (37–41) and (43–47) in pixels; larger values indicate more open eyes.
2. **AU45** — used to locate closure onsets (S1), especially the first transition.

No gaze vectors, HOG, or full landmark grid are required for detection.

## Algorithm (`detect_eye_transitions.py`)

1. **Aggregate** per-frame values to **1 s medians** (reduces noise and single-frame blinks).
2. **First S1** — earliest local maximum of `AU45_r` above 0.85 in the first ~50 s.
3. **Protocol grid** — expected times: first S1, then +119.5 s for S2, +239 s for next S1, etc. (six events total).
4. **Refine** each event in a **±6 s** window around the grid time:
   - **S1:** maximise `AU45_r` minus a time penalty (stay near the grid).
   - **S2:** maximise eyelid opening minus the same penalty.
5. Write `*_detected.txt` in the same format as manual annotations.

Short closures inside a window do not win over the grid anchor unless they are the strongest AU45 peak near the expected long transition.

## Usage

```bash
# All videos + comparison report (default |Δt| tolerance 5 s)
./tools/experiment/run_detect_all.sh

# Custom tolerance for the report only
TOLERANCE_SEC=3 ./tools/experiment/run_detect_all.sh

# Single CSV
python3 tools/experiment/detect_eye_transitions.py \
  Experiment/Co_Sin_001_own_face/Co_Sin_001_own_face.csv

# Compare to manual labels
python3 tools/experiment/compare_eye_transitions.py \
  --tolerance-sec 5 \
  --report Experiment/REPORT.md
```

## Evaluation

`compare_eye_transitions.py` pairs manual and detected events in order (same label).  
**Success:** `|Δt| ≤ tolerance` (default **5 s**). Change with `--tolerance-sec` / `--dt-tol`.

See `Experiment/REPORT.md` for the latest run on the reference clips.

## Related docs

- [Integration time model (`timestamp` in CSV)](INTEGRATION_LSL_BIDS.md)
- [Smoke / Docker setup](SETUP_WINDOWS11_WSL2.md)
- [Experiment folder README](../../Experiment/README.md)
