---
name: BosesPH Pipeline Operator
description: >
  Teaches an AI agent how to operate the BosesPH Toolkit — an open-source
  pipeline for building Philippine-language speech datasets, ASR benchmarks,
  and fine-tuned models. Covers the full workflow from raw audio ingestion
  to model evaluation, including metadata validation rules, transcript
  conventions, and pipeline sequencing.
---

# BosesPH Pipeline Operator Skill

You are an expert operator of the **BosesPH Toolkit**, a CLI-first pipeline
that turns raw Philippine-language speech recordings into clean datasets,
ASR benchmarks, and fine-tuned speech-recognition models.

## Core Concepts

### What BosesPH Does

BosesPH is a **developer toolkit**, not a transcription app. It produces:

1. A cleaned and standardized speech dataset
2. Train/validation/test benchmark splits
3. WER/CER evaluation results
4. An optional fine-tuned ASR model
5. Dataset cards, model cards, and documentation

### Supported Languages

The pipeline is language-agnostic but uses ISO 639-3 codes. The MVP pilot
language is **Kapampangan** (`pam`). Other Philippine languages like Tagalog
(`tgl`), Cebuano (`ceb`), Ilocano (`ilo`), and Hiligaynon (`hil`) are
supported by changing the language code.

---

## Pipeline Sequence (MUST follow this order)

```
Step 1: Import → Step 2: Normalize → Step 3: Review → Step 4: Build →
Step 5: Transcribe → Step 6: Evaluate → Step 7: Fine-tune (optional)
```

### Step 1 — Import Audio (`bosesph import-pld`)

Import a PLD (Philippine Language Documentation) recording session:

```bash
bosesph import-pld PLD/PAM/0400 --output outputs/dataset
```

- Parses session metadata and transcript rows
- Matches WAV files to transcripts
- Validates audio (corruption, silence, duration, sample rate)
- Standardizes to mono, 16 kHz, signed 16-bit PCM WAV
- Assigns deterministic IDs: `pam_000001.wav`, `pam_000002.wav`, etc.
- Produces `metadata.csv`, `audio_clean/`, and `ingestion_report.json`

Use `--overwrite` to replace existing output.

### Step 2 — Normalize Transcripts (`bosesph normalize-transcripts`)

```bash
bosesph normalize-transcripts outputs/dataset
```

- Fixes Unicode (NFC), whitespace, punctuation spacing
- Normalizes repeated punctuation and tag casing
- Updates `metadata.csv` in place
- Writes `normalization_report.json`
- Exit code 1 = completed with review warnings; exit code 2 = invalid input

### Step 3 — Review Clips (`bosesph review`)

```bash
bosesph review outputs/dataset
```

- Interactive terminal workflow for `pending` and `needs_review` clips
- Actions: approve (`a`), needs fix (`f`), reject (`r`), skip (`s`), quit (`q`)
- Only `approved` clips proceed to dataset building
- Decisions are saved immediately and resumable

### Step 4 — Build Dataset (`bosesph build-dataset`)

```bash
bosesph build-dataset outputs/dataset --output outputs/dataset
```

- Filters to approved clips only
- Speaker-aware train/val/test splits (default 70/15/15)
- Generates `train.csv`, `validation.csv`, `test.csv`
- Writes `dataset_stats.json` and `dataset_card.md`
- Use `--train`, `--val`, `--test` flags to adjust ratios
- Use `--seed` for reproducibility

**RULE**: Never build a dataset without reviewing clips first. Unapproved
clips are excluded.

### Step 5 — Transcribe (`bosesph transcribe`)

Single file:
```bash
bosesph transcribe sample.wav --model openai/whisper-small
```

Dataset split:
```bash
bosesph transcribe outputs/dataset --split test \
  --output outputs/benchmark/baseline_predictions.csv \
  --model openai/whisper-small
```

- Default model: `openai/whisper-small`
- `--language` flag sets Whisper decoding language (optional)
- `--limit N` processes only the first N clips

### Step 6 — Evaluate (`bosesph evaluate`)

```bash
bosesph evaluate \
  --predictions outputs/benchmark/baseline_predictions.csv \
  --output outputs/benchmark/baseline \
  --model-name baseline \
  --language kapampangan
```

- Computes **WER** (Word Error Rate) and **CER** (Character Error Rate)
- Normalizes text for scoring (lowercase, strip tags/punctuation)
- Writes `results.json` and `report.md` when `--output` is provided
- `--references` can override the reference column from a separate CSV

### Step 7 — Fine-Tune (optional) (`bosesph finetune`)

```bash
bosesph finetune outputs/dataset \
  --output outputs/model/bosesph-kapampangan-v1 \
  --base-model openai/whisper-tiny \
  --language tl \
  --max-steps 500
```

- Uses HuggingFace `Seq2SeqTrainer` with LoRA
- `--language tl` (Tagalog) as proxy since Whisper has no Kapampangan token
- Saves model, processor, `training_config.json`, and `model_card.md`

### Compare Models (`bosesph compare`)

```bash
bosesph compare \
  --baseline outputs/benchmark/baseline/results.json \
  --finetuned outputs/benchmark/finetuned/results.json \
  --output outputs/benchmark/comparison.md
```

---

## Critical Rules

### Metadata Validation Rules

Before building datasets, **always validate metadata**:

```bash
bosesph validate-metadata outputs/dataset/metadata.csv
```

Required columns: `audio_id`, `file_path`, `transcript`, `language`,
`speaker_id`, `duration_seconds`, `sample_rate`, `split`, `quality_status`.

- `audio_id` format: `{lang}_{six_digits}` (e.g., `pam_000001`)
- `file_path` must be relative POSIX, no `..` traversal
- `transcript` must be non-empty UTF-8 in NFC
- `language` must be a lowercase ISO 639-3 code
- `speaker_id` must start with `spk_` — never use real names
- Unknown columns are **rejected** (prevents accidental PII leaks)

### Transcript Annotation Tags

Only these four tags are allowed in transcripts:

| Tag | Meaning |
|---|---|
| `[noise]` | Non-speech sound overlapping speech |
| `[laughter]` | Audible laughter |
| `[unclear]` | Speech present but cannot be reliably transcribed |
| `[silence]` | Meaningful period of silence within the clip |

**Never invent new tags.** Place tags at the point where the event occurs.
Do not tag routine breaths or insignificant background sounds.

### Transcription Principles

- Transcribe what is spoken, not what "should" be spoken
- Preserve repetitions, restarts, hesitations, and discourse markers
- Do not translate code-switched speech — transcribe in the language used
- Record code-switching in `code_switch_languages` using ISO 639-3 codes
  (e.g., `eng;fil`)
- Use sentence casing and conservative punctuation
- Save all text as UTF-8 in Unicode NFC

### Data Safety

- **Never** include personal names, addresses, phone numbers, or account
  details in metadata
- **Never** commit raw private audio, model weights, `.env` files, or secrets
- **Reject** clips containing sensitive personal information
- Speaker IDs must be anonymized (`spk_001`, not real names)

---

## MCP Server Integration

When using the BosesPH MCP server (started with `bosesph-mcp`), the same
pipeline is available as standardized tools:

| MCP Tool | CLI Equivalent |
|---|---|
| `get_project_status` | Check workspace state |
| `validate_metadata` | `bosesph validate-metadata` |
| `import_pld_session` | `bosesph import-pld` |
| `normalize_transcripts` | `bosesph normalize-transcripts` |
| `build_dataset` | `bosesph build-dataset` |
| `transcribe_audio` | `bosesph transcribe` (single file) |
| `transcribe_dataset` | `bosesph transcribe` (dataset split) |
| `evaluate_predictions` | `bosesph evaluate` |
| `get_dataset_stats` | Read `dataset_stats.json` |
| `list_dataset_clips` | Read split CSVs |

All MCP tools use relative paths under the `BOSESPH_WORKSPACE` directory
(defaults to `outputs/`).

---

## API Server

The FastAPI backend (`bosesph-api`) exposes the same pipeline over HTTP.
Heavy operations (transcription, training, evaluation) run as background
jobs. Poll `GET /jobs/{job_id}` for progress.

Default: `http://0.0.0.0:8000` with OpenAPI docs at `/docs`.

---

## Output Structure

A complete pipeline run produces:

```
outputs/
  dataset/
    audio/                    # Standardized WAV files
    metadata.csv              # Full metadata with splits
    train.csv                 # Training split
    validation.csv            # Validation split
    test.csv                  # Test split
    dataset_stats.json        # Statistics
    dataset_card.md           # Auto-generated documentation
  benchmark/
    baseline_predictions.csv  # Baseline ASR output
    baseline/results.json     # Baseline WER/CER
    baseline/report.md        # Benchmark report
  model/
    bosesph-kapampangan-v1/   # Fine-tuned model
      model/                  # Model weights + processor
      model_card.md           # Auto-generated documentation
      training_config.json    # Training hyperparameters
```
