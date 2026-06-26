"""Generate a self-contained Google Colab fine-tuning notebook.

Colab has no official API for submitting jobs, so instead of driving it
remotely we emit a ready-to-run ``.ipynb``. The notebook installs ``bosesph``
from GitHub and calls the existing :func:`bosesph.finetune.finetune_model` on
Colab's GPU.

Two ways to get the dataset onto the Colab VM are supported:

- **Drive folder** (default): mount Google Drive and read an unzipped dataset
  folder; the trained model is written back to Drive.
- **Drive zip link** (``gdrive_zip_id``): download a zipped dataset from a Google
  Drive share link with ``gdown`` (no mount), unzip it to the VM's local disk,
  train, then download the model as a zip. Faster I/O and no Drive mount.

This module is intentionally dependency-free: an ``.ipynb`` is just JSON, so it
is built with the stdlib ``json`` module and needs none of the heavy ``[train]``
extras (torch/transformers). Generating a notebook works on a base install.
"""

from __future__ import annotations

import json
import re
import textwrap
from pathlib import Path
from typing import Any

from pydantic import BaseModel

NBFORMAT = 4
NBFORMAT_MINOR = 5

# Editable Drive base used to derive per-dataset paths in the CLI.
DEFAULT_DRIVE_BASE = "/content/drive/MyDrive/bosesph"
DEFAULT_REPO_URL = "https://github.com/klydddd/asteria-classmates.git"
DEFAULT_REPO_REF = "main"

# Where the zip is downloaded/unzipped and where output is written on the VM.
_LOCAL_DATA_ROOT = "/content/data"
_LOCAL_OUTPUT_DIR = "/content/output"


class ColabExportConfig(BaseModel):
    """Everything needed to render a Colab fine-tuning notebook.

    Mirrors the training parameters of
    :func:`bosesph.finetune.finetune_model` plus Colab-specific fields for the
    GitHub install source and the dataset transfer method.
    """

    # Training parameters (mirrors finetune_model).
    base_model: str
    language: str | None
    epochs: int
    max_steps: int | None
    batch_size: int
    learning_rate: float
    train_split: str
    eval_split: str
    gradient_checkpointing: bool
    optim: str
    use_lora: bool
    lora_r: int
    lora_alpha: int
    lora_dropout: float

    # Colab-specific.
    repo_url: str = DEFAULT_REPO_URL
    repo_ref: str = DEFAULT_REPO_REF
    drive_dataset_path: str
    drive_output_path: str
    fp16: bool = True
    # When set, download a zipped dataset from this Google Drive file ID with
    # gdown instead of mounting Drive.
    gdrive_zip_id: str | None = None


def parse_drive_file_id(value: str) -> str:
    """Extract a Google Drive file ID from a share link (or pass through an ID).

    Handles ``/file/d/<id>/...`` and ``?id=<id>`` URL forms; if ``value`` has no
    recognizable URL structure it is returned stripped as-is (already an ID).
    """
    match = re.search(r"/file/d/([A-Za-z0-9_-]+)", value)
    if match:
        return match.group(1)
    match = re.search(r"[?&]id=([A-Za-z0-9_-]+)", value)
    if match:
        return match.group(1)
    return value.strip()


# ---------------------------------------------------------------------------
# Cell helpers
# ---------------------------------------------------------------------------


def _markdown_cell(source: str) -> dict[str, Any]:
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": source,
    }


def _code_cell(source: str) -> dict[str, Any]:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": source,
    }


# ---------------------------------------------------------------------------
# Notebook assembly
# ---------------------------------------------------------------------------


def _pip_install_spec(config: ColabExportConfig) -> str:
    return f"git+{config.repo_url}@{config.repo_ref}#egg=bosesph-toolkit[train]"


def _config_block(config: ColabExportConfig) -> str:
    """Render the editable hyperparameter cell (baked from CLI args)."""
    return textwrap.dedent(
        f"""\
        # === Training hyperparameters (edit as needed) ===
        base_model = {config.base_model!r}
        language = {config.language!r}
        epochs = {config.epochs!r}
        max_steps = {config.max_steps!r}
        batch_size = {config.batch_size!r}
        learning_rate = {config.learning_rate!r}
        train_split = {config.train_split!r}
        eval_split = {config.eval_split!r}
        gradient_checkpointing = {config.gradient_checkpointing!r}
        optim = {config.optim!r}
        use_lora = {config.use_lora!r}
        lora_r = {config.lora_r!r}
        lora_alpha = {config.lora_alpha!r}
        lora_dropout = {config.lora_dropout!r}
        fp16 = {config.fp16!r}
        """
    )


def _intro_markdown(config: ColabExportConfig) -> dict[str, Any]:
    if config.gdrive_zip_id:
        prep = textwrap.dedent(
            f"""\
            **Before you run:**
            1. The dataset zip is downloaded automatically from your Google Drive
               share link (file ID `{config.gdrive_zip_id}`). Make sure the link
               is shared as **"Anyone with the link"**.
            2. Set the runtime to GPU: **Runtime → Change runtime type → GPU**.
            3. Run all cells (**Runtime → Run all**).

            The trained model is zipped and downloaded to your machine at the end
            (no Drive mount needed).
            """
        )
    else:
        prep = textwrap.dedent(
            f"""\
            **Before you run:**
            1. Upload your built dataset folder to Google Drive at:
               `{config.drive_dataset_path}`
               (it should contain `{config.train_split}.csv`,
               `{config.eval_split}.csv`, and the audio files).
            2. Set the runtime to GPU: **Runtime → Change runtime type → GPU**.
            3. Run all cells (**Runtime → Run all**).

            The trained model is written back to Drive at:
            `{config.drive_output_path}`
            """
        )
    return _markdown_cell(
        "# BosesPH Fine-Tuning on Google Colab\n\n"
        "This notebook fine-tunes a Whisper model on a BosesPH dataset using "
        "Colab's GPU. Generated by `bosesph export-colab`.\n\n"
        f"{prep}\n"
        f"> If the repo `{config.repo_url}` is private, change the install cell "
        "to include a GitHub token, e.g. `git+https://<TOKEN>@github.com/...`."
    )


def _data_source_cell(config: ColabExportConfig) -> dict[str, Any]:
    """Cell that makes the dataset available and defines dataset_dir/output_dir."""
    if config.gdrive_zip_id:
        return _code_cell(
            textwrap.dedent(
                f"""\
                # Download the zipped dataset from Google Drive (no mount needed).
                import glob
                import os

                !pip install -q gdown
                import gdown

                gdown.download(
                    id={config.gdrive_zip_id!r},
                    output="/content/dataset.zip",
                    quiet=False,
                )
                !unzip -q -o /content/dataset.zip -d {_LOCAL_DATA_ROOT}

                # Locate the dataset folder (the one containing the train split CSV).
                matches = glob.glob(
                    f"{_LOCAL_DATA_ROOT}/**/{{train_split}}.csv", recursive=True
                )
                assert matches, (
                    f"{{train_split}}.csv not found in the zip — check its contents"
                )
                dataset_dir = os.path.dirname(matches[0])
                output_dir = {_LOCAL_OUTPUT_DIR!r}
                print("dataset_dir =", dataset_dir)
                """
            )
        )
    return _code_cell(
        textwrap.dedent(
            f"""\
            # Mount Google Drive (dataset in / trained model out).
            from google.colab import drive

            drive.mount('/content/drive')
            dataset_dir = {config.drive_dataset_path!r}
            output_dir = {config.drive_output_path!r}
            """
        )
    )


def _finetune_cell() -> dict[str, Any]:
    return _code_cell(
        textwrap.dedent(
            """\
            # Run fine-tuning on the GPU.
            from bosesph.finetune import finetune_model

            report = finetune_model(
                dataset_dir,
                output_dir,
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
                fp16=fp16,
                progress_fn=print,
            )

            print()
            print("Fine-tuning complete.")
            print("Model saved to:", report.model_path)
            print("Config:", report.config_path)
            print("Model card:", report.card_path)
            """
        )
    )


def _download_output_cell() -> dict[str, Any]:
    return _code_cell(
        textwrap.dedent(
            """\
            # Zip the fine-tuned model and download it to your machine.
            import shutil

            from google.colab import files

            archive = shutil.make_archive("/content/finetuned_model", "zip", output_dir)
            print("Created", archive)
            files.download(archive)
            """
        )
    )


def _done_markdown(config: ColabExportConfig) -> dict[str, Any]:
    if config.gdrive_zip_id:
        return _markdown_cell(
            textwrap.dedent(
                """\
                ## Done

                The fine-tuned model was zipped and downloaded as
                `finetuned_model.zip`. It contains:

                - `model/` — the merged model + processor (load with
                  `transformers.pipeline`).
                - `model_card.md` — generated model card.
                - `training_config.json` — the exact training configuration.

                **Next steps:** unzip it locally, then evaluate it and run
                `bosesph compare` against your baseline.
                """
            )
        )
    return _markdown_cell(
        textwrap.dedent(
            f"""\
            ## Done

            Your fine-tuned model is in Drive at `{config.drive_output_path}`:

            - `model/` — the merged model + processor (load with
              `transformers.pipeline`).
            - `model_card.md` — generated model card.
            - `training_config.json` — the exact training configuration.

            **Next steps:** download the `model/` directory, then evaluate it
            locally and run `bosesph compare` against your baseline.
            """
        )
    )


def build_notebook(config: ColabExportConfig) -> dict[str, Any]:
    """Build the Colab notebook as an nbformat-v4 dict."""
    cells: list[dict[str, Any]] = [
        _intro_markdown(config),
        _code_cell("# Check the assigned GPU.\n!nvidia-smi"),
        _code_cell(
            "# Install the BosesPH toolkit (with training extras) from GitHub.\n"
            f'!pip install -q "{_pip_install_spec(config)}"\n'
            "# Colab preinstalls an old torchao that peft rejects on import; we\n"
            "# don't use torchao, so remove it to avoid an ImportError.\n"
            "!pip uninstall -y torchao"
        ),
        _code_cell(_config_block(config)),
        _data_source_cell(config),
        _finetune_cell(),
    ]
    if config.gdrive_zip_id:
        cells.append(_download_output_cell())
    cells.append(_done_markdown(config))

    return {
        "cells": cells,
        "metadata": {
            "accelerator": "GPU",
            "colab": {"provenance": []},
            "kernelspec": {
                "display_name": "Python 3",
                "name": "python3",
            },
            "language_info": {"name": "python"},
        },
        "nbformat": NBFORMAT,
        "nbformat_minor": NBFORMAT_MINOR,
    }


def write_notebook(config: ColabExportConfig, output_path: str | Path) -> Path:
    """Write the generated notebook to ``output_path`` and return the path."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    notebook = build_notebook(config)
    out.write_text(json.dumps(notebook, indent=1) + "\n", encoding="utf-8")
    return out
