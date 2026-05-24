from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from of2bids.csv_reader import column_index, read_openface_csv
from of2bids.details_parser import parse_of_details
from of2bids.events_io import EventsTable, events_relative_path, merge_events_asof_backward, read_events_tsv
from of2bids.sampling import choose_sampling_frequency, infer_sampling_frequency_hz
from of2bids.validators import Monotonicity, check_timestamp_monotonicity, validate_sequence_columns

# Shared with BIDS + LSL docs (see docs/INTEGRATION_LSL_BIDS.md). Written into every derivative JSON.
TIME_ALIGNMENT: dict[str, Any] = {
    "OpenFaceTimestamp": {
        "unit": "s",
        "description": (
            "Seconds on the OpenFace / video processing timeline (FeatureExtraction `timestamp` column). "
            "This is the primary time base in of2bids TSV files."
        ),
    },
    "BidsEventsOnset": {
        "unit": "s",
        "description": (
            "BIDS `events.tsv` `onset` is relative to the recording/task anchor defined by your BIDS dataset "
            "(see dataset_description and events sidecars). Use the same anchor as OpenFace only when your "
            "acquisition pipeline guarantees it."
        ),
        "mergeRule": (
            "When --merge-events is used, of2bids augments each OpenFace row with the last event row whose "
            "`onset` <= OpenFace `timestamp` (as-of backward, piecewise-constant events)."
        ),
    },
    "LSLReplayModeA": {
        "description": (
            "Post-hoc CSV→LSL (`tools/lsl_streamer`) assigns LSL sample times as local_clock() shifted so "
            "inter-sample intervals match the CSV. These LSL timestamps are not automatically equal to EEG "
            "wall time; record with LabRecorder and align using triggers, markers, or a documented affine map."
        ),
    },
}


def _rel_posix(root: Path, target: Path) -> str:
    try:
        return target.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return target.resolve().as_posix()


def _column_metadata(name: str) -> dict[str, Any]:
    meta: dict[str, Any] = {"name": name}
    if name == "timestamp":
        meta["LongName"] = "OpenFaceTimestamp"
        meta["Description"] = "Timestamp from OpenFace (seconds in source media timeline)."
        meta["Units"] = "s"
    elif name == "frame":
        meta["LongName"] = "FrameIndex"
        meta["Description"] = "Frame index in processed sequence."
        meta["Units"] = "n/a"
    elif name == "success":
        meta["LongName"] = "TrackingSuccess"
        meta["Description"] = "OpenFace landmark detection success flag (0/1)."
        meta["Units"] = "boolean"
    elif name.endswith("_r"):
        meta["LongName"] = name
        meta["Description"] = "OpenFace AU intensity (regression output)."
        meta["Units"] = "a.u."
    elif name.endswith("_c"):
        meta["LongName"] = name
        meta["Description"] = "OpenFace AU occurrence (classification output)."
        meta["Units"] = "probability"
    else:
        meta["LongName"] = name
        meta["Description"] = "OpenFace FeatureExtraction column (see OpenFace documentation)."
    return meta


def _ensure_dataset_description(deriv_root: Path, of2bids_version: str) -> None:
    desc_path = deriv_root / "dataset_description.json"
    if desc_path.exists():
        return
    payload = {
        "Name": "OpenFace facial behavior features",
        "BIDSVersion": "1.9.0",
        "DatasetType": "derivative",
        "GeneratedBy": [
            {
                "Name": "of2bids",
                "Version": of2bids_version,
                "Description": "Exports OpenFace FeatureExtraction CSV to BIDS-style TSV + JSON sidecars.",
            }
        ],
    }
    desc_path.parent.mkdir(parents=True, exist_ok=True)
    desc_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def discover_scan_pairs(scan_dir: Path, *, recursive: bool) -> list[tuple[Path, Path]]:
    it = scan_dir.rglob("*_of_details.txt") if recursive else scan_dir.glob("*_of_details.txt")
    pairs: list[tuple[Path, Path]] = []
    for det in sorted(it):
        stem = det.name[: -len("_of_details.txt")]
        csv_p = det.parent / f"{stem}.csv"
        if csv_p.is_file():
            pairs.append((csv_p, det))
    return pairs


def build_stem_entities(*, subject: str, task: str, recording: str | None, run: int | None) -> str:
    sub = subject if subject.startswith("sub-") else f"sub-{subject}"
    base = f"{sub}_task-{task}"
    if recording:
        rec = recording if recording.startswith("recording-") else f"recording-{recording}"
        base = f"{base}_{rec}"
    if run is not None:
        base = f"{base}_run-{run:02d}"
    return f"{base}_desc-openface_timeseries"


def export_openface_pair(
    *,
    bids_root: Path,
    csv_path: Path,
    details_path: Path,
    subject: str,
    task: str,
    recording: str | None,
    run: int | None,
    events_tsv: Path | None,
    events_json: Path | None,
    merge_events: bool,
    strict_timestamps: bool,
    prefer_details_fps: bool,
    of2bids_version: str,
    dry_run: bool,
) -> list[str]:
    """Export one (csv, details) pair; return log lines (warnings/errors)."""
    logs: list[str] = []
    table = read_openface_csv(csv_path)
    if not table.is_sequence:
        raise ValueError(
            f"{csv_path}: non-sequence OpenFace CSV (no timestamp/success); "
            "BIDS time series export is only defined for sequence/video mode."
        )

    v = validate_sequence_columns(table.columns)
    logs.extend(v.issues)
    if not v.ok:
        raise ValueError(f"{csv_path}: " + "; ".join(v.issues))

    ts_idx = column_index(table.columns, "timestamp")
    stamps = [float(r[ts_idx]) for r in table.rows]
    mono, mono_msgs = check_timestamp_monotonicity(stamps, strict=strict_timestamps)
    logs.extend(mono_msgs)
    if mono == Monotonicity.NON_INCREASING:
        raise ValueError(f"{csv_path}: timestamps are not monotonic: " + mono_msgs[0])
    if mono == Monotonicity.DUPLICATES and strict_timestamps:
        raise ValueError(f"{csv_path}: " + "; ".join(mono_msgs))

    details = parse_of_details(details_path)
    inferred = infer_sampling_frequency_hz(stamps)
    sf, sf_note = choose_sampling_frequency(
        fps_from_details=details.fps_from_file,
        inferred_hz=inferred,
        prefer_details_fps=prefer_details_fps,
    )

    stem = build_stem_entities(subject=subject, task=task, recording=recording, run=run)
    sub_label = subject[4:] if subject.startswith("sub-") else subject
    func_dir = bids_root / "derivatives" / "openface" / f"sub-{sub_label}" / "func"
    tsv_path = func_dir / f"{stem}.tsv"
    json_path = func_dir / f"{stem}.json"
    merged_stem = stem.replace("_desc-openface_timeseries", "_desc-openfacewithevents_timeseries")
    merged_tsv = func_dir / f"{merged_stem}.tsv" if merge_events and events_tsv else None
    merged_json = func_dir / f"{merged_stem}.json" if merge_events and events_tsv else None

    events_tab: EventsTable | None = None
    if events_tsv is not None:
        events_tab = read_events_tsv(events_tsv)

    columns_meta = [_column_metadata(c) for c in table.columns]
    sources = [
        _rel_posix(bids_root, csv_path),
        _rel_posix(bids_root, details_path),
    ]

    associated_events: dict[str, Any] | None = None
    if events_tsv is not None:
        associated_events = {
            "path": events_relative_path(bids_root, events_tsv),
            "description": (
                "BIDS events file paired with this OpenFace derivative for EEG/behavior alignment. "
                "Default interpretation: OpenFace `timestamp` (s) is on the same media clock as "
                "`onset` in this events.tsv unless your acquisition pipeline documents otherwise "
                "(see JSON `TimeAlignment` and docs/INTEGRATION_LSL_BIDS.md)."
            ),
        }
        if merge_events:
            associated_events["mergeStrategy"] = "asof_backward_on_onset"
        if events_json is not None and events_json.is_file():
            associated_events["eventsJsonPath"] = events_relative_path(bids_root, events_json)

    sidecar: dict[str, Any] = {
        "Description": "OpenFace FeatureExtraction facial feature time series (derivative).",
        "OpenFaceDerivative": True,
        "SamplingFrequency": sf,
        "SamplingFrequencyProvenance": sf_note,
        "TimeAlignment": TIME_ALIGNMENT,
        "Sources": sources,
        "SourceCSV": _rel_posix(bids_root, csv_path),
        "SourceOpenFaceDetails": _rel_posix(bids_root, details_path),
        "Columns": columns_meta,
        "OpenFaceDetailsExcerpt": {k: details.lines[k] for k in sorted(details.lines)[:12]},
    }
    if associated_events is not None:
        sidecar["AssociatedEvents"] = associated_events

    if dry_run:
        logs.append(f"dry-run: would write {tsv_path} and {json_path}")
        return logs

    func_dir.mkdir(parents=True, exist_ok=True)
    deriv_root = bids_root / "derivatives" / "openface"
    _ensure_dataset_description(deriv_root, of2bids_version)

    with tsv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n")
        w.writerow(table.columns)
        w.writerows(table.rows)

    json_path.write_text(json.dumps(sidecar, indent=2), encoding="utf-8")

    if merge_events and events_tab is not None and merged_tsv and merged_json:
        m_cols, m_rows = merge_events_asof_backward(
            of_columns=table.columns,
            of_rows=table.rows,
            time_idx=ts_idx,
            events=events_tab,
        )
        m_sidecar = dict(sidecar)
        m_sidecar["Description"] = (
            sidecar["Description"]
            + " Merged with BIDS events (last event with onset <= OpenFace timestamp)."
        )
        m_sidecar["Columns"] = [_column_metadata(c) for c in m_cols]
        m_sidecar["MergedEventsColumns"] = events_tab.columns
        with merged_tsv.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, delimiter="\t", lineterminator="\n")
            w.writerow(m_cols)
            w.writerows(m_rows)
        merged_json.write_text(json.dumps(m_sidecar, indent=2), encoding="utf-8")

    return logs
