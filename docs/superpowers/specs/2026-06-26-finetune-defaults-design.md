# Fine-Tuning Default Improvements Design

**Date:** 2026-06-26
**Branch:** feat/colab-finetuning
**Scope:** Update three default hyperparameters across `finetune.py`, `cli.py`, and `api/models.py` to improve 5-speaker model baseline quality.

## Motivation

Benchmarking revealed the 5-speaker LoRA model (WER 79.95%, CER 29.26%) outperforms the 15-speaker model, but both are still far from useful. Three root causes were identified that can be fixed by changing defaults:

1. **Wrong language token** — both models were trained with `language="tl"` (Tagalog), forcing Tagalog phoneme priors on Kapampangan audio during decoding.
2. **Under-powered base model** — `whisper-tiny` (39M params) has limited multilingual capacity for a low-resource language.
3. **Insufficient LoRA rank** — `r=16` limits how much the adapter can shift the model's internal representations.

## Changes

### `src/bosesph/finetune.py`

| Parameter | Old | New | Reason |
|-----------|-----|-----|--------|
| `finetune_model(base_model)` | `"openai/whisper-tiny"` | `"openai/whisper-small"` | 5× more params, stronger multilingual base |
| `finetune_model(language)` | `str = "tl"` | `str \| None = None` | Removes forced Tagalog token; Whisper decodes unconstrained |
| `finetune_model(lora_r)` | `16` | `32` | Doubles adapter capacity |
| `finetune_model(lora_alpha)` | `32` | `64` | Preserves `alpha/r = 2` effective scaling ratio |
| `FineTuneConfig.language` type | `str` | `str \| None` | Matches function signature |
| Model card limitations text | References Tagalog proxy | Describes unconstrained decoding | Accuracy |

The existing line `model.generation_config.language = language` already handles `None` correctly — passing `None` removes the forced language token from the generation config.

### `src/bosesph/cli.py`

Same default updates in both the `finetune` subparser and the `export-colab` subparser (they mirror each other). Updated args:

- `--base-model` default: `"openai/whisper-small"`
- `--language` default: `None`, help text updated
- `--lora-r` default: `32`
- `--lora-alpha` default: `64`

### `src/bosesph/api/models.py`

`TrainRequest` updated:

- `base_model: str = "openai/whisper-small"`
- `language: str | None = None`

## What Does Not Change

- LoRA dropout stays at `0.05`
- Epochs stay at `3` (separate improvement — not in scope)
- Learning rate stays at `1e-5`
- Target modules (decoder-only LoRA) unchanged
- All other CLI args and API fields unchanged
- No new files, no new CLI commands

## Testing

- Existing unit tests do not depend on these defaults (they pass synthetic fixtures with explicit args).
- Run `pytest` to confirm no regressions.
- Re-run fine-tuning on the 5-speaker dataset with new defaults and compare WER/CER to the old results (WER 79.95%, CER 29.26%).
