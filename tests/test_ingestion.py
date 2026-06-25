from __future__ import annotations

import csv
import json
import wave
from pathlib import Path

import pytest

from bosesph.audio import AudioError
from bosesph.ingestion import (
    OutputExistsError,
    import_pld_session,
)
from bosesph.metadata import validate_metadata_csv
from bosesph.pld import PldParseError
from tests.audio_fixtures import write_pcm_wav


def write_session(source: Path, rows: list[tuple[str, str]]) -> None:
    source.mkdir()
    transcript_lines = "".join(
        f'{filename} "KAP_Iso.txt" "{transcript}"\n' for filename, transcript in rows
    )
    (source / "0400.session.log").write_text(
        '\ufeffSessionID = "120223.051412"\n'
        'SessionEnvironment = "closed empty room"\n'
        'SpeakerID = "0400"\n'
        'SpeakerGender = "male"\n' + transcript_lines,
        encoding="utf-8",
    )


def read_metadata(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_import_pld_session_generates_standardized_metadata_and_statuses(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    output = tmp_path / "dataset"
    write_session(
        source,
        [
            ("clip-c.wav", "Quiet clip."),
            ("clip-a.wav", "Standard clip."),
            ("clip-b.wav", "Short clip."),
        ],
    )
    write_pcm_wav(source / "clip-a.wav", duration=6)
    write_pcm_wav(source / "clip-b.wav", duration=2, sample_rate=44100, channels=2)
    write_pcm_wav(source / "clip-c.wav", duration=6, amplitude=0.001)
    original_bytes = {path.name: path.read_bytes() for path in source.glob("*.wav")}

    result = import_pld_session(source, output)

    assert result.counts.model_dump() == {
        "pending": 1,
        "needs_review": 2,
        "rejected": 0,
    }
    rows = read_metadata(output / "metadata.csv")
    assert [row["audio_id"] for row in rows] == [
        "pam_000001",
        "pam_000002",
        "pam_000003",
    ]
    assert [row["quality_status"] for row in rows] == [
        "pending",
        "needs_review",
        "needs_review",
    ]
    assert rows[0]["speaker_id"] == "spk_0400"
    assert rows[0]["source_id"] == "120223.051412"
    assert validate_metadata_csv(output / "metadata.csv").error_count == 0
    for row in rows:
        with wave.open(str(output / row["file_path"]), "rb") as audio:
            assert audio.getframerate() == 16000
            assert audio.getnchannels() == 1
            assert audio.getsampwidth() == 2
    assert {
        path.name: path.read_bytes() for path in source.glob("*.wav")
    } == original_bytes


def test_import_pld_session_records_clip_level_rejections(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    output = tmp_path / "dataset"
    write_session(
        source,
        [
            ("corrupt.wav", "Corrupt."),
            ("empty.wav", "Empty."),
            ("missing.wav", "Missing."),
            ("silent.wav", "Silent."),
        ],
    )
    (source / "corrupt.wav").write_bytes(b"not a wav")
    write_pcm_wav(source / "empty.wav", duration=0)
    write_pcm_wav(source / "silent.wav", duration=1, amplitude=0)
    write_pcm_wav(source / "unmatched.wav", duration=6)

    result = import_pld_session(source, output)

    assert result.counts.rejected == 5
    report = json.loads((output / "ingestion_report.json").read_text())
    reason_codes = {
        reason["code"] for clip in report["clips"] for reason in clip["reasons"]
    }
    assert {
        "corrupt_audio",
        "empty_audio",
        "missing_audio",
        "fully_silent",
        "missing_transcript",
    } <= reason_codes
    unmatched = next(
        clip for clip in report["clips"] if clip["original_filename"] == "unmatched.wav"
    )
    assert unmatched["source_audio"]["sample_rate"] == 16000
    assert read_metadata(output / "metadata.csv") == []
    assert not any((output / "audio_clean").glob("*.wav"))


def test_import_pld_session_records_conversion_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "source"
    output = tmp_path / "dataset"
    write_session(source, [("clip.wav", "Text.")])
    write_pcm_wav(source / "clip.wav", duration=6)

    def fail_conversion(source_path: Path, output_path: Path) -> object:
        raise AudioError("write failed")

    monkeypatch.setattr("bosesph.ingestion.standardize_wav", fail_conversion)

    result = import_pld_session(source, output)

    assert result.counts.rejected == 1
    assert result.clips[0].reasons[0].code == "conversion_failed"


def test_import_refuses_nonempty_output_without_overwrite(tmp_path: Path) -> None:
    source = tmp_path / "source"
    output = tmp_path / "dataset"
    write_session(source, [("clip.wav", "Text.")])
    write_pcm_wav(source / "clip.wav", duration=6)
    output.mkdir()
    (output / "keep.txt").write_text("existing", encoding="utf-8")

    with pytest.raises(OutputExistsError):
        import_pld_session(source, output)

    assert (output / "keep.txt").read_text(encoding="utf-8") == "existing"


def test_import_overwrite_replaces_existing_output(tmp_path: Path) -> None:
    source = tmp_path / "source"
    output = tmp_path / "dataset"
    write_session(source, [("clip.wav", "Text.")])
    write_pcm_wav(source / "clip.wav", duration=6)
    output.mkdir()
    (output / "stale.txt").write_text("stale", encoding="utf-8")

    import_pld_session(source, output, overwrite=True)

    assert not (output / "stale.txt").exists()
    assert (output / "metadata.csv").exists()
    assert not list(tmp_path.glob(".dataset.stage-*"))
    assert not list(tmp_path.glob(".dataset.backup-*"))


def test_invalid_source_leaves_existing_output_untouched(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    output = tmp_path / "dataset"
    output.mkdir()
    (output / "keep.txt").write_text("existing", encoding="utf-8")

    with pytest.raises(PldParseError):
        import_pld_session(source, output, overwrite=True)

    assert (output / "keep.txt").read_text(encoding="utf-8") == "existing"
