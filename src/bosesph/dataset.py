"""Dataset builder: filter approved clips, split, and export."""

from __future__ import annotations

import shutil
import textwrap
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel

from bosesph.metadata import DatasetSplit, QualityStatus
from bosesph.transcripts import (
    TranscriptDatasetError,
    _read_rows,
    _write_csv,
)


class DatasetBuildError(ValueError):
    """Raised when the dataset cannot be built."""


class SplitDistribution(BaseModel):
    """Clip and duration counts for one split."""

    clips: int
    speakers: int
    duration_seconds: float


class SourceCounts(BaseModel):
    """Status counts from the source dataset before filtering."""

    approved: int
    pending: int
    needs_review: int
    rejected: int


class DatasetStats(BaseModel):
    """Comprehensive statistics for the built dataset."""

    total_clips: int
    total_duration_seconds: float
    total_duration_display: str
    total_speakers: int
    average_clip_seconds: float
    languages: dict[str, int]
    splits: dict[str, SplitDistribution]
    source_counts: SourceCounts


class DatasetBuildReport(BaseModel):
    """Result summary returned by the build function."""

    output: str
    total_clips: int
    train_clips: int
    validation_clips: int
    test_clips: int
    speakers: int
    excluded: int


def _format_duration(seconds: float) -> str:
    total = int(seconds)
    hours = total // 3600
    minutes = (total % 3600) // 60
    secs = total % 60
    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    return f"{minutes}m {secs}s"


def _assign_splits(
    rows: list[dict[str, str]],
    *,
    train_ratio: float,
    val_ratio: float,
    test_ratio: float,
    seed: int,
) -> None:
    """Assign splits in-place using speaker-aware greedy allocation."""
    # Group rows by speaker_id.
    speaker_rows: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        speaker_rows[row["speaker_id"]].append(row)

    # Sort speakers by total clip count (descending) for greedy balance.
    # Secondary sort by speaker_id for determinism.
    speakers = sorted(
        speaker_rows.keys(),
        key=lambda sid: (-len(speaker_rows[sid]), sid),
    )

    total = len(rows)
    targets = {
        DatasetSplit.TRAIN: round(total * train_ratio),
        DatasetSplit.VALIDATION: round(total * val_ratio),
        DatasetSplit.TEST: round(total * test_ratio),
    }
    counts: dict[DatasetSplit, int] = {
        DatasetSplit.TRAIN: 0,
        DatasetSplit.VALIDATION: 0,
        DatasetSplit.TEST: 0,
    }

    # Greedy assignment: give each speaker to the bucket furthest below target.
    for speaker_id in speakers:
        group = speaker_rows[speaker_id]
        group_size = len(group)

        # Pick the split with the largest remaining deficit.
        best_split = max(
            counts,
            key=lambda s: targets[s] - counts[s],
        )
        counts[best_split] += group_size
        for row in group:
            row["split"] = best_split.value


def _compute_stats(
    rows: list[dict[str, str]],
    source_counts: SourceCounts,
) -> DatasetStats:
    """Compute dataset statistics from the assigned rows."""
    total_clips = len(rows)
    durations = [float(row["duration_seconds"]) for row in rows]
    total_duration = sum(durations)
    speakers = {row["speaker_id"] for row in rows}

    languages: dict[str, int] = defaultdict(int)
    for row in rows:
        languages[row["language"]] += 1

    split_data: dict[str, SplitDistribution] = {}
    for split in (DatasetSplit.TRAIN, DatasetSplit.VALIDATION, DatasetSplit.TEST):
        split_rows = [row for row in rows if row["split"] == split.value]
        split_data[split.value] = SplitDistribution(
            clips=len(split_rows),
            speakers=len({row["speaker_id"] for row in split_rows}),
            duration_seconds=sum(float(row["duration_seconds"]) for row in split_rows),
        )

    return DatasetStats(
        total_clips=total_clips,
        total_duration_seconds=total_duration,
        total_duration_display=_format_duration(total_duration),
        total_speakers=len(speakers),
        average_clip_seconds=(
            round(total_duration / total_clips, 3) if total_clips else 0.0
        ),
        languages=dict(languages),
        splits=split_data,
        source_counts=source_counts,
    )


def _generate_dataset_card(stats: DatasetStats) -> str:
    """Generate a markdown dataset card from statistics."""
    languages = ", ".join(
        f"{lang} ({count} clips)" for lang, count in stats.languages.items()
    )
    empty_split = SplitDistribution(clips=0, speakers=0, duration_seconds=0)
    train = stats.splits.get("train", empty_split)
    validation = stats.splits.get("validation", empty_split)
    test = stats.splits.get("test", empty_split)
    train_duration = _format_duration(train.duration_seconds)
    validation_duration = _format_duration(validation.duration_seconds)
    test_duration = _format_duration(test.duration_seconds)
    validation_row = (
        f"| Validation | {validation.clips} | {validation.speakers} | "
        f"{validation_duration} |"
    )
    generated_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lines = textwrap.dedent(
        f"""\
        # BosesPH Dataset Card

        ## Overview

        | Field | Value |
        |---|---|
        | Total clips | {stats.total_clips} |
        | Total duration | {stats.total_duration_display} |
        | Total speakers | {stats.total_speakers} |
        | Average clip length | {stats.average_clip_seconds}s |
        | Languages | {languages} |

        ## Split Distribution

        | Split | Clips | Speakers | Duration |
        |---|---:|---:|---|
        | Train | {train.clips} | {train.speakers} | {train_duration} |
        {validation_row}
        | Test | {test.clips} | {test.speakers} | {test_duration} |

        ## Source Data Summary

        | Status | Count |
        |---|---:|
        | Approved | {stats.source_counts.approved} |
        | Pending | {stats.source_counts.pending} |
        | Needs review | {stats.source_counts.needs_review} |
        | Rejected | {stats.source_counts.rejected} |

        ## Collection Method

        Audio clips were imported from PLD (Philippine Languages Dataset) recording
        sessions and processed through the BosesPH Toolkit ingestion pipeline.

        ## Intended Use

        This dataset is intended for training and evaluating automatic speech
        recognition (ASR) models for Philippine languages.

        ## Limitations

        - Single-source recording sessions may have limited speaker diversity.
        - Transcription accuracy depends on human review quality.
        - Duration distribution may be uneven across clips.

        ---

        *Generated by BosesPH Toolkit on {generated_date}*
    """
    )
    return lines


def _write_split_csv(
    path: Path,
    fieldnames: list[str],
    rows: list[dict[str, str]],
    split: DatasetSplit,
) -> None:
    """Write a CSV containing only the rows for one split."""
    split_rows = [row for row in rows if row["split"] == split.value]
    _write_csv(path, fieldnames, split_rows)


def build_dataset(
    dataset: str | Path,
    output: str | Path,
    *,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    seed: int = 42,
    overwrite: bool = False,
) -> DatasetBuildReport:
    """Build the final dataset package from a reviewed dataset directory."""
    dataset_path = Path(dataset)
    output_path = Path(output)
    metadata_path = dataset_path / "metadata.csv"

    # Validate input.
    if not metadata_path.is_file():
        raise DatasetBuildError(
            f"metadata.csv not found in dataset directory: {dataset_path}"
        )

    total = round(train_ratio + val_ratio + test_ratio, 10)
    if not (0.99 <= total <= 1.01):
        raise DatasetBuildError(f"split ratios must sum to 1.0, got {total}")

    # Validate output.
    if output_path.exists() and not output_path.is_dir():
        raise DatasetBuildError(f"output path is not a directory: {output_path}")
    if output_path.is_dir() and any(output_path.iterdir()) and not overwrite:
        raise DatasetBuildError(
            f"output directory is not empty; use --overwrite: {output_path}"
        )

    # Read and validate source metadata.
    try:
        fieldnames, all_rows = _read_rows(metadata_path)
    except TranscriptDatasetError as error:
        raise DatasetBuildError(str(error)) from error

    # Count source statuses before filtering.
    source_counts = SourceCounts(
        approved=sum(
            1
            for row in all_rows
            if row.get("quality_status") == QualityStatus.APPROVED.value
        ),
        pending=sum(
            1
            for row in all_rows
            if row.get("quality_status") == QualityStatus.PENDING.value
        ),
        needs_review=sum(
            1
            for row in all_rows
            if row.get("quality_status") == QualityStatus.NEEDS_REVIEW.value
        ),
        rejected=sum(
            1
            for row in all_rows
            if row.get("quality_status") == QualityStatus.REJECTED.value
        ),
    )

    # Filter to approved-only rows.
    approved_rows = [
        dict(row)  # shallow copy so we can mutate split
        for row in all_rows
        if row.get("quality_status") == QualityStatus.APPROVED.value
    ]
    excluded = len(all_rows) - len(approved_rows)

    if not approved_rows:
        raise DatasetBuildError("no approved clips found; run review before building")

    # Assign splits.
    _assign_splits(
        approved_rows,
        train_ratio=train_ratio,
        val_ratio=val_ratio,
        test_ratio=test_ratio,
        seed=seed,
    )

    # Prepare output directory.
    if output_path.exists() and overwrite:
        shutil.rmtree(output_path)
    output_path.mkdir(parents=True, exist_ok=True)
    audio_output = output_path / "audio"
    audio_output.mkdir()

    # Copy audio files and update file_path to the new directory.
    for row in approved_rows:
        source_audio = dataset_path / row["file_path"]
        new_filename = Path(row["file_path"]).name
        new_file_path = f"audio/{new_filename}"
        dest = audio_output / new_filename
        if source_audio.is_file():
            shutil.copy2(source_audio, dest)
        row["file_path"] = new_file_path

    # Ensure 'split' column is in fieldnames.
    if "split" not in fieldnames:
        fieldnames.append("split")

    # Write CSVs.
    _write_csv(output_path / "metadata.csv", fieldnames, approved_rows)
    _write_split_csv(
        output_path / "train.csv", fieldnames, approved_rows, DatasetSplit.TRAIN
    )
    _write_split_csv(
        output_path / "validation.csv",
        fieldnames,
        approved_rows,
        DatasetSplit.VALIDATION,
    )
    _write_split_csv(
        output_path / "test.csv", fieldnames, approved_rows, DatasetSplit.TEST
    )

    # Compute and write statistics.
    stats = _compute_stats(approved_rows, source_counts)
    (output_path / "dataset_stats.json").write_text(
        stats.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )

    # Generate dataset card.
    (output_path / "dataset_card.md").write_text(
        _generate_dataset_card(stats),
        encoding="utf-8",
    )

    # Count splits for the report.
    train_clips = sum(
        1 for row in approved_rows if row["split"] == DatasetSplit.TRAIN.value
    )
    val_clips = sum(
        1 for row in approved_rows if row["split"] == DatasetSplit.VALIDATION.value
    )
    test_clips = sum(
        1 for row in approved_rows if row["split"] == DatasetSplit.TEST.value
    )

    return DatasetBuildReport(
        output=str(output_path),
        total_clips=len(approved_rows),
        train_clips=train_clips,
        validation_clips=val_clips,
        test_clips=test_clips,
        speakers=len({row["speaker_id"] for row in approved_rows}),
        excluded=excluded,
    )
