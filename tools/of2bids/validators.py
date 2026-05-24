from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Sequence


class Monotonicity(str, Enum):
    OK = "ok"
    NON_INCREASING = "non_increasing"
    DUPLICATES = "duplicates"


@dataclass
class ValidationResult:
    ok: bool
    issues: list[str]


REQUIRED_SEQUENCE = ("timestamp", "success")


def validate_sequence_columns(columns: Sequence[str]) -> ValidationResult:
    issues: list[str] = []
    s = set(columns)
    for c in REQUIRED_SEQUENCE:
        if c not in s:
            issues.append(f"missing required column: {c}")
    if "frame" not in s:
        issues.append("missing recommended column: frame (sequence mode)")
    return ValidationResult(ok=not any("missing required" in i for i in issues), issues=issues)


def check_timestamp_monotonicity(
    timestamps: Iterable[float],
    *,
    strict: bool,
) -> tuple[Monotonicity, list[str]]:
    """Return status and human-readable messages."""
    msgs: list[str] = []
    prev: float | None = None
    seen_dup = False
    seen_drop = False
    for i, t in enumerate(timestamps):
        if prev is not None:
            if t < prev:
                seen_drop = True
                msgs.append(f"timestamp decreases at row index {i}: {prev} -> {t}")
            elif t == prev:
                seen_dup = True
                msgs.append(f"duplicate timestamp at row index {i}: {t}")
        prev = t
    if seen_drop:
        return Monotonicity.NON_INCREASING, msgs
    if seen_dup:
        status = Monotonicity.DUPLICATES
        if strict:
            msgs.insert(0, "strict mode: duplicate timestamps are not allowed")
        else:
            msgs.insert(0, "warning: duplicate timestamps (allowed in non-strict mode)")
        return status, msgs
    return Monotonicity.OK, msgs
