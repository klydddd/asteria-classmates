from __future__ import annotations

import csv
import json
from pathlib import Path

from bosesph.cli import main
from bosesph.metadata import MetadataRecord
from tests.audio_fixtures import write_pcm_wav


def write_valid_csv(path: Path, *, duration: str = "8") -> None:
    row = {
        "audio_id": "pam_000001",
        "file_path": "audio/pam_000001.wav",
        "transcript": "Masanting ya ing aldo.",
        "language": "pam",
        "speaker_id": "spk_001",
        "duration_seconds": duration,
        "sample_rate": "16000",
        "split": "train",
        "quality_status": "approved",
    }
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)


def test_validate_metadata_json_output(tmp_path: Path, capsys: object) -> None:
    csv_path = tmp_path / "metadata.csv"
    write_valid_csv(csv_path, duration="3")

    exit_code = main(["validate-metadata", str(csv_path), "--format", "json"])
    output = capsys.readouterr().out  # type: ignore[attr-defined]
    payload = json.loads(output)

    assert exit_code == 0
    assert payload["warning_count"] == 1
    assert payload["error_count"] == 0


def test_validate_metadata_text_output_and_metadata_error_exit(
    tmp_path: Path,
    capsys: object,
) -> None:
    csv_path = tmp_path / "metadata.csv"
    write_valid_csv(csv_path)
    text = csv_path.read_text(encoding="utf-8").replace("pam_000001", "bad", 1)
    csv_path.write_text(text, encoding="utf-8")

    exit_code = main(["validate-metadata", str(csv_path)])
    output = capsys.readouterr().out  # type: ignore[attr-defined]

    assert exit_code == 1
    assert "ERROR" in output
    assert "invalid_audio_id" in output
    assert "Rows: 1" in output


def test_validate_metadata_input_error_exit(
    tmp_path: Path,
    capsys: object,
) -> None:
    missing = tmp_path / "missing.csv"

    exit_code = main(["validate-metadata", str(missing), "--format", "json"])
    captured = capsys.readouterr()  # type: ignore[attr-defined]

    assert exit_code == 2
    assert json.loads(captured.err)["code"] == "input_error"


def test_cli_misuse_returns_exit_two(capsys: object) -> None:
    exit_code = main(["validate-metadata", "file.csv", "--format", "xml"])

    assert exit_code == 2
    assert "invalid choice" in capsys.readouterr().err.lower()  # type: ignore[attr-defined]


def test_export_metadata_schema_matches_model(
    tmp_path: Path,
    capsys: object,
) -> None:
    output_path = tmp_path / "metadata.schema.json"

    exit_code = main(["export-metadata-schema", "--output", str(output_path)])

    assert exit_code == 0
    assert json.loads(output_path.read_text(encoding="utf-8")) == (
        MetadataRecord.model_json_schema()
    )
    assert str(output_path) in capsys.readouterr().out  # type: ignore[attr-defined]


def test_checked_in_metadata_schema_matches_model() -> None:
    schema_path = Path("docs/metadata.schema.json")

    assert json.loads(schema_path.read_text(encoding="utf-8")) == (
        MetadataRecord.model_json_schema()
    )


def test_sample_metadata_template_is_valid() -> None:
    from bosesph.metadata import validate_metadata_csv

    report = validate_metadata_csv("sample_data/metadata_template.csv")

    assert report.row_count == 1
    assert report.error_count == 0


def write_pld_session(directory: Path) -> None:
    directory.mkdir()
    (directory / "session.log").write_text(
        'SessionID = "session-01"\n'
        'SessionEnvironment = "room"\n'
        'SpeakerID = "0400"\n'
        'SpeakerGender = "male"\n'
        'clip.wav "prompt.txt" "Masanting ya ing aldo."\n',
        encoding="utf-8",
    )
    write_pcm_wav(directory / "clip.wav", duration=6)


def test_import_pld_cli_generates_output(
    tmp_path: Path,
    capsys: object,
) -> None:
    source = tmp_path / "source"
    output = tmp_path / "dataset"
    write_pld_session(source)

    exit_code = main(["import-pld", str(source), "--output", str(output)])
    captured = capsys.readouterr()  # type: ignore[attr-defined]

    assert exit_code == 0
    assert "Pending: 1" in captured.out
    assert "Needs review: 0" in captured.out
    assert "Rejected: 0" in captured.out
    assert (output / "metadata.csv").exists()


def test_import_pld_cli_overwrite_and_input_errors(
    tmp_path: Path,
    capsys: object,
) -> None:
    source = tmp_path / "source"
    output = tmp_path / "dataset"
    write_pld_session(source)
    output.mkdir()
    (output / "stale.txt").write_text("stale", encoding="utf-8")

    refused = main(["import-pld", str(source), "--output", str(output)])
    refused_output = capsys.readouterr()  # type: ignore[attr-defined]
    overwritten = main(
        [
            "import-pld",
            str(source),
            "--output",
            str(output),
            "--overwrite",
        ]
    )

    assert refused == 2
    assert "Input error:" in refused_output.err
    assert overwritten == 0
    assert not (output / "stale.txt").exists()


def test_import_pld_cli_missing_source_returns_exit_two(
    tmp_path: Path,
    capsys: object,
) -> None:
    exit_code = main(
        [
            "import-pld",
            str(tmp_path / "missing"),
            "--output",
            str(tmp_path / "dataset"),
        ]
    )

    assert exit_code == 2
    assert "Input error:" in capsys.readouterr().err  # type: ignore[attr-defined]
