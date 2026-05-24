"""Unit tests for *_of_details.txt path normalization in compare_smoke_outputs."""
from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_REG_PATH = _REPO_ROOT / "tools" / "regression" / "compare_smoke_outputs.py"


def _load_compare_module():
    spec = importlib.util.spec_from_file_location("compare_smoke_outputs", _REG_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["compare_smoke_outputs"] = mod
    spec.loader.exec_module(mod)
    return mod


_cmp = _load_compare_module()


class TestSanitizeOfDetails(unittest.TestCase):
    def test_strips_divergent_prefix_same_basename(self) -> None:
        a = (
            "Input:/home/runner/work/OpenFace-2.2.0/OpenFace-2.2.0/smoke_test/data/img1_2026-04-13_02-55-53.jpg\n"
            "Input full path:/home/runner/work/OpenFace-2.2.0/OpenFace-2.2.0/smoke_test/data/img1_2026-04-13_02-55-53.jpg\n"
            "Camera parameters:1000.52,1000.52,640,480.5\n"
        )
        b = (
            "Input:/mnt/c/Users/me/OpenFace-2.2.0/smoke_test/data/img1_2026-04-13_02-55-53.jpg\n"
            "Input full path:/mnt/c/Users/me/OpenFace-2.2.0/smoke_test/data/img1_2026-04-13_02-55-53.jpg\n"
            "Camera parameters:1000.52,1000.52,640,480.5\n"
        )
        sa = _cmp.sanitize_of_details_text(a)
        sb = _cmp.sanitize_of_details_text(b)
        self.assertEqual(sa, sb)

    def test_backslash_path_basename(self) -> None:
        raw = r"Input:C:\Users\me\smoke_test\data\img1_2026-04-13_02-55-53.jpg"
        out = _cmp.sanitize_of_details_text(raw + "\n")
        self.assertIn("Input:img1_2026-04-13_02-55-53.jpg", out)


class TestCompareTolerantOfDetailsFiles(unittest.TestCase):
    def test_temp_files_identical_after_sanitize(self) -> None:
        body = (
            "Output HOG:img1_2026-04-13_02-55-53.hog\n"
            "Camera parameters:1000.52,1000.52,640,480.5\n"
            "Gaze: 1\n"
        )
        a_text = (
            "Input:/home/runner/work/OpenFace-2.2.0/OpenFace-2.2.0/smoke_test/data/img1_2026-04-13_02-55-53.jpg\n"
            "Input full path:/home/runner/work/OpenFace-2.2.0/OpenFace-2.2.0/smoke_test/data/img1_2026-04-13_02-55-53.jpg\n"
        ) + body
        b_text = (
            "Input:/mnt/c/Users/me/OpenFace-2.2.0/smoke_test/data/img1_2026-04-13_02-55-53.jpg\n"
            "Input full path:/mnt/c/Users/me/OpenFace-2.2.0/smoke_test/data/img1_2026-04-13_02-55-53.jpg\n"
        ) + body
        with tempfile.TemporaryDirectory() as tmp:
            tdir = Path(tmp)
            ap = tdir / "img1_2026-04-13_02-55-53_of_details.txt"
            bp = tdir / "img1_2026-04-13_02-55-53_of_details.txt"
            ap.write_text(a_text, encoding="utf-8")
            bp.write_text(b_text, encoding="utf-8")
            ok, detail = _cmp.compare_tolerant_text(ap, bp, 1e-5)
            self.assertTrue(ok, detail)


if __name__ == "__main__":
    unittest.main()
