"""PLD session ingestion orchestration and generated dataset publication."""

from __future__ import annotations

import csv
import shutil
import tempfile
import uuid
from contextlib import suppress
from pathlib import Path

from pydantic import BaseModel, ValidationError

from bosesph.audio import (
    AudioError,
    AudioInspection,
    CorruptAudioError,
    EmptyAudioError,
    UnsupportedAudioError,
    inspect_wav,
    standardize_wav,
)
from bosesph.metadata import DatasetSplit, MetadataRecord, QualityStatus
from bosesph.pld import PldSession, PldTranscript, parse_pld_session

METADATA_COLUMNS = [
    "audio_id",
    "file_path",
    "transcript",
    "language",
    "speaker_id",
    "duration_seconds",
    "sample_rate",
    "split",
    "quality_status",
    "source_id",
    "region",
    "speaker_age_group",
    "speaker_gender",
    "recording_device",
    "environment",
    "code_switch_languages",
    "reviewer_notes",
]


class IngestionError(ValueError):
    """Base class for command-level ingestion failures."""


class OutputExistsError(IngestionError):
    """Raised when generated output would overwrite existing content."""


class IngestionReason(BaseModel):
    """One machine-readable reason for a clip's status."""

    code: str
    message: str


class SourceAudioProperties(BaseModel):
    """Serializable source audio inspection fields."""

    duration_seconds: float
    sample_rate: int
    channels: int
    sample_width: int
    rms: float


class IngestionClip(BaseModel):
    """One source filename and its generated ingestion disposition."""

    audio_id: str
    original_filename: str
    generated_filename: str | None
    prompt_list: str | None
    transcript: str | None
    status: QualityStatus
    source_audio: SourceAudioProperties | None
    reasons: list[IngestionReason]


class IngestionCounts(BaseModel):
    """Status totals for an ingestion batch."""

    pending: int
    needs_review: int
    rejected: int


class IngestionReport(BaseModel):
    """Complete, serializable result of importing one PLD session."""

    source: str
    output: str
    discovered_wav_count: int
    transcript_row_count: int
    counts: IngestionCounts
    clips: list[IngestionClip]


def _source_properties(inspection: AudioInspection) -> SourceAudioProperties:
    return SourceAudioProperties(
        duration_seconds=inspection.duration_seconds,
        sample_rate=inspection.sample_rate,
        channels=inspection.channels,
        sample_width=inspection.sample_width,
        rms=inspection.rms,
    )


def _rejected_clip(
    *,
    audio_id: str,
    filename: str,
    transcript: PldTranscript | None,
    code: str,
    message: str,
    inspection: AudioInspection | None = None,
) -> IngestionClip:
    return IngestionClip(
        audio_id=audio_id,
        original_filename=filename,
        generated_filename=None,
        prompt_list=transcript.prompt_list if transcript else None,
        transcript=transcript.transcript if transcript else None,
        status=QualityStatus.REJECTED,
        source_audio=_source_properties(inspection) if inspection else None,
        reasons=[IngestionReason(code=code, message=message)],
    )


def _metadata_row(record: MetadataRecord) -> dict[str, object]:
    values = record.model_dump(mode="json")
    languages = values.get("code_switch_languages")
    values["code_switch_languages"] = (
        ";".join(languages) if isinstance(languages, list) else ""
    )
    return {column: values.get(column) or "" for column in METADATA_COLUMNS}


def _write_metadata(path: Path, records: list[MetadataRecord]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=METADATA_COLUMNS)
        writer.writeheader()
        writer.writerows(_metadata_row(record) for record in records)


def _reason_for_audio_error(error: AudioError) -> str:
    if isinstance(error, CorruptAudioError):
        return "corrupt_audio"
    if isinstance(error, EmptyAudioError):
        return "empty_audio"
    if isinstance(error, UnsupportedAudioError):
        return "unsupported_audio"
    return "conversion_failed"


def _build_outputs(
    session: PldSession,
    output: Path,
    final_output: Path,
) -> IngestionReport:
    audio_output = output / "audio_clean"
    audio_output.mkdir(parents=True)
    transcripts = {row.filename: row for row in session.transcripts}
    wavs = {path.name: path for path in session.source.glob("*.wav")}
    filenames = sorted(set(transcripts) | set(wavs))
    clips: list[IngestionClip] = []
    records: list[MetadataRecord] = []

    for index, filename in enumerate(filenames, start=1):
        audio_id = f"pam_{index:06d}"
        generated_filename = f"{audio_id}.wav"
        transcript = transcripts.get(filename)
        source_audio = wavs.get(filename)

        if transcript is None:
            inspection = None
            if source_audio is not None:
                with suppress(AudioError):
                    inspection = inspect_wav(source_audio)
            clips.append(
                _rejected_clip(
                    audio_id=audio_id,
                    filename=filename,
                    transcript=None,
                    code="missing_transcript",
                    message="WAV file has no matching transcript row",
                    inspection=inspection,
                )
            )
            continue
        if source_audio is None:
            clips.append(
                _rejected_clip(
                    audio_id=audio_id,
                    filename=filename,
                    transcript=transcript,
                    code="missing_audio",
                    message="transcript row references a missing WAV file",
                )
            )
            continue
        try:
            inspection = inspect_wav(source_audio)
        except AudioError as error:
            clips.append(
                _rejected_clip(
                    audio_id=audio_id,
                    filename=filename,
                    transcript=transcript,
                    code=_reason_for_audio_error(error),
                    message=str(error),
                )
            )
            continue

        if not transcript.transcript.strip():
            clips.append(
                _rejected_clip(
                    audio_id=audio_id,
                    filename=filename,
                    transcript=transcript,
                    code="missing_transcript",
                    message="transcript is empty",
                    inspection=inspection,
                )
            )
            continue

        if inspection.fully_silent:
            clips.append(
                _rejected_clip(
                    audio_id=audio_id,
                    filename=filename,
                    transcript=transcript,
                    code="fully_silent",
                    message="audio contains no nonzero PCM samples",
                    inspection=inspection,
                )
            )
            continue

        reasons: list[IngestionReason] = []
        if not 5 <= inspection.duration_seconds <= 15:
            reasons.append(
                IngestionReason(
                    code="nonstandard_duration",
                    message="recommended clip duration is 5–15 seconds",
                )
            )
        if inspection.suspicious_quiet:
            reasons.append(
                IngestionReason(
                    code="suspicious_silence",
                    message="audio RMS is at or below -60 dBFS",
                )
            )
        status = QualityStatus.NEEDS_REVIEW if reasons else QualityStatus.PENDING
        reviewer_notes = "; ".join(reason.message for reason in reasons) or None
        record_data = {
            "audio_id": audio_id,
            "file_path": f"audio_clean/{generated_filename}",
            "transcript": transcript.transcript,
            "language": "pam",
            "speaker_id": session.speaker_id,
            "duration_seconds": inspection.duration_seconds,
            "sample_rate": 16000,
            "split": DatasetSplit.UNASSIGNED,
            "quality_status": status,
            "source_id": session.session_id,
            "speaker_gender": session.speaker_gender,
            "environment": session.environment,
            "reviewer_notes": reviewer_notes,
        }
        try:
            record = MetadataRecord.model_validate(record_data)
        except ValidationError as error:
            clips.append(
                _rejected_clip(
                    audio_id=audio_id,
                    filename=filename,
                    transcript=transcript,
                    code="invalid_metadata",
                    message=str(error),
                    inspection=inspection,
                )
            )
            continue

        try:
            standardize_wav(source_audio, audio_output / generated_filename)
        except AudioError as error:
            clips.append(
                _rejected_clip(
                    audio_id=audio_id,
                    filename=filename,
                    transcript=transcript,
                    code="conversion_failed",
                    message=str(error),
                    inspection=inspection,
                )
            )
            continue

        records.append(record)
        clips.append(
            IngestionClip(
                audio_id=audio_id,
                original_filename=filename,
                generated_filename=generated_filename,
                prompt_list=transcript.prompt_list,
                transcript=transcript.transcript,
                status=status,
                source_audio=_source_properties(inspection),
                reasons=reasons,
            )
        )

    counts = IngestionCounts(
        pending=sum(clip.status == QualityStatus.PENDING for clip in clips),
        needs_review=sum(clip.status == QualityStatus.NEEDS_REVIEW for clip in clips),
        rejected=sum(clip.status == QualityStatus.REJECTED for clip in clips),
    )
    report = IngestionReport(
        source=str(session.source),
        output=str(final_output),
        discovered_wav_count=len(wavs),
        transcript_row_count=len(session.transcripts),
        counts=counts,
        clips=clips,
    )
    _write_metadata(output / "metadata.csv", records)
    (output / "ingestion_report.json").write_text(
        report.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def _publish(stage: Path, output: Path) -> None:
    backup: Path | None = None
    try:
        if output.exists():
            backup = output.parent / f".{output.name}.backup-{uuid.uuid4().hex}"
            output.rename(backup)
        stage.rename(output)
    except OSError:
        if backup is not None and backup.exists() and not output.exists():
            backup.rename(output)
        raise
    else:
        if backup is not None:
            if backup.is_dir():
                shutil.rmtree(backup)
            else:
                backup.unlink()


def import_pld_session(
    source: str | Path,
    output: str | Path,
    *,
    overwrite: bool = False,
) -> IngestionReport:
    """Import one PLD session and safely publish a standardized dataset."""
    session = parse_pld_session(source)
    output_path = Path(output)
    if output_path.exists() and not output_path.is_dir():
        raise OutputExistsError(f"output path is not a directory: {output_path}")
    if output_path.is_dir() and any(output_path.iterdir()) and not overwrite:
        raise OutputExistsError(
            f"output directory is not empty; use --overwrite: {output_path}"
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(
        tempfile.mkdtemp(
            prefix=f".{output_path.name}.stage-",
            dir=output_path.parent,
        )
    )
    try:
        report = _build_outputs(session, stage, output_path)
        _publish(stage, output_path)
        return report
    finally:
        if stage.exists():
            shutil.rmtree(stage)
