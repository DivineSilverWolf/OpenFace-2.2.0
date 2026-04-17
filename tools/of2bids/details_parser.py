from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class OfDetailsMeta:
    """Structured fields parsed from OpenFace *_of_details.txt (best-effort)."""

    raw_text: str
    lines: dict[str, str]
    output_csv_relative: str | None
    fps_from_file: float | None

    def as_provenance_dict(self) -> dict[str, Any]:
        return {
            "openfaceDetailsFormat": "OpenFace_RecorderOpenFace_metadata",
            "outputCsvLine": self.lines.get("Output csv"),
            "outputCsvRelative": self.output_csv_relative,
            "fpsFromDetailsFile": self.fps_from_file,
        }


def parse_of_details(path: Path) -> OfDetailsMeta:
    text = path.read_text(encoding="utf-8", errors="replace")
    lines: dict[str, str] = {}
    for raw_line in text.splitlines():
        if ":" not in raw_line:
            continue
        key, val = raw_line.split(":", 1)
        lines[key.strip()] = val.strip()

    out_csv = lines.get("Output csv")
    fps_val: float | None = None
    # Optional extension line (not written by stock OpenFace; users may add for provenance).
    m = re.search(r"^FPS:\s*([0-9]+(?:\.[0-9]+)?)\s*$", text, flags=re.MULTILINE)
    if m:
        fps_val = float(m.group(1))
    return OfDetailsMeta(
        raw_text=text,
        lines=lines,
        output_csv_relative=out_csv,
        fps_from_file=fps_val,
    )
