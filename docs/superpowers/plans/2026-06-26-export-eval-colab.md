# export-eval-colab Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `bosesph export-eval-colab` CLI command that generates a ready-to-run Colab notebook for GPU-accelerated ASR evaluation of a baseline vs. fine-tuned Whisper model.

**Architecture:** A new `ColabEvalConfig` Pydantic model and `build_eval_notebook` / `write_eval_notebook` functions are added to the existing `colab.py` module, following the same patterns as `ColabExportConfig` / `build_notebook`. The CLI gets a new `export-eval-colab` subcommand in `cli.py` that constructs the config and calls `write_eval_notebook`.

**Tech Stack:** Python 3.10+, Pydantic v2, stdlib `json` / `pathlib` / `textwrap`, `pytest`.

## Global Constraints

- Python 3.10+ with type hints everywhere
- Pydantic v2 for all models
- `colab.py` must remain dependency-free (no torch/transformers imports at module level) — it's intentionally stdlib-only
- Atomic file writes: write to a temp location then rename (follow existing `write_notebook` pattern — it uses `Path.write_text` which is atomic on the platforms we target; keep the same)
- Exit codes: 0 = success, 2 = input error (match existing CLI conventions)
- Test files use `pytest`; no real audio or PLD data

---

### Task 1: `ColabEvalConfig` model + notebook generator in `colab.py`

**Files:**
- Modify: `src/bosesph/colab.py`
- Create: `tests/test_colab_eval.py`

**Interfaces:**
- Produces:
  - `ColabEvalConfig` — Pydantic v2 model (see fields below)
  - `build_eval_notebook(config: ColabEvalConfig) -> dict[str, Any]`
  - `write_eval_notebook(config: ColabEvalConfig, output_path: str | Path) -> Path`

---

- [ ] **Step 1: Write the failing tests**

Create `tests/test_colab_eval.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/bin/pytest tests/test_colab_eval.py -v 2>&1 | head -40
```

Expected: `ImportError` or `AttributeError` — `ColabEvalConfig`, `build_eval_notebook`, `write_eval_notebook` don't exist yet.

- [ ] **Step 3: Add `ColabEvalConfig` and notebook generator to `colab.py`**

Add the following to `src/bosesph/colab.py`, after the `ColabExportConfig` class (around line 77, before `parse_drive_file_id`):

```python
class ColabEvalConfig(BaseModel):
    """Everything needed to render a Colab evaluation notebook."""

    dataset_drive_path: str
    model_drive_path: str
    base_model: str = "openai/whisper-small"
    language: str | None = "tl"
    eval_language: str = "kapampangan"
    split: str = "test"
    baseline_name: str = "Baseline Whisper Small"
    finetuned_name: str = "Fine-tuned Whisper"
    baseline_limit: int | None = None
    repo_url: str = DEFAULT_REPO_URL
    repo_ref: str = DEFAULT_REPO_REF
```

Then, after the existing `write_notebook` function at the end of the file, add:

```python
# ---------------------------------------------------------------------------
# Eval notebook
# ---------------------------------------------------------------------------


def _eval_transcribe_cell(
    model_source: str,
    output_csv: str,
    config: ColabEvalConfig,
    limit: int | None = None,
) -> dict[str, Any]:
    lang_arg = f" --language {config.language}" if config.language is not None else ""
    limit_arg = f" --limit {limit}" if limit is not None else ""
    return _code_cell(
        f"!bosesph transcribe {{dataset_drive_path}}"
        f" --model {model_source}"
        f"{lang_arg}"
        f" --split {{split}}"
        f" --output {output_csv}"
        f"{limit_arg}"
    )


def _eval_evaluate_cell(
    predictions_csv: str,
    output_dir: str,
    model_name: str,
    config: ColabEvalConfig,
) -> dict[str, Any]:
    return _code_cell(
        f"!bosesph evaluate"
        f" --predictions {predictions_csv}"
        f" --output {output_dir}"
        f" --model-name {model_name!r}"
        f" --language {config.eval_language}"
    )


def build_eval_notebook(config: ColabEvalConfig) -> dict[str, Any]:
    """Build the Colab eval notebook as an nbformat-v4 dict."""
    cells: list[dict[str, Any]] = [
        _code_cell(
            "# Install the BosesPH toolkit (ASR extras only) from GitHub.\n"
            f'!pip install -q "git+{config.repo_url}@{config.repo_ref}#egg=bosesph-toolkit[asr]"'
        ),
        _code_cell(
            "from google.colab import drive\n"
            "drive.mount('/content/drive')"
        ),
        _code_cell(
            textwrap.dedent(f"""\
                # === Config (edit as needed) ===
                dataset_drive_path = {config.dataset_drive_path!r}
                model_drive_path = {config.model_drive_path!r}
                split = {config.split!r}
                """)
        ),
        _eval_transcribe_cell(
            config.base_model,
            "/content/baseline_predictions.csv",
            config,
            limit=config.baseline_limit,
        ),
        _eval_evaluate_cell(
            "/content/baseline_predictions.csv",
            "/content/baseline_results",
            config.baseline_name,
            config,
        ),
        _eval_transcribe_cell(
            "{model_drive_path}",
            "/content/finetuned_predictions.csv",
            config,
        ),
        _eval_evaluate_cell(
            "/content/finetuned_predictions.csv",
            "/content/finetuned_results",
            config.finetuned_name,
            config,
        ),
        _code_cell(
            "!bosesph compare"
            " --baseline /content/baseline_results/results.json"
            " --finetuned /content/finetuned_results/results.json"
            " --output /content/comparison.md"
        ),
        _code_cell(
            "from IPython.display import Markdown, display\n"
            "display(Markdown(open('/content/comparison.md').read()))"
        ),
    ]
    return {
        "cells": cells,
        "metadata": {
            "accelerator": "GPU",
            "colab": {"provenance": []},
            "kernelspec": {"display_name": "Python 3", "name": "python3"},
            "language_info": {"name": "python"},
        },
        "nbformat": NBFORMAT,
        "nbformat_minor": NBFORMAT_MINOR,
    }


def write_eval_notebook(config: ColabEvalConfig, output_path: str | Path) -> Path:
    """Write the generated eval notebook to ``output_path`` and return the path."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    notebook = build_eval_notebook(config)
    out.write_text(json.dumps(notebook, indent=1) + "\n", encoding="utf-8")
    return out
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/pytest tests/test_colab_eval.py -v
```

Expected: all tests pass. If `test_eval_notebook_baseline_transcribe_no_limit_by_default` fails, check that the `limit_arg` logic in `_eval_transcribe_cell` correctly produces an empty string when `limit is None`.

- [ ] **Step 5: Verify existing colab tests still pass**

```bash
.venv/bin/pytest tests/test_colab.py -v
```

Expected: all existing tests pass (we only added to the module, not changed existing code).

- [ ] **Step 6: Commit**

```bash
git add src/bosesph/colab.py tests/test_colab_eval.py
git commit -m "feat: add ColabEvalConfig and write_eval_notebook to colab.py"
```

---

### Task 2: `export-eval-colab` CLI subcommand in `cli.py`

**Files:**
- Modify: `src/bosesph/cli.py`
- Modify: `tests/test_colab_eval.py` (add CLI tests)

**Interfaces:**
- Consumes:
  - `ColabEvalConfig` from `bosesph.colab`
  - `write_eval_notebook(config: ColabEvalConfig, output_path: str | Path) -> Path` from `bosesph.colab`
  - `_resolve_repo_url(url: str | None) -> str` — already in `cli.py`
  - `main(argv: list[str] | None = None) -> int` — already in `cli.py`
- Produces: `bosesph export-eval-colab` CLI subcommand

---

- [ ] **Step 1: Write the failing CLI tests**

Append to `tests/test_colab_eval.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/bin/pytest tests/test_colab_eval.py::test_cli_export_eval_colab_generates_notebook tests/test_colab_eval.py::test_cli_export_eval_colab_defaults tests/test_colab_eval.py::test_cli_export_eval_colab_with_baseline_limit tests/test_colab_eval.py::test_cli_export_eval_colab_missing_required_args -v
```

Expected: all fail — `export-eval-colab` subcommand not yet registered.

- [ ] **Step 3: Add the `export-eval-colab` subparser to `cli.py`**

In `src/bosesph/cli.py`, locate the block starting at line 253 (`export_colab_parser = commands.add_parser(...)`). After the entire `export-colab` parser block ends (after all its `add_argument` calls, before the next parser or the end of the setup function), add:

```python
    export_eval_colab_parser = commands.add_parser(
        "export-eval-colab",
        help="generate a Google Colab notebook to evaluate a fine-tuned Whisper model on GPU",
    )
    export_eval_colab_parser.add_argument(
        "--dataset-drive-path",
        required=True,
        dest="dataset_drive_path",
        help="Google Drive path to the dataset folder (must contain <split>.csv and audio/)",
    )
    export_eval_colab_parser.add_argument(
        "--model-drive-path",
        required=True,
        dest="model_drive_path",
        help="Google Drive path to the fine-tuned model folder",
    )
    export_eval_colab_parser.add_argument(
        "--base-model",
        default="openai/whisper-small",
        dest="base_model",
        help="HuggingFace model ID for the baseline (default: openai/whisper-small)",
    )
    export_eval_colab_parser.add_argument(
        "--language",
        default="tl",
        help="transcription language for Whisper (default: tl)",
    )
    export_eval_colab_parser.add_argument(
        "--eval-language",
        default="kapampangan",
        dest="eval_language",
        help="language label for WER/CER evaluation (default: kapampangan)",
    )
    export_eval_colab_parser.add_argument(
        "--split",
        default="test",
        help="dataset split to evaluate (default: test)",
    )
    export_eval_colab_parser.add_argument(
        "--baseline-name",
        default="Baseline Whisper Small",
        dest="baseline_name",
        help='label for baseline in the comparison report',
    )
    export_eval_colab_parser.add_argument(
        "--finetuned-name",
        default="Fine-tuned Whisper",
        dest="finetuned_name",
        help='label for the fine-tuned model in the comparison report',
    )
    export_eval_colab_parser.add_argument(
        "--baseline-limit",
        type=int,
        default=None,
        dest="baseline_limit",
        help="limit number of samples transcribed for the baseline",
    )
    export_eval_colab_parser.add_argument(
        "--output",
        type=Path,
        default=Path("colab_eval.ipynb"),
        help="output notebook path (default: colab_eval.ipynb)",
    )
    export_eval_colab_parser.add_argument(
        "--repo-url",
        default=None,
        dest="repo_url",
        help="git URL to pip-install bosesph from (default: origin remote)",
    )
    export_eval_colab_parser.add_argument(
        "--repo-ref",
        default="main",
        dest="repo_ref",
        help="git branch/tag/commit to install (default: main)",
    )
```

- [ ] **Step 4: Add `_run_export_eval_colab` handler to `cli.py`**

In `src/bosesph/cli.py`, locate `_run_export_colab` (around line 725). Add the following function directly after it:

```python
def _run_export_eval_colab(
    *,
    dataset_drive_path: str,
    model_drive_path: str,
    base_model: str,
    language: str | None,
    eval_language: str,
    split: str,
    baseline_name: str,
    finetuned_name: str,
    baseline_limit: int | None,
    output: Path,
    repo_url: str | None,
    repo_ref: str,
) -> int:
    from bosesph.colab import ColabEvalConfig, write_eval_notebook

    config = ColabEvalConfig(
        dataset_drive_path=dataset_drive_path,
        model_drive_path=model_drive_path,
        base_model=base_model,
        language=language,
        eval_language=eval_language,
        split=split,
        baseline_name=baseline_name,
        finetuned_name=finetuned_name,
        baseline_limit=baseline_limit,
        repo_url=_resolve_repo_url(repo_url),
        repo_ref=repo_ref,
    )
    write_eval_notebook(config, output)

    print(f"Colab eval notebook written to: {output}")
    print("Next steps:")
    print("  1. Open the notebook in Google Colab and set the runtime to GPU.")
    print("  2. Run all cells — the comparison report is printed in the last cell.")
    return 0
```

- [ ] **Step 5: Wire the handler in `main()`**

In `src/bosesph/cli.py`, locate the dispatch block near line 900 (the series of `if args.command == "..."` checks). Add before the final `return 2`:

```python
    if args.command == "export-eval-colab":
        return _run_export_eval_colab(
            dataset_drive_path=args.dataset_drive_path,
            model_drive_path=args.model_drive_path,
            base_model=args.base_model,
            language=args.language,
            eval_language=args.eval_language,
            split=args.split,
            baseline_name=args.baseline_name,
            finetuned_name=args.finetuned_name,
            baseline_limit=args.baseline_limit,
            output=args.output,
            repo_url=args.repo_url,
            repo_ref=args.repo_ref,
        )
```

- [ ] **Step 6: Run all new CLI tests**

```bash
.venv/bin/pytest tests/test_colab_eval.py -v
```

Expected: all tests pass. If `test_cli_export_eval_colab_missing_required_args` fails with exit code 0 instead of 2, check that the argparse `required=True` on `--model-drive-path` is in place and that the custom `ArgumentParser` in `cli.py` sets `exit_code=2` for usage errors (it should, given the project's `ParserExit` pattern).

- [ ] **Step 7: Run the full test suite**

```bash
.venv/bin/pytest tests/test_colab.py tests/test_colab_eval.py tests/test_cli.py -v
```

Expected: all pass.

- [ ] **Step 8: Commit**

```bash
git add src/bosesph/cli.py tests/test_colab_eval.py
git commit -m "feat: add export-eval-colab CLI command"
```
