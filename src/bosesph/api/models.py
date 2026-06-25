"""Request and response models for the API layer.

Service-produced Pydantic models (``IngestionReport``, ``ValidationReport``,
etc.) are reused directly as ``response_model`` on endpoints.  This module
defines *additional* request bodies and API-specific response shapes.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------


class ImportPldRequest(BaseModel):
    """Body for ``POST /import-pld``."""

    source: str = Field(description="Relative path to the PLD session directory.")
    output: str = Field(description="Relative path for ingestion output.")
    overwrite: bool = False


class ValidateDatasetRequest(BaseModel):
    """Body for ``POST /validate-dataset``."""

    dataset: str = Field(
        description="Relative path to dataset directory containing metadata.csv."
    )


class NormalizeTranscriptsRequest(BaseModel):
    """Body for ``POST /normalize-transcripts``."""

    dataset: str = Field(description="Relative path to dataset directory.")


class ReviewDecisionRequest(BaseModel):
    """Body for ``POST /review/decision``."""

    dataset: str = Field(description="Relative path to dataset directory.")
    audio_id: str = Field(description="Audio ID of the clip to review.")
    decision: str = Field(
        description="One of: approve, needs_fix, reject.",
        pattern="^(approve|needs_fix|reject)$",
    )
    note: str | None = Field(
        default=None,
        description="Required for needs_fix and reject decisions.",
    )


class BuildDatasetRequest(BaseModel):
    """Body for ``POST /build-dataset``."""

    dataset: str = Field(description="Relative path to source dataset directory.")
    output: str = Field(description="Relative path for built dataset output.")
    train_ratio: float = Field(default=0.70, gt=0, lt=1)
    val_ratio: float = Field(default=0.15, gt=0, lt=1)
    test_ratio: float = Field(default=0.15, gt=0, lt=1)
    seed: int = 42
    overwrite: bool = False


class TranscribeRequest(BaseModel):
    """Body for ``POST /transcribe``."""

    dataset: str = Field(description="Relative path to built dataset directory.")
    model: str = Field(default="openai/whisper-small")
    language: str | None = None
    split: str = Field(default="test")
    output: str = Field(description="Relative path for predictions output.")


class EvaluateRequest(BaseModel):
    """Body for ``POST /evaluate``."""

    predictions: str = Field(description="Relative path to predictions CSV.")
    references: str | None = Field(
        default=None,
        description="Optional relative path to separate references CSV.",
    )
    output: str | None = Field(
        default=None,
        description="Relative path for results output directory.",
    )
    model_name: str = "baseline"
    language: str = "kapampangan"


class TrainRequest(BaseModel):
    """Body for ``POST /train``."""

    dataset: str = Field(description="Relative path to built dataset directory.")
    output: str = Field(description="Relative path for model output.")
    base_model: str = "openai/whisper-tiny"
    language: str = "tl"
    epochs: int = 3
    max_steps: int | None = None
    batch_size: int = 8
    learning_rate: float = 1e-5
    train_split: str = "train"
    eval_split: str = "validation"


class CompareRequest(BaseModel):
    """Body for ``POST /compare``."""

    baseline: str = Field(description="Relative path to baseline results.json.")
    finetuned: str = Field(description="Relative path to fine-tuned results.json.")
    output: str = Field(description="Relative path for comparison report.")


class DownloadRequest(BaseModel):
    """Query params for ``GET /download-output``."""

    path: str = Field(description="Relative path under workspace to download.")


# ---------------------------------------------------------------------------
# API-specific response shapes
# ---------------------------------------------------------------------------


class ReviewDecisionResult(BaseModel):
    """Response for ``POST /review/decision``."""

    audio_id: str
    new_status: str
    remaining_reviewable: int


class ApproveAllRequest(BaseModel):
    """Body for ``POST /review/approve-all``."""

    dataset: str = Field(description="Relative path to dataset directory.")


class ApproveAllResponse(BaseModel):
    """Response for ``POST /review/approve-all``."""

    approved: int
    skipped_missing_audio: int
    remaining: int


class ProjectStatus(BaseModel):
    """Aggregated project state for ``GET /project-status``."""

    dataset_available: bool = False
    dataset_stats: dict[str, Any] | None = None
    benchmark_available: bool = False
    benchmark_results: dict[str, Any] | None = None
    model_available: bool = False
    model_dir: str | None = None


class UploadResult(BaseModel):
    """Response for ``POST /upload-audio``."""

    saved_files: list[str]
    count: int
