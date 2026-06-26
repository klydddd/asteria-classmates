"""Thin wrapper functions bridging MCP tool calls to BosesPH service modules.

Each public function in this module:

1. Accepts simple types (strings, floats, ints) suitable for MCP tool schemas.
2. Resolves relative paths under a workspace root.
3. Delegates to the existing service function.
4. Returns a JSON-serializable dict (via Pydantic ``.model_dump()`` where
   available, or plain dicts).

The workspace root defaults to ``outputs/`` and can be overridden by setting
the ``BOSESPH_WORKSPACE`` environment variable.
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any


def _resolve(workspace: Path, relative: str) -> Path:
    """Join *relative* under *workspace* and reject traversal attempts."""
    if not relative or relative.startswith("/") or "\\" in relative:
        raise ValueError(
            f"Path must be a non-empty relative POSIX path: {relative!r}"
        )
    parts = relative.split("/")
    if any(part in {".", ".."} for part in parts):
        raise ValueError(
            f"Path must not contain traversal components: {relative!r}"
        )
    resolved = (workspace / relative).resolve()
    workspace_resolved = workspace.resolve()
    if (
        not str(resolved).startswith(str(workspace_resolved) + "/")
        and resolved != workspace_resolved
    ):
        raise ValueError(f"Resolved path escapes workspace root: {relative!r}")
    return resolved


def _read_json(path: Path) -> dict[str, object] | None:
    """Read a JSON file, returning ``None`` on any parse or I/O error."""
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        return None
    return data if isinstance(data, dict) else None


def _finite_float(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        converted = float(value)
    except OverflowError:
        return None
    return converted if math.isfinite(converted) else None


def _metric_summary(path: Path) -> dict[str, float] | None:
    data = _read_json(path)
    if data is None or "wer" not in data or "cer" not in data:
        return None
    wer = _finite_float(data["wer"])
    cer = _finite_float(data["cer"])
    if wer is None or cer is None:
        return None
    return {"wer": wer, "cer": cer}


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------


def get_project_status(workspace: Path) -> dict[str, Any]:
    """Return aggregated project status from conventional output paths."""
    ws = workspace.resolve()
    dataset_stats = _read_json(ws / "dataset_30spk" / "dataset_stats.json")
    model_root = ws / "model"
    model_dir: Path | None = None

    if model_root.is_dir():
        preferred = model_root / "colab_finetuned_model_tl_30speakers"
        if preferred.is_dir() and (preferred / "model_card.md").is_file():
            model_dir = preferred
        else:
            model_dir = next(
                (
                    child
                    for child in sorted(model_root.iterdir())
                    if child.is_dir() and (child / "model_card.md").is_file()
                ),
                None,
            )

    return {
        "dataset_available": dataset_stats is not None,
        "dataset_stats": dataset_stats,
        "baseline_metrics": _metric_summary(
            ws / "benchmark" / "baseline_small_tl" / "results.json"
        ),
        "finetuned_metrics": _metric_summary(
            ws / "benchmark" / "colab_small_tl_30spk" / "results.json"
        ),
        "model_available": model_dir is not None,
        "model_dir": str(model_dir.relative_to(ws)) if model_dir else None,
        "model_version": model_dir.name if model_dir else None,
    }


def validate_metadata(workspace: Path, dataset: str) -> dict[str, Any]:
    """Validate a dataset's ``metadata.csv`` and return the report."""
    from bosesph.metadata import validate_metadata_csv

    dataset_path = _resolve(workspace, dataset)
    metadata_csv = dataset_path / "metadata.csv"
    if not metadata_csv.is_file():
        raise FileNotFoundError(f"metadata.csv not found in {dataset}")
    report = validate_metadata_csv(metadata_csv)
    return report.model_dump()


def import_pld_session(
    workspace: Path,
    source: str,
    output: str,
    *,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Import a PLD recording session directory."""
    from bosesph.ingestion import import_pld_session as _import

    source_path = _resolve(workspace, source)
    output_path = _resolve(workspace, output)
    report = _import(source_path, output_path, overwrite=overwrite)
    return report.model_dump()


def normalize_transcripts(
    workspace: Path,
    dataset: str,
) -> dict[str, Any]:
    """Normalize transcript formatting in a dataset."""
    from bosesph.transcripts import normalize_dataset

    dataset_path = _resolve(workspace, dataset)
    report = normalize_dataset(dataset_path)
    return report.model_dump()


def apply_review_decision(
    workspace: Path,
    dataset: str,
    audio_id: str,
    decision: str,
    note: str | None = None,
) -> dict[str, Any]:
    """Apply a review decision (approved/rejected/needs_fix) to a single clip."""
    from bosesph.review import decide_clip

    dataset_path = _resolve(workspace, dataset)
    result = decide_clip(dataset_path, audio_id, decision, note=note)
    return result.model_dump()



def build_dataset(
    workspace: Path,
    dataset: str,
    output: str,
    *,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    test_ratio: float = 0.15,
    seed: int = 42,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Build a clean dataset with train/validation/test splits."""
    from bosesph.dataset import build_dataset as _build

    dataset_path = _resolve(workspace, dataset)
    output_path = _resolve(workspace, output)
    result = _build(
        dataset_path,
        output_path,
        train_ratio=train_ratio,
        val_ratio=val_ratio,
        test_ratio=test_ratio,
        seed=seed,
        overwrite=overwrite,
    )
    return result.model_dump()


def transcribe_audio(
    workspace: Path,
    audio_path: str,
    *,
    model: str = "openai/whisper-small",
    language: str | None = None,
) -> dict[str, str]:
    """Transcribe a single audio file and return the predicted text."""
    from bosesph.asr import load_model, transcribe_file

    resolved = _resolve(workspace, audio_path)
    if not resolved.is_file():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
    pipe = load_model(model)
    prediction = transcribe_file(pipe, resolved, language=language)
    return {"audio_path": audio_path, "prediction": prediction, "model": model}


def transcribe_dataset(
    workspace: Path,
    dataset: str,
    output: str,
    *,
    model: str = "openai/whisper-small",
    language: str | None = None,
    split: str = "test",
    limit: int | None = None,
) -> dict[str, Any]:
    """Transcribe a dataset split and write predictions CSV."""
    from bosesph.asr import load_model, transcribe_split

    dataset_path = _resolve(workspace, dataset)
    output_path = _resolve(workspace, output)
    split_csv = dataset_path / f"{split}.csv"
    if not split_csv.is_file():
        raise FileNotFoundError(f"Split CSV not found: {split}.csv in {dataset}")
    pipe = load_model(model)
    results = transcribe_split(
        split_csv,
        dataset_path,
        pipe,
        language=language,
        output_path=output_path,
        limit=limit,
    )
    return {
        "predictions_path": str(output_path),
        "clip_count": len(results),
        "model": model,
        "split": split,
    }


def evaluate_predictions(
    workspace: Path,
    predictions: str,
    *,
    references: str | None = None,
    model_name: str = "baseline",
    language: str = "kapampangan",
    output: str | None = None,
) -> dict[str, Any]:
    """Compute WER/CER from a predictions CSV."""
    from bosesph.asr import evaluate_predictions as _evaluate

    predictions_path = _resolve(workspace, predictions)
    references_path = (
        _resolve(workspace, references) if references else None
    )

    metrics = _evaluate(
        predictions_path,
        references_csv=references_path,
        model=model_name,
        language=language,
    )

    if output:
        from bosesph.asr import TranscriptionResult
        from bosesph.benchmark import generate_benchmark_report

        output_path = _resolve(workspace, output)
        preds: list[Any] = []
        with predictions_path.open(newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                preds.append(TranscriptionResult(**row))
        output_path.mkdir(parents=True, exist_ok=True)
        generate_benchmark_report(metrics, preds, output_path / "report.md")
        results_file = output_path / "results.json"
        results_file.write_text(
            metrics.model_dump_json(indent=2), encoding="utf-8"
        )

    return metrics.model_dump()


def get_dataset_stats(workspace: Path) -> dict[str, Any]:
    """Return the dataset statistics JSON if available."""
    stats_path = workspace.resolve() / "dataset" / "dataset_stats.json"
    data = _read_json(stats_path)
    if data is None:
        raise FileNotFoundError(
            "No dataset_stats.json found. Run build-dataset first."
        )
    return data


def list_dataset_clips(
    workspace: Path,
    split: str = "test",
    *,
    limit: int = 50,
) -> dict[str, Any]:
    """List clips in a dataset split CSV."""
    dataset_dir = workspace.resolve() / "dataset"
    split_csv = dataset_dir / f"{split}.csv"
    if not split_csv.is_file():
        raise FileNotFoundError(
            f"Split CSV not found: {split}.csv. Run build-dataset first."
        )
    clips: list[dict[str, str]] = []
    with split_csv.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for i, row in enumerate(reader):
            if i >= limit:
                break
            clips.append(dict(row))
    return {"split": split, "clip_count": len(clips), "clips": clips}
