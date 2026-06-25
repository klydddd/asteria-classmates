# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

BosesPH Toolkit (`bosesph`) is a CLI-first pipeline for turning raw Philippine-language speech recordings into reusable speech datasets, ASR benchmarks, and optional fine-tuned models. The MVP targets Kapampangan using audio from the Philippine Languages Database (PLD). The architecture must remain language-agnostic.

## Build & Development

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Commands

```bash
ruff check .              # lint
black --check .           # format check
pytest                    # run all tests
pytest tests/test_pld.py  # run a single test file
pytest -k test_name       # run a single test by name
```

CLI entry point: `bosesph` (defined in `src/bosesph/cli.py:entrypoint`).

## Architecture

All pipeline logic lives in `src/bosesph/`. The CLI (`cli.py`) is a thin argparse wrapper that delegates to service modules:

- **`pld.py`** — Parses PLD session directories and `.log` files into `PldSession`/`PldTranscript` dataclasses.
- **`audio.py`** — Zero-dependency WAV inspection and standardization (mono, 16kHz, 16-bit PCM) using only the stdlib `wave` module. No ffmpeg/pydub.
- **`ingestion.py`** — Orchestrates a PLD session import: parses logs, inspects/standardizes audio, writes `metadata.csv` and `ingestion_report.json` atomically via temp dir + rename.
- **`metadata.py`** — Pydantic models (`MetadataRecord`, `ValidationReport`) and CSV validation. Defines audio ID patterns (`pam_000001`), quality statuses, dataset splits, and allowed transcript annotations (`[noise]`, `[laughter]`, `[unclear]`, `[silence]`).
- **`transcripts.py`** — Deterministic transcript normalization (Unicode NFC, whitespace, punctuation, annotation casing) with a JSON audit trail.
- **`review.py`** — Resumable interactive terminal review for pending/needs-review clips. Decisions persist immediately to `metadata.csv`.
- **`dataset.py`** — Filters approved clips, performs speaker-aware train/val/test splitting, copies clean audio, and writes split CSVs plus `statistics.json` and a dataset card.
- **`asr.py`** — Lazy-loaded ASR inference and WER/CER evaluation via HuggingFace `transformers` + `jiwer`. Reuses `audio.py` for stdlib WAV loading (no ffmpeg). Optional `[asr]` extras.
- **`benchmark.py`** — Benchmark orchestration and report generation: baseline runs, comparison reports.
- **`finetune.py`** — Whisper fine-tuning via `Seq2SeqTrainer` with a custom `torch.utils.data.Dataset` and speech collator. Reuses `asr._load_audio_array` for stdlib audio. Optional `[train]` extras (extends `[asr]`).

Data flows linearly: `pld.py` → `ingestion.py` → `transcripts.py` → `review.py` → `dataset.py` → `asr.py`/`benchmark.py` → `finetune.py`.

## Key Conventions

- **Python 3.10+**, type hints everywhere, Pydantic v2 for models and validation.
- **No external audio dependencies** — `audio.py` uses only stdlib `wave` and `struct`. This is intentional.
- **Atomic file writes** — ingestion and transcript normalization write to a temp directory then rename, so a crash never leaves partial output.
- **Exit codes are meaningful** — 0 = success, 1 = completed with warnings/review needed, 2 = input error. The custom `ArgumentParser` raises `ParserExit` instead of calling `sys.exit()` so the CLI is testable.
- Tests use synthetic WAV fixtures generated in `tests/audio_fixtures.py`. Never use private or PLD audio in tests.
- The `PLD/` directory contains real PLD recordings and is gitignored. Never commit its contents.
- `outputs/` is for generated artifacts and is also gitignored.

## Project Documents

- `Requirements.md` — Full product requirements and architecture spec.
- `Tasks.md` — Phased build plan with implementation status.
- `AGENTS.md` — Repository conventions for AI contributors.
- `docs/dataset_format.md` — Metadata field definitions and validation rules.
- `docs/transcription_guidelines.md` — Kapampangan transcription policy.
