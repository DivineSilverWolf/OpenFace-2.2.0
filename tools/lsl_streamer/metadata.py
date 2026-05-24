"""XDF-oriented metadata helpers (JSON sidecar + key/value pairs for LSL desc)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable


def xdf_sidecar_template() -> dict[str, Any]:
    """Recommended keys to merge into XDF recording metadata (or BIDS sidecar)."""
    return {
        "TaskName": "",
        "InstitutionName": "",
        "SoftwareFilters": {
            "OpenFace": {
                "Version": "PLACEHOLDER_OpenFace_version",
                "FeatureExtraction": True,
            }
        },
        "LSL": {
            "stream_name": "",
            "stream_type": "",
            "nominal_srate": None,
            "channel_labels": [],
            "source_id": "",
        },
        "OpenFace": {
            "csv_path": "",
            "column_map": {
                "timestamp_column": "timestamp",
                "frame_column": "frame",
                "face_id_column": "face_id",
            },
        },
    }


def desc_key_values(
    *,
    source: str,
    openface_version: str,
    csv_path: str,
    stream_role: str,
    subject_id: str | None,
    run_id: str | None,
) -> list[tuple[str, str]]:
    """Flat (key, value) pairs for pylsl StreamInfo.desc().append_child_value."""
    pairs: list[tuple[str, str]] = [
        ("source", source),
        ("openface_version", openface_version),
        ("csv_path", csv_path),
        ("stream_role", stream_role),
        ("xdf_note", "See docs/LSL_OPENFACE.md for XDF/BIDS companion fields."),
    ]
    if subject_id:
        pairs.append(("subject_id", subject_id))
    if run_id:
        pairs.append(("run_id", run_id))
    return pairs


def write_sidecar_json(
    path: Path,
    *,
    stream_name: str,
    stream_type: str,
    nominal_srate: float,
    channel_labels: Iterable[str],
    source_id: str,
    csv_path: str,
    openface_version: str,
    subject_id: str | None,
    run_id: str | None,
) -> None:
    base = xdf_sidecar_template()
    base["LSL"]["stream_name"] = stream_name
    base["LSL"]["stream_type"] = stream_type
    base["LSL"]["nominal_srate"] = nominal_srate
    base["LSL"]["channel_labels"] = list(channel_labels)
    base["LSL"]["source_id"] = source_id
    base["OpenFace"]["csv_path"] = csv_path
    base["SoftwareFilters"]["OpenFace"]["Version"] = openface_version
    out: dict[str, Any] = dict(base)
    if subject_id:
        out["SubjectId"] = subject_id
    if run_id:
        out["RunId"] = run_id
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
