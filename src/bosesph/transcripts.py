"""Deterministic transcript normalization and dataset publication."""

from __future__ import annotations

import csv
import json
import os
import re
import tempfile
import unicodedata
from pathlib import Path

from pydantic import BaseModel, ValidationError

from bosesph.metadata import (
    ALLOWED_COLUMNS,
    REQUIRED_COLUMNS,
    MetadataRecord,
    QualityStatus,
)

ANNOTATION_CASE_PATTERN = re.compile(
    r"\[(noise|laughter|unclear|silence)\]",
    flags=re.IGNORECASE,
)
REPEATED_PUNCTUATION_PATTERN = re.compile(r"([.!?])(?:\s*[.!?])+")
SPACE_BEFORE_PUNCTUATION_PATTERN = re.compile(r"\s+([,.!?])")
MISSING_SPACE_AFTER_PUNCTUATION_PATTERN = re.compile(r"([,.!?])(?=[^\W\d_])")
WHITESPACE_PATTERN = re.compile(r"\s+")


class TranscriptDatasetError(ValueError):
    """Raised when transcript dataset input cannot be safely processed."""


class NormalizationWarning(BaseModel):
    """One unresolved transcript concern requiring human review."""

    code: str
    message: str


class NormalizationResult(BaseModel):
    """Pure normalization result for one transcript."""

    text: str
    applied_rules: list[str]
    warnings: list[NormalizationWarning]


class NormalizationRecord(BaseModel):
    """Audit entry for one metadata row."""

    audio_id: str
    before: str
    after: str
    applied_rules: list[str]
    warnings: list[NormalizationWarning]


class NormalizationReport(BaseModel):
    """Aggregate transcript normalization outcome."""

    dataset: str
    row_count: int
    changed: int
    unchanged: int
    needs_review: int
    records: list[NormalizationRecord]


def _replace_control_characters(text: str) -> str:
    characters = []
    for character in text:
        category = unicodedata.category(character)
        if category in {"Cc", "Cf"}:
            if character.isspace():
                characters.append(" ")
            continue
        characters.append(character)
    return "".join(characters)


def _sentence_case(text: str) -> str:
    characters = list(text)
    sentence_start = True
    inside_annotation = False
    for index, character in enumerate(characters):
        if character == "[":
            inside_annotation = True
            continue
        if character == "]":
            inside_annotation = False
            continue
        if inside_annotation:
            continue
        if sentence_start and character.isalpha():
            characters[index] = character.upper()
            sentence_start = False
        numeric_decimal = (
            character == "."
            and index > 0
            and index + 1 < len(characters)
            and characters[index - 1].isdigit()
            and characters[index + 1].isdigit()
        )
        if character in ".!?" and not numeric_decimal:
            sentence_start = True
    return "".join(characters)


def _unusual_symbols(text: str) -> list[str]:
    return sorted(
        {
            character
            for character in text
            if unicodedata.category(character) in {"So", "Sk"}
        }
    )


def normalize_transcript(text: str) -> NormalizationResult:
    """Apply conservative formatting rules without rewriting spoken content."""
    current = text
    applied_rules: list[str] = []

    normalized = unicodedata.normalize("NFC", current)
    if normalized != current:
        applied_rules.append("unicode_nfc")
        current = normalized

    normalized = _replace_control_characters(current)
    if normalized != current:
        applied_rules.append("remove_control_characters")
        current = normalized

    normalized = WHITESPACE_PATTERN.sub(" ", current).strip()
    if normalized != current:
        applied_rules.append("normalize_whitespace")
        current = normalized

    normalized = SPACE_BEFORE_PUNCTUATION_PATTERN.sub(r"\1", current)
    normalized = MISSING_SPACE_AFTER_PUNCTUATION_PATTERN.sub(r"\1 ", normalized)
    if normalized != current:
        applied_rules.append("normalize_punctuation_spacing")
        current = normalized

    normalized = REPEATED_PUNCTUATION_PATTERN.sub(r"\1", current)
    if normalized != current:
        applied_rules.append("collapse_repeated_punctuation")
        current = normalized

    normalized = ANNOTATION_CASE_PATTERN.sub(
        lambda match: f"[{match.group(1).lower()}]",
        current,
    )
    if normalized != current:
        applied_rules.append("normalize_annotation_casing")
        current = normalized

    normalized = _sentence_case(current)
    if normalized != current:
        applied_rules.append("sentence_case")
        current = normalized

    if not current:
        raise ValueError("transcript is empty after normalization")

    symbols = _unusual_symbols(current)
    warnings = []
    if symbols:
        warnings.append(
            NormalizationWarning(
                code="unusual_symbol",
                message=f"Transcript contains unusual symbol(s): {' '.join(symbols)}",
            )
        )
    return NormalizationResult(
        text=current,
        applied_rules=applied_rules,
        warnings=warnings,
    )


def _read_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle, strict=True)
            if reader.fieldnames is None:
                raise TranscriptDatasetError("metadata CSV header is missing")
            fieldnames = list(reader.fieldnames)
            rows = list(reader)
    except (OSError, UnicodeError, csv.Error) as error:
        raise TranscriptDatasetError(str(error)) from error

    missing = sorted(REQUIRED_COLUMNS - set(fieldnames))
    unknown = sorted(set(fieldnames) - ALLOWED_COLUMNS)
    if missing:
        raise TranscriptDatasetError(f"missing required column: {missing[0]}")
    if unknown:
        raise TranscriptDatasetError(f"unknown column: {unknown[0]}")
    return fieldnames, rows


def _validate_rows(rows: list[dict[str, str]]) -> None:
    seen_audio_ids: set[str] = set()
    seen_file_paths: set[str] = set()
    for row_number, row in enumerate(rows, start=2):
        audio_id = row.get("audio_id", "")
        file_path = row.get("file_path", "")
        if audio_id in seen_audio_ids:
            raise TranscriptDatasetError(
                f"duplicate_audio_id in metadata row {row_number}"
            )
        if file_path in seen_file_paths:
            raise TranscriptDatasetError(
                f"duplicate_file_path in metadata row {row_number}"
            )
        seen_audio_ids.add(audio_id)
        seen_file_paths.add(file_path)
        try:
            MetadataRecord.model_validate(row)
        except ValidationError as error:
            message = str(error.errors(include_url=False)[0]["msg"])
            message = message.removeprefix("Value error, ")
            raise TranscriptDatasetError(
                f"invalid metadata row {row_number}: {message}"
            ) from error


def _append_note(existing: str, messages: list[str]) -> str:
    notes = [note.strip() for note in existing.split(";") if note.strip()]
    for message in messages:
        if message not in notes:
            notes.append(message)
    return "; ".join(notes)


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def normalize_dataset(dataset: str | Path) -> NormalizationReport:
    """Normalize one generated dataset and atomically publish its metadata."""
    dataset_path = Path(dataset)
    metadata_path = dataset_path / "metadata.csv"
    report_path = dataset_path / "normalization_report.json"
    fieldnames, rows = _read_rows(metadata_path)
    records: list[NormalizationRecord] = []
    previous_records: dict[str, NormalizationRecord] = {}
    if report_path.exists():
        try:
            previous_report = NormalizationReport.model_validate_json(
                report_path.read_text(encoding="utf-8")
            )
        except (OSError, UnicodeError, ValidationError, ValueError) as error:
            raise TranscriptDatasetError(
                f"invalid normalization report: {error}"
            ) from error
        previous_records = {
            record.audio_id: record for record in previous_report.records
        }
    changed = 0

    for row_number, row in enumerate(rows, start=2):
        before = row.get("transcript", "")
        try:
            result = normalize_transcript(before)
        except ValueError as error:
            raise TranscriptDatasetError(
                f"invalid transcript in metadata row {row_number}: {error}"
            ) from error
        row["transcript"] = result.text
        if result.warnings:
            if "reviewer_notes" not in fieldnames:
                fieldnames.append("reviewer_notes")
            row["quality_status"] = QualityStatus.NEEDS_REVIEW.value
            row["reviewer_notes"] = _append_note(
                row.get("reviewer_notes", ""),
                [warning.message for warning in result.warnings],
            )
        if before != result.text:
            changed += 1
        previous = previous_records.get(row.get("audio_id", ""))
        audit_before = before
        applied_rules = result.applied_rules
        if previous is not None and previous.after == before:
            audit_before = previous.before
            applied_rules = list(
                dict.fromkeys(previous.applied_rules + result.applied_rules)
            )
        records.append(
            NormalizationRecord(
                audio_id=row.get("audio_id", ""),
                before=audit_before,
                after=result.text,
                applied_rules=applied_rules,
                warnings=result.warnings,
            )
        )

    _validate_rows(rows)
    report = NormalizationReport(
        dataset=str(dataset_path),
        row_count=len(rows),
        changed=changed,
        unchanged=len(rows) - changed,
        needs_review=sum(bool(record.warnings) for record in records),
        records=records,
    )

    original_metadata = metadata_path.read_bytes()
    original_report = report_path.read_bytes() if report_path.exists() else None
    try:
        dataset_path.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(
            prefix=".normalization-stage-",
            dir=dataset_path,
        ) as temporary_directory:
            stage = Path(temporary_directory)
            staged_metadata = stage / "metadata.csv"
            staged_report = stage / "normalization_report.json"
            _write_csv(staged_metadata, fieldnames, rows)
            staged_report.write_text(
                json.dumps(
                    report.model_dump(mode="json"),
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            os.replace(staged_metadata, metadata_path)
            os.replace(staged_report, report_path)
    except OSError as error:
        metadata_path.write_bytes(original_metadata)
        if original_report is None:
            report_path.unlink(missing_ok=True)
        else:
            report_path.write_bytes(original_report)
        raise TranscriptDatasetError(str(error)) from error
    return report
