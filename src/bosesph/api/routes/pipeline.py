"""Pipeline endpoints: ingest, validate, normalize, review, build, transcribe,
evaluate, fine-tune, and compare.

Synchronous endpoints (fast file-I/O) are declared with ``def`` so Starlette
runs them in a threadpool automatically.  Heavy operations are submitted to
the :class:`~bosesph.api.jobs.JobManager` and return ``202 Accepted``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request, UploadFile

from bosesph.api.jobs import Job
from bosesph.api.models import (
    ApproveAllRequest,
    ApproveAllResponse,
    BuildDatasetRequest,
    CompareRequest,
    EvaluateRequest,
    ImportPldRequest,
    NormalizeTranscriptsRequest,
    ReviewDecisionRequest,
    ReviewDecisionResult,
    TrainRequest,
    TranscribeRequest,
    UploadResult,
    ValidateDatasetRequest,
)
from bosesph.api.settings import PathTraversalError, resolve_path
from bosesph.ingestion import IngestionReport
from bosesph.metadata import ValidationReport
from bosesph.transcripts import NormalizationReport

router = APIRouter(tags=["pipeline"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _settings(request: Request) -> Any:
    return request.app.state.settings


def _jobs(request: Request) -> Any:
    return request.app.state.jobs


def _workspace(request: Request) -> Path:
    return _settings(request).workspace


# ---------------------------------------------------------------------------
# Synchronous endpoints
# ---------------------------------------------------------------------------


@router.post("/upload-audio", response_model=UploadResult)
def upload_audio(
    request: Request,
    destination: str,
    files: list[UploadFile],
) -> UploadResult:
    """Accept one or more audio file uploads and save them to *destination*."""
    dest = resolve_path(_workspace(request), destination)
    dest.mkdir(parents=True, exist_ok=True)
    saved: list[str] = []
    for upload in files:
        filename = upload.filename or "unnamed.wav"
        if (
            filename != Path(filename).name
            or "\\" in filename
            or filename in {".", ".."}
        ):
            raise PathTraversalError(
                f"Upload filename must be a basename: {filename!r}"
            )
        target = resolve_path(_workspace(request), f"{destination}/{filename}")
        with target.open("wb") as fp:
            while chunk := upload.file.read(1024 * 256):
                fp.write(chunk)
        saved.append(target.relative_to(_workspace(request).resolve()).as_posix())
    return UploadResult(saved_files=saved, count=len(saved))


@router.post("/import-pld", response_model=IngestionReport)
def import_pld(request: Request, body: ImportPldRequest) -> IngestionReport:
    """Import a PLD session directory."""
    from bosesph.ingestion import import_pld_session

    ws = _workspace(request)
    source = resolve_path(ws, body.source)
    output = resolve_path(ws, body.output)
    return import_pld_session(source, output, overwrite=body.overwrite)


@router.post("/validate-dataset", response_model=ValidationReport)
def validate_dataset(
    request: Request,
    body: ValidateDatasetRequest,
) -> ValidationReport:
    """Validate a dataset's metadata.csv."""
    from bosesph.metadata import validate_metadata_csv

    ws = _workspace(request)
    dataset = resolve_path(ws, body.dataset)
    metadata_csv = dataset / "metadata.csv"
    return validate_metadata_csv(metadata_csv)


@router.post("/normalize-transcripts", response_model=NormalizationReport)
def normalize_transcripts(
    request: Request,
    body: NormalizeTranscriptsRequest,
) -> NormalizationReport:
    """Normalize transcripts in a dataset."""
    from bosesph.transcripts import normalize_dataset

    ws = _workspace(request)
    dataset = resolve_path(ws, body.dataset)
    return normalize_dataset(dataset)


@router.post("/review/decision", response_model=ReviewDecisionResult)
def review_decision(
    request: Request, body: ReviewDecisionRequest
) -> ReviewDecisionResult:
    """Apply a single review decision to one clip."""
    from bosesph.review import decide_clip

    ws = _workspace(request)
    dataset = resolve_path(ws, body.dataset)
    result = decide_clip(
        dataset,
        body.audio_id,
        body.decision,
        note=body.note,
    )
    return result


@router.post("/review/approve-all", response_model=ApproveAllResponse)
def review_approve_all(
    request: Request, body: ApproveAllRequest
) -> ApproveAllResponse:
    """Approve all reviewable clips whose audio files exist."""
    from bosesph.review import approve_all_clips

    ws = _workspace(request)
    dataset = resolve_path(ws, body.dataset)
    result = approve_all_clips(dataset)
    return result


# ---------------------------------------------------------------------------
# Background-job endpoints (return 202 + Job)
# ---------------------------------------------------------------------------


@router.post("/build-dataset", response_model=Job, status_code=202)
def build_dataset(request: Request, body: BuildDatasetRequest) -> Job:
    """Build a clean dataset (background job)."""
    from bosesph.dataset import build_dataset as _build_dataset

    ws = _workspace(request)
    dataset_path = resolve_path(ws, body.dataset)
    output_path = resolve_path(ws, body.output)

    def _run(*, progress_fn: Any = None) -> Any:
        return _build_dataset(
            dataset_path,
            output_path,
            train_ratio=body.train_ratio,
            val_ratio=body.val_ratio,
            test_ratio=body.test_ratio,
            seed=body.seed,
            overwrite=body.overwrite,
        )

    return _jobs(request).submit("build-dataset", _run)


@router.post("/transcribe", response_model=Job, status_code=202)
def transcribe(request: Request, body: TranscribeRequest) -> Job:
    """Run ASR transcription on a dataset split (background job)."""
    ws = _workspace(request)
    dataset_path = resolve_path(ws, body.dataset)
    output_path = resolve_path(ws, body.output)

    def _run(*, progress_fn: Any = None) -> Any:
        from bosesph.asr import load_model, transcribe_split

        split_csv = dataset_path / f"{body.split}.csv"
        pipe = load_model(body.model)
        results = transcribe_split(
            split_csv,
            dataset_path,
            pipe,
            language=body.language,
            output_path=output_path,
            progress_fn=(
                (lambda done, total: progress_fn((done, total)))
                if progress_fn
                else None
            ),
        )
        from pydantic import BaseModel as _BM

        class _TranscribeResult(_BM):
            predictions_path: str
            clip_count: int

        return _TranscribeResult(
            predictions_path=str(output_path),
            clip_count=len(results),
        )

    return _jobs(request).submit("transcribe", _run)


@router.post("/evaluate", response_model=Job, status_code=202)
def evaluate(request: Request, body: EvaluateRequest) -> Job:
    """Evaluate predictions and optionally generate a report in the background."""
    ws = _workspace(request)
    predictions_path = resolve_path(ws, body.predictions)
    references_path = resolve_path(ws, body.references) if body.references else None
    output_path = resolve_path(ws, body.output) if body.output else None

    def _run(*, progress_fn: Any = None) -> Any:
        from bosesph.asr import evaluate_predictions

        metrics = evaluate_predictions(
            predictions_path,
            references_csv=references_path,
            model=body.model_name,
            language=body.language,
        )
        if output_path:
            # Read predictions for the report
            import csv

            from bosesph.asr import TranscriptionResult
            from bosesph.benchmark import generate_benchmark_report

            preds: list[TranscriptionResult] = []
            with predictions_path.open(newline="", encoding="utf-8") as fh:
                for row in csv.DictReader(fh):
                    preds.append(TranscriptionResult(**row))
            output_path.mkdir(parents=True, exist_ok=True)
            generate_benchmark_report(metrics, preds, output_path / "report.md")
            results_path = output_path / "results.json"
            results_path.write_text(metrics.model_dump_json(indent=2), encoding="utf-8")
        return metrics

    return _jobs(request).submit("evaluate", _run)


@router.post("/train", response_model=Job, status_code=202)
def train(request: Request, body: TrainRequest) -> Job:
    """Fine-tune an ASR model (background job)."""
    ws = _workspace(request)
    dataset_path = resolve_path(ws, body.dataset)
    output_path = resolve_path(ws, body.output)

    def _run(*, progress_fn: Any = None) -> Any:
        from bosesph.finetune import finetune_model

        return finetune_model(
            dataset_path,
            output_path,
            base_model=body.base_model,
            language=body.language,
            epochs=body.epochs,
            max_steps=body.max_steps,
            batch_size=body.batch_size,
            learning_rate=body.learning_rate,
            train_split=body.train_split,
            eval_split=body.eval_split,
            progress_fn=((lambda msg: progress_fn(msg)) if progress_fn else None),
        )

    return _jobs(request).submit("train", _run)


@router.post("/compare", response_model=Job, status_code=202)
def compare(request: Request, body: CompareRequest) -> Job:
    """Generate a baseline versus fine-tuned comparison in the background."""
    ws = _workspace(request)
    baseline_path = resolve_path(ws, body.baseline)
    finetuned_path = resolve_path(ws, body.finetuned)
    output_path = resolve_path(ws, body.output)

    def _run(*, progress_fn: Any = None) -> Any:
        from bosesph.asr import BenchmarkMetrics
        from bosesph.benchmark import generate_comparison_report

        baseline_data = json.loads(baseline_path.read_text(encoding="utf-8"))
        finetuned_data = json.loads(finetuned_path.read_text(encoding="utf-8"))
        baseline_metrics = BenchmarkMetrics(**baseline_data)
        finetuned_metrics = BenchmarkMetrics(**finetuned_data)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        report_path = generate_comparison_report(
            baseline_metrics, finetuned_metrics, output_path
        )
        from pydantic import BaseModel as _BM

        class _CompareResult(_BM):
            report_path: str

        return _CompareResult(report_path=str(report_path))

    return _jobs(request).submit("compare", _run)
