#!/usr/bin/env python3
"""Compare detected eye transitions to manual Experiment/*.txt annotations."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from detect_eye_transitions import Transition, detect_transitions, parse_manual_txt

METHOD_SUMMARY = """\
## Method (auto detection)

The detector (`tools/experiment/detect_eye_transitions.py`) uses OpenFace **FeatureExtraction** CSV:

| Signal | CSV columns | Role |
|--------|-------------|------|
| Eyelid opening | `x_37`,`y_37`,`x_41`,`y_41` and `x_43`,`y_43`,`x_47`,`y_47` | Mean vertical lid distance (px); higher ≈ eyes open |
| Blink / closure | `AU45_r` | Peak at sustained eye-closure onset |
| Frame time | `timestamp` | Seconds in the video |
| Quality | `success` | Only rows with `success == 1` are used |

**Protocol:** recording starts with eyes open; six transitions alternate **S1** (closed) / **S2** (open);
each phase lasts ~119–121 s. Short blinks are not separate events.

**Algorithm (short):**

1. Bin features to 1 s medians.
2. Find first **S1**: earliest local AU45 peak in the first ~50 s.
3. Build a time grid with phase 119.5 s (configurable).
4. Refine each event in a ±6 s window: maximise AU45 (S1) or eyelid opening (S2),
   minus a penalty for distance from the grid (keeps alignment, ignores brief blinks).
"""


@dataclass
class MatchStats:
    name: str
    manual: list[Transition]
    detected: list[Transition]
    errors_sec: list[float]
    matched: int
    tolerance_sec: float


def compare_one(
    name: str,
    manual_path: Path,
    csv_path: Path,
    *,
    tolerance_sec: float,
    **detect_kw,
) -> MatchStats:
    manual = parse_manual_txt(manual_path)
    detected = detect_transitions(csv_path, **detect_kw)
    errors: list[float] = []
    j = 0
    for m in manual:
        while j < len(detected) and detected[j].label != m.label:
            j += 1
        if j < len(detected):
            errors.append(abs(detected[j].seconds - m.seconds))
            j += 1
        else:
            errors.append(float("nan"))
    matched = sum(1 for e in errors if e == e and e <= tolerance_sec)
    return MatchStats(name, manual, detected, errors, matched, tolerance_sec)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--experiment-dir",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "Experiment",
    )
    ap.add_argument(
        "--tolerance-sec",
        "--dt-tol",
        type=float,
        default=5.0,
        dest="tolerance_sec",
        help="Success if same label and |Δt| ≤ this value (default: 5 s).",
    )
    ap.add_argument("--phase-sec", type=float, default=119.5)
    ap.add_argument("--refine-window-sec", type=float, default=6.0)
    ap.add_argument("--report", type=Path, help="Write markdown report to this path")
    args = ap.parse_args()

    exp = args.experiment_dir
    bases = sorted({p.stem for p in exp.glob("Co_Sin_001_*.mp4")})
    tol = args.tolerance_sec
    lines = [
        "# Experiment eye-transition comparison\n\n",
        METHOD_SUMMARY,
        f"\n**Success criterion:** same label (S1/S2) and |Δt| ≤ **{tol:g} s**.\n\n",
    ]
    detect_kw = {
        "phase_sec": args.phase_sec,
        "refine_window_sec": args.refine_window_sec,
        "max_events": 6,
    }

    total_matched = 0
    total_manual = 0
    for base in bases:
        manual_path = exp / f"{base}.txt"
        csv_path = exp / base / f"{base}.csv"
        if not csv_path.is_file():
            lines.append(f"## {base}\n\nCSV missing: `{csv_path}`\n")
            continue
        st = compare_one(
            base, manual_path, csv_path, tolerance_sec=tol, **detect_kw
        )
        total_matched += st.matched
        total_manual += len(st.manual)
        lines.append(f"## {base}\n")
        lines.append(f"- Manual events: {len(st.manual)}\n")
        lines.append(f"- Detected events: {len(st.detected)}\n")
        lines.append(
            f"- Matched within {tol:g} s: {st.matched}/{len(st.manual)}\n\n"
        )
        lines.append("| Manual | Detected (same label) | Δt (s) | OK |\n")
        lines.append("|--------|------------------------|--------|----|\n")
        j = 0
        for m in st.manual:
            while j < len(st.detected) and st.detected[j].label != m.label:
                j += 1
            if j < len(st.detected):
                d = st.detected[j]
                dt = d.seconds - m.seconds
                ok = "yes" if abs(dt) <= tol else "no"
                lines.append(
                    f"| {m.label} {_fmt(m.seconds)} | {d.label} {_fmt(d.seconds)} "
                    f"| {dt:+.1f} | {ok} |\n"
                )
                j += 1
            else:
                lines.append(f"| {m.label} {_fmt(m.seconds)} | — | — | no |\n")
        if len(st.detected) > len(st.manual):
            lines.append("\nExtra detected:\n")
            for d in st.detected[len(st.manual) :]:
                lines.append(f"- {d.label} {_fmt(d.seconds)}\n")
        lines.append("\n")

    lines.append(
        f"## Total\n\n**{total_matched}/{total_manual}** events within {tol:g} s.\n"
    )

    report = "".join(lines)
    print(report)
    if args.report:
        args.report.write_text(report, encoding="utf-8")
        print(f"Report written to {args.report}")


def _fmt(seconds: float) -> str:
    total = int(round(seconds))
    m, s = divmod(total, 60)
    return f"{m:02d}:{s:02d}"


if __name__ == "__main__":
    main()
