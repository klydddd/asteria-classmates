# Fine-Tuning Default Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Change three fine-tuning defaults — language token, base model size, and LoRA rank — across the CLI, service layer, and API to improve out-of-the-box ASR quality for Kapampangan.

**Architecture:** All defaults live in four files: `finetune.py` (core service), `cli.py` (CLI parser), `colab.py` (Colab config mirror), and `api/models.py` (API request schema). Each file is updated independently; no new files, no new commands, no interface changes beyond type widening `str → str | None` for `language`.

**Tech Stack:** Python 3.10+, Pydantic v2, argparse, pytest

## Global Constraints

- Python 3.10+ only — `str | None` union syntax (not `Optional[str]`) throughout
- Pydantic v2 — use `model_dump_json` / `model_validate_json`, not v1 `.json()` / `.parse_raw()`
- No new files, no new CLI subcommands, no new API endpoints
- All tests in existing test files; do not create new test files
- Run `ruff check .` and `black --check .` before each commit; fix any violations inline
- Run `pytest` (full suite) before the final commit to catch cross-task regressions

---

### Task 1: Update `finetune.py` — types, defaults, model card

**Files:**
- Modify: `src/bosesph/finetune.py`
- Test: `tests/test_finetune.py`

**Interfaces:**
- Produces: `FineTuneConfig(language: str | None, lora_r: int = 32, lora_alpha: int = 64)`
- Produces: `FineTuneReport(language: str | None)`
- Produces: `finetune_model(..., base_model="openai/whisper-small", language: str | None = None, lora_r=32, lora_alpha=64)`
- Produces: `_generate_model_card(config)` renders "unconstrained" when `config.language is None`

- [ ] **Step 1: Write failing tests**

Add the following six tests at the bottom of the `TestFineTuneConfig` class in `tests/test_finetune.py` (after the existing `test_lora_defaults_when_omitted` test, but REPLACE that test with the updated version below):

```python
# Replace the existing test_lora_defaults_when_omitted:
def test_lora_defaults_when_omitted(self) -> None:
    config = FineTuneConfig(
        base_model="openai/whisper-small",
        language=None,
        epochs=3,
        max_steps=None,
        batch_size=8,
        learning_rate=1e-5,
        train_clips=100,
        val_clips=0,
    )
    assert config.use_lora is False
    assert config.lora_r == 32   # updated from 16
    assert config.lora_alpha == 64  # updated from 32

def test_config_language_none_roundtrip(self) -> None:
    config = FineTuneConfig(
        base_model="openai/whisper-small",
        language=None,
        epochs=3,
        max_steps=None,
        batch_size=8,
        learning_rate=1e-5,
        train_clips=100,
        val_clips=15,
    )
    restored = FineTuneConfig.model_validate_json(config.model_dump_json())
    assert restored.language is None

def test_config_lora_new_defaults(self) -> None:
    config = FineTuneConfig(
        base_model="openai/whisper-small",
        language=None,
        epochs=3,
        max_steps=None,
        batch_size=8,
        learning_rate=1e-5,
        train_clips=100,
        val_clips=0,
    )
    assert config.lora_r == 32
    assert config.lora_alpha == 64
```

Add these two tests at the bottom of the `TestGenerateModelCard` class:

```python
def test_model_card_none_language_uses_unconstrained(self) -> None:
    config = FineTuneConfig(
        base_model="openai/whisper-small",
        language=None,
        epochs=3,
        max_steps=None,
        batch_size=8,
        learning_rate=1e-5,
        train_clips=100,
        val_clips=15,
    )
    card = _generate_model_card(config)
    assert "unconstrained" in card
    assert "Tagalog" not in card

def test_model_card_explicit_language_shows_token(self) -> None:
    config = FineTuneConfig(
        base_model="openai/whisper-small",
        language="tl",
        epochs=3,
        max_steps=None,
        batch_size=8,
        learning_rate=1e-5,
        train_clips=100,
        val_clips=15,
    )
    card = _generate_model_card(config)
    assert "`tl`" in card
```

Add this test inside the `TestFinetuneCLI` class:

```python
def test_finetune_parser_new_defaults(self) -> None:
    from bosesph.cli import build_parser

    args = build_parser().parse_args(
        ["finetune", "/tmp/ds", "--output", "/tmp/out"]
    )
    assert args.base_model == "openai/whisper-small"
    assert args.language is None
    assert args.lora_r == 32
    assert args.lora_alpha == 64
```

- [ ] **Step 2: Run tests to confirm they fail**

```
pytest tests/test_finetune.py::TestFineTuneConfig::test_lora_defaults_when_omitted \
       tests/test_finetune.py::TestFineTuneConfig::test_config_language_none_roundtrip \
       tests/test_finetune.py::TestFineTuneConfig::test_config_lora_new_defaults \
       tests/test_finetune.py::TestGenerateModelCard::test_model_card_none_language_uses_unconstrained \
       tests/test_finetune.py::TestGenerateModelCard::test_model_card_explicit_language_shows_token \
       tests/test_finetune.py::TestFinetuneCLI::test_finetune_parser_new_defaults \
       -v
```

Expected: all FAIL (type errors, assertion mismatches).

- [ ] **Step 3: Update `FineTuneConfig` and `FineTuneReport` in `finetune.py`**

In `src/bosesph/finetune.py`, replace the `FineTuneConfig` and `FineTuneReport` class bodies:

```python
class FineTuneConfig(BaseModel):
    """Training configuration persisted as ``training_config.json``."""

    base_model: str
    language: str | None
    epochs: int
    max_steps: int | None
    batch_size: int
    learning_rate: float
    train_clips: int
    val_clips: int
    use_lora: bool = False
    lora_r: int = 32
    lora_alpha: int = 64
    lora_dropout: float = 0.05


class FineTuneReport(BaseModel):
    """Result summary returned by the fine-tune function."""

    output_dir: str
    base_model: str
    language: str | None
    train_clips: int
    val_clips: int
    steps: int
    model_path: str
    config_path: str
    card_path: str
```

- [ ] **Step 4: Update `finetune_model` signature defaults**

In `src/bosesph/finetune.py`, replace the `finetune_model` signature (lines starting at `def finetune_model(`):

```python
def finetune_model(
    dataset_dir: str | Path,
    output_dir: str | Path,
    *,
    base_model: str = "openai/whisper-small",
    language: str | None = None,
    epochs: int = 3,
    max_steps: int | None = None,
    batch_size: int = 8,
    learning_rate: float = 1e-5,
    train_split: str = "train",
    eval_split: str = "validation",
    gradient_checkpointing: bool = False,
    optim: str = "adamw_torch",
    fp16: bool = False,
    use_lora: bool = True,
    lora_r: int = 32,
    lora_alpha: int = 64,
    lora_dropout: float = 0.05,
    progress_fn: Callable[[str], None] | None = None,
) -> FineTuneReport:
```

- [ ] **Step 5: Update `_generate_model_card` in `finetune.py`**

Replace the `_generate_model_card` function body. Add a pre-computation block before the `return` statement and update the two language-dependent strings:

```python
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

    lang_display = config.language if config.language is not None else "unconstrained"
    if config.language is None:
        lang_limitation = (
            "Kapampangan is not a natively supported Whisper language. "
            "This model decodes without a forced language token (unconstrained), "
            "which avoids language-specific tokenisation artefacts but may "
            "produce output in another language on ambiguous audio."
        )
    else:
        lang_limitation = (
            f"Kapampangan is not a natively supported Whisper language. This model "
            f"uses the `{config.language}` language token as a proxy, "
            f"which may introduce tokenisation artefacts."
        )

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
        | Language token | {lang_display} |
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

        - {lang_limitation}
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
```

- [ ] **Step 6: Run failing tests to confirm they now pass**

```
pytest tests/test_finetune.py::TestFineTuneConfig::test_lora_defaults_when_omitted \
       tests/test_finetune.py::TestFineTuneConfig::test_config_language_none_roundtrip \
       tests/test_finetune.py::TestFineTuneConfig::test_config_lora_new_defaults \
       tests/test_finetune.py::TestGenerateModelCard::test_model_card_none_language_uses_unconstrained \
       tests/test_finetune.py::TestGenerateModelCard::test_model_card_explicit_language_shows_token \
       tests/test_finetune.py::TestFinetuneCLI::test_finetune_parser_new_defaults \
       -v
```

Expected: all PASS.

- [ ] **Step 7: Run the full finetune test file to check for regressions**

```
pytest tests/test_finetune.py -v
```

Expected: all PASS.

- [ ] **Step 8: Lint and format check**

```
ruff check . && black --check .
```

Expected: no errors.

- [ ] **Step 9: Commit**

```bash
git add src/bosesph/finetune.py tests/test_finetune.py
git commit -m "feat: update finetune defaults — whisper-small, unconstrained language, lora_r=32"
```

---

### Task 2: Update `cli.py` — parser defaults and type hints

**Files:**
- Modify: `src/bosesph/cli.py`
- Test: `tests/test_finetune.py` (test added in Task 1 covers `finetune` parser)

**Interfaces:**
- Consumes: `finetune_model(language: str | None)` from Task 1
- Produces: `build_parser()` returns parser where `finetune` and `export-colab` subcommands default to `base_model="openai/whisper-small"`, `language=None`, `lora_r=32`, `lora_alpha=64`

- [ ] **Step 1: Update `finetune` subparser defaults in `cli.py`**

In `src/bosesph/cli.py`, apply these four changes inside the `finetune_parser` block:

```python
# --base-model default
finetune_parser.add_argument(
    "--base-model",
    default="openai/whisper-small",
    dest="base_model",
    help="HuggingFace model ID to fine-tune",
)

# --language default (None = unconstrained decoding)
finetune_parser.add_argument(
    "--language",
    default=None,
    help="language token for Whisper generation config (default: None for unconstrained decoding)",
)

# --lora-r default
finetune_parser.add_argument(
    "--lora-r",
    type=int,
    default=32,
    dest="lora_r",
    help="LoRA rank (default: 32)",
)

# --lora-alpha default
finetune_parser.add_argument(
    "--lora-alpha",
    type=int,
    default=64,
    dest="lora_alpha",
    help="LoRA alpha scaling factor (default: 64)",
)
```

- [ ] **Step 2: Update `export-colab` subparser defaults in `cli.py`**

Apply the same four changes in the `export_colab_parser` block:

```python
export_colab_parser.add_argument(
    "--base-model",
    default="openai/whisper-small",
    dest="base_model",
    help="HuggingFace model ID to fine-tune",
)

export_colab_parser.add_argument(
    "--language",
    default=None,
    help="language token for Whisper generation config (default: None for unconstrained decoding)",
)

export_colab_parser.add_argument(
    "--lora-r",
    type=int,
    default=32,
    dest="lora_r",
    help="LoRA rank (default: 32)",
)

export_colab_parser.add_argument(
    "--lora-alpha",
    type=int,
    default=64,
    dest="lora_alpha",
    help="LoRA alpha scaling factor (default: 64)",
)
```

- [ ] **Step 3: Update `_run_finetune` and `_run_export_colab` type hints**

In `_run_finetune`, change `language: str` → `language: str | None`.
In `_run_export_colab`, change `language: str` → `language: str | None`.

- [ ] **Step 4: Run the parser defaults test from Task 1**

```
pytest tests/test_finetune.py::TestFinetuneCLI::test_finetune_parser_new_defaults -v
```

Expected: PASS (it was already added in Task 1 Step 1).

- [ ] **Step 5: Run the full finetune and cli test files**

```
pytest tests/test_finetune.py tests/test_cli.py tests/test_colab.py -v
```

Expected: all PASS.

- [ ] **Step 6: Lint and format check**

```
ruff check . && black --check .
```

Expected: no errors.

- [ ] **Step 7: Commit**

```bash
git add src/bosesph/cli.py
git commit -m "feat: update CLI defaults — whisper-small, unconstrained language, lora_r=32"
```

---

### Task 3: Update `api/models.py` and `colab.py` — type and defaults

**Files:**
- Modify: `src/bosesph/api/models.py`
- Modify: `src/bosesph/colab.py`
- Test: `tests/test_api.py`

**Interfaces:**
- Consumes: Nothing new from Tasks 1–2
- Produces: `TrainRequest(base_model="openai/whisper-small", language: str | None = None)`
- Produces: `ColabExportConfig(language: str | None)`

- [ ] **Step 1: Write a failing test for `TrainRequest` defaults**

Add the following test to `tests/test_api.py`, inside a new class `TestTrainRequestDefaults` at the bottom of the file:

```python
class TestTrainRequestDefaults:
    def test_train_request_new_defaults(self) -> None:
        from bosesph.api.models import TrainRequest

        req = TrainRequest(dataset="ds", output="out")
        assert req.base_model == "openai/whisper-small"
        assert req.language is None
```

- [ ] **Step 2: Run the test to confirm it fails**

```
pytest tests/test_api.py::TestTrainRequestDefaults::test_train_request_new_defaults -v
```

Expected: FAIL — `assert req.base_model == "openai/whisper-small"` fails (currently `"whisper-tiny"`).

- [ ] **Step 3: Update `api/models.py`**

In `src/bosesph/api/models.py`, update the `TrainRequest` model:

```python
class TrainRequest(BaseModel):
    """Body for ``POST /train``."""

    dataset: str = Field(description="Relative path to built dataset directory.")
    output: str = Field(description="Relative path for model output.")
    base_model: str = "openai/whisper-small"
    language: str | None = None
    epochs: int = 3
    max_steps: int | None = None
    batch_size: int = 8
    learning_rate: float = 1e-5
    train_split: str = "train"
    eval_split: str = "validation"
```

- [ ] **Step 4: Update `colab.py` type annotation**

In `src/bosesph/colab.py`, change the `language` field on `ColabExportConfig`:

```python
language: str | None
```

(It is currently `language: str` with no default — it's a required field. The type widens to `str | None` without adding a default, so callers that pass `None` now type-check correctly.)

- [ ] **Step 5: Run the failing test to confirm it passes**

```
pytest tests/test_api.py::TestTrainRequestDefaults::test_train_request_new_defaults -v
```

Expected: PASS.

- [ ] **Step 6: Run the full test suite**

```
pytest -v
```

Expected: all PASS. If any test fails, fix it before committing.

- [ ] **Step 7: Lint and format check**

```
ruff check . && black --check .
```

Expected: no errors.

- [ ] **Step 8: Commit**

```bash
git add src/bosesph/api/models.py src/bosesph/colab.py tests/test_api.py
git commit -m "feat: update API and Colab defaults — whisper-small, unconstrained language"
```
