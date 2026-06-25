from __future__ import annotations

import csv
import json
import unicodedata
from pathlib import Path

import pytest
from pydantic import ValidationError

from bosesph.metadata import (
    MetadataRecord,
    Severity,
    validate_metadata_csv,
)

REQUIRED_COLUMNS = [
    "audio_id",
    "file_path",
    "transcript",
    "language",
    "speaker_id",
    "duration_seconds",
    "sample_rate",
    "split",
    "quality_status",
]


def complete_row(**overrides: str) -> dict[str, str]:
    row = {
        "audio_id": "pam_000001",
        "file_path": "audio/pam_000001.wav",
        "transcript": "Masanting ya ing aldo.",
        "language": "pam",
        "speaker_id": "spk_001",
        "duration_seconds": "8.5",
        "sample_rate": "16000",
        "split": "train",
        "quality_status": "approved",
    }
    row.update(overrides)
    return row


def write_csv(
    path: Path,
    rows: list[dict[str, str]],
    fieldnames: list[str] | None = None,
) -> None:
    columns = fieldnames or list(rows[0])
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=columns,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def issue_codes(report: object) -> set[str]:
    return {issue.code for issue in report.issues}  # type: ignore[attr-defined]


def test_complete_record_accepts_optional_metadata() -> None:
    record = MetadataRecord.model_validate(
        complete_row(
            source_id="field_session_01",
            region="Pampanga",
            speaker_age_group="adult",
            speaker_gender="woman",
            recording_device="handheld recorder",
            environment="quiet indoor",
            code_switch_languages="eng;fil",
            reviewer_notes="Consent recorded.",
        )
    )

    assert record.audio_id == "pam_000001"
    assert record.code_switch_languages == ["eng", "fil"]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("audio_id", "kap-1"),
        ("speaker_id", "speaker_001"),
        ("language", "PAM"),
        ("file_path", "../private/pam_000001.wav"),
        ("file_path", "/tmp/pam_000001.wav"),
        ("file_path", "audio/pam_000001.txt"),
        ("duration_seconds", "0"),
        ("sample_rate", "-1"),
        ("split", "dev"),
        ("quality_status", "valid"),
        ("transcript", ""),
        ("transcript", "Masanting [music]"),
        ("code_switch_languages", "English"),
    ],
)
def test_record_rejects_invalid_fields(field: str, value: str) -> None:
    with pytest.raises(ValidationError):
        MetadataRecord.model_validate(complete_row(**{field: value}))


def test_audio_id_prefix_must_match_language() -> None:
    with pytest.raises(ValidationError, match="prefix"):
        MetadataRecord.model_validate(complete_row(language="eng"))


def test_transcript_must_be_unicode_nfc() -> None:
    decomposed = unicodedata.normalize("NFD", "Á")

    with pytest.raises(ValidationError, match="NFC"):
        MetadataRecord.model_validate(complete_row(transcript=decomposed))


def test_all_supported_transcript_annotations_are_allowed() -> None:
    record = MetadataRecord.model_validate(
        complete_row(transcript=("Masanting [noise] [laughter] [unclear] [silence]"))
    )

    assert "[unclear]" in record.transcript


def test_csv_reports_missing_and_unknown_columns(tmp_path: Path) -> None:
    path = tmp_path / "metadata.csv"
    columns = [column for column in REQUIRED_COLUMNS if column != "speaker_id"]
    columns.append("private_name")
    write_csv(path, [complete_row()], fieldnames=columns)

    report = validate_metadata_csv(path)

    assert report.error_count == 2
    assert {"missing_column", "unknown_column"} <= issue_codes(report)


def test_csv_reports_duplicates_and_aggregates_row_errors(tmp_path: Path) -> None:
    path = tmp_path / "metadata.csv"
    write_csv(
        path,
        [
            complete_row(),
            complete_row(audio_id="pam_000001", file_path="audio/other.wav"),
            complete_row(
                audio_id="pam_000003",
                file_path="audio/pam_000001.wav",
                transcript="[music]",
                sample_rate="0",
            ),
        ],
    )

    report = validate_metadata_csv(path)

    assert report.row_count == 3
    assert report.valid_row_count == 1
    assert report.error_count == 4
    assert {"duplicate_audio_id", "duplicate_file_path"} <= issue_codes(report)
    assert {
        issue.row for issue in report.issues if issue.severity == Severity.ERROR
    } >= {
        3,
        4,
    }


def test_csv_warns_for_nonstandard_duration_and_sample_rate(
    tmp_path: Path,
) -> None:
    path = tmp_path / "metadata.csv"
    write_csv(
        path,
        [
            complete_row(duration_seconds="4.9"),
            complete_row(
                audio_id="pam_000002",
                file_path="audio/pam_000002.wav",
                duration_seconds="15.1",
                sample_rate="44100",
            ),
        ],
    )

    report = validate_metadata_csv(path)

    assert report.error_count == 0
    assert report.warning_count == 3
    assert report.valid_row_count == 2
    assert issue_codes(report) == {
        "nonstandard_duration",
        "nonstandard_sample_rate",
    }


def test_csv_decodes_utf8_strictly(tmp_path: Path) -> None:
    path = tmp_path / "metadata.csv"
    path.write_bytes(b"audio_id,transcript\npam_000001,\xff\n")

    with pytest.raises(UnicodeError):
        validate_metadata_csv(path)


def test_csv_rejects_malformed_quoting(tmp_path: Path) -> None:
    path = tmp_path / "metadata.csv"
    path.write_text(
        ",".join(REQUIRED_COLUMNS)
        + '\npam_000001,a.wav,"unterminated,pam,spk_001,8,16000,train,approved',
        encoding="utf-8",
    )

    with pytest.raises(csv.Error):
        validate_metadata_csv(path)


def test_report_json_contract(tmp_path: Path) -> None:
    path = tmp_path / "metadata.csv"
    write_csv(path, [complete_row(duration_seconds="2")])

    payload = json.loads(validate_metadata_csv(path).model_dump_json())

    assert payload["row_count"] == 1
    assert payload["valid_row_count"] == 1
    assert payload["error_count"] == 0
    assert payload["warning_count"] == 1
    assert set(payload["issues"][0]) == {
        "severity",
        "code",
        "row",
        "field",
        "message",
    }
