"""Tests for the Google Colab notebook generator."""

from __future__ import annotations

import json
from pathlib import Path

from bosesph.cli import main
from bosesph.colab import (
    ColabExportConfig,
    build_notebook,
    parse_drive_file_id,
    write_notebook,
)


def _config(**overrides: object) -> ColabExportConfig:
    base: dict[str, object] = {
        "base_model": "openai/whisper-tiny",
        "language": "tl",
        "epochs": 3,
        "max_steps": None,
        "batch_size": 8,
        "learning_rate": 1e-5,
        "train_split": "train",
        "eval_split": "validation",
        "gradient_checkpointing": False,
        "optim": "adamw_torch",
        "use_lora": True,
        "lora_r": 16,
        "lora_alpha": 32,
        "lora_dropout": 0.05,
        "repo_url": "https://github.com/klydddd/asteria-classmates.git",
        "repo_ref": "main",
        "drive_dataset_path": "/content/drive/MyDrive/bosesph/dataset",
        "drive_output_path": "/content/drive/MyDrive/bosesph/dataset-finetuned",
        "fp16": True,
    }
    base.update(overrides)
    return ColabExportConfig(**base)  # type: ignore[arg-type]


def _config_source(notebook: dict) -> str:
    """Join every cell's source into one searchable string."""
    chunks: list[str] = []
    for cell in notebook["cells"]:
        source = cell["source"]
        chunks.append(source if isinstance(source, str) else "".join(source))
    return "\n".join(chunks)


def test_build_notebook_is_valid_nbformat_v4() -> None:
    notebook = build_notebook(_config())

    # Round-trips as JSON.
    reparsed = json.loads(json.dumps(notebook))
    assert reparsed["nbformat"] == 4
    assert "nbformat_minor" in reparsed
    assert isinstance(reparsed["cells"], list)
    assert reparsed["cells"]
    assert isinstance(reparsed["metadata"], dict)


def test_notebook_requests_gpu_accelerator() -> None:
    notebook = build_notebook(_config())
    assert notebook["metadata"].get("accelerator") == "GPU"


def test_cells_have_required_fields() -> None:
    notebook = build_notebook(_config())
    for cell in notebook["cells"]:
        assert cell["cell_type"] in {"markdown", "code"}
        assert "source" in cell
        if cell["cell_type"] == "code":
            assert cell.get("outputs") == []
            assert cell.get("execution_count") is None


def test_notebook_bakes_hyperparameters() -> None:
    source = _config_source(
        build_notebook(_config(epochs=7, lora_r=24, base_model="openai/whisper-small"))
    )
    assert "epochs = 7" in source
    assert "lora_r = 24" in source
    assert "openai/whisper-small" in source
    assert "/content/drive/MyDrive/bosesph/dataset" in source
    assert "fp16 = True" in source


def test_notebook_pip_installs_from_resolved_repo() -> None:
    source = _config_source(
        build_notebook(_config(repo_url="https://example.com/x.git", repo_ref="dev"))
    )
    assert "git+https://example.com/x.git@dev" in source
    assert "bosesph-toolkit[train]" in source


def test_notebook_mounts_drive_and_checks_gpu() -> None:
    source = _config_source(build_notebook(_config()))
    assert "drive.mount" in source
    assert "nvidia-smi" in source


def test_notebook_removes_incompatible_torchao() -> None:
    # Colab's preinstalled torchao breaks peft import; the notebook must drop it.
    source = _config_source(build_notebook(_config()))
    assert "pip uninstall -y torchao" in source


def test_lora_and_gradient_checkpointing_toggles_reflected() -> None:
    source = _config_source(build_notebook(_config(use_lora=False)))
    assert "use_lora = False" in source

    source = _config_source(build_notebook(_config(gradient_checkpointing=True)))
    assert "gradient_checkpointing = True" in source


def test_write_notebook_writes_valid_ipynb(tmp_path: Path) -> None:
    out = tmp_path / "nested" / "colab.ipynb"
    result = write_notebook(_config(), out)

    assert result == out
    assert out.is_file()
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded["nbformat"] == 4


def test_cli_export_colab_generates_notebook(tmp_path: Path, capsys: object) -> None:
    dataset = tmp_path / "mydataset"
    dataset.mkdir()
    out = tmp_path / "run.ipynb"

    exit_code = main(
        [
            "export-colab",
            str(dataset),
            "--output",
            str(out),
            "--epochs",
            "5",
            "--repo-ref",
            "feature-x",
        ]
    )

    assert exit_code == 0
    assert out.is_file()
    notebook = json.loads(out.read_text(encoding="utf-8"))
    assert notebook["nbformat"] == 4
    source = _config_source(notebook)
    assert "epochs = 5" in source
    # Drive paths derived from the dataset folder name.
    assert "/content/drive/MyDrive/bosesph/mydataset" in source
    assert "@feature-x" in source
    captured = capsys.readouterr().out  # type: ignore[attr-defined]
    assert str(out) in captured


def test_cli_export_colab_missing_dataset_is_input_error(tmp_path: Path) -> None:
    out = tmp_path / "run.ipynb"
    exit_code = main(["export-colab", str(tmp_path / "missing"), "--output", str(out)])
    assert exit_code == 2
    assert not out.exists()


def test_parse_drive_file_id() -> None:
    fid = "1kllfMNwiC1rA3dQlJmthLvG-iJgUcGf9"
    assert (
        parse_drive_file_id(f"https://drive.google.com/file/d/{fid}/view?usp=sharing")
        == fid
    )
    assert parse_drive_file_id(f"https://drive.google.com/open?id={fid}") == fid
    assert parse_drive_file_id(fid) == fid


def test_gdrive_zip_notebook_uses_gdown_and_no_mount() -> None:
    fid = "ABC123_-xyz"
    source = _config_source(build_notebook(_config(gdrive_zip_id=fid)))
    assert "gdown" in source
    assert fid in source
    assert "drive.mount" not in source
    # Trains from the unzipped local copy and downloads the model zip.
    assert "/content/data" in source
    assert "files.download" in source


def test_drive_folder_mode_still_mounts_by_default() -> None:
    source = _config_source(build_notebook(_config()))
    assert "drive.mount" in source
    assert "gdown" not in source


def test_cli_export_colab_with_gdrive_zip(tmp_path: Path, capsys: object) -> None:
    out = tmp_path / "run.ipynb"
    fid = "1kllfMNwiC1rA3dQlJmthLvG-iJgUcGf9"
    # Local dataset need not exist when a Drive zip link is given.
    exit_code = main(
        [
            "export-colab",
            str(tmp_path / "no_local_dataset"),
            "--output",
            str(out),
            "--gdrive-zip",
            f"https://drive.google.com/file/d/{fid}/view?usp=sharing",
        ]
    )
    assert exit_code == 0
    source = _config_source(json.loads(out.read_text(encoding="utf-8")))
    assert fid in source
    assert "gdown" in source
    assert "drive.mount" not in source


def test_export_colab_does_not_import_torch() -> None:
    """Generating a notebook must not require the [train] extras."""
    import bosesph.colab as colab_mod

    # The module should not pull torch/transformers into scope.
    assert "torch" not in dir(colab_mod)
    assert "transformers" not in dir(colab_mod)
