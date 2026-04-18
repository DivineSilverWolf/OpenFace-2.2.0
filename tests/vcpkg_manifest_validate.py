#!/usr/bin/env python3
"""Static checks for vcpkg manifest, CMakePresets, FindOpenBLAS, log/, and related guardrails.

Run from repo root: python3 tests/vcpkg_manifest_validate.py
Used in CI (no vcpkg install required).
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    here = Path(__file__).resolve().parent
    return here.parent


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _flatten_dep_names(dependencies: object) -> list[str]:
    names: list[str] = []
    if not isinstance(dependencies, list):
        return names
    for item in dependencies:
        if isinstance(item, str):
            names.append(item)
        elif isinstance(item, dict) and isinstance(item.get("name"), str):
            names.append(item["name"])
    return names


def validate_vcpkg(repo: Path) -> None:
    path = repo / "vcpkg.json"
    data = _load_json(path)
    assert isinstance(data, dict), "vcpkg.json must be a JSON object"

    assert data.get("name") == "openface", "vcpkg.json name must be openface"
    baseline = data.get("builtin-baseline")
    assert isinstance(baseline, str) and re.fullmatch(r"[0-9a-f]{40}", baseline), (
        "builtin-baseline must be a 40-char lowercase hex commit"
    )

    deps = data.get("dependencies")
    names = set(_flatten_dep_names(deps))
    required = {"opencv4", "boost-filesystem", "boost-system", "openblas", "dlib"}
    missing = required - names
    assert not missing, f"vcpkg.json missing dependencies: {sorted(missing)}"

    opencv = next(
        (d for d in deps if isinstance(d, dict) and d.get("name") == "opencv4"),
        None,
    )
    assert isinstance(opencv, dict), "opencv4 entry must be an object"
    assert opencv.get("default-features") is not False, (
        'opencv4 must not set "default-features": false (drops calib3d/highgui/objdetect; '
        "breaks find_package(OpenCV COMPONENTS …) in CMakeLists.txt)"
    )
    feats = opencv.get("features")
    assert isinstance(feats, list) and "ffmpeg" in feats, "opencv4 must list ffmpeg in features"


def validate_cmake_presets(repo: Path) -> None:
    path = repo / "CMakePresets.json"
    data = _load_json(path)
    assert isinstance(data, dict), "CMakePresets.json must be a JSON object"
    assert data.get("version") == 3, "CMakePresets version must be 3 (CMake 3.21+)"

    cmr = data.get("cmakeMinimumRequired")
    assert isinstance(cmr, dict), "cmakeMinimumRequired must be present"
    assert int(cmr.get("major", 0)) >= 3 and int(cmr.get("minor", 0)) >= 21, (
        "cmakeMinimumRequired must be at least 3.21 for preset version 3"
    )

    cps = data.get("configurePresets")
    assert isinstance(cps, list) and cps, "configurePresets must be a non-empty list"
    names = {p.get("name") for p in cps if isinstance(p, dict)}
    for need in ("windows-msvc-vcpkg", "linux-gcc", "wsl-clang", "vcpkg-common"):
        assert need in names, f"configurePresets missing {need!r}"

    bps = data.get("buildPresets")
    assert isinstance(bps, list) and bps, "buildPresets must be a non-empty list"
    by_name = {p.get("name"): p for p in bps if isinstance(p, dict)}
    assert "windows-msvc-vcpkg-release" in by_name
    assert by_name["windows-msvc-vcpkg-release"].get("configurePreset") == "windows-msvc-vcpkg"
    for n in ("linux-gcc", "wsl-clang"):
        assert n in by_name and by_name[n].get("configurePreset") == n


def validate_find_openblas(repo: Path) -> None:
    text = (repo / "cmake" / "modules" / "FindOpenBLAS.cmake").read_text(encoding="utf-8", errors="replace")
    assert "OpenBLAS}cd" not in text, "FindOpenBLAS.cmake must not contain the historical typo OpenBLAS}cd"
    assert "VCPKG_INSTALLED_DIR" in text and "VCPKG_TARGET_TRIPLET" in text, (
        "FindOpenBLAS.cmake should reference vcpkg triplet variables when vcpkg is used"
    )


def validate_no_vendor_findblas(repo: Path) -> None:
    """A vendored FindBLAS in CMAKE_MODULE_PATH shadows CMake's FindBLAS; vcpkg dlib needs BLAS::BLAS (CMake 3.18+)."""
    legacy = repo / "cmake" / "modules" / "FindBLAS.cmake"
    assert not legacy.is_file(), (
        "Remove cmake/modules/FindBLAS.cmake — it shadows CMake's FindBLAS and breaks "
        "find_dependency(BLAS) for vcpkg dlib (BLAS::BLAS not defined)."
    )


def validate_log_directory(repo: Path) -> None:
    """log/ holds local thesis/PS logs; README is tracked, other files must stay gitignored."""
    readme = repo / "log" / "README.md"
    assert readme.is_file(), "log/README.md must exist (placeholder for tracked log/ directory)"
    text = (repo / ".gitignore").read_text(encoding="utf-8", errors="replace")
    assert "/log/*" in text, ".gitignore must contain /log/* so generated logs are not committed"
    assert "!/log/README.md" in text, ".gitignore must contain !/log/README.md to keep log/README.md in git"


def _cmake_semver() -> tuple[int, int, int] | None:
    exe = shutil.which("cmake")
    if not exe:
        return None
    proc = subprocess.run(
        [exe, "--version"],
        check=True,
        capture_output=True,
        text=True,
    )
    first = (proc.stdout or "").splitlines()[0] if proc.stdout else ""
    # e.g. cmake version 3.28.3
    m = re.search(r"cmake version (\d+)\.(\d+)\.(\d+)", first, re.I)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def validate_cmake_presets_cli(repo: Path) -> None:
    """Parse CMakePresets.json the same way CMake does (requires CMake 3.21+)."""
    ver = _cmake_semver()
    if ver is None:
        print("vcpkg_manifest_validate: SKIP cmake --list-presets (cmake not in PATH)", file=sys.stderr)
        return
    major, minor, _patch = ver
    if (major, minor) < (3, 21):
        print(
            f"vcpkg_manifest_validate: SKIP cmake --list-presets (found {major}.{minor}, need 3.21+)",
            file=sys.stderr,
        )
        return
    exe = shutil.which("cmake")
    assert exe is not None
    subprocess.run([exe, "--list-presets"], cwd=repo, check=True)
    print("vcpkg_manifest_validate: cmake --list-presets OK")


def main() -> int:
    repo = _repo_root()
    validate_vcpkg(repo)
    validate_cmake_presets(repo)
    validate_find_openblas(repo)
    validate_no_vendor_findblas(repo)
    validate_log_directory(repo)
    validate_cmake_presets_cli(repo)
    print("vcpkg_manifest_validate: OK")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"vcpkg_manifest_validate: FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
