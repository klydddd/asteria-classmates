from __future__ import annotations

import csv
import json
import os
import unicodedata
from pathlib import Path

import pytest

from bosesph.transcripts import (
    TranscriptDatasetError,
    normalize_dataset,
    normalize_transcript,
)


def metadata_row(**overrides: str) -> dict[str, str]:
    row = {
        "audio_id": "pam_000001",
        "file_path": "audio_clean/pam_000001.wav",
        "transcript": "Masanting ya ing aldo.",
        "language": "pam",
        "speaker_id": "spk_001",
        "duration_seconds": "8",
        "sample_rate": "16000",
        "split": "unassigned",
        "quality_status": "pending",
        "source_id": "",
        "region": "",
        "speaker_age_group": "",
        "speaker_gender": "",
        "recording_device": "",
        "environment": "",
        "code_switch_languages": "",
        "reviewer_notes": "",
    }
    row.update(overrides)
    return row


def write_metadata(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def read_metadata(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_normalize_transcript_applies_safe_formatting_rules() -> None:
    decomposed = unicodedata.normalize("NFD", "Á")
    text = f"  {decomposed}ldo  ya  !?!  [Noise]\u200b " "masanting...  [LAUGHTER]  "

    result = normalize_transcript(text)

    assert result.text == "Áldo ya! [noise] Masanting. [laughter]"
    assert set(result.applied_rules) == {
        "unicode_nfc",
        "remove_control_characters",
        "normalize_whitespace",
        "normalize_punctuation_spacing",
        "collapse_repeated_punctuation",
        "normalize_annotation_casing",
        "sentence_case",
    }
    assert result.warnings == []


def test_normalizer_preserves_spelling_repetition_and_code_switching() -> None:
    result = normalize_transcript("hello hello, masanting YA, magandang umaga.")

    assert result.text == "Hello hello, masanting YA, magandang umaga."


def test_normalize_transcript_flags_unusual_symbols_without_removing_them() -> None:
    result = normalize_transcript("Masanting ya 🙂")

    assert result.text == "Masanting ya 🙂"
    assert [warning.code for warning in result.warnings] == ["unusual_symbol"]


def test_normalize_transcript_preserves_numeric_punctuation() -> None:
    result = normalize_transcript("version 3.14 has 1,000 samples.")

    assert result.text == "Version 3.14 has 1,000 samples."


def test_normalize_transcript_rejects_empty_text() -> None:
    with pytest.raises(ValueError, match="empty"):
        normalize_transcript(" \u200b ")


def test_normalize_transcript_is_idempotent() -> None:
    first = normalize_transcript("  masanting... [Noise]  ")
    second = normalize_transcript(first.text)

    assert second.text == first.text
    assert second.applied_rules == []
    assert second.warnings == first.warnings


def test_normalize_dataset_updates_metadata_and_writes_audit_report(
    tmp_path: Path,
) -> None:
    dataset = tmp_path / "dataset"
    dataset.mkdir()
    write_metadata(
        dataset / "metadata.csv",
        [
            metadata_row(transcript="  masanting... [Noise]  "),
            metadata_row(
                audio_id="pam_000002",
                file_path="audio_clean/pam_000002.wav",
                transcript="Masanting ya 🙂",
                reviewer_notes="Duration requires review.",
            ),
        ],
    )

    report = normalize_dataset(dataset)

    rows = read_metadata(dataset / "metadata.csv")
    assert rows[0]["transcript"] == "Masanting. [noise]"
    assert rows[0]["quality_status"] == "pending"
    assert rows[1]["quality_status"] == "needs_review"
    assert rows[1]["reviewer_notes"] == (
        "Duration requires review.; Transcript contains unusual symbol(s): 🙂"
    )
    assert report.changed == 1
    assert report.unchanged == 1
    assert report.needs_review == 1
    payload = json.loads((dataset / "normalization_report.json").read_text())
    assert payload["records"][0]["before"] == "  masanting... [Noise]  "
    assert payload["records"][0]["after"] == "Masanting. [noise]"
    assert payload["records"][1]["warnings"][0]["code"] == "unusual_symbol"


def test_normalize_dataset_does_not_duplicate_warning_notes_on_rerun(
    tmp_path: Path,
) -> None:
    dataset = tmp_path / "dataset"
    dataset.mkdir()
    write_metadata(
        dataset / "metadata.csv",
        [metadata_row(transcript="  masanting... 🙂  ")],
    )

    first = normalize_dataset(dataset)
    normalize_dataset(dataset)

    row = read_metadata(dataset / "metadata.csv")[0]
    payload = json.loads((dataset / "normalization_report.json").read_text(encoding="utf-8"))
    assert row["reviewer_notes"].count("Transcript contains unusual") == 1
    assert payload["records"][0]["before"] == first.records[0].before
    assert payload["records"][0]["applied_rules"] == first.records[0].applied_rules


def test_normalize_dataset_leaves_files_untouched_for_invalid_metadata(
    tmp_path: Path,
) -> None:
    dataset = tmp_path / "dataset"
    dataset.mkdir()
    metadata = dataset / "metadata.csv"
    write_metadata(metadata, [metadata_row(transcript="Masanting [music]")])
    original = metadata.read_bytes()

    with pytest.raises(TranscriptDatasetError, match="unsupported"):
        normalize_dataset(dataset)

    assert metadata.read_bytes() == original
    assert not (dataset / "normalization_report.json").exists()


def test_normalize_dataset_rejects_duplicate_rows_before_publication(
    tmp_path: Path,
) -> None:
    dataset = tmp_path / "dataset"
    dataset.mkdir()
    metadata = dataset / "metadata.csv"
    write_metadata(metadata, [metadata_row(), metadata_row()])

    with pytest.raises(TranscriptDatasetError, match="duplicate_audio_id"):
        normalize_dataset(dataset)


def test_normalize_dataset_rolls_back_if_report_publication_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dataset = tmp_path / "dataset"
    dataset.mkdir()
    metadata = dataset / "metadata.csv"
    report = dataset / "normalization_report.json"
    write_metadata(metadata, [metadata_row(transcript="Masanting.")])
    normalize_dataset(dataset)
    write_metadata(metadata, [metadata_row(transcript="  masanting...  ")])
    original_metadata = metadata.read_bytes()
    original_report = report.read_bytes()
    real_replace = os.replace
    failed = False

    def fail_report_once(source: object, destination: object) -> None:
        nonlocal failed
        if Path(destination) == report and not failed:
            failed = True
            raise OSError("report publication failed")
        real_replace(source, destination)

    monkeypatch.setattr("bosesph.transcripts.os.replace", fail_report_once)

    with pytest.raises(TranscriptDatasetError, match="report publication failed"):
        normalize_dataset(dataset)

    assert metadata.read_bytes() == original_metadata
    assert report.read_bytes() == original_report
