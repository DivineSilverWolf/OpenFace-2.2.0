from __future__ import annotations

import statistics
from typing import Sequence


def infer_sampling_frequency_hz(timestamps: Sequence[float]) -> float | None:
    """Infer sampling rate from median positive delta of timestamps (seconds)."""
    if len(timestamps) < 2:
        return None
    diffs: list[float] = []
    prev = timestamps[0]
    for t in timestamps[1:]:
        d = t - prev
        if d > 0:
            diffs.append(d)
        prev = t
    if not diffs:
        return None
    med = statistics.median(diffs)
    if med <= 0:
        return None
    return 1.0 / med


def choose_sampling_frequency(
    *,
    fps_from_details: float | None,
    inferred_hz: float | None,
    prefer_details_fps: bool,
) -> tuple[float | None, str]:
    """Return (SamplingFrequency_Hz, provenance note)."""
    if prefer_details_fps and fps_from_details is not None and fps_from_details > 0:
        return fps_from_details, "fps_from_of_details_file"
    if fps_from_details is not None and fps_from_details > 0 and inferred_hz is None:
        return fps_from_details, "fps_from_of_details_file_no_csv_inference"
    if inferred_hz is not None and inferred_hz > 0:
        if fps_from_details is not None and fps_from_details > 0:
            return inferred_hz, "inferred_from_csv_timestamps_details_fps_ignored"
        return inferred_hz, "inferred_from_csv_timestamps"
    if fps_from_details is not None and fps_from_details > 0:
        return fps_from_details, "fps_from_of_details_file_fallback"
    return None, "sampling_frequency_unknown"
