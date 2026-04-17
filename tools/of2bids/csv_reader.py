from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class OpenFaceTable:
    """Rows from an OpenFace FeatureExtraction CSV."""

    columns: list[str]
    rows: list[list[Any]]
    is_sequence: bool


def read_openface_csv(path: Path) -> OpenFaceTable:
    with path.open(newline="", encoding="utf-8", errors="replace") as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration as e:
            raise ValueError(f"empty csv: {path}") from e
        cols = [c.strip() for c in header]
        is_sequence = "timestamp" in cols and "success" in cols
        rows: list[list[Any]] = []
        for row in reader:
            if not row or all(c == "" for c in row):
                continue
            # Pad short rows
            if len(row) < len(cols):
                row = row + [""] * (len(cols) - len(row))
            conv: list[Any] = []
            for i, cell in enumerate(row[: len(cols)]):
                name = cols[i]
                if name in {"frame", "face_id", "face", "success"}:
                    try:
                        conv.append(int(float(cell)))
                    except ValueError:
                        conv.append(cell)
                elif name in {"timestamp", "confidence"} or name.startswith(
                    ("gaze_", "pose_", "x_", "y_", "X_", "Y_", "Z_", "p_", "eye_")
                ) or name.endswith(("_r", "_c")):
                    try:
                        conv.append(float(cell))
                    except ValueError:
                        conv.append(cell)
                else:
                    conv.append(cell)
            rows.append(conv)
    return OpenFaceTable(columns=cols, rows=rows, is_sequence=is_sequence)


def column_index(columns: list[str], name: str) -> int:
    try:
        return columns.index(name)
    except ValueError as e:
        raise KeyError(name) from e
