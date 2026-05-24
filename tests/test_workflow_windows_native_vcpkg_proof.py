"""Guardrails: Windows native vcpkg proof workflow stays wired (no PyYAML; Linux CI safe)."""
from __future__ import annotations

import unittest
from pathlib import Path


class TestWindowsNativeVcpkgProofWorkflow(unittest.TestCase):
    def test_yaml_contains_dispatch_preset_and_paths(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        wf = repo / ".github" / "workflows" / "windows-native-vcpkg-proof.yml"
        self.assertTrue(wf.is_file(), f"missing {wf}")
        text = wf.read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", text)
        self.assertIn("push:", text)
        self.assertIn("reengineering", text)
        self.assertIn("windows-msvc-vcpkg", text)
        self.assertIn("cmake --preset windows-msvc-vcpkg", text)
        self.assertIn("cmake --build --preset windows-msvc-vcpkg-release", text)
        self.assertIn("vcpkg.json", text)
        self.assertIn("CMakePresets.json", text)
        self.assertIn("lib/local/**/CMakeLists.txt", text)
        # Shallow vcpkg clone must fetch builtin-baseline or manifest install breaks (git show baseline.json).
        self.assertIn("git -C $vp fetch origin $baseline", text)
        # Parity with Linux CI: Python static checks + native smoke (no Docker).
        self.assertIn("vcpkg_manifest_validate.py", text)
        self.assertIn('unittest discover -s tests -p "test_workflow*.py"', text)
        self.assertIn('unittest discover -s tests -p "test_compare_smoke*.py"', text)
        self.assertIn('unittest discover -s tests -p "test_lsl_streamer*.py"', text)
        self.assertIn("tests.test_of2bids", text)
        self.assertIn("download_models.ps1", text)
        self.assertIn("Run-NativeSmokeAndCompare.ps1", text)
        self.assertIn("baseline_manifest_ci.json", text)

    def test_windows_native_tooling_scripts_exist(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        win = repo / "tools" / "windows"
        for name in (
            "README.md",
            "Ensure-NativeOpenFaceRepoLayout.ps1",
            "Remove-NativeOpenFaceRepoLayout.ps1",
            "Run-NativeSmokeAndCompare.ps1",
            "Run-WindowsNativeTestSuite.ps1",
        ):
            path = win / name
            self.assertTrue(path.is_file(), f"missing {path}")


if __name__ == "__main__":
    unittest.main()
