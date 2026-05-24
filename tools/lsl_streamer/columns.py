"""OpenFace CSV column grouping (respects OpenFace FeatureExtraction naming)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Sequence


AU_R = re.compile(r"^AU\d+_r$")
AU_C = re.compile(r"^AU\d+_c$")

# Core continuous features (common in analyses; excludes massive landmark grids by default).
CORE_COLUMNS_ORDERED: tuple[str, ...] = (
    "confidence",
    "success",
    "gaze_angle_x",
    "gaze_angle_y",
    "gaze_0_x",
    "gaze_0_y",
    "gaze_0_z",
    "gaze_1_x",
    "gaze_1_y",
    "gaze_1_z",
    "pose_Tx",
    "pose_Ty",
    "pose_Tz",
    "pose_Rx",
    "pose_Ry",
    "pose_Rz",
)


@dataclass(frozen=True)
class ColumnGroups:
    au_r: list[str]
    au_c: list[str]
    core: list[str]
    all_numeric_stream: list[str]


def group_columns(headers: Sequence[str]) -> ColumnGroups:
    hset = list(headers)
    au_r = sorted([h for h in hset if AU_R.match(h)], key=_au_sort_key)
    au_c = sorted([h for h in hset if AU_C.match(h)], key=_au_sort_key)
    core = [c for c in CORE_COLUMNS_ORDERED if c in hset]
    combined = au_r + au_c + core
    return ColumnGroups(au_r=au_r, au_c=au_c, core=core, all_numeric_stream=combined)


def _au_sort_key(name: str) -> tuple[int, str]:
    m = re.search(r"AU(\d+)", name)
    n = int(m.group(1)) if m else 0
    return (n, name)
