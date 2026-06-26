"""ASR inference and evaluation with lazy-loaded optional dependencies."""

from __future__ import annotations

import csv
import re
import unicodedata
from collections.abc import Callable
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from bosesph.audio import _read_wav
from bosesph.metadata import ANNOTATION_PATTERN


class ASRError(ValueError):
    """Raised for missing ASR dependencies, model failures, or invalid input."""


class TranscriptionResult(BaseModel):
    """One clip's transcription output."""

    audio_id: str
    reference: str
    prediction: str
    file_path: str


class BenchmarkMetrics(BaseModel):
    """Aggregate WER/CER metrics for a benchmark run."""

    model: str
    language: str
    wer: float
    cer: float
    test_clips: int
    total_duration_seconds: float


# ---------------------------------------------------------------------------
# Lazy dependency helpers
# ---------------------------------------------------------------------------

_INSTALL_HINT = 'pip install -e ".[asr]"'


def _require_torch() -> Any:
    try:
        import torch  # noqa: F811

        return torch
    except ImportError as error:
        raise ASRError(
            f"torch is required for ASR inference; install with: {_INSTALL_HINT}"
        ) from error


def _require_transformers() -> Any:
    try:
        import transformers  # noqa: F811

        return transformers
    except ImportError as error:
        raise ASRError(
            f"transformers is required for ASR inference; install with: {_INSTALL_HINT}"
        ) from error


def _require_numpy() -> Any:
    try:
        import numpy  # noqa: F811

        return numpy
    except ImportError as error:
        raise ASRError(
            f"numpy is required for ASR inference; install with: {_INSTALL_HINT}"
        ) from error


def _require_jiwer() -> Any:
    try:
        import jiwer  # noqa: F811

        return jiwer
    except ImportError as error:
        raise ASRError(
            f"jiwer is required for ASR evaluation; install with: {_INSTALL_HINT}"
        ) from error


# ---------------------------------------------------------------------------
# Device detection
# ---------------------------------------------------------------------------


def _get_device() -> str:
    """Detect the best available device for inference."""
    torch = _require_torch()
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


# ---------------------------------------------------------------------------
# Audio loading (stdlib, no ffmpeg)
# ---------------------------------------------------------------------------


def _load_audio_array(path: Path) -> tuple[Any, int]:
    """Load a WAV file into a numpy float32 array and return (array, sample_rate).

    Reuses the existing stdlib ``audio._read_wav`` so no ffmpeg or torchaudio
    is needed.  The dataset clips are already standardised to 16 kHz mono PCM.
    """
    np = _require_numpy()
    inspection, samples = _read_wav(path)
    # Flatten to mono if multi-channel (shouldn't happen for standardised clips).
    if inspection.channels > 1:
        mono: list[float] = []
        for i in range(0, len(samples), inspection.channels):
            mono.append(sum(samples[i : i + inspection.channels]) / inspection.channels)
        samples = mono
    return np.array(samples, dtype=np.float32), inspection.sample_rate


# ---------------------------------------------------------------------------
# Model loading
# ---------------------------------------------------------------------------


def load_model(model_name: str, device: str | None = None) -> Any:
    """Load a HuggingFace ASR pipeline.

    Returns the pipeline object.  Raises ``ASRError`` on failure.
    """
    transformers = _require_transformers()
    _require_torch()  # ensure torch is available
    if device is None:
        device = _get_device()
    try:
        pipe = transformers.pipeline(
            "automatic-speech-recognition",
            model=model_name,
            device=device,
        )
    except Exception as error:
        raise ASRError(f"failed to load model {model_name!r}: {error}") from error
    return pipe


# ---------------------------------------------------------------------------
# Transcription
# ---------------------------------------------------------------------------


def transcribe_file(
    pipe: Any,
    audio_path: str | Path,
    *,
    language: str | None = None,
) -> str:
    """Transcribe a single audio file and return the predicted text."""
    path = Path(audio_path)
    if not path.is_file():
        raise ASRError(f"audio file not found: {path}")

    audio_array, sample_rate = _load_audio_array(path)
    kwargs: dict[str, Any] = {}
    if language:
        kwargs["generate_kwargs"] = {"language": language}
    result = pipe(
        {"raw": audio_array, "sampling_rate": sample_rate},
        **kwargs,
    )
    return str(result["text"]).strip()


def transcribe_split(
    split_csv: str | Path,
    dataset_dir: str | Path,
    pipe: Any,
    *,
    language: str | None = None,
    output_path: str | Path,
    progress_fn: Callable[[int, int], None] | None = None,
    limit: int | None = None,
) -> list[TranscriptionResult]:
    """Transcribe every clip in a split CSV and write predictions.csv.

    Returns a list of ``TranscriptionResult`` objects.  Missing audio files
    produce an empty prediction with a note rather than crashing the batch.
    """
    csv_path = Path(split_csv)
    ds_dir = Path(dataset_dir)
    out_path = Path(output_path)

    if not csv_path.is_file():
        raise ASRError(f"split CSV not found: {csv_path}")

    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, strict=True)
        rows = list(reader)

    if not rows:
        raise ASRError(f"split CSV is empty: {csv_path}")

    if limit is not None and limit > 0:
        rows = rows[:limit]

    results: list[TranscriptionResult] = []
    total = len(rows)

    for index, row in enumerate(rows):
        audio_id = row.get("audio_id", "")
        reference = row.get("transcript", "")
        file_path = row.get("file_path", "")
        audio_file = ds_dir / file_path

        if audio_file.is_file():
            try:
                prediction = transcribe_file(pipe, audio_file, language=language)
            except (ASRError, Exception) as error:
                prediction = f"[error: {error}]"
        else:
            prediction = "[missing audio]"

        results.append(
            TranscriptionResult(
                audio_id=audio_id,
                reference=reference,
                prediction=prediction,
                file_path=file_path,
            )
        )

        if progress_fn is not None:
            progress_fn(index + 1, total)

    # Write predictions CSV.
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["audio_id", "reference", "prediction", "file_path"]
    with out_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            writer.writerow(result.model_dump())

    return results


# ---------------------------------------------------------------------------
# Scoring normalisation
# ---------------------------------------------------------------------------

_PUNCTUATION_PATTERN = re.compile(r"[^\w\s]", flags=re.UNICODE)
_WHITESPACE_PATTERN = re.compile(r"\s+")


def normalize_for_scoring(text: str) -> str:
    """Normalise text for WER/CER scoring.

    Lowercases, strips annotation tags (``[noise]`` etc.), removes punctuation,
    applies Unicode NFC, and collapses whitespace.
    """
    result = unicodedata.normalize("NFC", text)
    result = result.lower()
    # Remove annotation tags.
    result = ANNOTATION_PATTERN.sub("", result)
    # Remove punctuation.
    result = _PUNCTUATION_PATTERN.sub("", result)
    # Collapse whitespace.
    result = _WHITESPACE_PATTERN.sub(" ", result).strip()
    return result


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


def calculate_metrics(
    references: list[str],
    predictions: list[str],
    *,
    model: str = "baseline",
    language: str = "kapampangan",
    total_duration_seconds: float = 0.0,
) -> BenchmarkMetrics:
    """Compute WER and CER from parallel reference/prediction lists."""
    jiwer = _require_jiwer()

    if not references:
        raise ASRError("no references provided for metric calculation")

    # Normalise both sides for fair comparison.
    norm_refs = [normalize_for_scoring(r) for r in references]
    norm_preds = [normalize_for_scoring(p) for p in predictions]

    # Guard against all-empty references after normalisation.
    if all(not r for r in norm_refs):
        raise ASRError("all references are empty after normalisation")

    # Replace empty strings with a placeholder so jiwer doesn't crash.
    norm_refs = [r if r else "<empty>" for r in norm_refs]
    norm_preds = [p if p else "<empty>" for p in norm_preds]

    wer = jiwer.wer(norm_refs, norm_preds)
    cer = jiwer.cer(norm_refs, norm_preds)

    return BenchmarkMetrics(
        model=model,
        language=language,
        wer=round(wer, 4),
        cer=round(cer, 4),
        test_clips=len(references),
        total_duration_seconds=round(total_duration_seconds, 3),
    )


def evaluate_predictions(
    predictions_csv: str | Path,
    *,
    references_csv: str | Path | None = None,
    model: str = "baseline",
    language: str = "kapampangan",
) -> BenchmarkMetrics:
    """Load a predictions CSV, optionally override references, and compute metrics."""
    pred_path = Path(predictions_csv)
    if not pred_path.is_file():
        raise ASRError(f"predictions CSV not found: {pred_path}")

    with pred_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, strict=True)
        pred_rows = list(reader)

    if not pred_rows:
        raise ASRError(f"predictions CSV is empty: {pred_path}")

    # Build reference/prediction lists.
    references: list[str] = [row.get("reference", "") for row in pred_rows]
    predictions: list[str] = [row.get("prediction", "") for row in pred_rows]

    # Optionally override references from a separate CSV.
    if references_csv is not None:
        ref_path = Path(references_csv)
        if not ref_path.is_file():
            raise ASRError(f"references CSV not found: {ref_path}")
        with ref_path.open("r", encoding="utf-8", newline="") as handle:
            ref_rows = list(csv.DictReader(handle, strict=True))
        ref_map = {row["audio_id"]: row.get("transcript", "") for row in ref_rows}
        references = [
            ref_map.get(row.get("audio_id", ""), row.get("reference", ""))
            for row in pred_rows
        ]

    # Compute total duration from predictions if available.
    total_duration = sum(
        float(row.get("duration_seconds", 0))
        for row in pred_rows
        if row.get("duration_seconds")
    )

    return calculate_metrics(
        references,
        predictions,
        model=model,
        language=language,
        total_duration_seconds=total_duration,
    )
