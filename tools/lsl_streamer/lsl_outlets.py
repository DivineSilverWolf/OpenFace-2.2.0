"""Create LSL outlets and push rows (requires pylsl + liblsl at runtime)."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Sequence

from tools.lsl_streamer.columns import ColumnGroups, group_columns
from tools.lsl_streamer.csv_load import (
    column_indices,
    estimate_nominal_srate,
    iter_sample_times,
    load_openface_csv,
    parse_float_row,
    timestamps_seconds,
)
from tools.lsl_streamer.metadata import desc_key_values, write_sidecar_json

try:
    import pylsl

    HAS_PYLSL = True
except Exception:  # pragma: no cover - import guard for CI without liblsl
    pylsl = None  # type: ignore[assignment]
    HAS_PYLSL = False


@dataclass(frozen=True)
class StreamSpec:
    name: str
    stype: str
    labels: list[str]


def _apply_desc(info: object, pairs: Sequence[tuple[str, str]], channel_labels: Sequence[str]) -> None:
    desc = info.desc()
    for k, v in pairs:
        desc.append_child_value(k, v)
    channels = desc.append_child("channels")
    for label in channel_labels:
        ch = channels.append_child("channel")
        ch.append_child_value("label", label)


def build_specs(
    base_name: str,
    groups: ColumnGroups,
    layout: str,
) -> list[StreamSpec]:
    if layout == "single":
        labels = groups.all_numeric_stream
        if not labels:
            raise ValueError("No AU/core columns found in CSV header.")
        return [StreamSpec(name=base_name, stype="OpenFace", labels=labels)]
    if layout == "split":
        specs: list[StreamSpec] = []
        au_labels = groups.au_r + groups.au_c
        if au_labels:
            specs.append(StreamSpec(name=f"{base_name}-AU", stype="OpenFace", labels=au_labels))
        if groups.core:
            specs.append(StreamSpec(name=f"{base_name}-core", stype="OpenFace", labels=groups.core))
        if not specs:
            raise ValueError("No AU or core columns found for split layout.")
        return specs
    raise ValueError(f"Unknown layout: {layout}")


def replay_csv_to_lsl(
    csv_path: Path,
    *,
    stream_name: str,
    layout: str,
    subject_id: str | None,
    run_id: str | None,
    openface_version: str,
    fps: float | None,
    source_id: str,
    realtime: bool,
    sidecar_dir: Path | None,
    outlet_factory: Callable[..., object] | None = None,
    pylsl_module: Any | None = None,
) -> None:
    """Push all rows to LSL.

    `outlet_factory` is for tests (returns objects with push_sample).
    `pylsl_module` overrides the binding (for unit tests without liblsl).
    """
    pls = pylsl_module if pylsl_module is not None else pylsl
    if pls is None:
        raise RuntimeError("pylsl is not available (install pylsl and liblsl).")

    loaded = load_openface_csv(csv_path)
    groups = group_columns(loaded.headers)
    specs = build_specs(stream_name, groups, layout)
    ts_list = timestamps_seconds(loaded)
    nominal = estimate_nominal_srate(ts_list, fps)
    n = len(loaded.rows)

    outlets: list[object] = []
    all_indices: list[list[int]] = []

    for spec in specs:
        n_ch = len(spec.labels)
        info = pls.StreamInfo(
            spec.name,
            spec.stype,
            n_ch,
            nominal,
            pls.cf_float32,
            source_id,
        )
        pairs = desc_key_values(
            source="OpenFace-FeatureExtraction-CSV",
            openface_version=openface_version,
            csv_path=str(csv_path.resolve()),
            stream_role=spec.name,
            subject_id=subject_id,
            run_id=run_id,
        )
        _apply_desc(info, pairs, spec.labels)
        if outlet_factory:
            out = outlet_factory(info)
        else:
            out = pls.StreamOutlet(info)
        outlets.append(out)
        all_indices.append(column_indices(loaded.headers, spec.labels))

    if sidecar_dir:
        sidecar_dir.mkdir(parents=True, exist_ok=True)
        stem = csv_path.stem
        for spec in specs:
            sc = sidecar_dir / f"{stem}__{spec.name.replace(' ', '_')}_lsl_meta.json"
            write_sidecar_json(
                sc,
                stream_name=spec.name,
                stream_type=spec.stype,
                nominal_srate=nominal,
                channel_labels=spec.labels,
                source_id=source_id,
                csv_path=str(csv_path.resolve()),
                openface_version=openface_version,
                subject_id=subject_id,
                run_id=run_id,
            )

    t0_csv = ts_list[0] if ts_list else 0.0
    t0_lsl = pls.local_clock()

    times = list(iter_sample_times(ts_list, n, nominal))
    prev_csv_t: float | None = None
    for row_i, row in enumerate(loaded.rows):
        csv_t = times[row_i]
        lsl_t = t0_lsl + (csv_t - t0_csv)
        for out, idxs in zip(outlets, all_indices):
            sample = parse_float_row(row, idxs)
            out.push_sample(sample, timestamp=lsl_t)  # type: ignore[union-attr]
        if realtime and prev_csv_t is not None:
            dt = csv_t - prev_csv_t
            if dt > 0:
                time.sleep(dt)
        prev_csv_t = csv_t
