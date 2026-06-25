"""Tests for the Phase 5 ASR benchmark pipeline."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from bosesph.asr import (
    ASRError,
    BenchmarkMetrics,
    TranscriptionResult,
    normalize_for_scoring,
    transcribe_file,
    transcribe_split,
)
from bosesph.benchmark import generate_benchmark_report
from bosesph.cli import main
from tests.audio_fixtures import write_pcm_wav

SPLIT_FIELDNAMES = [
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


def _write_split_csv(
    path: Path,
    rows: list[dict[str, str]],
    *,
    fieldnames: list[str] | None = None,
) -> None:
    """Write a split CSV matching the dataset builder format."""
    fnames = fieldnames or SPLIT_FIELDNAMES
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fnames)
        writer.writeheader()
        writer.writerows(rows)


def _make_dataset(
    base: Path,
    *,
    n_clips: int = 3,
    split: str = "test",
    create_audio: bool = True,
) -> tuple[Path, list[dict[str, str]]]:
    """Build a minimal dataset directory with audio files and a split CSV."""
    audio_dir = base / "audio"
    audio_dir.mkdir(parents=True)

    rows = []
    for i in range(1, n_clips + 1):
        audio_id = f"pam_{i:06d}"
        file_path = f"audio/{audio_id}.wav"
        rows.append(
            {
                "audio_id": audio_id,
                "file_path": file_path,
                "transcript": f"Transcript number {i}.",
                "language": "pam",
                "speaker_id": "spk_001",
                "duration_seconds": "5.0",
                "sample_rate": "16000",
                "split": split,
                "quality_status": "approved",
                "reviewer_notes": "",
            }
        )
        if create_audio:
            write_pcm_wav(base / file_path, duration=1)

    _write_split_csv(base / f"{split}.csv", rows)
    return base, rows


def _fake_pipe(text: str = "fake prediction") -> Any:
    """Return a callable mimicking a HuggingFace ASR pipeline."""

    def pipe(audio_input: Any, **kwargs: Any) -> dict[str, str]:
        return {"text": text}

    return pipe


# ---------------------------------------------------------------------------
# normalize_for_scoring — pure function, no extras needed
# ---------------------------------------------------------------------------


class TestNormalizeForScoring:
    def test_lowercases(self) -> None:
        assert normalize_for_scoring("HELLO World") == "hello world"

    def test_strips_annotation_tags(self) -> None:
        assert normalize_for_scoring("Hello [noise] world") == "hello world"
        assert normalize_for_scoring("[laughter] hi [silence]") == "hi"

    def test_strips_punctuation(self) -> None:
        assert normalize_for_scoring("Hello, world!") == "hello world"
        assert normalize_for_scoring("It's a test.") == "its a test"

    def test_collapses_whitespace(self) -> None:
        assert normalize_for_scoring("hello   world") == "hello world"

    def test_combined(self) -> None:
        assert normalize_for_scoring("  [noise] Hello,  World!  ") == "hello world"

    def test_empty_string(self) -> None:
        assert normalize_for_scoring("") == ""

    def test_only_annotations(self) -> None:
        assert normalize_for_scoring("[noise] [silence]") == ""


# ---------------------------------------------------------------------------
# calculate_metrics — needs jiwer
# ---------------------------------------------------------------------------


class TestCalculateMetrics:
    @pytest.fixture(autouse=True)
    def _require_jiwer(self) -> None:
        pytest.importorskip("jiwer")

    def test_perfect_match(self) -> None:
        from bosesph.asr import calculate_metrics

        metrics = calculate_metrics(
            ["hello world", "foo bar"],
            ["hello world", "foo bar"],
        )
        assert metrics.wer == 0.0
        assert metrics.cer == 0.0

    def test_known_error(self) -> None:
        from bosesph.asr import calculate_metrics

        # "hello world" → "hello earth": 1 substitution out of 2 words = 0.5 WER
        metrics = calculate_metrics(["hello world"], ["hello earth"])
        assert metrics.wer == 0.5

    def test_empty_references_raises(self) -> None:
        from bosesph.asr import calculate_metrics

        with pytest.raises(ASRError, match="no references"):
            calculate_metrics([], [])

    def test_all_empty_after_normalisation_raises(self) -> None:
        from bosesph.asr import calculate_metrics

        with pytest.raises(ASRError, match="all references are empty"):
            calculate_metrics(["[noise]"], ["hello"])

    def test_metrics_model_fields(self) -> None:
        from bosesph.asr import calculate_metrics

        metrics = calculate_metrics(
            ["hello"],
            ["hello"],
            model="test-model",
            language="pam",
            total_duration_seconds=42.5,
        )
        assert metrics.model == "test-model"
        assert metrics.language == "pam"
        assert metrics.total_duration_seconds == 42.5
        assert metrics.test_clips == 1


# ---------------------------------------------------------------------------
# transcribe_file — uses fake pipe + real stdlib audio loading
# ---------------------------------------------------------------------------


class TestTranscribeFile:
    def test_returns_predicted_text(self, tmp_path: Path) -> None:
        audio = tmp_path / "clip.wav"
        write_pcm_wav(audio, duration=1)
        pytest.importorskip("numpy")

        pipe = _fake_pipe("masanting ya ing aldo")
        result = transcribe_file(pipe, audio)
        assert result == "masanting ya ing aldo"

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        pipe = _fake_pipe()
        with pytest.raises(ASRError, match="audio file not found"):
            transcribe_file(pipe, tmp_path / "missing.wav")


# ---------------------------------------------------------------------------
# transcribe_split — uses fake pipe, writes predictions CSV
# ---------------------------------------------------------------------------


class TestTranscribeSplit:
    def test_writes_predictions_csv(self, tmp_path: Path) -> None:
        pytest.importorskip("numpy")
        ds, rows = _make_dataset(tmp_path / "ds")
        output = tmp_path / "predictions.csv"

        results = transcribe_split(
            ds / "test.csv",
            ds,
            _fake_pipe("predicted text"),
            output_path=output,
        )

        assert len(results) == 3
        assert output.is_file()

        with output.open("r", encoding="utf-8", newline="") as handle:
            csv_rows = list(csv.DictReader(handle))
        assert len(csv_rows) == 3
        assert set(csv_rows[0].keys()) == {
            "audio_id",
            "reference",
            "prediction",
            "file_path",
        }

    def test_predictions_contain_correct_data(self, tmp_path: Path) -> None:
        pytest.importorskip("numpy")
        ds, rows = _make_dataset(tmp_path / "ds", n_clips=1)
        output = tmp_path / "predictions.csv"

        results = transcribe_split(
            ds / "test.csv",
            ds,
            _fake_pipe("whisper output"),
            output_path=output,
        )

        assert results[0].audio_id == "pam_000001"
        assert results[0].reference == "Transcript number 1."
        assert results[0].prediction == "whisper output"

    def test_progress_callback_invoked(self, tmp_path: Path) -> None:
        pytest.importorskip("numpy")
        ds, _ = _make_dataset(tmp_path / "ds", n_clips=2)
        output = tmp_path / "predictions.csv"
        progress = MagicMock()

        transcribe_split(
            ds / "test.csv",
            ds,
            _fake_pipe(),
            output_path=output,
            progress_fn=progress,
        )

        assert progress.call_count == 2
        progress.assert_any_call(1, 2)
        progress.assert_any_call(2, 2)

    def test_missing_audio_produces_placeholder(self, tmp_path: Path) -> None:
        ds, _ = _make_dataset(tmp_path / "ds", n_clips=1, create_audio=False)
        output = tmp_path / "predictions.csv"

        results = transcribe_split(
            ds / "test.csv",
            ds,
            _fake_pipe(),
            output_path=output,
        )

        assert results[0].prediction == "[missing audio]"

    def test_empty_csv_raises(self, tmp_path: Path) -> None:
        ds = tmp_path / "ds"
        ds.mkdir()
        _write_split_csv(ds / "test.csv", [])

        with pytest.raises(ASRError, match="empty"):
            transcribe_split(
                ds / "test.csv",
                ds,
                _fake_pipe(),
                output_path=tmp_path / "pred.csv",
            )

    def test_missing_csv_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ASRError, match="not found"):
            transcribe_split(
                tmp_path / "missing.csv",
                tmp_path,
                _fake_pipe(),
                output_path=tmp_path / "pred.csv",
            )


# ---------------------------------------------------------------------------
# evaluate_predictions — needs jiwer
# ---------------------------------------------------------------------------


class TestEvaluatePredictions:
    @pytest.fixture(autouse=True)
    def _require_jiwer(self) -> None:
        pytest.importorskip("jiwer")

    def _write_predictions(
        self,
        path: Path,
        rows: list[dict[str, str]],
    ) -> None:
        fieldnames = ["audio_id", "reference", "prediction", "file_path"]
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def test_basic_evaluation(self, tmp_path: Path) -> None:
        from bosesph.asr import evaluate_predictions

        pred_csv = tmp_path / "predictions.csv"
        self._write_predictions(
            pred_csv,
            [
                {
                    "audio_id": "pam_000001",
                    "reference": "hello world",
                    "prediction": "hello world",
                    "file_path": "audio/pam_000001.wav",
                },
            ],
        )

        metrics = evaluate_predictions(pred_csv)
        assert metrics.wer == 0.0
        assert metrics.cer == 0.0

    def test_missing_predictions_raises(self, tmp_path: Path) -> None:
        from bosesph.asr import evaluate_predictions

        with pytest.raises(ASRError, match="not found"):
            evaluate_predictions(tmp_path / "missing.csv")

    def test_references_override(self, tmp_path: Path) -> None:
        from bosesph.asr import evaluate_predictions

        pred_csv = tmp_path / "predictions.csv"
        self._write_predictions(
            pred_csv,
            [
                {
                    "audio_id": "pam_000001",
                    "reference": "wrong reference",
                    "prediction": "correct reference",
                    "file_path": "audio/pam_000001.wav",
                },
            ],
        )

        # Write a references CSV that matches the prediction.
        ref_csv = tmp_path / "references.csv"
        with ref_csv.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["audio_id", "transcript"])
            writer.writeheader()
            writer.writerow(
                {"audio_id": "pam_000001", "transcript": "correct reference"}
            )

        metrics = evaluate_predictions(pred_csv, references_csv=ref_csv)
        assert metrics.wer == 0.0


# ---------------------------------------------------------------------------
# generate_benchmark_report
# ---------------------------------------------------------------------------


class TestGenerateBenchmarkReport:
    def test_report_contains_key_fields(self, tmp_path: Path) -> None:
        metrics = BenchmarkMetrics(
            model="openai/whisper-small",
            language="kapampangan",
            wer=0.85,
            cer=0.45,
            test_clips=10,
            total_duration_seconds=50.0,
        )
        predictions = [
            TranscriptionResult(
                audio_id="pam_000001",
                reference="masanting ya",
                prediction="masanting",
                file_path="audio/pam_000001.wav",
            ),
        ]

        report_path = tmp_path / "report.md"
        generate_benchmark_report(metrics, predictions, report_path)

        report = report_path.read_text(encoding="utf-8")
        assert "openai/whisper-small" in report
        assert "kapampangan" in report
        assert "0.85" in report  # WER
        assert "0.45" in report  # CER
        assert "pam_000001" in report

    def test_report_error_examples_present(self, tmp_path: Path) -> None:
        pytest.importorskip("jiwer")
        metrics = BenchmarkMetrics(
            model="test",
            language="pam",
            wer=1.0,
            cer=0.5,
            test_clips=2,
            total_duration_seconds=10.0,
        )
        predictions = [
            TranscriptionResult(
                audio_id="pam_000001",
                reference="hello world",
                prediction="completely wrong text",
                file_path="audio/pam_000001.wav",
            ),
            TranscriptionResult(
                audio_id="pam_000002",
                reference="perfect match",
                prediction="perfect match",
                file_path="audio/pam_000002.wav",
            ),
        ]

        report_path = tmp_path / "report.md"
        generate_benchmark_report(metrics, predictions, report_path)

        report = report_path.read_text(encoding="utf-8")
        # The higher-error example should appear.
        assert "pam_000001" in report

    def test_results_json_roundtrip(self, tmp_path: Path) -> None:
        metrics = BenchmarkMetrics(
            model="openai/whisper-small",
            language="kapampangan",
            wer=0.85,
            cer=0.45,
            test_clips=10,
            total_duration_seconds=50.0,
        )

        results_path = tmp_path / "results.json"
        results_path.write_text(
            metrics.model_dump_json(indent=2) + "\n", encoding="utf-8"
        )

        loaded = json.loads(results_path.read_text(encoding="utf-8"))
        assert loaded["model"] == "openai/whisper-small"
        assert loaded["wer"] == 0.85
        assert loaded["cer"] == 0.45
        assert loaded["test_clips"] == 10

        roundtrip = BenchmarkMetrics.model_validate(loaded)
        assert roundtrip == metrics


# ---------------------------------------------------------------------------
# CLI integration tests
# ---------------------------------------------------------------------------


class TestTranscribeCLI:
    def test_transcribe_missing_source_returns_two(
        self, tmp_path: Path, capsys: object
    ) -> None:
        exit_code = main(["transcribe", str(tmp_path / "nonexistent.wav")])
        assert exit_code == 2

    def test_transcribe_dataset_missing_output_returns_two(
        self, tmp_path: Path, capsys: object
    ) -> None:
        ds, _ = _make_dataset(tmp_path / "ds")
        # Dataset dir without --output.
        exit_code = main(["transcribe", str(ds)])
        assert exit_code == 2
        captured = capsys.readouterr()  # type: ignore[attr-defined]
        assert "--output is required" in captured.err

    def test_transcribe_dataset_missing_split_returns_two(
        self, tmp_path: Path, capsys: object
    ) -> None:
        ds, _ = _make_dataset(tmp_path / "ds", split="train")
        # Default --split is test, which doesn't exist here.
        exit_code = main(
            ["transcribe", str(ds), "--output", str(tmp_path / "pred.csv")]
        )
        assert exit_code == 2
        captured = capsys.readouterr()  # type: ignore[attr-defined]
        assert "test.csv not found" in captured.err


class TestEvaluateCLI:
    def test_evaluate_missing_predictions_returns_two(
        self, tmp_path: Path, capsys: object
    ) -> None:
        exit_code = main(["evaluate", "--predictions", str(tmp_path / "missing.csv")])
        assert exit_code == 2
        captured = capsys.readouterr()  # type: ignore[attr-defined]
        assert "Input error:" in captured.err

    def test_evaluate_success(self, tmp_path: Path, capsys: object) -> None:
        pytest.importorskip("jiwer")

        pred_csv = tmp_path / "predictions.csv"
        fieldnames = ["audio_id", "reference", "prediction", "file_path"]
        with pred_csv.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerow(
                {
                    "audio_id": "pam_000001",
                    "reference": "hello",
                    "prediction": "hello",
                    "file_path": "audio/pam_000001.wav",
                }
            )

        exit_code = main(["evaluate", "--predictions", str(pred_csv)])
        assert exit_code == 0
        captured = capsys.readouterr()  # type: ignore[attr-defined]
        assert "WER:" in captured.out
        assert "CER:" in captured.out

    def test_evaluate_with_output_writes_files(
        self, tmp_path: Path, capsys: object
    ) -> None:
        pytest.importorskip("jiwer")

        pred_csv = tmp_path / "predictions.csv"
        fieldnames = ["audio_id", "reference", "prediction", "file_path"]
        with pred_csv.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerow(
                {
                    "audio_id": "pam_000001",
                    "reference": "hello world",
                    "prediction": "hello earth",
                    "file_path": "audio/pam_000001.wav",
                }
            )

        output_dir = tmp_path / "benchmark"
        exit_code = main(
            [
                "evaluate",
                "--predictions",
                str(pred_csv),
                "--output",
                str(output_dir),
            ]
        )

        assert exit_code == 0
        assert (output_dir / "results.json").is_file()
        assert (output_dir / "report.md").is_file()

        results = json.loads((output_dir / "results.json").read_text(encoding="utf-8"))
        assert results["wer"] == 0.5
