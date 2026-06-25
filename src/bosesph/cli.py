"""Command-line interface for BosesPH metadata tools."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections.abc import Sequence
from pathlib import Path

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
    return 2


def entrypoint() -> None:
    """Console-script entry point."""
    raise SystemExit(main())
