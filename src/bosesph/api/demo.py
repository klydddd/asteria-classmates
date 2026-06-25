"""Controlled model options for the direct transcription demo."""

from __future__ import annotations

import json
from pathlib import Path

from bosesph.api.models import DemoLanguageOption, DemoModelOption, DemoOptions

DEFAULT_DECODING_LANGUAGE = "tl"


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


def _find_finetuned_model(workspace: Path) -> Path | None:
    model_root = workspace / "model"
    if not model_root.is_dir():
        return None

    return next(
        (
            child
            for child in sorted(model_root.iterdir())
            if child.is_dir()
            and _is_within_workspace(child, workspace)
            and _is_within_workspace(child / "model", workspace)
            and _is_safe_model_tree(child / "model", workspace)
            and (child / "model_card.md").is_file()
            and (child / "model" / "config.json").is_file()
        ),
        None,
    )


def discover_demo_options(workspace: Path) -> DemoOptions:
    """Return the fixed demo choices and any valid local fine-tuned model."""
    workspace = workspace.resolve()
    candidate = _find_finetuned_model(workspace)

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
            DemoModelOption(
                id="finetuned",
                label="BosesPH fine-tuned model",
                model_path=(
                    str((candidate / "model").relative_to(workspace))
                    if candidate
                    else ""
                ),
                available=candidate is not None,
                unavailable_reason=(
                    None if candidate else "No local fine-tuned model found."
                ),
                decoding_language=(
                    _read_decoding_language(candidate) if candidate else None
                ),
            ),
        ],
        default_language_id="kapampangan",
        default_model_id="baseline",
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
