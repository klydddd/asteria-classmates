"""Command-line interface for BosesPH metadata tools."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from bosesph.asr import ASRError
from bosesph.dataset import DatasetBuildError, build_dataset
from bosesph.ingestion import IngestionError, import_pld_session
from bosesph.metadata import MetadataRecord, Severity, ValidationReport
from bosesph.metadata import validate_metadata_csv as validate_csv
from bosesph.pld import PldParseError
from bosesph.review import ReviewError, review_dataset
from bosesph.transcripts import TranscriptDatasetError, normalize_dataset


class ArgumentParser(argparse.ArgumentParser):
    """Argument parser that returns exit codes instead of terminating."""

    def exit(self, status: int = 0, message: str | None = None) -> None:
        if message:
            self._print_message(message, sys.stderr)
        raise ParserExit(status)

    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: {message}\n")


class ParserExit(Exception):
    """Internal control flow for argparse exits."""

    def __init__(self, status: int) -> None:
        self.status = status


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(prog="bosesph")
    commands = parser.add_subparsers(dest="command", required=True)

    validate_parser = commands.add_parser(
        "validate-metadata",
        help="validate a metadata CSV",
    )
    validate_parser.add_argument("csv", type=Path)
    validate_parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        dest="output_format",
    )

    schema_parser = commands.add_parser(
        "export-metadata-schema",
        help="export the MetadataRecord JSON Schema",
    )
    schema_parser.add_argument("--output", type=Path, required=True)

    import_parser = commands.add_parser(
        "import-pld",
        help="import and standardize one PLD session directory",
    )
    import_parser.add_argument("source", type=Path)
    import_parser.add_argument("--output", type=Path, required=True)
    import_parser.add_argument("--overwrite", action="store_true")

    normalize_parser = commands.add_parser(
        "normalize-transcripts",
        help="normalize transcripts in a generated dataset",
    )
    normalize_parser.add_argument("dataset", type=Path)

    review_parser = commands.add_parser(
        "review",
        help="interactively review pending dataset clips",
    )
    review_parser.add_argument("dataset", type=Path)

    build_parser = commands.add_parser(
        "build-dataset",
        help="build final dataset package from reviewed clips",
    )
    build_parser.add_argument("dataset", type=Path)
    build_parser.add_argument("--output", type=Path, required=True)
    build_parser.add_argument("--train", type=float, default=0.70, dest="train_ratio")
    build_parser.add_argument("--val", type=float, default=0.15, dest="val_ratio")
    build_parser.add_argument("--test", type=float, default=0.15, dest="test_ratio")
    build_parser.add_argument("--seed", type=int, default=42)
    build_parser.add_argument("--overwrite", action="store_true")

    transcribe_parser = commands.add_parser(
        "transcribe",
        help="transcribe audio using a pretrained ASR model",
    )
    transcribe_parser.add_argument(
        "source", type=Path, help="single audio file or dataset directory"
    )
    transcribe_parser.add_argument(
        "--model", default="openai/whisper-small", help="HuggingFace model ID"
    )
    transcribe_parser.add_argument(
        "--language", default=None, help="language hint for Whisper (optional)"
    )
    transcribe_parser.add_argument(
        "--split", default="test", help="which split to transcribe"
    )
    transcribe_parser.add_argument(
        "--output", type=Path, default=None, help="output predictions CSV"
    )

    evaluate_parser = commands.add_parser(
        "evaluate",
        help="compute WER/CER from predictions",
    )
    evaluate_parser.add_argument(
        "--predictions", type=Path, required=True, help="predictions CSV"
    )
    evaluate_parser.add_argument(
        "--references",
        type=Path,
        default=None,
        help="optional reference CSV to override predictions reference column",
    )
    evaluate_parser.add_argument(
        "--output", type=Path, default=None, help="output directory for report"
    )
    evaluate_parser.add_argument(
        "--model-name", default="baseline", dest="model_name", help="model label"
    )
    evaluate_parser.add_argument(
        "--language", default="kapampangan", help="language label for report"
    )

    finetune_parser = commands.add_parser(
        "finetune",
        help="fine-tune a Whisper model on the built dataset",
    )
    finetune_parser.add_argument("dataset", type=Path, help="built dataset directory")
    finetune_parser.add_argument(
        "--output", type=Path, required=True, help="model output directory"
    )
    finetune_parser.add_argument(
        "--base-model",
        default="openai/whisper-tiny",
        dest="base_model",
        help="HuggingFace model ID to fine-tune",
    )
    finetune_parser.add_argument(
        "--language",
        default="tl",
        help="language token for label tokenization (default: tl for Tagalog proxy)",
    )
    finetune_parser.add_argument(
        "--epochs", type=int, default=3, help="number of training epochs"
    )
    finetune_parser.add_argument(
        "--max-steps",
        type=int,
        default=None,
        dest="max_steps",
        help="override epochs with a fixed step count",
    )
    finetune_parser.add_argument(
        "--batch-size",
        type=int,
        default=8,
        dest="batch_size",
        help="per-device training batch size",
    )
    finetune_parser.add_argument(
        "--learning-rate",
        type=float,
        default=1e-5,
        dest="learning_rate",
        help="learning rate",
    )
    finetune_parser.add_argument(
        "--train-split",
        default="train",
        dest="train_split",
        help="split CSV to train on",
    )
    finetune_parser.add_argument(
        "--eval-split",
        default="validation",
        dest="eval_split",
        help="split CSV for evaluation during training",
    )
    finetune_parser.add_argument(
        "--gradient-checkpointing",
        action="store_true",
        default=False,
        dest="gradient_checkpointing",
        help="trade compute for memory by recomputing activations during backward pass",
    )
    finetune_parser.add_argument(
        "--optim",
        default="adamw_torch",
        help="optimizer (use 'adafactor' to reduce memory)",
    )
    finetune_parser.add_argument(
        "--full",
        action="store_false",
        dest="use_lora",
        default=True,
        help="use full fine-tuning instead of LoRA (default: LoRA)",
    )
    finetune_parser.add_argument(
        "--lora-r",
        type=int,
        default=16,
        dest="lora_r",
        help="LoRA rank (default: 16)",
    )
    finetune_parser.add_argument(
        "--lora-alpha",
        type=int,
        default=32,
        dest="lora_alpha",
        help="LoRA alpha scaling factor (default: 32)",
    )
    finetune_parser.add_argument(
        "--lora-dropout",
        type=float,
        default=0.05,
        dest="lora_dropout",
        help="LoRA dropout rate (default: 0.05)",
    )

    compare_parser = commands.add_parser(
        "compare",
        help="compare baseline vs fine-tuned benchmark results",
    )
    compare_parser.add_argument(
        "--baseline", type=Path, required=True, help="baseline results.json"
    )
    compare_parser.add_argument(
        "--finetuned", type=Path, required=True, help="fine-tuned results.json"
    )
    compare_parser.add_argument(
        "--output", type=Path, required=True, help="output report path (.md)"
    )

    export_colab_parser = commands.add_parser(
        "export-colab",
        help="generate a Google Colab notebook to fine-tune on Colab's GPU",
    )
    export_colab_parser.add_argument(
        "dataset", type=Path, help="built dataset directory (used to derive names)"
    )
    export_colab_parser.add_argument(
        "--output", type=Path, required=True, help="path to write the .ipynb"
    )
    export_colab_parser.add_argument(
        "--repo-url",
        default=None,
        dest="repo_url",
        help="git URL to pip-install bosesph from (default: origin remote)",
    )
    export_colab_parser.add_argument(
        "--repo-ref",
        default="main",
        dest="repo_ref",
        help="git branch/tag/commit to install (default: main)",
    )
    export_colab_parser.add_argument(
        "--drive-base",
        default="/content/drive/MyDrive/bosesph",
        dest="drive_base",
        help="Google Drive base path for dataset and output",
    )
    # Training hyperparameters (mirror the 'finetune' command).
    export_colab_parser.add_argument(
        "--base-model",
        default="openai/whisper-tiny",
        dest="base_model",
        help="HuggingFace model ID to fine-tune",
    )
    export_colab_parser.add_argument(
        "--language",
        default="tl",
        help="language token for label tokenization (default: tl for Tagalog proxy)",
    )
    export_colab_parser.add_argument(
        "--epochs", type=int, default=3, help="number of training epochs"
    )
    export_colab_parser.add_argument(
        "--max-steps",
        type=int,
        default=None,
        dest="max_steps",
        help="override epochs with a fixed step count",
    )
    export_colab_parser.add_argument(
        "--batch-size",
        type=int,
        default=8,
        dest="batch_size",
        help="per-device training batch size",
    )
    export_colab_parser.add_argument(
        "--learning-rate",
        type=float,
        default=1e-5,
        dest="learning_rate",
        help="learning rate",
    )
    export_colab_parser.add_argument(
        "--train-split",
        default="train",
        dest="train_split",
        help="split CSV to train on",
    )
    export_colab_parser.add_argument(
        "--eval-split",
        default="validation",
        dest="eval_split",
        help="split CSV for evaluation during training",
    )
    export_colab_parser.add_argument(
        "--gradient-checkpointing",
        action="store_true",
        default=False,
        dest="gradient_checkpointing",
        help="trade compute for memory by recomputing activations during backward pass",
    )
    export_colab_parser.add_argument(
        "--optim",
        default="adamw_torch",
        help="optimizer (use 'adafactor' to reduce memory)",
    )
    export_colab_parser.add_argument(
        "--no-fp16",
        action="store_false",
        dest="fp16",
        default=True,
        help="disable mixed-precision training (fp16 is on by default for GPU)",
    )
    export_colab_parser.add_argument(
        "--full",
        action="store_false",
        dest="use_lora",
        default=True,
        help="use full fine-tuning instead of LoRA (default: LoRA)",
    )
    export_colab_parser.add_argument(
        "--lora-r",
        type=int,
        default=16,
        dest="lora_r",
        help="LoRA rank (default: 16)",
    )
    export_colab_parser.add_argument(
        "--lora-alpha",
        type=int,
        default=32,
        dest="lora_alpha",
        help="LoRA alpha scaling factor (default: 32)",
    )
    export_colab_parser.add_argument(
        "--lora-dropout",
        type=float,
        default=0.05,
        dest="lora_dropout",
        help="LoRA dropout rate (default: 0.05)",
    )
    return parser


def _print_text_report(report: ValidationReport) -> None:
    print(
        f"Rows: {report.row_count} | Valid: {report.valid_row_count} | "
        f"Errors: {report.error_count} | Warnings: {report.warning_count}"
    )
    for issue in report.issues:
        location = []
        if issue.row is not None:
            location.append(f"row {issue.row}")
        if issue.field is not None:
            location.append(issue.field)
        suffix = f" ({', '.join(location)})" if location else ""
        print(f"{issue.severity.value.upper()} {issue.code}{suffix}: {issue.message}")


def _print_input_error(message: str, output_format: str) -> None:
    if output_format == "json":
        print(
            json.dumps({"code": "input_error", "message": message}),
            file=sys.stderr,
        )
    else:
        print(f"Input error: {message}", file=sys.stderr)


def _run_validate(path: Path, output_format: str) -> int:
    try:
        report = validate_csv(path)
    except (OSError, UnicodeError, csv.Error) as error:
        _print_input_error(str(error), output_format)
        return 2

    if output_format == "json":
        print(report.model_dump_json(indent=2))
    else:
        _print_text_report(report)
    return 1 if any(issue.severity == Severity.ERROR for issue in report.issues) else 0


def _run_export_schema(output: Path) -> int:
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(
                MetadataRecord.model_json_schema(),
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    except OSError as error:
        _print_input_error(str(error), "text")
        return 2
    print(f"Wrote metadata schema to {output}")
    return 0


def _run_import_pld(source: Path, output: Path, overwrite: bool) -> int:
    try:
        report = import_pld_session(source, output, overwrite=overwrite)
    except (IngestionError, PldParseError, OSError) as error:
        _print_input_error(str(error), "text")
        return 2
    print(f"Wrote standardized dataset to {output}")
    print(f"Pending: {report.counts.pending}")
    print(f"Needs review: {report.counts.needs_review}")
    print(f"Rejected: {report.counts.rejected}")
    return 0


def _run_normalize_transcripts(dataset: Path) -> int:
    try:
        report = normalize_dataset(dataset)
    except TranscriptDatasetError as error:
        _print_input_error(str(error), "text")
        return 2
    print(f"Normalized transcripts in {dataset}")
    print(f"Changed: {report.changed}")
    print(f"Unchanged: {report.unchanged}")
    print(f"Needs review: {report.needs_review}")
    return 1 if report.needs_review else 0


def _run_review(dataset: Path) -> int:
    try:
        summary = review_dataset(dataset, input_fn=input, output_fn=print)
    except ReviewError as error:
        _print_input_error(str(error), "text")
        return 2
    print("Review session complete.")
    print(f"Approved: {summary.approved}")
    print(f"Needs fix: {summary.needs_fix}")
    print(f"Rejected: {summary.rejected}")
    print(f"Skipped: {summary.skipped}")
    print(f"Remaining: {summary.remaining}")
    return 0


def _run_build_dataset(
    dataset: Path,
    output: Path,
    *,
    train_ratio: float,
    val_ratio: float,
    test_ratio: float,
    seed: int,
    overwrite: bool,
) -> int:
    try:
        report = build_dataset(
            dataset,
            output,
            train_ratio=train_ratio,
            val_ratio=val_ratio,
            test_ratio=test_ratio,
            seed=seed,
            overwrite=overwrite,
        )
    except DatasetBuildError as error:
        _print_input_error(str(error), "text")
        return 2
    print(f"Built dataset at {report.output}")
    print(f"Total clips: {report.total_clips}")
    print(f"Train: {report.train_clips}")
    print(f"Validation: {report.validation_clips}")
    print(f"Test: {report.test_clips}")
    print(f"Speakers: {report.speakers}")
    print(f"Excluded (non-approved): {report.excluded}")
    return 0


def _run_transcribe(
    source: Path,
    *,
    model: str,
    language: str | None,
    split: str,
    output: Path | None,
) -> int:
    from bosesph.asr import load_model, transcribe_file, transcribe_split

    try:
        if source.is_file():
            # Single-file mode: print transcript to stdout.
            pipe = load_model(model)
            text = transcribe_file(pipe, source, language=language)
            print(text)
            return 0

        if source.is_dir():
            if output is None:
                _print_input_error(
                    "--output is required when source is a dataset directory",
                    "text",
                )
                return 2
            split_csv = source / f"{split}.csv"
            if not split_csv.is_file():
                _print_input_error(
                    f"{split}.csv not found in {source}",
                    "text",
                )
                return 2
            pipe = load_model(model)

            def progress(current: int, total: int) -> None:
                print(f"  [{current}/{total}]", end="\r", flush=True)

            results = transcribe_split(
                split_csv,
                source,
                pipe,
                language=language,
                output_path=output,
                progress_fn=progress,
            )
            print(f"\nWrote {len(results)} predictions to {output}")
            return 0

        _print_input_error(f"source not found: {source}", "text")
        return 2
    except ASRError as error:
        _print_input_error(str(error), "text")
        return 2


def _run_evaluate(
    predictions: Path,
    *,
    references: Path | None,
    output: Path | None,
    model_name: str,
    language: str,
) -> int:
    from bosesph.asr import evaluate_predictions
    from bosesph.benchmark import generate_benchmark_report

    try:
        metrics = evaluate_predictions(
            predictions,
            references_csv=references,
            model=model_name,
            language=language,
        )
    except ASRError as error:
        _print_input_error(str(error), "text")
        return 2

    print(f"Model: {metrics.model}")
    print(f"Language: {metrics.language}")
    print(f"Test clips: {metrics.test_clips}")
    print(f"WER: {metrics.wer:.4f}")
    print(f"CER: {metrics.cer:.4f}")

    if output is not None:
        output.mkdir(parents=True, exist_ok=True)
        results_path = output / "results.json"
        results_path.write_text(
            metrics.model_dump_json(indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"Wrote results to {results_path}")

        # Load predictions for the report.
        import csv

        with predictions.open("r", encoding="utf-8", newline="") as handle:
            pred_rows = list(csv.DictReader(handle, strict=True))

        from bosesph.asr import TranscriptionResult

        results = [
            TranscriptionResult(
                audio_id=row.get("audio_id", ""),
                reference=row.get("reference", ""),
                prediction=row.get("prediction", ""),
                file_path=row.get("file_path", ""),
            )
            for row in pred_rows
        ]
        report_path = output / "report.md"
        generate_benchmark_report(metrics, results, report_path)
        print(f"Wrote report to {report_path}")

    return 0


def _run_finetune(
    dataset: Path,
    *,
    output: Path,
    base_model: str,
    language: str,
    epochs: int,
    max_steps: int | None,
    batch_size: int,
    learning_rate: float,
    train_split: str,
    eval_split: str,
    gradient_checkpointing: bool,
    optim: str,
    use_lora: bool,
    lora_r: int,
    lora_alpha: int,
    lora_dropout: float,
) -> int:
    from bosesph.finetune import finetune_model

    try:
        if not dataset.is_dir():
            _print_input_error(f"dataset directory not found: {dataset}", "text")
            return 2

        def progress(message: str) -> None:
            print(f"  {message}")

        report = finetune_model(
            dataset,
            output,
            base_model=base_model,
            language=language,
            epochs=epochs,
            max_steps=max_steps,
            batch_size=batch_size,
            learning_rate=learning_rate,
            train_split=train_split,
            eval_split=eval_split,
            gradient_checkpointing=gradient_checkpointing,
            optim=optim,
            use_lora=use_lora,
            lora_r=lora_r,
            lora_alpha=lora_alpha,
            lora_dropout=lora_dropout,
            progress_fn=progress,
        )
    except ASRError as error:
        _print_input_error(str(error), "text")
        return 2

    print("Fine-tuning complete.")
    print(f"Base model: {report.base_model}")
    print(f"Language: {report.language}")
    print(f"Training clips: {report.train_clips}")
    print(f"Validation clips: {report.val_clips}")
    print(f"Steps: {report.steps}")
    print(f"Model saved to: {report.model_path}")
    print(f"Config: {report.config_path}")
    print(f"Model card: {report.card_path}")
    return 0


def _resolve_repo_url(repo_url: str | None) -> str:
    """Return the explicit repo URL, the origin remote, or the known default."""
    from bosesph.colab import DEFAULT_REPO_URL

    if repo_url:
        return repo_url
    import subprocess

    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=True,
        )
        url = result.stdout.strip()
        if url:
            return url
    except (OSError, subprocess.SubprocessError):
        pass
    return DEFAULT_REPO_URL


def _run_export_colab(
    dataset: Path,
    *,
    output: Path,
    repo_url: str | None,
    repo_ref: str,
    drive_base: str,
    base_model: str,
    language: str,
    epochs: int,
    max_steps: int | None,
    batch_size: int,
    learning_rate: float,
    train_split: str,
    eval_split: str,
    gradient_checkpointing: bool,
    optim: str,
    fp16: bool,
    use_lora: bool,
    lora_r: int,
    lora_alpha: int,
    lora_dropout: float,
) -> int:
    from bosesph.colab import ColabExportConfig, write_notebook

    if not dataset.is_dir():
        _print_input_error(f"dataset directory not found: {dataset}", "text")
        return 2

    dataset_name = dataset.resolve().name
    base = drive_base.rstrip("/")
    config = ColabExportConfig(
        base_model=base_model,
        language=language,
        epochs=epochs,
        max_steps=max_steps,
        batch_size=batch_size,
        learning_rate=learning_rate,
        train_split=train_split,
        eval_split=eval_split,
        gradient_checkpointing=gradient_checkpointing,
        optim=optim,
        use_lora=use_lora,
        lora_r=lora_r,
        lora_alpha=lora_alpha,
        lora_dropout=lora_dropout,
        repo_url=_resolve_repo_url(repo_url),
        repo_ref=repo_ref,
        drive_dataset_path=f"{base}/{dataset_name}",
        drive_output_path=f"{base}/{dataset_name}-finetuned",
        fp16=fp16,
    )
    write_notebook(config, output)

    print(f"Colab notebook written to: {output}")
    print("Next steps:")
    print(f"  1. Upload your dataset folder to Drive: {config.drive_dataset_path}")
    print("  2. Open the notebook in Google Colab and set the runtime to GPU.")
    print("  3. Run all cells.")
    print(f"  Trained model will be saved to: {config.drive_output_path}")
    return 0


def _run_compare(
    baseline: Path,
    finetuned: Path,
    output: Path,
) -> int:
    from bosesph.asr import BenchmarkMetrics
    from bosesph.benchmark import generate_comparison_report

    try:
        if not baseline.is_file():
            _print_input_error(f"baseline results not found: {baseline}", "text")
            return 2
        if not finetuned.is_file():
            _print_input_error(f"fine-tuned results not found: {finetuned}", "text")
            return 2

        baseline_metrics = BenchmarkMetrics.model_validate_json(
            baseline.read_text(encoding="utf-8")
        )
        finetuned_metrics = BenchmarkMetrics.model_validate_json(
            finetuned.read_text(encoding="utf-8")
        )
        report_path = generate_comparison_report(
            baseline_metrics, finetuned_metrics, output
        )
    except (OSError, ValueError) as error:
        _print_input_error(str(error), "text")
        return 2

    print(f"Baseline WER: {baseline_metrics.wer:.4f}")
    print(f"Fine-tuned WER: {finetuned_metrics.wer:.4f}")
    delta = finetuned_metrics.wer - baseline_metrics.wer
    sign = "+" if delta >= 0 else ""
    print(f"Delta: {sign}{delta:.4f}")
    print(f"Wrote comparison report to {report_path}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return its documented process exit code."""
    try:
        args = build_parser().parse_args(argv)
    except ParserExit as error:
        return error.status

    if args.command == "validate-metadata":
        return _run_validate(args.csv, args.output_format)
    if args.command == "export-metadata-schema":
        return _run_export_schema(args.output)
    if args.command == "import-pld":
        return _run_import_pld(args.source, args.output, args.overwrite)
    if args.command == "normalize-transcripts":
        return _run_normalize_transcripts(args.dataset)
    if args.command == "review":
        return _run_review(args.dataset)
    if args.command == "build-dataset":
        return _run_build_dataset(
            args.dataset,
            args.output,
            train_ratio=args.train_ratio,
            val_ratio=args.val_ratio,
            test_ratio=args.test_ratio,
            seed=args.seed,
            overwrite=args.overwrite,
        )
    if args.command == "transcribe":
        return _run_transcribe(
            args.source,
            model=args.model,
            language=args.language,
            split=args.split,
            output=args.output,
        )
    if args.command == "evaluate":
        return _run_evaluate(
            args.predictions,
            references=args.references,
            output=args.output,
            model_name=args.model_name,
            language=args.language,
        )
    if args.command == "finetune":
        return _run_finetune(
            args.dataset,
            output=args.output,
            base_model=args.base_model,
            language=args.language,
            epochs=args.epochs,
            max_steps=args.max_steps,
            batch_size=args.batch_size,
            learning_rate=args.learning_rate,
            train_split=args.train_split,
            eval_split=args.eval_split,
            gradient_checkpointing=args.gradient_checkpointing,
            optim=args.optim,
            use_lora=args.use_lora,
            lora_r=args.lora_r,
            lora_alpha=args.lora_alpha,
            lora_dropout=args.lora_dropout,
        )
    if args.command == "export-colab":
        return _run_export_colab(
            args.dataset,
            output=args.output,
            repo_url=args.repo_url,
            repo_ref=args.repo_ref,
            drive_base=args.drive_base,
            base_model=args.base_model,
            language=args.language,
            epochs=args.epochs,
            max_steps=args.max_steps,
            batch_size=args.batch_size,
            learning_rate=args.learning_rate,
            train_split=args.train_split,
            eval_split=args.eval_split,
            gradient_checkpointing=args.gradient_checkpointing,
            optim=args.optim,
            fp16=args.fp16,
            use_lora=args.use_lora,
            lora_r=args.lora_r,
            lora_alpha=args.lora_alpha,
            lora_dropout=args.lora_dropout,
        )
    if args.command == "compare":
        return _run_compare(args.baseline, args.finetuned, args.output)
    return 2


def entrypoint() -> None:
    """Console-script entry point."""
    raise SystemExit(main())
