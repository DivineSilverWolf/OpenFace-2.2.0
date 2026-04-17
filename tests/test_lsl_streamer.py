"""Unit tests for tools.lsl_streamer (no liblsl required; uses fake pylsl for replay)."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_REPO_ROOT = Path(__file__).resolve().parents[1]
_FIXTURE = _REPO_ROOT / "tests" / "fixtures" / "lsl_streamer" / "minimal_openface.csv"

if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools.lsl_streamer.columns import group_columns
from tools.lsl_streamer.csv_load import (
    estimate_nominal_srate,
    iter_sample_times,
    load_openface_csv,
    timestamps_seconds,
)
from tools.lsl_streamer import lsl_outlets
from tools.lsl_streamer.cli import main as cli_main
from tools.lsl_streamer.lsl_outlets import build_specs, replay_csv_to_lsl


class _Ch:
    def append_child_value(self, k: str, v: str) -> None:
        return


class _Channels:
    def append_child(self, name: str) -> _Ch:
        return _Ch()


class _Desc:
    def append_child_value(self, k: str, v: str) -> None:
        return

    def append_child(self, name: str) -> _Channels:
        return _Channels()


class FakeStreamInfo:
    def __init__(self, name: str, stype: str, n_ch: int, rate: float, fmt: int, source_id: str) -> None:
        self.name = name
        self.stype = stype
        self.n_ch = n_ch
        self.rate = rate
        self.fmt = fmt
        self.source_id = source_id

    def desc(self) -> _Desc:
        return _Desc()


class FakeOutlet:
    created: list[FakeStreamInfo] = []
    pushes: list[tuple[str, list[float], float]] = []

    def __init__(self, info: FakeStreamInfo) -> None:
        self._info = info
        FakeOutlet.created.append(info)

    def push_sample(self, sample: list[float], timestamp: float = 0.0, pushthrough: bool = True) -> None:
        FakeOutlet.pushes.append((self._info.name, list(sample), float(timestamp)))


class FakePylsl:
    cf_float32 = 1
    StreamInfo = FakeStreamInfo
    StreamOutlet = FakeOutlet

    @staticmethod
    def local_clock() -> float:
        return 1000.0


class TestCsvLoad(unittest.TestCase):
    def test_load_fixture(self) -> None:
        loaded = load_openface_csv(_FIXTURE)
        self.assertIn("timestamp", loaded.headers)
        self.assertEqual(len(loaded.rows), 3)
        ts = timestamps_seconds(loaded)
        assert ts is not None
        self.assertAlmostEqual(ts[1] - ts[0], 0.033, places=3)

    def test_nominal_srate_from_timestamps(self) -> None:
        loaded = load_openface_csv(_FIXTURE)
        ts = timestamps_seconds(loaded)
        r = estimate_nominal_srate(ts, None)
        # Median delta between 0.033 and 0.034 s → ~29.85 Hz
        self.assertAlmostEqual(r, 29.85, places=1)

    def test_nominal_srate_fps_override(self) -> None:
        r = estimate_nominal_srate([0.0, 0.5, 1.0], 60.0)
        self.assertEqual(r, 60.0)

    def test_iter_sample_times_fallback(self) -> None:
        t = list(iter_sample_times(None, 4, 25.0))
        self.assertEqual(len(t), 4)
        self.assertAlmostEqual(t[3], 3 / 25.0)


class TestColumnGroups(unittest.TestCase):
    def test_group_columns_order(self) -> None:
        loaded = load_openface_csv(_FIXTURE)
        g = group_columns(loaded.headers)
        self.assertEqual(g.au_r, ["AU01_r", "AU12_r"])
        self.assertEqual(g.au_c, ["AU01_c", "AU12_c"])
        self.assertIn("confidence", g.core)


class TestBuildSpecs(unittest.TestCase):
    def test_split_layout(self) -> None:
        loaded = load_openface_csv(_FIXTURE)
        g = group_columns(loaded.headers)
        specs = build_specs("OF", g, "split")
        names = {s.name for s in specs}
        self.assertEqual(names, {"OF-AU", "OF-core"})


class TestReplayMockPylsl(unittest.TestCase):
    def setUp(self) -> None:
        FakeOutlet.created.clear()
        FakeOutlet.pushes.clear()

    def test_replay_split_pushes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sc = Path(tmp)
            replay_csv_to_lsl(
                _FIXTURE,
                stream_name="OF",
                layout="split",
                subject_id="S01",
                run_id="run01",
                openface_version="2.2.0-test",
                fps=None,
                source_id="src_test",
                realtime=False,
                sidecar_dir=sc,
                pylsl_module=FakePylsl,
            )
        # Two outlets × 3 rows = 6 pushes interleaved per row order in code: both each row
        self.assertEqual(len(FakeOutlet.pushes), 6)
        au_first = FakeOutlet.pushes[0]
        self.assertEqual(au_first[0], "OF-AU")
        self.assertEqual(len(au_first[1]), 4)
        core_first = FakeOutlet.pushes[1]
        self.assertEqual(core_first[0], "OF-core")
        self.assertEqual(len(core_first[1]), len(group_columns(load_openface_csv(_FIXTURE).headers).core))
        # Timestamps monotonic in LSL space
        self.assertAlmostEqual(FakeOutlet.pushes[0][2], 1000.0, places=5)
        self.assertGreater(FakeOutlet.pushes[2][2], FakeOutlet.pushes[0][2])

    def test_sidecar_written(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sc = Path(tmp)
            replay_csv_to_lsl(
                _FIXTURE,
                stream_name="OF",
                layout="split",
                subject_id=None,
                run_id=None,
                openface_version="x",
                fps=30.0,
                source_id="sid",
                realtime=False,
                sidecar_dir=sc,
                pylsl_module=FakePylsl,
            )
            files = list(sc.glob("*.json"))
            self.assertEqual(len(files), 2)
            data = json.loads(files[0].read_text(encoding="utf-8"))
            self.assertIn("LSL", data)
            self.assertEqual(data["SoftwareFilters"]["OpenFace"]["Version"], "x")

    def test_replay_single_one_outlet(self) -> None:
        FakeOutlet.created.clear()
        FakeOutlet.pushes.clear()
        replay_csv_to_lsl(
            _FIXTURE,
            stream_name="OnlyOne",
            layout="single",
            subject_id=None,
            run_id=None,
            openface_version="x",
            fps=30.0,
            source_id="sid",
            realtime=False,
            sidecar_dir=None,
            pylsl_module=FakePylsl,
        )
        names = {p[0] for p in FakeOutlet.pushes}
        self.assertEqual(names, {"OnlyOne"})
        self.assertEqual(len(FakeOutlet.pushes), 3)
        self.assertEqual(len(FakeOutlet.pushes[0][1]), 20)


try:
    import pylsl  # noqa: F401, F811

    _HAVE_PYLSL = True
except Exception:
    _HAVE_PYLSL = False


@unittest.skipUnless(_HAVE_PYLSL, "pylsl / liblsl not available")
class TestPylslImport(unittest.TestCase):
    def test_has_pylsl_flag(self) -> None:
        self.assertTrue(lsl_outlets.HAS_PYLSL)


class TestCli(unittest.TestCase):
    def test_cli_missing_pylsl_exits_2(self) -> None:
        with patch.object(lsl_outlets, "HAS_PYLSL", False):
            code = cli_main([str(_FIXTURE)])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
