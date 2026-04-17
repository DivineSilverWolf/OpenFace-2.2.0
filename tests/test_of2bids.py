"""Unit tests for tools/of2bids BIDS derivative export."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_TOOLS = _REPO / "tools"
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

from of2bids.csv_reader import read_openface_csv  # noqa: E402
from of2bids.details_parser import parse_of_details  # noqa: E402
from of2bids.export_bids import discover_scan_pairs, export_openface_pair  # noqa: E402
from of2bids.sampling import infer_sampling_frequency_hz  # noqa: E402
from of2bids.validators import check_timestamp_monotonicity  # noqa: E402


_FIX = _REPO / "tests" / "of2bids_fixtures"


class TestSampling(unittest.TestCase):
    def test_infer_hz_from_timestamps(self) -> None:
        ts = [0.0, 1 / 30.0, 2 / 30.0]
        hz = infer_sampling_frequency_hz(ts)
        self.assertIsNotNone(hz)
        self.assertAlmostEqual(hz, 30.0, places=4)


class TestMonotonic(unittest.TestCase):
    def test_ok(self) -> None:
        st, _ = check_timestamp_monotonicity([0.0, 0.1, 0.2], strict=False)
        self.assertEqual(st.value, "ok")

    def test_dup_warn(self) -> None:
        st, msgs = check_timestamp_monotonicity([0.0, 0.1, 0.1], strict=False)
        self.assertIn("duplicate", msgs[0].lower())


class TestExportOpenFace(unittest.TestCase):
    def test_export_creates_tsv_json_and_sampling(self) -> None:
        csv_p = _FIX / "synthetic.csv"
        det_p = _FIX / "synthetic_of_details.txt"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            export_openface_pair(
                bids_root=root,
                csv_path=csv_p,
                details_path=det_p,
                subject="01",
                task="rest",
                recording=None,
                run=None,
                events_tsv=_FIX / "sub-01_task-rest_events.tsv",
                events_json=_FIX / "sub-01_task-rest_events.json",
                merge_events=True,
                strict_timestamps=False,
                prefer_details_fps=True,
                of2bids_version="0.test",
                dry_run=False,
            )
            func = root / "derivatives" / "openface" / "sub-01" / "func"
            tsv = func / "sub-01_task-rest_desc-openface_timeseries.tsv"
            js = func / "sub-01_task-rest_desc-openface_timeseries.json"
            mtsv = func / "sub-01_task-rest_desc-openfacewithevents_timeseries.tsv"
            self.assertTrue(tsv.is_file())
            self.assertTrue(js.is_file())
            self.assertTrue(mtsv.is_file())
            meta = json.loads(js.read_text(encoding="utf-8"))
            self.assertTrue(meta.get("OpenFaceDerivative"))
            self.assertIn("SamplingFrequency", meta)
            self.assertAlmostEqual(float(meta["SamplingFrequency"]), 30.0, places=3)
            self.assertIn("TimeAlignment", meta)
            self.assertIn("OpenFaceTimestamp", meta["TimeAlignment"])
            self.assertIn("LSLReplayModeA", meta["TimeAlignment"])
            self.assertIn("AssociatedEvents", meta)
            self.assertEqual(
                meta["AssociatedEvents"].get("mergeStrategy"),
                "asof_backward_on_onset",
            )
            evp = meta["AssociatedEvents"]["path"].replace("\\", "/")
            self.assertIn("sub-01_task-rest_events.tsv", evp)

    def test_export_without_events_still_has_time_alignment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            export_openface_pair(
                bids_root=root,
                csv_path=_FIX / "synthetic.csv",
                details_path=_FIX / "synthetic_of_details.txt",
                subject="01",
                task="rest",
                recording=None,
                run=None,
                events_tsv=None,
                events_json=None,
                merge_events=False,
                strict_timestamps=False,
                prefer_details_fps=True,
                of2bids_version="0.test",
                dry_run=False,
            )
            js = root / "derivatives" / "openface" / "sub-01" / "func" / "sub-01_task-rest_desc-openface_timeseries.json"
            meta = json.loads(js.read_text(encoding="utf-8"))
            self.assertIn("TimeAlignment", meta)
            self.assertNotIn("AssociatedEvents", meta)

    def test_non_monotonic_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(ValueError):
                export_openface_pair(
                    bids_root=root,
                    csv_path=_FIX / "bad_nonmonotonic.csv",
                    details_path=_FIX / "synthetic_of_details.txt",
                    subject="01",
                    task="rest",
                    recording=None,
                    run=None,
                    events_tsv=None,
                    events_json=None,
                    merge_events=False,
                    strict_timestamps=False,
                    prefer_details_fps=False,
                    of2bids_version="0.test",
                    dry_run=False,
                )

    def test_discover_scan_pairs(self) -> None:
        pairs = discover_scan_pairs(_FIX, recursive=False)
        stems = {a.name for a, _ in pairs}
        self.assertIn("synthetic.csv", stems)


class TestDetailsParser(unittest.TestCase):
    def test_fps_line(self) -> None:
        m = parse_of_details(_FIX / "synthetic_of_details.txt")
        self.assertEqual(m.fps_from_file, 30.0)


class TestReadCsv(unittest.TestCase):
    def test_types(self) -> None:
        tab = read_openface_csv(_FIX / "synthetic.csv")
        self.assertTrue(tab.is_sequence)
        self.assertEqual(len(tab.rows), 3)

    def test_duplicate_timestamps_warn(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            logs = export_openface_pair(
                bids_root=root,
                csv_path=_FIX / "synthetic_with_dup.csv",
                details_path=_FIX / "synthetic_of_details.txt",
                subject="01",
                task="rest",
                recording=None,
                run=None,
                events_tsv=None,
                events_json=None,
                merge_events=False,
                strict_timestamps=False,
                prefer_details_fps=False,
                of2bids_version="0.test",
                dry_run=False,
            )
            self.assertTrue(any("duplicate" in m.lower() for m in logs))

    def test_strict_duplicate_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(ValueError):
                export_openface_pair(
                    bids_root=root,
                    csv_path=_FIX / "synthetic_with_dup.csv",
                    details_path=_FIX / "synthetic_of_details.txt",
                    subject="01",
                    task="rest",
                    recording=None,
                    run=None,
                    events_tsv=None,
                    events_json=None,
                    merge_events=False,
                    strict_timestamps=True,
                    prefer_details_fps=False,
                    of2bids_version="0.test",
                    dry_run=False,
                )


if __name__ == "__main__":
    unittest.main()
