"""Load OpenFace CSV (FeatureExtraction) with stdlib only."""

from __future__ import annotations

import csv
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Sequence


@dataclass(frozen=True)
class LoadedCsv:
    headers: list[str]
    rows: list[list[str]]
    timestamp_index: int | None


def load_openface_csv(path: Path) -> LoadedCsv:
    text = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if not text:
        raise ValueError(f"Empty CSV: {path}")
    reader = csv.reader(text)
    try:
        headers = next(reader)
    except StopIteration as e:
        raise ValueError(f"No header row: {path}") from e
    rows = [row for row in reader if any(cell.strip() for cell in row)]
    ts_idx = None
    for i, h in enumerate(headers):
        if h.strip() == "timestamp":
            ts_idx = i
            break
    return LoadedCsv(headers=headers, rows=rows, timestamp_index=ts_idx)


def column_indices(headers: Sequence[str], names: Sequence[str]) -> list[int]:
    hmap = {h: i for i, h in enumerate(headers)}
    missing = [n for n in names if n not in hmap]
    if missing:
        raise KeyError(f"CSV missing columns: {missing}")
    return [hmap[n] for n in names]


def parse_float_row(row: Sequence[str], indices: Sequence[int]) -> list[float]:
    out: list[float] = []
    for i in indices:
        cell = row[i].strip() if i < len(row) else ""
        if cell == "":
            out.append(float("nan"))
        else:
            out.append(float(cell))
    return out


def timestamps_seconds(loaded: LoadedCsv) -> list[float] | None:
    if loaded.timestamp_index is None:
        return None
    idx = loaded.timestamp_index
    vals: list[float] = []
    for row in loaded.rows:
        if idx >= len(row):
            continue
        cell = row[idx].strip()
        if not cell:
            continue
        vals.append(float(cell))
    return vals or None


def estimate_nominal_srate(timestamps: Sequence[float] | None, fps_hint: float | None) -> float:
    if fps_hint is not None and fps_hint > 0:
        return float(fps_hint)
    if not timestamps or len(timestamps) < 2:
        return 30.0
    deltas = [b - a for a, b in zip(timestamps, timestamps[1:]) if (b - a) > 0]
    if not deltas:
        return 30.0
    med = statistics.median(deltas)
    if med <= 0:
        return 30.0
    return 1.0 / med


def iter_sample_times(timestamps: list[float] | None, n_rows: int, nominal_srate: float) -> Iterator[float]:
    if timestamps is not None and len(timestamps) == n_rows:
        for t in timestamps:
            yield t
        return
    dt = 1.0 / nominal_srate if nominal_srate > 0 else 1.0 / 30.0
    for i in range(n_rows):
        yield i * dt
