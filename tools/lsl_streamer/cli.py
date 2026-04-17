"""Command-line entry for post-hoc OpenFace CSV → LSL."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from tools.lsl_streamer import lsl_outlets


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Replay OpenFace FeatureExtraction CSV to Lab Streaming Layer (LSL) outlets."
    )
    p.add_argument("csv", type=Path, help="Path to OpenFace *.csv (FeatureExtraction output).")
    p.add_argument(
        "--stream-name",
        default="OpenFace",
        help="Base LSL stream name (split layout adds -AU / -core suffixes).",
    )
    p.add_argument("--subject-id", default=None, help="Optional subject identifier (LSL desc + sidecar).")
    p.add_argument("--run-id", default=None, help="Optional run identifier (LSL desc + sidecar).")
    p.add_argument(
        "--openface-version",
        default="unknown",
        help="OpenFace build or version string for metadata (placeholder if unknown).",
    )
    p.add_argument(
        "--fps",
        type=float,
        default=None,
        help="Override nominal sampling rate (Hz). If omitted, estimated from timestamp column.",
    )
    p.add_argument(
        "--source-id",
        default="openface_csv_replay",
        help="LSL source_id (identifies this outlet instance).",
    )
    p.add_argument(
        "--layout",
        choices=("split", "single"),
        default="split",
        help="split: AU stream + core gaze/pose stream; single: one combined stream.",
    )
    p.add_argument(
        "--sidecar-dir",
        type=Path,
        default=None,
        help="If set, write XDF-oriented JSON sidecar files alongside metadata per stream.",
    )
    p.add_argument(
        "--realtime",
        action="store_true",
        help="Sleep between rows to approximate CSV timestamps (default: push as fast as possible).",
    )
    args = p.parse_args(argv)

    if not lsl_outlets.HAS_PYLSL:
        print(
            "Error: pylsl could not be imported. Install pylsl and the LSL liblsl runtime for your OS, "
            "then retry. See docs/LSL_OPENFACE.md.",
            file=sys.stderr,
        )
        return 2

    csv_path = args.csv
    if not csv_path.is_file():
        print(f"Error: CSV not found: {csv_path}", file=sys.stderr)
        return 2

    try:
        lsl_outlets.replay_csv_to_lsl(
            csv_path,
            stream_name=args.stream_name,
            layout=args.layout,
            subject_id=args.subject_id,
            run_id=args.run_id,
            openface_version=args.openface_version,
            fps=args.fps,
            source_id=args.source_id,
            realtime=args.realtime,
            sidecar_dir=args.sidecar_dir,
        )
    except Exception as e:  # pragma: no cover - user-facing
        print(f"Error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
