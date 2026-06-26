"""Tests for the Phase 6 fine-tuning pipeline."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from bosesph.asr import BenchmarkMetrics
from bosesph.benchmark import generate_comparison_report
from bosesph.cli import main
from bosesph.finetune import (
    FineTuneConfig,
    FineTuneReport,
    _build_example,
    _generate_model_card,
    _load_split_clips,
)
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
    split: str = "train",
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


def _fake_processor() -> Any:
    """Return a mock processor mimicking WhisperProcessor."""
    processor = MagicMock()

    # feature_extractor returns object with input_features attribute
    fe_result = MagicMock()
    fe_result.input_features = [[0.1, 0.2, 0.3]]
    processor.feature_extractor.return_value = fe_result

    # tokenizer returns object with input_ids attribute
    tok_result = MagicMock()
    tok_result.input_ids = [1, 2, 3, 4]
    processor.tokenizer.return_value = tok_result

    return processor


# -----------------------------------------------------------------------
# FineTuneConfig / FineTuneReport JSON roundtrip
# -----------------------------------------------------------------------


class TestFineTuneConfig:
    def test_json_roundtrip(self) -> None:
        config = FineTuneConfig(
            base_model="openai/whisper-tiny",
            language="tl",
            epochs=3,
            max_steps=None,
            batch_size=8,
            learning_rate=1e-5,
            train_clips=100,
            val_clips=15,
        )
        raw = config.model_dump_json()
        restored = FineTuneConfig.model_validate_json(raw)
        assert restored == config

    def test_with_max_steps(self) -> None:
        config = FineTuneConfig(
            base_model="openai/whisper-tiny",
            language="tl",
            epochs=3,
            max_steps=50,
            batch_size=8,
            learning_rate=1e-5,
            train_clips=100,
            val_clips=0,
        )
        data = json.loads(config.model_dump_json())
        assert data["max_steps"] == 50

    def test_lora_fields_roundtrip(self) -> None:
        config = FineTuneConfig(
            base_model="openai/whisper-tiny",
            language="tl",
            epochs=3,
            max_steps=None,
            batch_size=8,
            learning_rate=1e-5,
            train_clips=100,
            val_clips=15,
            use_lora=True,
            lora_r=16,
            lora_alpha=32,
            lora_dropout=0.05,
        )
        raw = config.model_dump_json()
        restored = FineTuneConfig.model_validate_json(raw)
        assert restored == config
        assert restored.use_lora is True
        assert restored.lora_r == 16

    def test_lora_defaults_when_omitted(self) -> None:
        config = FineTuneConfig(
            base_model="openai/whisper-small",
            language=None,
            epochs=3,
            max_steps=None,
            batch_size=8,
            learning_rate=1e-5,
            train_clips=100,
            val_clips=0,
        )
        assert config.use_lora is False
        assert config.lora_r == 32  # updated from 16
        assert config.lora_alpha == 64  # updated from 32

    def test_config_language_none_roundtrip(self) -> None:
        config = FineTuneConfig(
            base_model="openai/whisper-small",
            language=None,
            epochs=3,
            max_steps=None,
            batch_size=8,
            learning_rate=1e-5,
            train_clips=100,
            val_clips=15,
        )
        restored = FineTuneConfig.model_validate_json(config.model_dump_json())
        assert restored.language is None

    def test_config_lora_new_defaults(self) -> None:
        config = FineTuneConfig(
            base_model="openai/whisper-small",
            language=None,
            epochs=3,
            max_steps=None,
            batch_size=8,
            learning_rate=1e-5,
            train_clips=100,
            val_clips=0,
        )
        assert config.lora_r == 32
        assert config.lora_alpha == 64


class TestFineTuneReport:
    def test_json_roundtrip(self) -> None:
        report = FineTuneReport(
            output_dir="/tmp/out",
            base_model="openai/whisper-tiny",
            language="tl",
            train_clips=100,
            val_clips=15,
            steps=375,
            model_path="/tmp/out/model",
            config_path="/tmp/out/training_config.json",
            card_path="/tmp/out/model_card.md",
        )
        raw = report.model_dump_json()
        restored = FineTuneReport.model_validate_json(raw)
        assert restored == report


# -----------------------------------------------------------------------
# _load_split_clips
# -----------------------------------------------------------------------


class TestLoadSplitClips:
    def test_loads_clips(self, tmp_path: Path) -> None:
        ds, rows = _make_dataset(tmp_path, n_clips=3, split="train")
        clips = _load_split_clips(ds / "train.csv", ds)
        assert len(clips) == 3
        for path, transcript in clips:
            assert path.is_file()
            assert transcript.startswith("Transcript")

    def test_missing_csv_returns_empty(self, tmp_path: Path) -> None:
        clips = _load_split_clips(tmp_path / "nonexistent.csv", tmp_path)
        assert clips == []

    def test_empty_csv_returns_empty(self, tmp_path: Path) -> None:
        csv_path = tmp_path / "empty.csv"
        _write_split_csv(csv_path, [])
        clips = _load_split_clips(csv_path, tmp_path)
        assert clips == []

    def test_missing_audio_skipped(self, tmp_path: Path) -> None:
        ds, _rows = _make_dataset(
            tmp_path, n_clips=3, split="train", create_audio=False
        )
        clips = _load_split_clips(ds / "train.csv", ds)
        assert clips == []


# -----------------------------------------------------------------------
# _build_example
# -----------------------------------------------------------------------


class TestBuildExample:
    def test_returns_expected_keys(self, tmp_path: Path) -> None:
        pytest.importorskip("numpy")
        wav = tmp_path / "test.wav"
        write_pcm_wav(wav, duration=1)
        processor = _fake_processor()
        example = _build_example(processor, wav, "Hello world")
        assert "input_features" in example
        assert "labels" in example

    def test_calls_processor(self, tmp_path: Path) -> None:
        pytest.importorskip("numpy")
        wav = tmp_path / "test.wav"
        write_pcm_wav(wav, duration=1)
        processor = _fake_processor()
        _build_example(processor, wav, "Test transcript")
        processor.feature_extractor.assert_called_once()
        processor.tokenizer.assert_called_once_with("Test transcript")


# -----------------------------------------------------------------------
# _DataCollatorSpeechSeq2Seq
# -----------------------------------------------------------------------


class _AttrDict(dict):
    """Dict that also supports attribute access (mimics BatchEncoding)."""

    def __getattr__(self, key: str) -> Any:
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key) from None


class TestDataCollator:
    def test_pads_labels(self) -> None:
        torch = pytest.importorskip("torch")
        from bosesph.finetune import _DataCollatorSpeechSeq2Seq

        processor = MagicMock()
        # feature_extractor.pad returns a batch with input_features tensor
        processor.feature_extractor.pad.return_value = _AttrDict(
            {"input_features": torch.randn(2, 80, 100)}
        )
        # tokenizer.pad returns padded labels + attention mask
        processor.tokenizer.pad.return_value = _AttrDict(
            {
                "input_ids": torch.tensor([[1, 10, 20, 0], [1, 30, 0, 0]]),
                "attention_mask": torch.tensor([[1, 1, 1, 0], [1, 1, 0, 0]]),
            }
        )
        processor.tokenizer.bos_token_id = 1

        collator = _DataCollatorSpeechSeq2Seq(processor)
        features = [
            {"input_features": [0.1, 0.2], "labels": [1, 10, 20]},
            {"input_features": [0.3, 0.4], "labels": [1, 30]},
        ]
        batch = collator(features)

        assert "labels" in batch
        assert "input_features" in batch
        labels = batch["labels"]
        # BOS stripped, so first column is the actual token.
        assert labels.shape[0] == 2
        # Padding positions should be -100.
        assert (labels[1, -1] == -100).item()


# -----------------------------------------------------------------------
# _generate_model_card
# -----------------------------------------------------------------------


class TestGenerateModelCard:
    def test_includes_base_model(self) -> None:
        config = FineTuneConfig(
            base_model="openai/whisper-tiny",
            language="tl",
            epochs=3,
            max_steps=None,
            batch_size=8,
            learning_rate=1e-5,
            train_clips=100,
            val_clips=15,
        )
        card = _generate_model_card(config)
        assert "openai/whisper-tiny" in card
        assert "Kapampangan" in card
        assert "pipeline" in card

    def test_includes_metrics_when_provided(self) -> None:
        config = FineTuneConfig(
            base_model="openai/whisper-tiny",
            language="tl",
            epochs=3,
            max_steps=None,
            batch_size=8,
            learning_rate=1e-5,
            train_clips=100,
            val_clips=15,
        )
        card = _generate_model_card(config, metrics={"wer": 0.45, "cer": 0.22})
        assert "0.45" in card
        assert "0.22" in card
        assert "Evaluation" in card

    def test_no_eval_section_without_metrics(self) -> None:
        config = FineTuneConfig(
            base_model="openai/whisper-tiny",
            language="tl",
            epochs=3,
            max_steps=None,
            batch_size=8,
            learning_rate=1e-5,
            train_clips=100,
            val_clips=0,
        )
        card = _generate_model_card(config)
        assert "## Evaluation" not in card

    def test_includes_lora_method_when_enabled(self) -> None:
        config = FineTuneConfig(
            base_model="openai/whisper-tiny",
            language="tl",
            epochs=3,
            max_steps=None,
            batch_size=8,
            learning_rate=1e-5,
            train_clips=100,
            val_clips=15,
            use_lora=True,
            lora_r=16,
            lora_alpha=32,
            lora_dropout=0.05,
        )
        card = _generate_model_card(config)
        assert "LoRA" in card
        assert "r=16" in card
        assert "alpha=32" in card

    def test_shows_full_finetuning_when_no_lora(self) -> None:
        config = FineTuneConfig(
            base_model="openai/whisper-tiny",
            language="tl",
            epochs=3,
            max_steps=None,
            batch_size=8,
            learning_rate=1e-5,
            train_clips=100,
            val_clips=15,
        )
        card = _generate_model_card(config)
        assert "Full fine-tuning" in card

    def test_includes_usage_snippet(self) -> None:
        config = FineTuneConfig(
            base_model="openai/whisper-tiny",
            language="tl",
            epochs=3,
            max_steps=None,
            batch_size=8,
            learning_rate=1e-5,
            train_clips=50,
            val_clips=10,
        )
        card = _generate_model_card(config)
        assert "from transformers import pipeline" in card
        assert 'task="transcribe"' not in card or "automatic-speech-recognition" in card

    def test_model_card_none_language_uses_unconstrained(self) -> None:
        config = FineTuneConfig(
            base_model="openai/whisper-small",
            language=None,
            epochs=3,
            max_steps=None,
            batch_size=8,
            learning_rate=1e-5,
            train_clips=100,
            val_clips=15,
        )
        card = _generate_model_card(config)
        assert "unconstrained" in card
        assert "Tagalog" not in card

    def test_model_card_explicit_language_shows_token(self) -> None:
        config = FineTuneConfig(
            base_model="openai/whisper-small",
            language="tl",
            epochs=3,
            max_steps=None,
            batch_size=8,
            learning_rate=1e-5,
            train_clips=100,
            val_clips=15,
        )
        card = _generate_model_card(config)
        assert "`tl`" in card


# -----------------------------------------------------------------------
# generate_comparison_report
# -----------------------------------------------------------------------


class TestComparisonReport:
    def test_includes_both_models(self, tmp_path: Path) -> None:
        baseline = BenchmarkMetrics(
            model="openai/whisper-small",
            language="kapampangan",
            wer=0.85,
            cer=0.55,
            test_clips=100,
            total_duration_seconds=500.0,
        )
        finetuned = BenchmarkMetrics(
            model="bosesph-kapampangan-v1",
            language="kapampangan",
            wer=0.45,
            cer=0.25,
            test_clips=100,
            total_duration_seconds=500.0,
        )
        report_path = tmp_path / "comparison.md"
        generate_comparison_report(baseline, finetuned, report_path)
        content = report_path.read_text(encoding="utf-8")
        assert "openai/whisper-small" in content
        assert "bosesph-kapampangan-v1" in content

    def test_shows_improvement(self, tmp_path: Path) -> None:
        baseline = BenchmarkMetrics(
            model="baseline",
            language="kapampangan",
            wer=0.85,
            cer=0.55,
            test_clips=50,
            total_duration_seconds=250.0,
        )
        finetuned = BenchmarkMetrics(
            model="finetuned",
            language="kapampangan",
            wer=0.45,
            cer=0.25,
            test_clips=50,
            total_duration_seconds=250.0,
        )
        report_path = tmp_path / "comparison.md"
        generate_comparison_report(baseline, finetuned, report_path)
        content = report_path.read_text(encoding="utf-8")
        assert "improved" in content.lower()

    def test_shows_regression(self, tmp_path: Path) -> None:
        baseline = BenchmarkMetrics(
            model="baseline",
            language="kapampangan",
            wer=0.45,
            cer=0.25,
            test_clips=50,
            total_duration_seconds=250.0,
        )
        finetuned = BenchmarkMetrics(
            model="finetuned",
            language="kapampangan",
            wer=0.65,
            cer=0.40,
            test_clips=50,
            total_duration_seconds=250.0,
        )
        report_path = tmp_path / "comparison.md"
        generate_comparison_report(baseline, finetuned, report_path)
        content = report_path.read_text(encoding="utf-8")
        assert "regressed" in content.lower()

    def test_shows_deltas(self, tmp_path: Path) -> None:
        baseline = BenchmarkMetrics(
            model="baseline",
            language="kapampangan",
            wer=0.80,
            cer=0.50,
            test_clips=50,
            total_duration_seconds=250.0,
        )
        finetuned = BenchmarkMetrics(
            model="finetuned",
            language="kapampangan",
            wer=0.40,
            cer=0.20,
            test_clips=50,
            total_duration_seconds=250.0,
        )
        report_path = tmp_path / "comparison.md"
        generate_comparison_report(baseline, finetuned, report_path)
        content = report_path.read_text(encoding="utf-8")
        # Delta for WER: 0.40 - 0.80 = -0.40
        assert "-0.4000" in content


# -----------------------------------------------------------------------
# CLI: finetune subcommand
# -----------------------------------------------------------------------


class TestFp16Parameter:
    def test_finetune_model_accepts_fp16_defaulting_false(self) -> None:
        import inspect

        from bosesph.finetune import finetune_model

        param = inspect.signature(finetune_model).parameters["fp16"]
        assert param.default is False


class TestFinetuneCLI:
    def test_missing_dataset_exits_2(self, tmp_path: Path) -> None:
        code = main(
            [
                "finetune",
                str(tmp_path / "nonexistent"),
                "--output",
                str(tmp_path / "out"),
            ]
        )
        assert code == 2

    def test_missing_output_flag_exits_2(self) -> None:
        code = main(["finetune", "/tmp/ds"])
        assert code == 2

    def test_parser_accepts_all_flags(self) -> None:
        from bosesph.cli import build_parser

        args = build_parser().parse_args(
            [
                "finetune",
                "/tmp/ds",
                "--output",
                "/tmp/out",
                "--base-model",
                "openai/whisper-tiny",
                "--language",
                "tl",
                "--epochs",
                "5",
                "--max-steps",
                "100",
                "--batch-size",
                "4",
                "--learning-rate",
                "2e-5",
                "--lora-r",
                "8",
                "--lora-alpha",
                "16",
                "--lora-dropout",
                "0.1",
            ]
        )
        assert args.base_model == "openai/whisper-tiny"
        assert args.epochs == 5
        assert args.max_steps == 100
        assert args.batch_size == 4
        assert args.learning_rate == 2e-5
        assert args.use_lora is True
        assert args.lora_r == 8
        assert args.lora_alpha == 16
        assert args.lora_dropout == 0.1

    def test_parser_lora_is_default(self) -> None:
        from bosesph.cli import build_parser

        args = build_parser().parse_args(
            ["finetune", "/tmp/ds", "--output", "/tmp/out"]
        )
        assert args.use_lora is True

    def test_parser_full_disables_lora(self) -> None:
        from bosesph.cli import build_parser

        args = build_parser().parse_args(
            ["finetune", "/tmp/ds", "--output", "/tmp/out", "--full"]
        )
        assert args.use_lora is False

    def test_finetune_parser_new_defaults(self) -> None:
        from bosesph.cli import build_parser

        args = build_parser().parse_args(
            ["finetune", "/tmp/ds", "--output", "/tmp/out"]
        )
        assert args.base_model == "openai/whisper-small"
        assert args.language is None
        assert args.lora_r == 32
        assert args.lora_alpha == 64

    def test_export_colab_parser_new_defaults(self) -> None:
        from bosesph.cli import build_parser

        args = build_parser().parse_args(
            ["export-colab", "/tmp/ds", "--output", "/tmp/out.ipynb"]
        )
        assert args.base_model == "openai/whisper-small"
        assert args.language is None
        assert args.lora_r == 32
        assert args.lora_alpha == 64


# -----------------------------------------------------------------------
# CLI: compare subcommand
# -----------------------------------------------------------------------


class TestCompareCLI:
    def test_missing_baseline_exits_2(self, tmp_path: Path) -> None:
        code = main(
            [
                "compare",
                "--baseline",
                str(tmp_path / "missing.json"),
                "--finetuned",
                str(tmp_path / "also_missing.json"),
                "--output",
                str(tmp_path / "comparison.md"),
            ]
        )
        assert code == 2

    def test_missing_finetuned_exits_2(self, tmp_path: Path) -> None:
        baseline = tmp_path / "baseline.json"
        metrics = BenchmarkMetrics(
            model="baseline",
            language="kapampangan",
            wer=0.85,
            cer=0.55,
            test_clips=50,
            total_duration_seconds=250.0,
        )
        baseline.write_text(metrics.model_dump_json(), encoding="utf-8")

        code = main(
            [
                "compare",
                "--baseline",
                str(baseline),
                "--finetuned",
                str(tmp_path / "missing.json"),
                "--output",
                str(tmp_path / "comparison.md"),
            ]
        )
        assert code == 2

    def test_valid_compare(self, tmp_path: Path) -> None:
        baseline_metrics = BenchmarkMetrics(
            model="baseline",
            language="kapampangan",
            wer=0.85,
            cer=0.55,
            test_clips=50,
            total_duration_seconds=250.0,
        )
        finetuned_metrics = BenchmarkMetrics(
            model="finetuned",
            language="kapampangan",
            wer=0.45,
            cer=0.25,
            test_clips=50,
            total_duration_seconds=250.0,
        )
        baseline = tmp_path / "baseline.json"
        finetuned = tmp_path / "finetuned.json"
        baseline.write_text(baseline_metrics.model_dump_json(), encoding="utf-8")
        finetuned.write_text(finetuned_metrics.model_dump_json(), encoding="utf-8")

        output = tmp_path / "comparison.md"
        code = main(
            [
                "compare",
                "--baseline",
                str(baseline),
                "--finetuned",
                str(finetuned),
                "--output",
                str(output),
            ]
        )
        assert code == 0
        assert output.is_file()
        content = output.read_text(encoding="utf-8")
        assert "improved" in content.lower()
