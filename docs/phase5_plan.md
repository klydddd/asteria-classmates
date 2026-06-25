# Phase 5 — Baseline ASR and Benchmark

Implement `bosesph transcribe` and `bosesph evaluate` CLI commands to run baseline ASR inference on the test split and produce WER/CER benchmark results.

## Proposed Changes

### New Dependencies

#### [MODIFY] [pyproject.toml](file:///Users/klydu/PersonalProjects/Asteria/pyproject.toml)

Add a new optional dependency group `[asr]`:

```toml
[project.optional-dependencies]
asr = [
  "transformers>=4.40,<5",
  "torch>=2.2",
  "torchaudio>=2.2",
  "jiwer>=3.0,<4",
]
```

- **`transformers`** — HuggingFace pipeline API for Whisper inference. Same stack needed for Phase 6 fine-tuning.
- **`torch`** — Backend. On Apple Silicon M5, supports MPS acceleration out of the box.
- **`torchaudio`** — Audio loading and resampling (consistent with torch ecosystem).
- **`jiwer`** — Standard library for WER/CER computation using Levenshtein edit distance.

Installed via: `pip install -e ".[asr]"` — keeps the core toolkit lightweight for users who only need data processing.

> [!NOTE]
> **MacBook Air M5 16GB**: Recommended model is `openai/whisper-small` (244M params, ~2GB RAM). For quick pipeline testing, use `openai/whisper-tiny` (39M params, ~1GB). Both fit comfortably. The pipeline will auto-detect MPS (Apple Silicon GPU) and use it when available, falling back to CPU.

---

### ASR Module

#### [NEW] [asr.py](file:///Users/klydu/PersonalProjects/Asteria/src/bosesph/asr.py)

Core ASR and evaluation logic with lazy imports (so the core package works without `[asr]` extras).

**Transcription functions:**
- `_get_device()` → Detects best available device: `"mps"` on Apple Silicon, `"cuda"` if NVIDIA GPU, `"cpu"` fallback.
- `load_model(model_name, device)` → Loads a HuggingFace ASR pipeline: `pipeline("automatic-speech-recognition", model=model_name, device=device)`. Returns the pipeline object.
- `transcribe_file(pipe, audio_path, language)` → Run the pipeline on one audio file, return predicted text.
- `transcribe_split(split_csv, dataset_dir, pipe, language, output_path, progress_fn)` → Iterate over a split CSV, transcribe each clip, write `predictions.csv` with columns: `audio_id, reference, prediction, file_path`.

**Evaluation functions:**
- `normalize_for_scoring(text)` → Lowercase, strip punctuation, collapse whitespace, remove annotation tags like `[noise]`. Standard ASR eval normalization for fair comparison.
- `calculate_metrics(references, predictions)` → Use `jiwer.wer()` and `jiwer.cer()` to compute word and character error rates. Returns a `BenchmarkMetrics` model.
- `evaluate_predictions(predictions_csv)` → Load a predictions CSV and compute aggregate WER/CER.

**Key types:**
- `TranscriptionResult(BaseModel)` — audio_id, reference, prediction
- `BenchmarkMetrics(BaseModel)` — model, language, wer, cer, test_clips, total_duration_seconds
- `ASRError(ValueError)` — raised for missing dependencies, model loading failures, or empty inputs

**Lazy imports:** `transformers`, `torch`, and `jiwer` are imported inside functions. If not installed, a clear `ASRError` is raised telling the user to run `pip install -e ".[asr]"`.

---

### Benchmark Module

#### [NEW] [benchmark.py](file:///Users/klydu/PersonalProjects/Asteria/src/bosesph/benchmark.py)

Orchestration and report generation:

- `run_baseline_benchmark(dataset_dir, output_dir, model_name, language, split, progress_fn)` — Full pipeline: load split CSV → load model → transcribe → evaluate → write outputs.
- `generate_benchmark_report(metrics, predictions, output_path)` — Generate `report.md` with:
  - Model name and ID
  - Dataset info (clip count, total duration)
  - WER and CER scores
  - Top 10 highest-error examples (sorted by per-clip WER)
  - Limitations and notes
- `BenchmarkReport(BaseModel)` — Complete result model.

Output structure:
```text
outputs/benchmark/
  baseline_predictions.csv    # audio_id, reference, prediction, file_path
  results.json                # { model, language, wer, cer, test_clips, ... }
  report.md                   # human-readable benchmark report
```

---

### CLI Integration

#### [MODIFY] [cli.py](file:///Users/klydu/PersonalProjects/Asteria/src/bosesph/cli.py)

**`bosesph transcribe`** subcommand:
- `source` (positional) — path to a single audio file OR a dataset directory
- `--model` (default: `openai/whisper-small`) — HuggingFace model ID
- `--language` (default: `kapampangan`) — language hint for Whisper
- `--output` (required when source is a dataset directory) — path for predictions CSV
- `--split` (default: `test`) — which split to transcribe (train, validation, test)

Single file mode prints the transcript to stdout. Dataset mode writes `predictions.csv`.

**`bosesph evaluate`** subcommand:
- `--references` (required) — path to the reference split CSV (e.g., test.csv)
- `--predictions` (required) — path to the predictions CSV
- `--output` (optional) — output directory for results.json and report.md
- `--model-name` (default: `baseline`) — model label for the report

---

### Tests

#### [NEW] [test_benchmark.py](file:///Users/klydu/PersonalProjects/Asteria/tests/test_benchmark.py)

Tests **mock** the transformers pipeline to avoid requiring model downloads in CI:

**WER/CER calculation tests** (using `jiwer` — no mock needed):
- Perfect match → WER=0, CER=0
- Known error cases with expected rates
- Empty predictions handling
- Text normalization for scoring (case, punctuation, annotation tags)

**Transcription pipeline tests** (mocked pipeline):
- Predictions CSV has correct columns and row count
- Progress callback is invoked
- Missing audio files produce empty predictions with a note
- Single-file transcription returns text

**Benchmark report tests:**
- report.md contains model name, WER, CER, error examples
- results.json is valid JSON and matches metrics model
- Top-error examples are sorted by WER descending

**CLI integration tests:**
- `transcribe` and `evaluate` subcommands parse arguments correctly
- Error paths (missing files, missing `[asr]` extras) return exit code 2

---

## Open Questions

> [!IMPORTANT]
> **Current dataset has only 1 speaker → all 397 clips are in `train`, 0 in `test`.** For a real demo, you can either:
> 1. Use `--split train` to transcribe the training clips (supported by the implementation)
> 2. Re-build the dataset with more speaker sessions later for a proper train/test split
>
> The implementation supports any `--split` value so this is not a blocker.

## Verification Plan

### Automated Tests
```bash
pip install -e ".[asr]"          # install ASR dependencies
pytest tests/test_benchmark.py -v
pytest                            # full suite
```

### Manual Verification
```bash
# Transcribe a single file (quick test)
bosesph transcribe /tmp/pld_output/audio_clean/pam_000001.wav --model openai/whisper-tiny

# Transcribe an entire split
bosesph transcribe /tmp/final_dataset --model openai/whisper-small --split train --output /tmp/benchmark/predictions.csv

# Evaluate predictions against references
bosesph evaluate --references /tmp/final_dataset/train.csv --predictions /tmp/benchmark/predictions.csv --output /tmp/benchmark

# Check outputs
cat /tmp/benchmark/results.json
cat /tmp/benchmark/report.md
head /tmp/benchmark/predictions.csv
```
