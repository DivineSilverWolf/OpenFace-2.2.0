from __future__ import annotations

import csv
from bisect import bisect_right
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class EventsTable:
    columns: list[str]
    rows: list[list[Any]]
    sidecar: dict[str, Any] | None


def read_events_tsv(path: Path) -> EventsTable:
    with path.open(newline="", encoding="utf-8", errors="replace") as f:
        sample = f.read(4096)
        f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters="\t,")
        except csv.Error:
            dialect = csv.excel_tab
        reader = csv.reader(f, dialect)
        header = next(reader)
        cols = [c.strip() for c in header]
        if "onset" not in cols:
            raise ValueError(f"events.tsv must contain 'onset' column: {path}")
        rows: list[list[Any]] = []
        for row in reader:
            if not row or all(c == "" for c in row):
                continue
            if len(row) < len(cols):
                row = row + [""] * (len(cols) - len(row))
            out: list[Any] = []
            for i, c in enumerate(row[: len(cols)]):
                name = cols[i]
                if name == "onset" or name == "duration":
                    try:
                        out.append(float(c))
                    except ValueError:
                        out.append(c)
                else:
                    out.append(c)
            rows.append(out)
    return EventsTable(columns=cols, rows=rows, sidecar=None)


def merge_events_asof_backward(
    *,
    of_columns: list[str],
    of_rows: list[list[Any]],
    time_idx: int,
    events: EventsTable,
) -> tuple[list[str], list[list[Any]]]:
    """Append event columns using last event with onset <= openface_timestamp."""
    ev_cols = events.columns
    onset_i = ev_cols.index("onset")
    onsets = [float(r[onset_i]) for r in events.rows]
    new_cols = list(of_columns) + [f"event_{c}" for c in ev_cols]
    new_rows: list[list[Any]] = []
    for r in of_rows:
        t = float(r[time_idx])
        j = bisect_right(onsets, t) - 1
        if j < 0:
            ev_vals = ["" for _ in ev_cols]
        else:
            ev_vals = list(events.rows[j])
        new_rows.append(list(r) + ev_vals)
    return new_cols, new_rows


def events_relative_path(bids_root: Path, events_path: Path) -> str:
    try:
        return events_path.resolve().relative_to(bids_root.resolve()).as_posix()
    except ValueError:
        return events_path.resolve().as_posix()
