#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Dict, Iterable, List, Sequence, Tuple

SUPPORTED_EXTENSIONS = {".csv", ".hog"}
SUPPORTED_SUFFIX = "_of_details.txt"
NUMBER_RE = re.compile(r"[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?")


@dataclass
class DiffResult:
    path: str
    status: str
    detail: str = ""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_manifest(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8"))


def collect_supported_files(root: Path) -> List[Path]:
    files: List[Path] = []
    for candidate in root.rglob("*"):
        if not candidate.is_file():
            continue
        if candidate.suffix in SUPPORTED_EXTENSIONS or candidate.name.endswith(SUPPORTED_SUFFIX):
            files.append(candidate)
    files.sort()
    return files


def relpath(path: Path, root: Path) -> str:
    return str(path.relative_to(root)).replace("\\", "/")


def compile_patterns(manifest: Dict) -> Sequence[str]:
    patterns = manifest.get("patterns", [])
    if not isinstance(patterns, list):
        raise ValueError("'patterns' in manifest must be a list")
    cleaned = [pattern for pattern in patterns if isinstance(pattern, str) and pattern.strip()]
    if not cleaned:
        raise ValueError("manifest must contain at least one non-empty pattern")
    return cleaned


def filter_relpaths_by_patterns(paths: Iterable[str], patterns: Sequence[str]) -> List[str]:
    selected = set()
    for rel in paths:
        rel_path = Path(rel)
        if any(rel_path.match(pattern) for pattern in patterns):
            selected.add(rel)
    return sorted(selected)


def compare_strict(actual: Path, baseline: Path) -> Tuple[bool, str]:
    actual_sha = sha256_file(actual)
    baseline_sha = sha256_file(baseline)
    if actual_sha == baseline_sha:
        return True, f"sha256={actual_sha[:12]}..."
    return False, f"sha256 differs: actual={actual_sha[:12]}..., baseline={baseline_sha[:12]}..."


def parse_numeric_tokens(text: str) -> List[float]:
    return [float(match.group(0)) for match in NUMBER_RE.finditer(text)]


# Longer prefix first so we never treat "Input full path:" as "Input:".
_OF_DETAILS_INPUT_PREFIXES: Tuple[str, ...] = ("Input full path:", "Input:")


def sanitize_of_details_text(text: str) -> str:
    """Strip machine-specific directories from *_of_details.txt path lines.

    OpenFace writes absolute paths on the first lines; GitHub Actions vs WSL vs
    local checkouts differ in length and digit-rich segments (e.g. OpenFace-2.2.0
    repeated in a runner workdir). Tolerant numeric compare should not treat those
    path digits as part of the regression signal.
    """
    out: List[str] = []
    for raw in text.splitlines():
        line = raw.rstrip("\r")
        new_line = line
        for prefix in _OF_DETAILS_INPUT_PREFIXES:
            if line.startswith(prefix):
                remainder = line[len(prefix) :].strip().strip('"')
                if remainder:
                    posix = remainder.replace("\\", "/")
                    basename = PurePosixPath(posix).name
                else:
                    basename = ""
                new_line = prefix + basename
                break
        out.append(new_line)
    return "\n".join(out)


def compare_tolerant_text(actual: Path, baseline: Path, abs_tol: float) -> Tuple[bool, str]:
    actual_text = actual.read_text(encoding="utf-8", errors="replace")
    baseline_text = baseline.read_text(encoding="utf-8", errors="replace")

    if actual.name.endswith(SUPPORTED_SUFFIX) and baseline.name.endswith(SUPPORTED_SUFFIX):
        actual_text = sanitize_of_details_text(actual_text)
        baseline_text = sanitize_of_details_text(baseline_text)

    actual_numbers = parse_numeric_tokens(actual_text)
    baseline_numbers = parse_numeric_tokens(baseline_text)

    if len(actual_numbers) != len(baseline_numbers):
        return False, (
            "numeric token count differs: "
            f"actual={len(actual_numbers)}, baseline={len(baseline_numbers)}"
        )

    if not actual_numbers:
        # For text files without numbers we require exact text match.
        if actual_text == baseline_text:
            return True, "text identical (no numeric tokens)"
        return False, "text differs and no numeric tokens found"

    max_abs = 0.0
    bad_count = 0
    for actual_value, baseline_value in zip(actual_numbers, baseline_numbers):
        if math.isnan(actual_value) and math.isnan(baseline_value):
            continue
        delta = abs(actual_value - baseline_value)
        max_abs = max(max_abs, delta)
        if delta > abs_tol:
            bad_count += 1

    if bad_count == 0:
        return True, (
            f"within tol={abs_tol:g}; numeric_count={len(actual_numbers)}; max_abs={max_abs:.3e}"
        )

    return False, (
        f"exceeds tol={abs_tol:g}; bad={bad_count}/{len(actual_numbers)}; max_abs={max_abs:.3e}"
    )


def compare_tolerant(actual: Path, baseline: Path, abs_tol: float) -> Tuple[bool, str]:
    if actual.suffix == ".hog":
        # .hog is binary; tolerant mode still compares it byte-for-byte.
        return compare_strict(actual, baseline)
    return compare_tolerant_text(actual, baseline, abs_tol)


def maybe_parse_csv(path: Path) -> Tuple[int, int]:
    if path.suffix != ".csv":
        return (0, 0)
    rows = 0
    max_cols = 0
    with path.open("r", encoding="utf-8", errors="replace", newline="") as file_obj:
        reader = csv.reader(file_obj)
        for row in reader:
            rows += 1
            max_cols = max(max_cols, len(row))
    return (rows, max_cols)


def validate_sha256_manifest(manifest: Dict, baseline_root: Path, target_paths: Sequence[str]) -> List[str]:
    expected = manifest.get("sha256", {})
    if not isinstance(expected, dict):
        raise ValueError("'sha256' in manifest must be an object when provided")
    # Empty or omitted sha256 means "do not pin hashes" (common for local / evolving baselines).
    if not expected:
        return []
    missing_hash_entries: List[str] = []
    for rel in target_paths:
        if rel not in expected:
            missing_hash_entries.append(rel)
            continue
        baseline_path = baseline_root / rel
        if not baseline_path.exists():
            continue
        actual_hash = sha256_file(baseline_path)
        if actual_hash != expected[rel]:
            missing_hash_entries.append(rel + " (baseline hash mismatch with manifest)")
    return missing_hash_entries


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare smoke outputs against baseline outputs")
    parser.add_argument("--actual-dir", required=True, type=Path, help="Path to smoke output under test")
    parser.add_argument("--baseline-dir", required=True, type=Path, help="Path to baseline smoke output")
    parser.add_argument("--manifest", required=True, type=Path, help="Path to baseline manifest JSON")
    parser.add_argument(
        "--mode",
        default="strict",
        choices=["strict", "tolerant"],
        help="strict=byte-for-byte; tolerant=numeric tolerance for text outputs",
    )
    parser.add_argument("--abs-tol", type=float, default=1e-6, help="Absolute tolerance for numeric comparison")
    args = parser.parse_args()

    actual_dir = args.actual_dir.resolve()
    baseline_dir = args.baseline_dir.resolve()
    manifest_path = args.manifest.resolve()

    if not actual_dir.exists():
        print(f"[ERROR] actual directory not found: {actual_dir}")
        return 2
    if not baseline_dir.exists():
        print(f"[ERROR] baseline directory not found: {baseline_dir}")
        return 2
    if not manifest_path.exists():
        print(f"[ERROR] manifest not found: {manifest_path}")
        return 2
    if args.abs_tol < 0:
        print("[ERROR] --abs-tol must be non-negative")
        return 2

    manifest = load_manifest(manifest_path)
    patterns = compile_patterns(manifest)

    actual_files = collect_supported_files(actual_dir)
    baseline_files = collect_supported_files(baseline_dir)
    actual_rel = {relpath(path, actual_dir) for path in actual_files}
    baseline_rel = {relpath(path, baseline_dir) for path in baseline_files}

    target_paths = sorted(set(filter_relpaths_by_patterns(actual_rel | baseline_rel, patterns)))

    if not target_paths:
        print("[ERROR] no files matched manifest patterns in actual/baseline trees")
        return 2

    sha_manifest_issues = validate_sha256_manifest(manifest, baseline_dir, target_paths)
    if sha_manifest_issues:
        print("[ERROR] baseline manifest sha256 validation failed:")
        for issue in sha_manifest_issues:
            print(f"  - {issue}")
        return 2

    compare_fn = compare_strict if args.mode == "strict" else lambda a, b: compare_tolerant(a, b, args.abs_tol)
    results: List[DiffResult] = []

    for rel in target_paths:
        actual_path = actual_dir / rel
        baseline_path = baseline_dir / rel

        if not actual_path.exists():
            results.append(DiffResult(path=rel, status="MISSING_IN_ACTUAL"))
            continue
        if not baseline_path.exists():
            results.append(DiffResult(path=rel, status="MISSING_IN_BASELINE"))
            continue

        ok, detail = compare_fn(actual_path, baseline_path)
        if ok:
            extra = ""
            rows, cols = maybe_parse_csv(actual_path)
            if rows > 0:
                extra = f" (csv rows={rows}, max_cols={cols})"
            results.append(DiffResult(path=rel, status="OK", detail=detail + extra))
        else:
            results.append(DiffResult(path=rel, status="DIFF", detail=detail))

    diffs = [item for item in results if item.status != "OK"]

    print("=== Smoke Regression Comparison ===")
    print(f"Mode: {args.mode}")
    print(f"Abs tolerance: {args.abs_tol:g}")
    print(f"Actual dir: {actual_dir}")
    print(f"Baseline dir: {baseline_dir}")
    print(f"Manifest: {manifest_path}")
    print(f"Files checked: {len(results)}")
    print(f"Differences: {len(diffs)}")
    print()

    if diffs:
        print("Differences detail:")
        for item in diffs:
            suffix = f" :: {item.detail}" if item.detail else ""
            print(f"  - [{item.status}] {item.path}{suffix}")
        print()
        print("[FAIL] Regression differences detected.")
        return 1

    print("[PASS] All compared files match.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
