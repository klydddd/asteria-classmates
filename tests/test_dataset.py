"""Tests for the Phase 4 dataset builder."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from bosesph.cli import main
from bosesph.dataset import (
    DatasetBuildError,
    _assign_splits,
    _format_duration,
    build_dataset,
)
from bosesph.metadata import DatasetSplit, QualityStatus
from tests.audio_fixtures import write_pcm_wav

FIELDNAMES = [
    "audio_id",
    "file_path",
    "transcript",
    "language",
    "speaker_id",
    "duration_seconds",
    "sample_rate",
    "split",
    "quality_status",
    "reviewer_notes",
]


def _write_reviewed_dataset(
    dataset: Path,
    *,
    rows: list[dict[str, str]] | None = None,
    create_audio: bool = True,
) -> Path:
    """Write a reviewed dataset directory with metadata.csv and audio files."""
    audio_dir = dataset / "audio_clean"
    audio_dir.mkdir(parents=True)

    if rows is None:
        rows = [
            {
                "audio_id": "pam_000001",
                "file_path": "audio_clean/pam_000001.wav",
                "transcript": "Masanting ya ing aldo.",
                "language": "pam",
                "speaker_id": "spk_001",
                "duration_seconds": "8.0",
                "sample_rate": "16000",
                "split": "unassigned",
                "quality_status": "approved",
                "reviewer_notes": "",
            },
            {
                "audio_id": "pam_000002",
                "file_path": "audio_clean/pam_000002.wav",
                "transcript": "Makananu ka?",
                "language": "pam",
                "speaker_id": "spk_002",
                "duration_seconds": "6.5",
                "sample_rate": "16000",
                "split": "unassigned",
                "quality_status": "approved",
                "reviewer_notes": "",
            },
            {
                "audio_id": "pam_000003",
                "file_path": "audio_clean/pam_000003.wav",
                "transcript": "Mayap a abak.",
                "language": "pam",
                "speaker_id": "spk_001",
                "duration_seconds": "7.0",
                "sample_rate": "16000",
                "split": "unassigned",
                "quality_status": "approved",
                "reviewer_notes": "",
            },
        ]

    with (dataset / "metadata.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    if create_audio:
        for row in rows:
            audio_path = dataset / row["file_path"]
            if not audio_path.exists():
                write_pcm_wav(audio_path, duration=int(float(row["duration_seconds"])))

    return dataset


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, strict=True))


# --- Unit tests for helper functions ---


class TestFormatDuration:
    def test_seconds_only(self) -> None:
        assert _format_duration(45) == "0m 45s"

    def test_minutes_and_seconds(self) -> None:
        assert _format_duration(125) == "2m 5s"

    def test_hours(self) -> None:
        assert _format_duration(3661) == "1h 1m 1s"


class TestAssignSplits:
    def test_single_speaker_goes_to_train(self) -> None:
        rows = [
            {"speaker_id": "spk_001", "split": "unassigned"},
            {"speaker_id": "spk_001", "split": "unassigned"},
        ]
        _assign_splits(
            rows, train_ratio=0.7, val_ratio=0.15, test_ratio=0.15, seed=42
        )
        # Single speaker → all go to train (largest bucket).
        assert all(row["split"] == "train" for row in rows)

    def test_two_speakers_no_speaker_in_both_train_and_test(self) -> None:
        rows = [
            {"speaker_id": "spk_001", "split": "unassigned"},
            {"speaker_id": "spk_001", "split": "unassigned"},
            {"speaker_id": "spk_001", "split": "unassigned"},
            {"speaker_id": "spk_001", "split": "unassigned"},
            {"speaker_id": "spk_002", "split": "unassigned"},
            {"speaker_id": "spk_002", "split": "unassigned"},
        ]
        _assign_splits(
            rows, train_ratio=0.7, val_ratio=0.15, test_ratio=0.15, seed=42
        )
        spk1_splits = {row["split"] for row in rows if row["speaker_id"] == "spk_001"}
        spk2_splits = {row["split"] for row in rows if row["speaker_id"] == "spk_002"}
        assert len(spk1_splits) == 1
        assert len(spk2_splits) == 1
        assert spk1_splits != spk2_splits  # Different speakers go to different splits.

    def test_three_speakers_each_gets_own_split(self) -> None:
        rows = []
        for i in range(1, 4):
            for _ in range(4):
                rows.append(
                    {"speaker_id": f"spk_{i:03d}", "split": "unassigned"}
                )
        _assign_splits(
            rows, train_ratio=0.34, val_ratio=0.33, test_ratio=0.33, seed=42
        )
        # Each speaker should be in exactly one split.
        for i in range(1, 4):
            splits = {
                row["split"]
                for row in rows
                if row["speaker_id"] == f"spk_{i:03d}"
            }
            assert len(splits) == 1

    def test_deterministic_with_same_seed(self) -> None:
        def make_rows() -> list[dict[str, str]]:
            return [
                {"speaker_id": f"spk_{i:03d}", "split": "unassigned"}
                for i in range(1, 11)
            ]

        rows1 = make_rows()
        rows2 = make_rows()
        _assign_splits(
            rows1, train_ratio=0.7, val_ratio=0.15, test_ratio=0.15, seed=42
        )
        _assign_splits(
            rows2, train_ratio=0.7, val_ratio=0.15, test_ratio=0.15, seed=42
        )
        assert [row["split"] for row in rows1] == [row["split"] for row in rows2]


# --- Integration tests for build_dataset ---


class TestBuildDataset:
    def test_basic_build_creates_output_structure(self, tmp_path: Path) -> None:
        dataset = tmp_path / "reviewed"
        output = tmp_path / "final"
        _write_reviewed_dataset(dataset)

        report = build_dataset(dataset, output)

        assert (output / "audio").is_dir()
        assert (output / "metadata.csv").is_file()
        assert (output / "train.csv").is_file()
        assert (output / "validation.csv").is_file()
        assert (output / "test.csv").is_file()
        assert (output / "dataset_stats.json").is_file()
        assert (output / "dataset_card.md").is_file()
        assert report.total_clips == 3
        assert report.excluded == 0

    def test_only_approved_clips_included(self, tmp_path: Path) -> None:
        dataset = tmp_path / "reviewed"
        output = tmp_path / "final"
        rows = [
            {
                "audio_id": "pam_000001",
                "file_path": "audio_clean/pam_000001.wav",
                "transcript": "Approved clip.",
                "language": "pam",
                "speaker_id": "spk_001",
                "duration_seconds": "8.0",
                "sample_rate": "16000",
                "split": "unassigned",
                "quality_status": "approved",
                "reviewer_notes": "",
            },
            {
                "audio_id": "pam_000002",
                "file_path": "audio_clean/pam_000002.wav",
                "transcript": "Rejected clip.",
                "language": "pam",
                "speaker_id": "spk_001",
                "duration_seconds": "6.0",
                "sample_rate": "16000",
                "split": "unassigned",
                "quality_status": "rejected",
                "reviewer_notes": "bad audio",
            },
            {
                "audio_id": "pam_000003",
                "file_path": "audio_clean/pam_000003.wav",
                "transcript": "Pending clip.",
                "language": "pam",
                "speaker_id": "spk_001",
                "duration_seconds": "7.0",
                "sample_rate": "16000",
                "split": "unassigned",
                "quality_status": "pending",
                "reviewer_notes": "",
            },
        ]
        _write_reviewed_dataset(dataset, rows=rows)

        report = build_dataset(dataset, output)

        assert report.total_clips == 1
        assert report.excluded == 2
        output_rows = _read_csv(output / "metadata.csv")
        assert len(output_rows) == 1
        assert output_rows[0]["audio_id"] == "pam_000001"

    def test_audio_files_copied_to_audio_directory(self, tmp_path: Path) -> None:
        dataset = tmp_path / "reviewed"
        output = tmp_path / "final"
        _write_reviewed_dataset(dataset)

        build_dataset(dataset, output)

        assert (output / "audio" / "pam_000001.wav").is_file()
        assert (output / "audio" / "pam_000002.wav").is_file()
        assert (output / "audio" / "pam_000003.wav").is_file()

    def test_file_paths_updated_in_csvs(self, tmp_path: Path) -> None:
        dataset = tmp_path / "reviewed"
        output = tmp_path / "final"
        _write_reviewed_dataset(dataset)

        build_dataset(dataset, output)

        rows = _read_csv(output / "metadata.csv")
        for row in rows:
            assert row["file_path"].startswith("audio/")

    def test_split_csvs_are_partitions(self, tmp_path: Path) -> None:
        dataset = tmp_path / "reviewed"
        output = tmp_path / "final"
        _write_reviewed_dataset(dataset)

        build_dataset(dataset, output)

        all_rows = _read_csv(output / "metadata.csv")
        train_rows = _read_csv(output / "train.csv")
        val_rows = _read_csv(output / "validation.csv")
        test_rows = _read_csv(output / "test.csv")

        assert len(train_rows) + len(val_rows) + len(test_rows) == len(all_rows)

        # Each split CSV should only contain rows with that split value.
        for row in train_rows:
            assert row["split"] == "train"
        for row in val_rows:
            assert row["split"] == "validation"
        for row in test_rows:
            assert row["split"] == "test"

    def test_dataset_stats_json_correct(self, tmp_path: Path) -> None:
        dataset = tmp_path / "reviewed"
        output = tmp_path / "final"
        _write_reviewed_dataset(dataset)

        build_dataset(dataset, output)

        stats = json.loads(
            (output / "dataset_stats.json").read_text(encoding="utf-8")
        )
        assert stats["total_clips"] == 3
        assert stats["total_speakers"] == 2
        assert stats["total_duration_seconds"] == 21.5
        assert "pam" in stats["languages"]
        assert stats["languages"]["pam"] == 3
        assert stats["source_counts"]["approved"] == 3

    def test_dataset_card_generated(self, tmp_path: Path) -> None:
        dataset = tmp_path / "reviewed"
        output = tmp_path / "final"
        _write_reviewed_dataset(dataset)

        build_dataset(dataset, output)

        card = (output / "dataset_card.md").read_text(encoding="utf-8")
        assert "BosesPH Dataset Card" in card
        assert "3" in card  # total clips
        assert "pam" in card

    def test_no_approved_clips_raises(self, tmp_path: Path) -> None:
        dataset = tmp_path / "reviewed"
        output = tmp_path / "final"
        rows = [
            {
                "audio_id": "pam_000001",
                "file_path": "audio_clean/pam_000001.wav",
                "transcript": "Rejected.",
                "language": "pam",
                "speaker_id": "spk_001",
                "duration_seconds": "8.0",
                "sample_rate": "16000",
                "split": "unassigned",
                "quality_status": "rejected",
                "reviewer_notes": "bad",
            },
        ]
        _write_reviewed_dataset(dataset, rows=rows)

        with pytest.raises(DatasetBuildError, match="no approved clips"):
            build_dataset(dataset, output)

    def test_missing_metadata_raises(self, tmp_path: Path) -> None:
        dataset = tmp_path / "missing"
        output = tmp_path / "final"

        with pytest.raises(DatasetBuildError, match="metadata.csv not found"):
            build_dataset(dataset, output)

    def test_invalid_ratios_raises(self, tmp_path: Path) -> None:
        dataset = tmp_path / "reviewed"
        output = tmp_path / "final"
        _write_reviewed_dataset(dataset)

        with pytest.raises(DatasetBuildError, match="split ratios must sum to 1.0"):
            build_dataset(dataset, output, train_ratio=0.5, val_ratio=0.1, test_ratio=0.1)

    def test_overwrite_flag(self, tmp_path: Path) -> None:
        dataset = tmp_path / "reviewed"
        output = tmp_path / "final"
        _write_reviewed_dataset(dataset)

        # First build succeeds.
        build_dataset(dataset, output)

        # Second build without overwrite fails.
        with pytest.raises(DatasetBuildError, match="not empty"):
            build_dataset(dataset, output)

        # With overwrite flag it succeeds.
        report = build_dataset(dataset, output, overwrite=True)
        assert report.total_clips == 3

    def test_source_counts_include_all_statuses(self, tmp_path: Path) -> None:
        dataset = tmp_path / "reviewed"
        output = tmp_path / "final"
        rows = [
            {
                "audio_id": "pam_000001",
                "file_path": "audio_clean/pam_000001.wav",
                "transcript": "Approved.",
                "language": "pam",
                "speaker_id": "spk_001",
                "duration_seconds": "8.0",
                "sample_rate": "16000",
                "split": "unassigned",
                "quality_status": "approved",
                "reviewer_notes": "",
            },
            {
                "audio_id": "pam_000002",
                "file_path": "audio_clean/pam_000002.wav",
                "transcript": "Rejected.",
                "language": "pam",
                "speaker_id": "spk_002",
                "duration_seconds": "6.0",
                "sample_rate": "16000",
                "split": "unassigned",
                "quality_status": "rejected",
                "reviewer_notes": "bad",
            },
        ]
        _write_reviewed_dataset(dataset, rows=rows)

        build_dataset(dataset, output)

        stats = json.loads(
            (output / "dataset_stats.json").read_text(encoding="utf-8")
        )
        assert stats["source_counts"]["approved"] == 1
        assert stats["source_counts"]["rejected"] == 1


# --- CLI integration tests ---


class TestBuildDatasetCLI:
    def test_build_dataset_cli_success(
        self, tmp_path: Path, capsys: object
    ) -> None:
        dataset = tmp_path / "reviewed"
        output = tmp_path / "final"
        _write_reviewed_dataset(dataset)

        exit_code = main(
            ["build-dataset", str(dataset), "--output", str(output)]
        )
        captured = capsys.readouterr()  # type: ignore[attr-defined]

        assert exit_code == 0
        assert "Built dataset at" in captured.out
        assert "Total clips: 3" in captured.out
        assert "Speakers: 2" in captured.out

    def test_build_dataset_cli_missing_input_returns_two(
        self, tmp_path: Path, capsys: object
    ) -> None:
        exit_code = main(
            [
                "build-dataset",
                str(tmp_path / "missing"),
                "--output",
                str(tmp_path / "final"),
            ]
        )

        assert exit_code == 2
        assert "Input error:" in capsys.readouterr().err  # type: ignore[attr-defined]

    def test_build_dataset_cli_overwrite(
        self, tmp_path: Path, capsys: object
    ) -> None:
        dataset = tmp_path / "reviewed"
        output = tmp_path / "final"
        _write_reviewed_dataset(dataset)

        main(["build-dataset", str(dataset), "--output", str(output)])

        refused = main(
            ["build-dataset", str(dataset), "--output", str(output)]
        )
        assert refused == 2

        overwritten = main(
            [
                "build-dataset",
                str(dataset),
                "--output",
                str(output),
                "--overwrite",
            ]
        )
        assert overwritten == 0

    def test_build_dataset_cli_custom_ratios(
        self, tmp_path: Path, capsys: object
    ) -> None:
        dataset = tmp_path / "reviewed"
        output = tmp_path / "final"
        _write_reviewed_dataset(dataset)

        exit_code = main(
            [
                "build-dataset",
                str(dataset),
                "--output",
                str(output),
                "--train",
                "0.6",
                "--val",
                "0.2",
                "--test",
                "0.2",
            ]
        )

        assert exit_code == 0
