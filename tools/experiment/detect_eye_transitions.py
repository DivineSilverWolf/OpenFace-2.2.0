#!/usr/bin/env python3
"""
Detect sustained eye open/closed transitions from OpenFace FeatureExtraction CSV.

Protocol (Experiment): eyes start open; subject closes for ~2 min (S1), opens (S2),
repeats with ~119-121 s per phase. Short blinks are ignored via smoothing and a
local refinement window around each expected transition.

Output format matches Experiment/*.txt:
  # S1 - закрыл глаза
  # S2 - открыл глаза
  MM:SS - S1|S2
"""
from __future__ import annotations

import argparse
import csv
import math
import re
import statistics
from collections import deque
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Transition:
    seconds: float
    label: str  # "S1" or "S2"


def _pt(row: dict[str, str], i: int) -> tuple[float, float]:
    x = row.get(f"x_{i}")
    y = row.get(f"y_{i}")
    if x is None or y is None or x == "" or y == "":
        raise ValueError(f"missing landmark x_{i}/y_{i}")
    return float(x), float(y)


def _dist(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def eyelid_opening(row: dict[str, str]) -> float:
    """Mean vertical eyelid separation (px) for left/right eye (68-point model)."""
    return (_dist(_pt(row, 37), _pt(row, 41)) + _dist(_pt(row, 43), _pt(row, 47))) / 2.0


def au45_intensity(row: dict[str, str]) -> float:
    v = row.get("AU45_r")
    if v is None or v == "":
        return 0.0
    return float(v)


@dataclass
class FrameSeries:
    times: list[float]
    opening: list[float]
    au45: list[float]


def read_series(csv_path: Path) -> FrameSeries:
    times: list[float] = []
    opening: list[float] = []
    au45: list[float] = []
    with csv_path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("success") != "1":
                continue
            try:
                op = eyelid_opening(row)
            except ValueError:
                continue
            times.append(float(row["timestamp"]))
            opening.append(op)
            au45.append(au45_intensity(row))
    if not times:
        raise SystemExit(f"No successful frames in {csv_path}")
    return FrameSeries(times, opening, au45)


def bin_median_series(
    series: FrameSeries, *, bin_sec: float = 1.0
) -> FrameSeries:
    t0 = series.times[0]
    bins_op: dict[int, list[float]] = {}
    bins_au: dict[int, list[float]] = {}
    for t, op, au in zip(series.times, series.opening, series.au45):
        key = int((t - t0) // bin_sec)
        bins_op.setdefault(key, []).append(op)
        bins_au.setdefault(key, []).append(au)
    out_t: list[float] = []
    out_op: list[float] = []
    out_au: list[float] = []
    for key in sorted(bins_op):
        out_t.append(t0 + (key + 0.5) * bin_sec)
        out_op.append(statistics.median(bins_op[key]))
        out_au.append(statistics.median(bins_au[key]))
    return FrameSeries(out_t, out_op, out_au)


def rolling_median(values: list[float], window: int) -> list[float]:
    out: list[float] = []
    buf: deque[float] = deque()
    for v in values:
        buf.append(v)
        if len(buf) > window:
            buf.popleft()
        out.append(statistics.median(buf))
    return out


def _percentile(sorted_vals: list[float], p: float) -> float:
    if not sorted_vals:
        return 0.0
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    idx = (len(sorted_vals) - 1) * p
    lo = int(math.floor(idx))
    hi = int(math.ceil(idx))
    if lo == hi:
        return sorted_vals[lo]
    frac = idx - lo
    return sorted_vals[lo] * (1.0 - frac) + sorted_vals[hi] * frac


def _interp(series: FrameSeries, t: float) -> tuple[float, float]:
    if t <= series.times[0]:
        return series.opening[0], series.au45[0]
    if t >= series.times[-1]:
        return series.opening[-1], series.au45[-1]
    lo = 0
    hi = len(series.times) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if series.times[mid] <= t:
            lo = mid
        else:
            hi = mid
    t0, t1 = series.times[lo], series.times[hi]
    w = (t - t0) / (t1 - t0) if t1 > t0 else 0.0
    op = series.opening[lo] * (1.0 - w) + series.opening[hi] * w
    au = series.au45[lo] * (1.0 - w) + series.au45[hi] * w
    return op, au


def _is_au45_peak(series: FrameSeries, i: int) -> bool:
    if i <= 0 or i >= len(series.times) - 1:
        return False
    return series.au45[i] >= series.au45[i - 1] and series.au45[i] >= series.au45[i + 1]


def find_first_s1(series: FrameSeries, *, search_end: float = 50.0) -> float:
    """First closure: earliest AU45 peak in the opening segment (not the strongest later blink)."""
    idx = [i for i, t in enumerate(series.times) if t <= search_end]
    if not idx:
        idx = list(range(min(50, len(series.times))))
    peaks = [
        i
        for i in idx
        if series.au45[i] > 0.85 and _is_au45_peak(series, i)
    ]
    if peaks:
        return series.times[min(peaks, key=lambda i: series.times[i])]
    smooth = rolling_median(series.opening, window=5)
    best_au = max(idx, key=lambda i: series.au45[i])
    if series.au45[best_au] > 0.5:
        return series.times[best_au]
    return series.times[min(idx, key=lambda i: smooth[i])]


def estimate_phase_sec(series: FrameSeries, t_first: float) -> float:
    """Median S1→S1 interval from AU45 peaks after the first closure."""
    peaks: list[float] = []
    for i in range(1, len(series.times) - 1):
        t = series.times[i]
        if t < t_first + 30.0:
            continue
        if series.au45[i] < 0.8:
            continue
        if series.au45[i] < series.au45[i - 1] or series.au45[i] < series.au45[i + 1]:
            continue
        if peaks and (t - peaks[-1]) < 80.0:
            continue
        peaks.append(t)
    if len(peaks) >= 2:
        gaps = [peaks[i + 1] - peaks[i] for i in range(len(peaks) - 1)]
        cycle = statistics.median(gaps)
        # AU45 peaks align with S1; gap is two phases (closed + open).
        return cycle / 2.0 if cycle > 150.0 else cycle
    return 119.5


def refine_transition(
    series: FrameSeries,
    expected: float,
    *,
    window_sec: float = 6.0,
    label: str,
    time_penalty: float = 0.35,
) -> float:
    """Pick timestamp in a narrow window; score favours signal + proximity to grid."""
    t0 = max(series.times[0], expected - window_sec)
    t1 = min(series.times[-1], expected + window_sec)
    indices = [i for i, t in enumerate(series.times) if t0 <= t <= t1]
    if not indices:
        return expected

    smooth_op = rolling_median(series.opening, window=5)

    def score(i: int, signal: float) -> float:
        return signal - time_penalty * abs(series.times[i] - expected)

    if label == "S1":
        best_i = max(indices, key=lambda i: score(i, series.au45[i]))
    else:
        best_i = max(indices, key=lambda i: score(i, smooth_op[i]))
    return series.times[best_i]


def detect_transitions(
    csv_path: Path,
    *,
    bin_sec: float = 1.0,
    phase_sec: float | None = None,
    refine_window_sec: float = 6.0,
    first_s1_search_sec: float = 50.0,
    max_events: int = 6,
) -> list[Transition]:
    raw = read_series(csv_path)
    series = bin_median_series(raw, bin_sec=bin_sec)
    duration = series.times[-1]

    t_first = find_first_s1(series, search_end=first_s1_search_sec)
    period = phase_sec if phase_sec is not None else 119.5

    transitions: list[Transition] = []
    k = 0
    while len(transitions) < max_events:
        t_s1 = t_first + k * 2 * period
        t_s2 = t_first + period + k * 2 * period
        if t_s1 > duration + refine_window_sec:
            break
        if t_s1 <= duration:
            transitions.append(
                Transition(
                    refine_transition(
                        series, t_s1, window_sec=refine_window_sec, label="S1"
                    ),
                    "S1",
                )
            )
        if len(transitions) >= max_events:
            break
        if t_s2 <= duration:
            transitions.append(
                Transition(
                    refine_transition(
                        series, t_s2, window_sec=refine_window_sec, label="S2"
                    ),
                    "S2",
                )
            )
        k += 1

    return transitions


def format_mmss(seconds: float) -> str:
    total = int(round(seconds))
    m, s = divmod(total, 60)
    return f"{m:02d}:{s:02d}"


def write_txt(path: Path, transitions: list[Transition]) -> None:
    lines = [
        "# S1 - закрыл глаза",
        "# S2 - открыл глаза",
    ]
    for tr in transitions:
        lines.append(f"{format_mmss(tr.seconds)} - {tr.label}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_manual_txt(path: Path) -> list[Transition]:
    out: list[Transition] = []
    pat = re.compile(r"^\s*(\d{1,2}):(\d{2})\s*-\s*(S[12])\s*$")
    for line in path.read_text(encoding="utf-8").splitlines():
        m = pat.match(line)
        if m:
            mm, ss, label = m.groups()
            out.append(Transition(int(mm) * 60 + int(ss), label))
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("csv", type=Path, help="OpenFace FeatureExtraction CSV")
    ap.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output .txt (default: <csv_stem>_detected.txt beside csv)",
    )
    ap.add_argument(
        "--phase-sec",
        type=float,
        default=None,
        help="Seconds per open/closed phase (default: estimate from AU45 peaks).",
    )
    ap.add_argument("--refine-window-sec", type=float, default=10.0)
    ap.add_argument(
        "--max-events",
        type=int,
        default=6,
        help="Stop after this many transitions (protocol uses 6).",
    )
    args = ap.parse_args()

    transitions = detect_transitions(
        args.csv,
        phase_sec=args.phase_sec,
        refine_window_sec=args.refine_window_sec,
        max_events=args.max_events,
    )
    out = args.output or args.csv.with_name(args.csv.stem + "_detected.txt")
    write_txt(out, transitions)
    print(f"Wrote {len(transitions)} transitions to {out}")
    for tr in transitions:
        print(f"  {format_mmss(tr.seconds)} - {tr.label}")


if __name__ == "__main__":
    main()
