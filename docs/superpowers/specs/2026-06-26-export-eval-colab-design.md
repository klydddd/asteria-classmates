# Design: `bosesph export-eval-colab`

**Date:** 2026-06-26
**Status:** Approved

## Problem

Running `run_eval_tl.sh` locally is slow because Whisper transcription has no GPU. The fine-tuned model and test dataset are already on Google Drive from the Colab fine-tuning workflow. The goal is a generated Colab notebook that runs the full eval pipeline on Colab's GPU.

## Approach

Add a new `bosesph export-eval-colab` CLI command that generates a ready-to-run `.ipynb` notebook. Follows the same pattern as the existing `export-colab` / `colab.py` architecture.

## CLI Interface

```
bosesph export-eval-colab \
  --dataset-drive-path <Drive path to dataset folder> \
  --model-drive-path   <Drive path to fine-tuned model folder> \
  [--base-model        openai/whisper-small] \
  [--language          tl] \
  [--eval-language     kapampangan] \
  [--split             test] \
  [--baseline-name     "Baseline Whisper Small"] \
  [--finetuned-name    "Fine-tuned Whisper"] \
  [--baseline-limit    <int, optional>] \
  [--output            colab_eval.ipynb] \
  [--repo-url          <GitHub URL>] \
  [--repo-ref          main]
```

`--dataset-drive-path` and `--model-drive-path` are required. All other arguments have sensible defaults.

## Config Model

`ColabEvalConfig` (Pydantic v2, in `colab.py`) holds all fields above. Mirrors `ColabExportConfig`.

## Notebook Structure (9 cells)

| # | Type | Purpose |
|---|------|---------|
| 1 | shell | `pip install git+<repo_url>@<repo_ref>#egg=bosesph[asr]` |
| 2 | code | Mount Google Drive (`google.colab.drive.mount`) |
| 3 | code | Define path variables (dataset, model, output dirs) |
| 4 | shell | `bosesph transcribe` — baseline model → `/content/baseline_predictions.csv` (with `--limit` if set) |
| 5 | shell | `bosesph evaluate` — baseline predictions → `/content/baseline_results/` |
| 6 | shell | `bosesph transcribe` — fine-tuned model → `/content/finetuned_predictions.csv` |
| 7 | shell | `bosesph evaluate` — fine-tuned predictions → `/content/finetuned_results/` |
| 8 | shell | `bosesph compare` → `/content/comparison.md` |
| 9 | code | Read and print `comparison.md` inline |

Intermediate files (CSVs, result JSONs) stay on `/content/` (VM disk). The final comparison is printed in cell 9 output — no Drive write-back needed.

## Implementation

### `src/bosesph/colab.py`
- Add `ColabEvalConfig` Pydantic model
- Add `write_eval_notebook(config: ColabEvalConfig, output_path: Path)` — builds `.ipynb` JSON using existing cell-construction helpers, writes atomically via temp file + rename

### `src/bosesph/cli.py`
- Add `export-eval-colab` subparser with all arguments listed above
- Add `_run_export_eval_colab()` handler: constructs `ColabEvalConfig`, calls `write_eval_notebook()`

### `tests/test_colab_eval.py`
- `ColabEvalConfig` validates required fields and applies defaults
- `write_eval_notebook()` produces valid JSON with correct cell count and key commands present
- CLI parser defaults resolve correctly

## Out of Scope

- Writing results back to Google Drive (printed inline is sufficient)
- Support for Drive zip datasets (Drive folder mount is the only mode needed)
- Any changes to existing `export-colab` / fine-tuning flow
