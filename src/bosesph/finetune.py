"""Whisper fine-tuning with lazy-loaded optional dependencies."""

from __future__ import annotations

import csv
import textwrap
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from bosesph.asr import (
    ASRError,
    _load_audio_array,
    _require_torch,
    _require_transformers,
)

_INSTALL_HINT = 'pip install -e ".[train]"'


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


class FineTuneConfig(BaseModel):
    """Training configuration persisted as ``training_config.json``."""

    base_model: str
    language: str
    epochs: int
    max_steps: int | None
    batch_size: int
    learning_rate: float
    train_clips: int
    val_clips: int
    use_lora: bool = False
    lora_r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.05


class FineTuneReport(BaseModel):
    """Result summary returned by the fine-tune function."""

    output_dir: str
    base_model: str
    language: str
    train_clips: int
    val_clips: int
    steps: int
    model_path: str
    config_path: str
    card_path: str


# ---------------------------------------------------------------------------
# Lazy dependency helpers
# ---------------------------------------------------------------------------


def _require_accelerate() -> Any:
    try:
        import accelerate  # noqa: F811

        return accelerate
    except ImportError as error:
        raise ASRError(
            f"accelerate is required for fine-tuning; install with: {_INSTALL_HINT}"
        ) from error


def _require_peft() -> Any:
    try:
        import peft  # noqa: F811

        return peft
    except ImportError as error:
        raise ASRError(
            f"peft is required for LoRA fine-tuning; install with: {_INSTALL_HINT}"
        ) from error


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


def _load_split_clips(
    split_csv: str | Path,
    dataset_dir: str | Path,
) -> list[tuple[Path, str]]:
    """Read a split CSV and return ``[(audio_path, transcript)]``.

    Returns an empty list when the CSV is missing or has no rows, so
    fine-tuning can skip an absent validation split gracefully.
    """
    csv_path = Path(split_csv)
    ds_dir = Path(dataset_dir)

    if not csv_path.is_file():
        return []

    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, strict=True)
        rows = list(reader)

    if not rows:
        return []

    clips: list[tuple[Path, str]] = []
    for row in rows:
        file_path = row.get("file_path", "")
        transcript = row.get("transcript", "")
        audio_path = ds_dir / file_path
        if not audio_path.is_file():
            continue  # skip missing audio silently
        clips.append((audio_path, transcript))

    return clips


def _build_example(
    processor: Any,
    audio_path: Path,
    transcript: str,
) -> dict[str, Any]:
    """Build a single training example dict from audio + transcript.

    Returns ``{"input_features": ..., "labels": ...}`` suitable for the
    Whisper ``Seq2SeqTrainer``.
    """
    audio_array, sample_rate = _load_audio_array(audio_path)

    features = processor.feature_extractor(
        audio_array,
        sampling_rate=sample_rate,
        return_tensors="np",
    )
    input_features = features.input_features[0]

    labels = processor.tokenizer(transcript).input_ids

    return {
        "input_features": input_features,
        "labels": labels,
    }


# ---------------------------------------------------------------------------
# Dataset wrapper
# ---------------------------------------------------------------------------


def _make_dataset_class() -> type:
    """Create and return the WhisperDataset class (requires torch)."""
    torch = _require_torch()

    class WhisperDataset(torch.utils.data.Dataset):  # type: ignore[name-defined]
        """Thin wrapper around clip list + processor for Seq2SeqTrainer."""

        def __init__(
            self,
            clips: list[tuple[Path, str]],
            processor: Any,
        ) -> None:
            self.clips = clips
            self.processor = processor

        def __len__(self) -> int:
            return len(self.clips)

        def __getitem__(self, index: int) -> dict[str, Any]:
            audio_path, transcript = self.clips[index]
            return _build_example(self.processor, audio_path, transcript)

    return WhisperDataset


# ---------------------------------------------------------------------------
# Data collator
# ---------------------------------------------------------------------------


class _DataCollatorSpeechSeq2Seq:
    """Whisper-specific collator: pad features and labels."""

    def __init__(self, processor: Any) -> None:
        self.processor = processor

    def __call__(self, features: list[dict[str, Any]]) -> dict[str, Any]:
        _require_torch()

        # Pad input features.
        input_features = [{"input_features": f["input_features"]} for f in features]
        batch = self.processor.feature_extractor.pad(
            input_features,
            return_tensors="pt",
        )

        # Pad labels and mask padding with -100.
        label_features = [{"input_ids": f["labels"]} for f in features]
        labels_batch = self.processor.tokenizer.pad(
            label_features,
            return_tensors="pt",
        )
        labels = labels_batch["input_ids"]
        labels = labels.masked_fill(labels_batch.attention_mask.ne(1), -100)

        # Strip the leading forced BOS token if present.
        if (labels[:, 0] == self.processor.tokenizer.bos_token_id).all():
            labels = labels[:, 1:]

        batch["labels"] = labels
        return batch


# ---------------------------------------------------------------------------
# Model card generation
# ---------------------------------------------------------------------------


def _generate_model_card(
    config: FineTuneConfig,
    *,
    metrics: dict[str, float] | None = None,
) -> str:
    """Generate a markdown model card for the fine-tuned checkpoint."""
    eval_section = ""
    if metrics:
        wer = metrics.get("wer", "N/A")
        cer = metrics.get("cer", "N/A")
        eval_section = textwrap.dedent(
            f"""\

            ## Evaluation

            | Metric | Score |
            |---|---|
            | WER | {wer} |
            | CER | {cer} |
        """
        )

    if config.use_lora:
        method = f"LoRA (r={config.lora_r}, alpha={config.lora_alpha})"
    else:
        method = "Full fine-tuning"

    return textwrap.dedent(
        f"""\
        # BosesPH Fine-Tuned ASR Model

        ## Overview

        A Whisper model fine-tuned for Kapampangan speech recognition using the
        BosesPH Toolkit pipeline.

        ## Model Details

        | Field | Value |
        |---|---|
        | Base model | {config.base_model} |
        | Language token | {config.language} (proxy for Kapampangan) |
        | Training clips | {config.train_clips} |
        | Validation clips | {config.val_clips} |
        | Epochs | {config.epochs} |
        | Max steps | {config.max_steps or "—"} |
        | Batch size | {config.batch_size} |
        | Learning rate | {config.learning_rate} |
        | Method | {method} |
        {eval_section}
        ## Usage

        ```python
        from transformers import pipeline

        pipe = pipeline(
            "automatic-speech-recognition",
            model="<path-to-this-model>",
        )
        result = pipe("audio.wav")
        print(result["text"])
        ```

        ## Limitations

        - Kapampangan is not a natively supported Whisper language. This model
          uses the Tagalog (`{config.language}`) language token as a proxy,
          which may introduce tokenization artefacts.
        - Training data comes from a single PLD recording session with limited
          speaker diversity. Real-world performance may vary.
        - The model inherits all base-Whisper limitations (hallucinations on
          silence, timestamp drift, etc.).

        ## Intended Use

        Research and development of ASR systems for Philippine languages.

        ---

        *Generated by BosesPH Toolkit on \
{datetime.now(timezone.utc).strftime("%Y-%m-%d")}*
    """
    )


# ---------------------------------------------------------------------------
# Fine-tuning orchestration
# ---------------------------------------------------------------------------


def finetune_model(
    dataset_dir: str | Path,
    output_dir: str | Path,
    *,
    base_model: str = "openai/whisper-tiny",
    language: str = "tl",
    epochs: int = 3,
    max_steps: int | None = None,
    batch_size: int = 8,
    learning_rate: float = 1e-5,
    train_split: str = "train",
    eval_split: str = "validation",
    gradient_checkpointing: bool = False,
    optim: str = "adamw_torch",
    use_lora: bool = True,
    lora_r: int = 16,
    lora_alpha: int = 32,
    lora_dropout: float = 0.05,
    progress_fn: Callable[[str], None] | None = None,
) -> FineTuneReport:
    """Fine-tune a Whisper model on a built dataset.

    Returns a ``FineTuneReport`` with paths to the saved model, config, and
    model card.
    """
    transformers = _require_transformers()
    _require_torch()
    _require_accelerate()

    ds_dir = Path(dataset_dir)
    out_dir = Path(output_dir)

    def _log(message: str) -> None:
        if progress_fn is not None:
            progress_fn(message)

    # ------------------------------------------------------------------
    # Load training clips
    # ------------------------------------------------------------------
    train_csv = ds_dir / f"{train_split}.csv"
    train_clips = _load_split_clips(train_csv, ds_dir)
    if not train_clips:
        raise ASRError(
            f"no training clips found in {train_csv}; "
            "build the dataset first with 'bosesph build-dataset'"
        )
    _log(f"Loaded {len(train_clips)} training clips")

    val_csv = ds_dir / f"{eval_split}.csv"
    val_clips = _load_split_clips(val_csv, ds_dir)
    _log(f"Loaded {len(val_clips)} validation clips")

    # ------------------------------------------------------------------
    # Load processor and model
    # ------------------------------------------------------------------
    _log(f"Loading model: {base_model}")
    processor = transformers.WhisperProcessor.from_pretrained(base_model)
    model = transformers.WhisperForConditionalGeneration.from_pretrained(
        base_model,
    )

    # Force language and task in generation config.
    model.generation_config.language = language
    model.generation_config.task = "transcribe"
    model.generation_config.forced_decoder_ids = None

    if gradient_checkpointing:
        model.config.use_cache = False
        model.gradient_checkpointing_enable(
            gradient_checkpointing_kwargs={"use_reentrant": False}
        )

    # ------------------------------------------------------------------
    # Apply LoRA adapter (if enabled)
    # ------------------------------------------------------------------
    if use_lora:
        peft = _require_peft()
        if gradient_checkpointing:
            model.enable_input_require_grads()
        lora_config = peft.LoraConfig(
            r=lora_r,
            lora_alpha=lora_alpha,
            lora_dropout=lora_dropout,
            target_modules=["q_proj", "v_proj"],
            bias="none",
        )
        model = peft.get_peft_model(model, lora_config)
        trainable, total = model.get_nb_trainable_parameters()
        _log(
            f"LoRA enabled: {trainable:,} trainable / {total:,} total params "
            f"({100 * trainable / total:.1f}%)"
        )

    # ------------------------------------------------------------------
    # Build datasets
    # ------------------------------------------------------------------
    WhisperDataset = _make_dataset_class()
    train_dataset = WhisperDataset(train_clips, processor)
    eval_dataset = WhisperDataset(val_clips, processor) if val_clips else None
    collator = _DataCollatorSpeechSeq2Seq(processor)

    # ------------------------------------------------------------------
    # Training arguments
    # ------------------------------------------------------------------
    out_dir.mkdir(parents=True, exist_ok=True)

    training_args_kwargs: dict[str, Any] = {
        "output_dir": str(out_dir),
        "per_device_train_batch_size": batch_size,
        "num_train_epochs": epochs,
        "learning_rate": learning_rate,
        "warmup_steps": 50,
        "logging_steps": 10,
        "save_strategy": "epoch",
        "fp16": False,
        "remove_unused_columns": False,
        "report_to": "none",
        "optim": optim,
    }

    if use_lora:
        training_args_kwargs["label_names"] = ["labels"]

    if max_steps is not None:
        training_args_kwargs["max_steps"] = max_steps

    if eval_dataset is not None:
        training_args_kwargs["eval_strategy"] = "epoch"
    else:
        training_args_kwargs["eval_strategy"] = "no"

    training_args = transformers.Seq2SeqTrainingArguments(
        **training_args_kwargs,
    )

    # ------------------------------------------------------------------
    # Train
    # ------------------------------------------------------------------
    _log("Starting training")
    trainer = transformers.Seq2SeqTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        data_collator=collator,
        tokenizer=processor.feature_extractor,
    )
    train_result = trainer.train()
    steps = train_result.global_step
    _log(f"Training complete — {steps} steps")

    # ------------------------------------------------------------------
    # Save model + processor
    # ------------------------------------------------------------------
    model_path = out_dir / "model"
    model_path.mkdir(parents=True, exist_ok=True)
    if use_lora:
        merged = model.merge_and_unload()
        merged.save_pretrained(str(model_path))
        _log("Merged LoRA weights into base model")
    else:
        trainer.save_model(str(model_path))
    processor.save_pretrained(str(model_path))
    _log(f"Saved model to {model_path}")

    # ------------------------------------------------------------------
    # Write config and model card
    # ------------------------------------------------------------------
    config = FineTuneConfig(
        base_model=base_model,
        language=language,
        epochs=epochs,
        max_steps=max_steps,
        batch_size=batch_size,
        learning_rate=learning_rate,
        train_clips=len(train_clips),
        val_clips=len(val_clips),
        use_lora=use_lora,
        lora_r=lora_r,
        lora_alpha=lora_alpha,
        lora_dropout=lora_dropout,
    )

    config_path = out_dir / "training_config.json"
    config_path.write_text(
        config.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )

    card_path = out_dir / "model_card.md"
    card_path.write_text(
        _generate_model_card(config),
        encoding="utf-8",
    )

    return FineTuneReport(
        output_dir=str(out_dir),
        base_model=base_model,
        language=language,
        train_clips=len(train_clips),
        val_clips=len(val_clips),
        steps=steps,
        model_path=str(model_path),
        config_path=str(config_path),
        card_path=str(card_path),
    )
