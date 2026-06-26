"""Tests for the Colab eval notebook generator."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from bosesph.colab import ColabEvalConfig, build_eval_notebook, write_eval_notebook


def _cfg(**overrides: object) -> ColabEvalConfig:
    base: dict[str, object] = {
        "dataset_drive_path": "/content/drive/MyDrive/bosesph/dataset_15spk",
        "model_drive_path": "/content/drive/MyDrive/bosesph/model",
    }
    base.update(overrides)
    return ColabEvalConfig(**base)  # type: ignore[arg-type]


def _source(notebook: dict) -> str:
    """Join all cell sources into one searchable string."""
    chunks: list[str] = []
    for cell in notebook["cells"]:
        src = cell["source"]
        chunks.append(src if isinstance(src, str) else "".join(src))
    return "\n".join(chunks)


def test_eval_config_requires_drive_paths() -> None:
    with pytest.raises(Exception):
        ColabEvalConfig()  # type: ignore[call-arg]


def test_eval_config_defaults() -> None:
    cfg = _cfg()
    assert cfg.base_model == "openai/whisper-small"
    assert cfg.language == "tl"
    assert cfg.eval_language == "kapampangan"
    assert cfg.split == "test"
    assert cfg.baseline_name == "Baseline Whisper Small"
    assert cfg.finetuned_name == "Fine-tuned Whisper"
    assert cfg.baseline_limit is None
    assert cfg.repo_ref == "main"


def test_build_eval_notebook_is_valid_nbformat_v4() -> None:
    nb = build_eval_notebook(_cfg())
    reparsed = json.loads(json.dumps(nb))
    assert reparsed["nbformat"] == 4
    assert "nbformat_minor" in reparsed
    assert isinstance(reparsed["cells"], list)
    assert reparsed["metadata"]["accelerator"] == "GPU"


def test_build_eval_notebook_has_9_cells() -> None:
    nb = build_eval_notebook(_cfg())
    assert len(nb["cells"]) == 9


def test_eval_cells_have_required_fields() -> None:
    nb = build_eval_notebook(_cfg())
    for cell in nb["cells"]:
        assert cell["cell_type"] in {"markdown", "code"}
        assert "source" in cell
        if cell["cell_type"] == "code":
            assert cell.get("outputs") == []
            assert cell.get("execution_count") is None


def test_eval_notebook_installs_asr_extras_not_train() -> None:
    src = _source(build_eval_notebook(_cfg()))
    assert "bosesph-toolkit[asr]" in src
    assert "bosesph-toolkit[train]" not in src


def test_eval_notebook_mounts_drive() -> None:
    src = _source(build_eval_notebook(_cfg()))
    assert "drive.mount" in src


def test_eval_notebook_bakes_drive_paths() -> None:
    cfg = _cfg(
        dataset_drive_path="/content/drive/MyDrive/mydata",
        model_drive_path="/content/drive/MyDrive/mymodel",
    )
    src = _source(build_eval_notebook(cfg))
    assert "/content/drive/MyDrive/mydata" in src
    assert "/content/drive/MyDrive/mymodel" in src


def test_eval_notebook_bakes_baseline_model_and_language() -> None:
    cfg = _cfg(base_model="openai/whisper-medium", language="fil")
    src = _source(build_eval_notebook(cfg))
    assert "openai/whisper-medium" in src
    assert "fil" in src


def test_eval_notebook_baseline_transcribe_includes_limit_when_set() -> None:
    src = _source(build_eval_notebook(_cfg(baseline_limit=300)))
    assert "--limit 300" in src


def test_eval_notebook_baseline_transcribe_no_limit_by_default() -> None:
    src = _source(build_eval_notebook(_cfg()))
    assert "--limit" not in src


def test_eval_notebook_bakes_model_names() -> None:
    cfg = _cfg(baseline_name="My Baseline", finetuned_name="My Finetuned")
    src = _source(build_eval_notebook(cfg))
    assert "My Baseline" in src
    assert "My Finetuned" in src


def test_eval_notebook_bakes_eval_language() -> None:
    src = _source(build_eval_notebook(_cfg(eval_language="tagalog")))
    assert "tagalog" in src


def test_eval_notebook_displays_comparison_inline() -> None:
    src = _source(build_eval_notebook(_cfg()))
    assert "comparison.md" in src


def test_eval_notebook_runs_compare_command() -> None:
    src = _source(build_eval_notebook(_cfg()))
    assert "bosesph compare" in src
    assert "baseline_results" in src
    assert "finetuned_results" in src


def test_eval_notebook_pip_installs_from_repo() -> None:
    cfg = _cfg(repo_url="https://example.com/repo.git", repo_ref="v2")
    src = _source(build_eval_notebook(cfg))
    assert "git+https://example.com/repo.git@v2" in src


def test_write_eval_notebook_writes_valid_ipynb(tmp_path: Path) -> None:
    out = tmp_path / "nested" / "eval.ipynb"
    result = write_eval_notebook(_cfg(), out)
    assert result == out
    assert out.is_file()
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded["nbformat"] == 4


def test_eval_notebook_does_not_import_torch() -> None:
    import bosesph.colab as colab_mod
    assert "torch" not in dir(colab_mod)
    assert "transformers" not in dir(colab_mod)


# ---------------------------------------------------------------------------
# CLI tests (added in Task 2)
# ---------------------------------------------------------------------------

from bosesph.cli import main


def test_cli_export_eval_colab_generates_notebook(tmp_path: Path) -> None:
    out = tmp_path / "eval.ipynb"
    exit_code = main(
        [
            "export-eval-colab",
            "--dataset-drive-path", "/content/drive/MyDrive/bosesph/dataset_15spk",
            "--model-drive-path", "/content/drive/MyDrive/bosesph/model_tl",
            "--output", str(out),
            "--repo-ref", "feature-eval",
        ]
    )
    assert exit_code == 0
    assert out.is_file()
    nb = json.loads(out.read_text(encoding="utf-8"))
    assert nb["nbformat"] == 4
    src = _source(nb)
    assert "/content/drive/MyDrive/bosesph/dataset_15spk" in src
    assert "/content/drive/MyDrive/bosesph/model_tl" in src
    assert "@feature-eval" in src


def test_cli_export_eval_colab_defaults(tmp_path: Path) -> None:
    out = tmp_path / "eval.ipynb"
    exit_code = main(
        [
            "export-eval-colab",
            "--dataset-drive-path", "/d/data",
            "--model-drive-path", "/d/model",
            "--output", str(out),
        ]
    )
    assert exit_code == 0
    src = _source(json.loads(out.read_text(encoding="utf-8")))
    assert "openai/whisper-small" in src
    assert "kapampangan" in src
    assert "Baseline Whisper Small" in src
    assert "--limit" not in src


def test_cli_export_eval_colab_with_baseline_limit(tmp_path: Path) -> None:
    out = tmp_path / "eval.ipynb"
    exit_code = main(
        [
            "export-eval-colab",
            "--dataset-drive-path", "/d/data",
            "--model-drive-path", "/d/model",
            "--baseline-limit", "300",
            "--output", str(out),
        ]
    )
    assert exit_code == 0
    src = _source(json.loads(out.read_text(encoding="utf-8")))
    assert "--limit 300" in src


def test_cli_export_eval_colab_missing_required_args() -> None:
    # Missing --model-drive-path should cause argparse to error (exit code 2).
    exit_code = main(["export-eval-colab", "--dataset-drive-path", "/d/data"])
    assert exit_code == 2
