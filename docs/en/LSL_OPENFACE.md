# OpenFace and Lab Streaming Layer (LSL)

**How this fits BIDS / EEG clocks:** read **[INTEGRATION_LSL_BIDS.md](INTEGRATION_LSL_BIDS.md)** first.

This document describes **Mode A** integration in this fork: replaying OpenFace `FeatureExtraction` CSV files into **LSL outlets** for a synchronizable time series (e.g. alongside EEG or eye-tracking streams recorded with LSL).

LSL (Lab Streaming Layer) provides networked streams with timing metadata. **XDF** is a common container for multi-stream recordings; stream headers come from LSL, and additional metadata can live in sidecar JSON aligned with BIDS / companion conventions.

## Mode A (implemented): post-hoc CSV → LSL

OpenFace writes one row per processed frame with a `timestamp` column (seconds, when available from the source) plus `frame`, `face_id`, and many feature columns. The utility under `tools/lsl_streamer/`:

- Reads the CSV using **OpenFace column names** as produced by `FeatureExtraction`.
- Estimates **nominal sampling rate** from successive `timestamp` values (or uses `--fps`).
- Creates one or two **float32** continuous streams:
  - **split** (default): `\<stream-name\>-AU` (all `AU*_r` and `AU*_c` columns present) and `\<stream-name\>-core` (confidence, success, gaze vectors/angles, head pose).
  - **single**: one stream combining AU + core in a fixed column order (AU intensities, then AU presence, then core columns).
- Pushes each row with an LSL timestamp aligned to **`local_clock()`** so that **relative timing** matches the CSV: `lsl_t = t0_lsl + (csv_timestamp - csv_timestamp_first)`.

### Install

1. Install a **liblsl** build for your operating system (see [LabStreamingLayer releases](https://github.com/sccn/liblsl/releases)).
2. Install Python bindings:

```bash
pip install -r tools/lsl_streamer/requirements.txt
```

Optional: `tools/lsl_streamer/pyproject.toml` lists the same dependency for tooling that reads PEP 621 metadata.

### CLI (from repository root)

```bash
python -m tools.lsl_streamer path/to/video_of.csv --stream-name OpenFace --subject-id S01 --run-id 001
```

Useful flags:

- `--layout split|single` — default `split`.
- `--fps 30` — override nominal rate if timestamps are missing or unreliable.
- `--openface-version 2.2.0` — stored in LSL `desc` and JSON sidecar.
- `--sidecar-dir ./meta` — writes one JSON file per stream with **XDF-oriented** fields (stream name, nominal rate, channel labels, OpenFace version placeholder, CSV path).
- `--realtime` — sleep between samples to approximate real-time delivery (default pushes as fast as possible).

### XDF-oriented metadata

LSL `StreamInfo` carries a small XML `desc` tree. The tool adds key/value pairs such as `source`, `openface_version`, `csv_path`, `stream_role`, optional `subject_id` / `run_id`, and per-channel `<label>` entries under `<channels>`.

For richer metadata compatible with archiving pipelines, the optional **JSON sidecar** mirrors common EEG/BIDS-adjacent ideas:

- `SoftwareFilters.OpenFace.Version` — set via `--openface-version`.
- `LSL.channel_labels` — same order as LSL channels.
- `OpenFace.column_map` — documents canonical OpenFace columns (`timestamp`, `frame`, `face_id`).

When merging with other modalities into XDF, map these sidecars into the recording’s meta structure alongside **`tools/of2bids/`** for BIDS conversion; keep **OpenFace `timestamp`** and LSL clock semantics aligned with [INTEGRATION_LSL_BIDS.md](INTEGRATION_LSL_BIDS.md).

## Limitations

- **Landmarks / full mesh columns** are not streamed by default (hundreds of channels). Extend the column lists in `tools/lsl_streamer/columns.py` if your study needs them (allowed zone: `tools/**`).
- **Post-hoc burst** mode can push samples with timestamps in the past relative to “now”; some receivers assume near-present timestamps. Prefer `--realtime` for interactive demos, or consume immediately after starting the outlet.
- **Multiple faces** (`face_id`): all rows are pushed in file order; downstream should filter on `face_id` if you add it as a channel (not included in default streams).

## Mode B (future work): near real-time from webcam

Near real-time LSL from a live camera would require **pushing samples from inside or alongside** `FeatureExtraction` as each frame is processed, or an IPC bridge from the C++ executable. That touches the `exe/FeatureExtraction` pipeline and is **not** implemented here. A practical path:

1. Add an optional compile-time or runtime hook in the **executable** layer (`exe/**`) to serialize a compact feature vector per frame to stdout, a named pipe, or a ZeroMQ socket.
2. Keep LSL-specific code in **Python** under `tools/lsl_streamer/` reading that stream and calling `push_sample` with `local_clock()` timestamps.

This keeps `lib/local/**` (algorithm core) unchanged while still enabling live fusion in a separate process.

## Related tooling

- **BIDS derivatives:** `tools/of2bids/` — see [BIDS_OPENFACE_DERIVATIVES.md](BIDS_OPENFACE_DERIVATIVES.md).
- **Single time model (LSL + BIDS + events):** [INTEGRATION_LSL_BIDS.md](INTEGRATION_LSL_BIDS.md).

## Tests

From repository root:

```bash
python -m unittest discover -s tests -p "test_lsl_streamer*.py" -v
```

Tests use a **synthetic CSV** under `tests/fixtures/lsl_streamer/` and a **fake pylsl** module so CI does not require liblsl. If `pylsl` is installed, an extra test asserts the `HAS_PYLSL` flag.

### Local integration test (real LSL)

With liblsl installed and an LSL viewer running (e.g. LabRecorder or another inlet):

```bash
python -m tools.lsl_streamer tests/fixtures/lsl_streamer/minimal_openface.csv --stream-name DemoOF --sidecar-dir ./lsl_meta_out
```

Confirm that streams appear and sample counts match the CSV row count per layout.
