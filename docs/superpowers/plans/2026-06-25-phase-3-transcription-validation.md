# Phase 3 Transcript Normalization and Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Normalize Phase 2 transcripts conservatively and provide a resumable
interactive CLI review flow that produces approved metadata for Phase 4.

**Architecture:** A focused transcript module handles pure text normalization
and atomic dataset updates. A separate review module owns terminal interaction
through injected input/output callables, keeping reviewer behavior directly
testable. The existing CLI delegates to both services and maps their outcomes
to stable process exit codes.

**Tech Stack:** Python 3.10+, standard-library `csv`, `json`, `re`,
`unicodedata`, `tempfile`, Pydantic, argparse, pytest, Ruff, Black.

---

### Task 1: Transcript normalization primitives

**Files:**
- Create: `src/bosesph/transcripts.py`
- Create: `tests/test_transcripts.py`

- [ ] Write failing tests for Unicode NFC, whitespace, punctuation, annotation
  casing, sentence initials, control characters, unresolved symbols, empty
  text, and idempotence.
- [ ] Run `../../.venv/bin/pytest tests/test_transcripts.py -v` and confirm the
  tests fail because the transcript API does not exist.
- [ ] Implement `NormalizationChange`, `NormalizationWarning`,
  `NormalizationResult`, and `normalize_transcript(text)`.
- [ ] Rerun the focused tests and confirm they pass.

### Task 2: Dataset normalization and atomic publication

**Files:**
- Modify: `src/bosesph/transcripts.py`
- Modify: `tests/test_transcripts.py`

- [ ] Write failing tests for metadata updates, report output, warning routing,
  note deduplication, invalid metadata rollback, and rerun idempotence.
- [ ] Run the focused tests and confirm the new cases fail for missing dataset
  behavior.
- [ ] Implement `NormalizationReport`, `TranscriptDatasetError`, and
  `normalize_dataset(dataset_path)` using staged files and atomic replacement.
- [ ] Rerun the focused tests and the existing metadata tests.

### Task 3: Resumable interactive review

**Files:**
- Create: `src/bosesph/review.py`
- Create: `tests/test_review.py`

- [ ] Write failing tests for approve, needs-fix and reject notes, skip, quit,
  resume, missing audio, and invalid dataset input.
- [ ] Run `../../.venv/bin/pytest tests/test_review.py -v` and confirm failure
  because the review API does not exist.
- [ ] Implement `ReviewSummary`, `ReviewError`, and `review_dataset()` with
  injected `input_fn` and `output_fn`.
- [ ] Atomically checkpoint each disposition and preserve earlier decisions on
  quit or interruption.
- [ ] Rerun review and metadata tests.

### Task 4: CLI and end-to-end integration

**Files:**
- Modify: `src/bosesph/cli.py`
- Modify: `tests/test_cli.py`
- Modify: `tests/test_ingestion.py`

- [ ] Write failing CLI tests for both commands, summaries, warning exit code,
  invalid input, and scripted review input.
- [ ] Write a failing synthetic integration test covering PLD import,
  normalization, and reviewer approval.
- [ ] Add `normalize-transcripts DATASET` and `review DATASET` parsers and
  command handlers.
- [ ] Run focused CLI and ingestion tests until green.

### Task 5: Documentation and completion

**Files:**
- Modify: `README.md`
- Modify: `Tasks.md`
- Modify: `Simple_Tasks.md`

- [ ] Document command usage, generated reports, status behavior, and the
  external-player review workflow.
- [ ] Mark all Phase 3 tasks complete with the implementation date.
- [ ] Run `../../.venv/bin/ruff check .`,
  `../../.venv/bin/black --check .`, `../../.venv/bin/pytest`, and
  `git diff --check`.
- [ ] Commit the verified Phase 3 implementation.

