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
    return 2


def entrypoint() -> None:
    """Console-script entry point."""
    raise SystemExit(main())
