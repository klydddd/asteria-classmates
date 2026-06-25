"""Metadata models and CSV validation for speech datasets."""

from __future__ import annotations

import csv
import re
import unicodedata
from enum import Enum
from pathlib import Path, PurePosixPath
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    computed_field,
    field_validator,
    model_validator,
)

AUDIO_ID_PATTERN = re.compile(r"^(?P<language>[a-z]{3})_[0-9]{6}$")
SPEAKER_ID_PATTERN = re.compile(r"^spk_[a-z0-9]+(?:_[a-z0-9]+)*$")
LANGUAGE_PATTERN = re.compile(r"^[a-z]{3}$")
ANNOTATION_PATTERN = re.compile(r"\[[^\[\]]+\]")
ALLOWED_ANNOTATIONS = {
    "[noise]",
    "[laughter]",
    "[unclear]",
    "[silence]",
}
SUPPORTED_AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".flac"}


class DatasetSplit(str, Enum):
    """Supported dataset partitions."""

    UNASSIGNED = "unassigned"
    TRAIN = "train"
    VALIDATION = "validation"
    TEST = "test"


class QualityStatus(str, Enum):
    """Supported metadata review states."""

    PENDING = "pending"
    APPROVED = "approved"
    NEEDS_REVIEW = "needs_review"
    REJECTED = "rejected"


class Severity(str, Enum):
    """Validation issue severity."""

    ERROR = "error"
    WARNING = "warning"


class MetadataRecord(BaseModel):
    """One audio clip's complete metadata."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)

    audio_id: str
    file_path: str
    transcript: str
    language: str
    speaker_id: str
    duration_seconds: float = Field(gt=0)
    sample_rate: int = Field(gt=0)
    split: DatasetSplit
    quality_status: QualityStatus
    source_id: str | None = None
    region: str | None = None
    speaker_age_group: str | None = None
    speaker_gender: str | None = None
    recording_device: str | None = None
    environment: str | None = None
    code_switch_languages: list[str] | None = None
    reviewer_notes: str | None = None

    @field_validator(
        "source_id",
        "region",
        "speaker_age_group",
        "speaker_gender",
        "recording_device",
        "environment",
        "reviewer_notes",
        mode="before",
    )
    @classmethod
    def empty_optional_strings_are_none(cls, value: Any) -> Any:
        """Treat empty optional CSV cells as missing values."""
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("audio_id")
    @classmethod
    def valid_audio_id(cls, value: str) -> str:
        if not AUDIO_ID_PATTERN.fullmatch(value):
            raise ValueError("must use a lowercase ISO prefix and six digits")
        return value

    @field_validator("speaker_id")
    @classmethod
    def valid_speaker_id(cls, value: str) -> str:
        if not SPEAKER_ID_PATTERN.fullmatch(value):
            raise ValueError("must be an anonymized spk_* identifier")
        return value

    @field_validator("language")
    @classmethod
    def valid_language(cls, value: str) -> str:
        if not LANGUAGE_PATTERN.fullmatch(value):
            raise ValueError("must be a lowercase ISO 639-3 code")
        return value

    @field_validator("file_path")
    @classmethod
    def valid_file_path(cls, value: str) -> str:
        if not value or "\\" in value:
            raise ValueError("must be a nonempty POSIX-style relative path")
        path = PurePosixPath(value)
        if path.is_absolute() or any(part in {".", ".."} for part in value.split("/")):
            raise ValueError("must be a traversal-safe relative path")
        if path.suffix.lower() not in SUPPORTED_AUDIO_EXTENSIONS:
            raise ValueError("has an unsupported audio extension")
        return value

    @field_validator("transcript")
    @classmethod
    def valid_transcript(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be empty")
        if unicodedata.normalize("NFC", value) != value:
            raise ValueError("must be Unicode NFC normalized")
        annotations = ANNOTATION_PATTERN.findall(value)
        unsupported = sorted(set(annotations) - ALLOWED_ANNOTATIONS)
        text_without_allowed = value
        for annotation in ALLOWED_ANNOTATIONS:
            text_without_allowed = text_without_allowed.replace(annotation, "")
        if unsupported or "[" in text_without_allowed or "]" in text_without_allowed:
            raise ValueError("contains an unsupported transcript annotation")
        return value

    @field_validator("code_switch_languages", mode="before")
    @classmethod
    def parse_code_switch_languages(cls, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, str):
            if not value.strip():
                return None
            return [code.strip() for code in value.split(";")]
        return value

    @field_validator("code_switch_languages")
    @classmethod
    def valid_code_switch_languages(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        if not value or any(not LANGUAGE_PATTERN.fullmatch(code) for code in value):
            raise ValueError("must contain semicolon-separated ISO 639-3 codes")
        if len(set(value)) != len(value):
            raise ValueError("must not contain duplicate language codes")
        return value

    @model_validator(mode="after")
    def matching_language_prefix(self) -> MetadataRecord:
        match = AUDIO_ID_PATTERN.fullmatch(self.audio_id)
        if match and match.group("language") != self.language:
            raise ValueError("audio_id prefix must match language")
        return self


REQUIRED_COLUMNS = {
    "audio_id",
    "file_path",
    "transcript",
    "language",
    "speaker_id",
    "duration_seconds",
    "sample_rate",
    "split",
    "quality_status",
}
OPTIONAL_COLUMNS = {
    "source_id",
    "region",
    "speaker_age_group",
    "speaker_gender",
    "recording_device",
    "environment",
    "code_switch_languages",
    "reviewer_notes",
}
ALLOWED_COLUMNS = REQUIRED_COLUMNS | OPTIONAL_COLUMNS


class ValidationIssue(BaseModel):
    """One actionable CSV validation issue."""

    severity: Severity
    code: str
    row: int | None
    field: str | None
    message: str


class ValidationReport(BaseModel):
    """Aggregate result for a metadata CSV."""

    row_count: int
    valid_row_count: int
    issues: list[ValidationIssue]

    @computed_field
    @property
    def error_count(self) -> int:
        return sum(issue.severity == Severity.ERROR for issue in self.issues)

    @computed_field
    @property
    def warning_count(self) -> int:
        return sum(issue.severity == Severity.WARNING for issue in self.issues)


def _issue_code(field: str | None, message: str) -> str:
    if field == "transcript" and "annotation" in message:
        return "unsupported_annotation"
    if field is None and "prefix" in message:
        return "language_prefix_mismatch"
    return f"invalid_{field or 'record'}"


def _validation_issues(
    error: ValidationError, row_number: int
) -> list[ValidationIssue]:
    issues = []
    for detail in error.errors(include_url=False):
        location = detail.get("loc", ())
        field = str(location[0]) if location else None
        message = str(detail["msg"]).removeprefix("Value error, ")
        issues.append(
            ValidationIssue(
                severity=Severity.ERROR,
                code=_issue_code(field, message),
                row=row_number,
                field=field,
                message=message,
            )
        )
    return issues


def _warning_issues(record: MetadataRecord, row_number: int) -> list[ValidationIssue]:
    issues = []
    if not 5 <= record.duration_seconds <= 15:
        issues.append(
            ValidationIssue(
                severity=Severity.WARNING,
                code="nonstandard_duration",
                row=row_number,
                field="duration_seconds",
                message="recommended clip duration is 5–15 seconds",
            )
        )
    if record.sample_rate != 16000:
        issues.append(
            ValidationIssue(
                severity=Severity.WARNING,
                code="nonstandard_sample_rate",
                row=row_number,
                field="sample_rate",
                message="recommended sample rate is 16000 Hz",
            )
        )
    return issues


def validate_metadata_csv(path: str | Path) -> ValidationReport:
    """Validate every row in a UTF-8 metadata CSV and aggregate all issues."""
    csv_path = Path(path)
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, strict=True)
        if reader.fieldnames is None:
            raise csv.Error("CSV header is missing")

        fieldnames = set(reader.fieldnames)
        missing = sorted(REQUIRED_COLUMNS - fieldnames)
        unknown = sorted(fieldnames - ALLOWED_COLUMNS)
        rows = list(reader)

    column_issues = [
        ValidationIssue(
            severity=Severity.ERROR,
            code="missing_column",
            row=None,
            field=column,
            message=f"required column is missing: {column}",
        )
        for column in missing
    ]
    column_issues.extend(
        ValidationIssue(
            severity=Severity.ERROR,
            code="unknown_column",
            row=None,
            field=column,
            message=f"unknown column is not allowed: {column}",
        )
        for column in unknown
    )
    if column_issues:
        return ValidationReport(
            row_count=len(rows),
            valid_row_count=0,
            issues=column_issues,
        )

    issues: list[ValidationIssue] = []
    valid_row_count = 0
    seen_audio_ids: dict[str, int] = {}
    seen_file_paths: dict[str, int] = {}

    for row_number, row in enumerate(rows, start=2):
        row_error_count = 0
        duplicate_values = (
            ("audio_id", row.get("audio_id"), seen_audio_ids),
            ("file_path", row.get("file_path"), seen_file_paths),
        )
        for field, value, seen in duplicate_values:
            if value and value in seen:
                issues.append(
                    ValidationIssue(
                        severity=Severity.ERROR,
                        code=f"duplicate_{field}",
                        row=row_number,
                        field=field,
                        message=f"duplicates row {seen[value]}",
                    )
                )
                row_error_count += 1
            elif value:
                seen[value] = row_number

        try:
            record = MetadataRecord.model_validate(row)
        except ValidationError as error:
            record_issues = _validation_issues(error, row_number)
            issues.extend(record_issues)
            row_error_count += len(record_issues)
        else:
            issues.extend(_warning_issues(record, row_number))

        if row_error_count == 0:
            valid_row_count += 1

    return ValidationReport(
        row_count=len(rows),
        valid_row_count=valid_row_count,
        issues=issues,
    )
