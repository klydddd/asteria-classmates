# Phase 2 PLD Audio Ingestion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a tested `bosesph import-pld` command that parses one PLD session, validates and standardizes its WAV files, and generates metadata and an ingestion report.

**Architecture:** Keep PLD log parsing, PCM WAV processing, and batch orchestration in separate modules. The existing CLI remains a thin adapter that converts service errors into documented exit codes. Tests generate small WAV fixtures and exercise each layer before the real `PLD/PAM/0400` integration run.

**Tech Stack:** Python 3.10+, standard-library `argparse`, `wave`, `struct`, `math`, `csv`, `json`, `tempfile`, Pydantic, pytest, Ruff, Black.

---

## File Map

- Create `src/bosesph/pld.py`: PLD session models, parser, and structural errors.
- Create `src/bosesph/audio.py`: PCM decoding, inspection, silence detection, mono conversion, resampling, and WAV writing.
- Create `src/bosesph/ingestion.py`: deterministic matching, statuses, staged publication, metadata CSV, and JSON reporting.
- Modify `src/bosesph/cli.py`: expose `import-pld` and print summaries/errors.
- Create `tests/audio_fixtures.py`: reusable synthetic PCM WAV writer.
- Create `tests/test_pld.py`: PLD parser behavior.
- Create `tests/test_audio.py`: inspection and conversion behavior.
- Create `tests/test_ingestion.py`: complete service behavior and output safety.
- Modify `tests/test_cli.py`: command contract and exit codes.
- Modify `README.md`, `Tasks.md`, and `Simple_Tasks.md`: command documentation and completed task state.

### Task 1: Parse PLD Session Logs

**Files:**
- Create: `src/bosesph/pld.py`
- Create: `tests/test_pld.py`

- [ ] **Step 1: Write failing parser tests**

```python
def test_parse_pld_session_reads_bom_metadata_and_transcripts(tmp_path: Path) -> None:
    log = tmp_path / "0400.session.log"
    log.write_text(
        "\ufeffSessionID = \"120223.051412\"\n"
        "SessionEnvironment = \"closed empty room\"\n"
        "SpeakerID = \"0400\"\n"
        "SpeakerGender = \"male\"\n"
        'clip.0002.wav "KAP_Iso.txt" "Masanting ya ing aldo."\n',
        encoding="utf-8",
    )

    session = parse_pld_session(tmp_path)

    assert session.session_id == "120223.051412"
    assert session.speaker_id == "spk_0400"
    assert session.transcripts[0].filename == "clip.0002.wav"
    assert session.transcripts[0].transcript == "Masanting ya ing aldo."
```

Also test missing/multiple logs, malformed transcript rows, duplicate filenames,
and absent required `SessionID` or `SpeakerID`.

- [ ] **Step 2: Run parser tests and verify RED**

Run: `.venv/bin/pytest tests/test_pld.py -q`

Expected: collection failure because `bosesph.pld` does not exist.

- [ ] **Step 3: Implement typed PLD parsing**

Create frozen dataclasses `PldTranscript` and `PldSession`, plus
`PldParseError`. Implement `parse_pld_session(source: Path) -> PldSession` using
`shlex.split` for transcript rows and a strict key/value pattern for session
fields. Reject structural ambiguity while retaining prompt-list names for the
reporting layer.

- [ ] **Step 4: Run parser tests and verify GREEN**

Run: `.venv/bin/pytest tests/test_pld.py -q`

Expected: all parser tests pass.

### Task 2: Inspect and Standardize PCM WAV

**Files:**
- Create: `tests/audio_fixtures.py`
- Create: `tests/test_audio.py`
- Create: `src/bosesph/audio.py`

- [ ] **Step 1: Add a synthetic WAV fixture helper**

Implement:

```python
def write_pcm_wav(
    path: Path,
    *,
    duration: float,
    sample_rate: int = 16000,
    channels: int = 1,
    sample_width: int = 2,
    amplitude: float = 0.25,
) -> None:
    ...
```

The helper writes deterministic sine-wave PCM and can write silence when
`amplitude=0`.

- [ ] **Step 2: Write failing audio tests**

Cover:

```python
def test_standardize_wav_resamples_stereo_to_16khz_mono(tmp_path: Path) -> None:
    source = tmp_path / "source.wav"
    output = tmp_path / "output.wav"
    write_pcm_wav(source, duration=0.2, sample_rate=44100, channels=2)

    inspection = standardize_wav(source, output)

    assert inspection.sample_rate == 44100
    with wave.open(str(output), "rb") as audio:
        assert audio.getframerate() == 16000
        assert audio.getnchannels() == 1
        assert audio.getsampwidth() == 2
```

Also cover 8-, 16-, 24-, and 32-bit decoding; zero-frame files; corrupt files;
fully silent files; quiet files at or below `0.001` RMS; and normal audio.

- [ ] **Step 3: Run audio tests and verify RED**

Run: `.venv/bin/pytest tests/test_audio.py -q`

Expected: collection failure because `bosesph.audio` does not exist.

- [ ] **Step 4: Implement audio processing**

Define `AudioInspection`, `AudioError`, `CorruptAudioError`,
`EmptyAudioError`, and `UnsupportedAudioError`. Decode integer PCM to
normalized floats, calculate RMS, average channels, linearly resample to
16 kHz, clamp, and write signed little-endian 16-bit mono PCM.

Expose:

```python
def inspect_wav(path: Path) -> AudioInspection: ...
def standardize_wav(source: Path, output: Path) -> AudioInspection: ...
```

- [ ] **Step 5: Run audio tests and verify GREEN**

Run: `.venv/bin/pytest tests/test_audio.py -q`

Expected: all audio tests pass.

### Task 3: Build the Ingestion Service

**Files:**
- Create: `tests/test_ingestion.py`
- Create: `src/bosesph/ingestion.py`

- [ ] **Step 1: Write failing happy-path and status tests**

Create a temporary PLD session with transcript rows deliberately out of order
and WAV fixtures of 6 seconds, 2 seconds, and quiet nonzero audio. Assert:

```python
result = import_pld_session(source, output)

assert result.counts == {"pending": 1, "needs_review": 2, "rejected": 0}
assert [row["audio_id"] for row in read_csv(output / "metadata.csv")] == [
    "pam_000001",
    "pam_000002",
    "pam_000003",
]
assert validate_metadata_csv(output / "metadata.csv").error_count == 0
```

Verify source bytes remain unchanged and every exported WAV is 16 kHz mono
16-bit PCM.

- [ ] **Step 2: Run service tests and verify RED**

Run: `.venv/bin/pytest tests/test_ingestion.py -q`

Expected: collection failure because `bosesph.ingestion` does not exist.

- [ ] **Step 3: Implement matching, statuses, and serialization**

Define Pydantic report models for reason codes, per-clip results, counts, and
the complete report. Implement deterministic filename sorting and IDs,
clip-level handling for missing/corrupt/empty/unsupported/silent audio, and CSV
serialization using the complete metadata column order from
`bosesph.metadata`.

Use `pending` for 5–15-second normal audio, `needs_review` for nonstandard
duration or quiet audio, and `rejected` for non-exportable clips.

- [ ] **Step 4: Add rejection and report tests**

Test missing referenced WAV, unreferenced WAV, corrupt input, empty input,
fully silent input, and simulated conversion failure. Assert reason codes,
counts, generated filename presence, and absence of rejected rows from
`metadata.csv`.

- [ ] **Step 5: Run service tests and verify GREEN**

Run: `.venv/bin/pytest tests/test_ingestion.py -q`

Expected: happy-path and rejection tests pass.

### Task 4: Make Publication Safe

**Files:**
- Modify: `tests/test_ingestion.py`
- Modify: `src/bosesph/ingestion.py`

- [ ] **Step 1: Write failing output-safety tests**

Test that:

- a nonempty output directory raises `OutputExistsError` without overwrite;
- `overwrite=True` replaces stale generated content;
- malformed source validation leaves existing output untouched; and
- temporary stage/backup directories are removed after success.

- [ ] **Step 2: Run safety tests and verify RED**

Run: `.venv/bin/pytest tests/test_ingestion.py -q -k "overwrite or output"`

Expected: failures showing missing overwrite and staged-publication behavior.

- [ ] **Step 3: Implement staged publication**

Validate the PLD session before creating a stage directory. Generate all files
in a sibling temporary directory. Publish with same-filesystem renames and
restore a backup if replacement fails. Clean up stage and backup paths in
`finally` blocks.

- [ ] **Step 4: Run safety tests and verify GREEN**

Run: `.venv/bin/pytest tests/test_ingestion.py -q`

Expected: all ingestion tests pass.

### Task 5: Expose `bosesph import-pld`

**Files:**
- Modify: `tests/test_cli.py`
- Modify: `src/bosesph/cli.py`

- [ ] **Step 1: Write failing CLI tests**

Cover successful invocation, `--overwrite`, missing source, malformed source,
and existing output. The success assertion includes:

```python
exit_code = main(["import-pld", str(source), "--output", str(output)])
captured = capsys.readouterr()

assert exit_code == 0
assert "Pending:" in captured.out
assert "Needs review:" in captured.out
assert (output / "metadata.csv").exists()
```

Command-level failures must return `2` and print `Input error:` to standard
error.

- [ ] **Step 2: Run CLI tests and verify RED**

Run: `.venv/bin/pytest tests/test_cli.py -q -k import_pld`

Expected: parser failure because `import-pld` is not registered.

- [ ] **Step 3: Implement the CLI adapter**

Register positional `source`, required `--output`, and boolean `--overwrite`.
Invoke `import_pld_session`, print status counts and output path, and catch only
documented command-level ingestion/parser/filesystem errors.

- [ ] **Step 4: Run CLI and complete test suites**

Run:

```bash
.venv/bin/pytest tests/test_cli.py -q
.venv/bin/pytest -q
```

Expected: all tests pass.

### Task 6: Document and Verify Phase 2

**Files:**
- Modify: `README.md`
- Modify: `Tasks.md`
- Modify: `Simple_Tasks.md`

- [ ] **Step 1: Run the real PLD integration**

Run:

```bash
.venv/bin/bosesph import-pld PLD/PAM/0400 \
  --output outputs/dataset \
  --overwrite
.venv/bin/bosesph validate-metadata outputs/dataset/metadata.csv
```

Expected: 397 source transcript rows are accounted for, generated metadata has
zero errors, and all exported recordings are standardized.

- [ ] **Step 2: Independently inspect integration output**

Read `outputs/dataset/ingestion_report.json` and verify:

- totals equal the discovered source files/transcripts;
- status counts add to total results;
- metadata row count equals pending plus needs-review clips; and
- every metadata path exists.

- [ ] **Step 3: Update project documentation**

Document `import-pld` usage and output in `README.md`. Mark Phase 1.3 and Phase
2.1–2.4 complete with the completion date and concise implementation notes in
`Tasks.md`. Check the matching items in `Simple_Tasks.md`.

- [ ] **Step 4: Run full verification**

Run:

```bash
.venv/bin/ruff check .
.venv/bin/black --check .
.venv/bin/pytest
git diff --check
```

Expected: every command exits `0`.

- [ ] **Step 5: Review tracked changes**

Run: `git status --short`

Expected: only Phase 2 source, tests, documentation, task tracking, and plan
changes are present; generated `outputs/` files remain ignored.
