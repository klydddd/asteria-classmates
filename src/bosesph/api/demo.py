"""Controlled model options for the direct transcription demo."""

from __future__ import annotations

import json
import logging
import shutil
import uuid
from collections.abc import Callable
from pathlib import Path

from fastapi import UploadFile

from bosesph.api.models import (
    DemoLanguageOption,
    DemoModelOption,
    DemoOptions,
    DemoTranscriptionResult,
)

DEFAULT_DECODING_LANGUAGE = "tl"
CHUNK_SIZE = 256 * 1024
LOGGER = logging.getLogger(__name__)


def _read_decoding_language(candidate: Path) -> str:
    config_path = candidate / "training_config.json"
    if not config_path.is_file():
        return DEFAULT_DECODING_LANGUAGE

    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return DEFAULT_DECODING_LANGUAGE

    if not isinstance(config, dict):
        return DEFAULT_DECODING_LANGUAGE
    language = config.get("language")
    if not isinstance(language, str) or not language.strip():
        return DEFAULT_DECODING_LANGUAGE
    return language.strip()


def _is_within_workspace(path: Path, workspace: Path) -> bool:
    return path.resolve().is_relative_to(workspace)


def _is_safe_model_tree(model_dir: Path, workspace: Path) -> bool:
    try:
        if model_dir.is_symlink() or not _is_within_workspace(model_dir, workspace):
            return False
        return all(
            not entry.is_symlink() and _is_within_workspace(entry, workspace)
            for entry in model_dir.rglob("*")
        )
    except OSError:
        return False


def _make_model_label(dirname: str) -> str:
    return " ".join(w.capitalize() for w in dirname.replace("_", " ").replace("-", " ").split())


def _discover_finetuned_models(workspace: Path) -> list[DemoModelOption]:
    """Return all valid fine-tuned models found in workspace/model/, sorted by name."""
    model_root = workspace / "model"
    if not model_root.is_dir():
        return []

    models = []
    for child in sorted(model_root.iterdir()):
        if (
            child.is_dir()
            and not child.is_symlink()
            and _is_within_workspace(child, workspace)
            and (child / "model_card.md").is_file()
            and (child / "model" / "config.json").is_file()
            and _is_safe_model_tree(child / "model", workspace)
        ):
            models.append(
                DemoModelOption(
                    id=f"finetuned_{child.name}",
                    label=_make_model_label(child.name),
                    model_path=str((child / "model").relative_to(workspace)),
                    available=True,
                    unavailable_reason=None,
                    decoding_language=_read_decoding_language(child),
                )
            )
    return models


def discover_demo_options(workspace: Path) -> DemoOptions:
    """Return the fixed demo choices and all valid local fine-tuned models."""
    workspace = workspace.resolve()
    finetuned_models = _discover_finetuned_models(workspace)

    # Default to the 30-speaker Colab model if available, otherwise baseline.
    default_model_id = "baseline"
    for m in finetuned_models:
        if "30speaker" in m.id:
            default_model_id = m.id
            break

    return DemoOptions(
        languages=[
            DemoLanguageOption(
                id="kapampangan",
                label="Kapampangan",
                description="Kapampangan speech with model-specific decoding.",
            ),
            DemoLanguageOption(
                id="auto",
                label="Auto-detect",
                description="Let the selected model determine decoding language.",
            ),
        ],
        models=[
            DemoModelOption(
                id="baseline",
                label="Whisper Small (baseline)",
                model_path="openai/whisper-small",
                available=True,
            ),
            *finetuned_models,
        ],
        default_language_id="kapampangan",
        default_model_id=default_model_id,
    )


def select_demo_model(
    options: DemoOptions,
    model_id: str,
    language_id: str,
) -> tuple[DemoModelOption, str | None]:
    """Validate a controlled selection and resolve its decoding language."""
    model = next((item for item in options.models if item.id == model_id), None)
    if model is None:
        raise ValueError(f"Unknown demo model: {model_id}")
    if not model.available:
        raise ValueError(model.unavailable_reason or "Selected model is unavailable.")
    if language_id not in {item.id for item in options.languages}:
        raise ValueError(f"Unknown demo language: {language_id}")
    if language_id == "auto" or model.id == "baseline":
        return model, None
    return model, model.decoding_language


def remove_demo_upload(directory: Path) -> None:
    """Remove one transient upload and its root when it becomes empty."""
    root = directory.parent
    try:
        shutil.rmtree(directory)
        if root.is_dir() and not any(root.iterdir()):
            root.rmdir()
    except OSError:
        LOGGER.exception("Failed to remove demo upload directory %s", directory)


def save_demo_upload(workspace: Path, upload: UploadFile) -> tuple[Path, Path]:
    """Copy one WAV upload to a unique, fixed-name transient directory."""
    filename = upload.filename or ""
    if Path(filename).suffix.lower() != ".wav":
        raise ValueError("Only PCM WAV uploads are supported.")

    resolved_workspace = workspace.resolve()
    root = resolved_workspace / ".demo_uploads"
    if root.is_symlink() or not root.resolve().is_relative_to(resolved_workspace):
        raise ValueError("Demo upload root escapes workspace.")
    directory = root / uuid.uuid4().hex
    directory.mkdir(parents=True)
    target = directory / "audio.wav"
    size = 0

    try:
        with target.open("wb") as handle:
            while chunk := upload.file.read(CHUNK_SIZE):
                size += len(chunk)
                handle.write(chunk)
    except Exception:
        remove_demo_upload(directory)
        raise

    if size == 0:
        remove_demo_upload(directory)
        raise ValueError("Uploaded audio is empty.")
    return target, directory


def run_demo_transcription(
    *,
    audio_path: Path,
    upload_directory: Path,
    model: DemoModelOption,
    language_id: str,
    decoding_language: str | None,
    reference: str | None,
    progress_fn: Callable[[object], None],
) -> DemoTranscriptionResult:
    """Transcribe one temporary upload and always attempt to remove it."""
    try:
        from bosesph.asr import calculate_metrics, load_model, transcribe_file

        progress_fn("loading-model")
        pipe = load_model(model.model_path)
        print(f"[DEMO] Model: {model.model_path} ({model.label})")
        progress_fn("transcribing")
        prediction = transcribe_file(
            pipe,
            audio_path,
            language=decoding_language,
        )
        print(f"[DEMO] Transcript: {prediction}")
        wer: float | None = None
        cer: float | None = None
        if reference and reference.strip():
            metrics = calculate_metrics(
                [reference],
                [prediction],
                model=model.id,
                language=language_id,
            )
            wer = round(metrics.wer, 4)
            cer = round(metrics.cer, 4)
            print(f"[DEMO] WER: {wer:.2%} | CER: {cer:.2%}")
        return DemoTranscriptionResult(
            prediction=prediction,
            model_id=model.id,
            model_label=model.label,
            language_id=language_id,
            wer=wer,
            cer=cer,
        )
    finally:
        remove_demo_upload(upload_directory)
