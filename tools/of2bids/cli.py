from __future__ import annotations

import argparse
import sys
from pathlib import Path

from of2bids import __version__
from of2bids.export_bids import discover_scan_pairs, export_openface_pair


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="of2bids",
        description="Export OpenFace FeatureExtraction outputs as BIDS-style derivatives (TSV + JSON).",
    )
    p.add_argument("--bids-root", type=Path, required=True, help="Root of the BIDS dataset (derivative paths created below this root).")
    p.add_argument("--subject", required=True, help='Subject label, e.g. "01" or "sub-01".')
    p.add_argument("--task", required=True, help="BIDS task label (without task- prefix).")
    p.add_argument("--recording", default=None, help='Optional recording label, e.g. "01" -> recording-01.')
    p.add_argument("--run", type=int, default=None, help="Optional run index (integer); formatted as run-NN in filename.")
    p.add_argument("--csv", type=Path, default=None, help="Path to OpenFace *.csv (sequence mode).")
    p.add_argument("--of-details", type=Path, default=None, help="Path to matching *_of_details.txt.")
    p.add_argument("--scan-dir", type=Path, default=None, help="Directory containing paired stem.csv + stem_of_details.txt.")
    p.add_argument(
        "--recursive",
        action="store_true",
        help="With --scan-dir, discover *_of_details.txt recursively.",
    )
    p.add_argument("--events-tsv", type=Path, default=None, help="Optional BIDS events.tsv for EEG/behavior coupling.")
    p.add_argument("--events-json", type=Path, default=None, help="Optional BIDS events.json sidecar (provenance only).")
    p.add_argument(
        "--merge-events",
        action="store_true",
        help="Also write desc-openfacewithevents_timeseries.tsv with event columns (asof backward on onset).",
    )
    p.add_argument(
        "--strict-timestamps",
        action="store_true",
        help="Fail on duplicate timestamps (default: warn only).",
    )
    p.add_argument(
        "--prefer-details-fps",
        action="store_true",
        help="Prefer FPS: line from _of_details.txt over CSV timestamp inference when both exist.",
    )
    p.add_argument("--dry-run", action="store_true", help="Validate and print paths without writing files.")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    bids_root: Path = args.bids_root
    if args.csv is None and args.scan_dir is None:
        print("error: provide either (--csv and --of-details) or --scan-dir", file=sys.stderr)
        return 2
    if args.csv is not None and args.of_details is None:
        print("error: --of-details is required when --csv is set", file=sys.stderr)
        return 2
    if args.of_details is not None and args.csv is None:
        print("error: --csv is required when --of-details is set", file=sys.stderr)
        return 2
    if args.merge_events or args.events_json is not None:
        if args.events_tsv is None:
            print("error: --events-tsv is required when using --merge-events or --events-json", file=sys.stderr)
            return 2

    pairs: list[tuple[Path, Path]]
    if args.scan_dir is not None:
        scan_dir = args.scan_dir
        if not scan_dir.is_dir():
            print(f"error: not a directory: {scan_dir}", file=sys.stderr)
            return 2
        pairs = discover_scan_pairs(scan_dir, recursive=args.recursive)
        if not pairs:
            print(f"error: no stem.csv + stem_of_details.txt pairs under {scan_dir}", file=sys.stderr)
            return 2
    else:
        pairs = [(args.csv, args.of_details)]

    if args.run is not None and len(pairs) > 1:
        print("error: do not combine --run with multi-pair --scan-dir (use auto run index instead)", file=sys.stderr)
        return 2

    exit_code = 0
    for i, (csv_p, det_p) in enumerate(pairs, start=1):
        run = args.run if args.run is not None else (i if len(pairs) > 1 else None)
        try:
            logs = export_openface_pair(
                bids_root=bids_root,
                csv_path=csv_p,
                details_path=det_p,
                subject=args.subject,
                task=args.task,
                recording=args.recording,
                run=run,
                events_tsv=args.events_tsv,
                events_json=args.events_json,
                merge_events=args.merge_events,
                strict_timestamps=args.strict_timestamps,
                prefer_details_fps=args.prefer_details_fps,
                of2bids_version=__version__,
                dry_run=args.dry_run,
            )
        except Exception as e:
            print(f"error: {csv_p}: {e}", file=sys.stderr)
            exit_code = 1
            continue
        for line in logs:
            print(line, file=sys.stderr)
    return exit_code
