"""Resumable terminal review for generated speech metadata."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Callable
from pathlib import Path

from pydantic import BaseModel

from bosesph.metadata import QualityStatus
from bosesph.transcripts import (
    TranscriptDatasetError,
    _append_note,
    _read_rows,
    _validate_rows,
    _write_csv,
)


class ReviewError(ValueError):
    """Raised when a dataset cannot be reviewed safely."""


class ReviewSummary(BaseModel):
    """Disposition counts for one interactive review session."""

    approved: int = 0
    needs_fix: int = 0
    rejected: int = 0
    skipped: int = 0
    remaining: int = 0
    quit: bool = False


def _checkpoint(
    metadata_path: Path,
    fieldnames: list[str],
    rows: list[dict[str, str]],
) -> None:
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".metadata-review-",
        suffix=".csv",
        dir=metadata_path.parent,
    )
    os.close(descriptor)
    temporary_path = Path(temporary_name)
    try:
        _validate_rows(rows)
        _write_csv(temporary_path, fieldnames, rows)
        os.replace(temporary_path, metadata_path)
    except (OSError, TranscriptDatasetError) as error:
        raise ReviewError(str(error)) from error
    finally:
        temporary_path.unlink(missing_ok=True)


def _display_clip(
    dataset: Path,
    row: dict[str, str],
    output_fn: Callable[[str], object],
) -> Path:
    audio_path = dataset / row["file_path"]
    output_fn("")
    output_fn(f"Audio ID: {row['audio_id']}")
    output_fn(f"Audio path: {audio_path}")
    output_fn(f"Transcript: {row['transcript']}")
    output_fn(f"Language: {row['language']}")
    output_fn(f"Speaker: {row['speaker_id']}")
    output_fn(f"Region: {row.get('region') or '(not provided)'}")
    output_fn(f"Age group: {row.get('speaker_age_group') or '(not provided)'}")
    output_fn(f"Gender: {row.get('speaker_gender') or '(not provided)'}")
    output_fn(f"Duration: {row['duration_seconds']} seconds")
    output_fn(f"Current status: {row['quality_status']}")
    output_fn(f"Reviewer notes: {row.get('reviewer_notes') or '(none)'}")
    output_fn("Checklist:")
    output_fn("- Audio understandable?")
    output_fn("- Transcript matches speech?")
    output_fn("- Language label correct?")
    output_fn("- Speaker metadata complete?")
    return audio_path


def _required_note(
    input_fn: Callable[[str], str],
    output_fn: Callable[[str], object],
) -> str:
    while True:
        note = input_fn("Reviewer note: ").strip()
        if note:
            return note
        output_fn("A note is required.")


def _remaining(rows: list[dict[str, str]]) -> int:
    reviewable = {
        QualityStatus.PENDING.value,
        QualityStatus.NEEDS_REVIEW.value,
    }
    return sum(row.get("quality_status") in reviewable for row in rows)


def review_dataset(
    dataset: str | Path,
    *,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], object] = print,
) -> ReviewSummary:
    """Interactively review pending rows and checkpoint every decision."""
    dataset_path = Path(dataset)
    metadata_path = dataset_path / "metadata.csv"
    try:
        fieldnames, rows = _read_rows(metadata_path)
        _validate_rows(rows)
    except TranscriptDatasetError as error:
        raise ReviewError(str(error)) from error

    summary = ReviewSummary()
    reviewable = {
        QualityStatus.PENDING.value,
        QualityStatus.NEEDS_REVIEW.value,
    }
    try:
        for row in rows:
            if row.get("quality_status") not in reviewable:
                continue
            audio_path = _display_clip(dataset_path, row, output_fn)
            while True:
                action = (
                    input_fn(
                        "Action [a]pprove, needs [f]ix, [r]eject, [s]kip, [q]uit: "
                    )
                    .strip()
                    .lower()
                )
                if action in {"a", "approve"}:
                    if not audio_path.is_file():
                        output_fn("Cannot approve: audio file is missing.")
                        continue
                    row["quality_status"] = QualityStatus.APPROVED.value
                    _checkpoint(metadata_path, fieldnames, rows)
                    summary.approved += 1
                    break
                if action in {"f", "fix", "needs_fix"}:
                    note = _required_note(input_fn, output_fn)
                    if "reviewer_notes" not in fieldnames:
                        fieldnames.append("reviewer_notes")
                    row["quality_status"] = QualityStatus.NEEDS_REVIEW.value
                    row["reviewer_notes"] = _append_note(
                        row.get("reviewer_notes", ""),
                        [note],
                    )
                    _checkpoint(metadata_path, fieldnames, rows)
                    summary.needs_fix += 1
                    break
                if action in {"r", "reject"}:
                    note = _required_note(input_fn, output_fn)
                    if "reviewer_notes" not in fieldnames:
                        fieldnames.append("reviewer_notes")
                    row["quality_status"] = QualityStatus.REJECTED.value
                    row["reviewer_notes"] = _append_note(
                        row.get("reviewer_notes", ""),
                        [note],
                    )
                    _checkpoint(metadata_path, fieldnames, rows)
                    summary.rejected += 1
                    break
                if action in {"s", "skip"}:
                    summary.skipped += 1
                    break
                if action in {"q", "quit"}:
                    summary.quit = True
                    summary.remaining = _remaining(rows)
                    return summary
                output_fn("Unknown action. Choose a, f, r, s, or q.")
    except KeyboardInterrupt:
        summary.quit = True

    summary.remaining = _remaining(rows)
    return summary
