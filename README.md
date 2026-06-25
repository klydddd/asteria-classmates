# BosesPH Toolkit

BosesPH Toolkit is a CLI-first, open-source pipeline for turning raw
Philippine-language speech recordings and transcripts into reusable datasets,
ASR benchmarks, and optional fine-tuned speech-recognition models.

The MVP focuses on Kapampangan while keeping the workflow reusable for other
Philippine languages. It is a dataset and model-development toolkit—not only a
transcription application.

## What the Toolkit Will Do

The complete workflow is designed to take a project from raw recordings to a
documented release package:

```text
Raw audio + transcripts + metadata
                 |
                 v
        Import and validation
                 |
                 v
 Audio standardization and transcript normalization
                 |
                 v
       Human review and approval
                 |
                 v
 Clean dataset + train/validation/test splits
                 |
                 v
   Baseline ASR transcription and WER/CER evaluation
                 |
                 v
        Optional ASR fine-tuning
                 |
                 v
 Dataset, benchmark, model, and documentation package
```

In practice, the pipeline will:

1. Import recordings, transcripts, and available speaker or language metadata.
2. Match each recording to its transcript and report missing or invalid inputs.
3. Validate audio structure, duration, sample rate, channels, silence, and
   readability without stopping the entire batch when one clip fails.
4. Standardize usable audio to mono, 16 kHz, signed 16-bit PCM WAV and assign
   deterministic language-prefixed IDs.
5. Normalize transcript formatting and route questionable clips for human
   review.
6. Export approved clips as a clean dataset with speaker-aware
   train/validation/test splits and summary statistics.
7. Run a pretrained multilingual ASR model against the test split.
8. Calculate word error rate (WER) and character error rate (CER), then produce
   a benchmark report with representative errors and limitations.
9. Optionally fine-tune a small ASR model and compare it with the baseline.
10. Package the dataset, benchmark results, model artifacts, dataset card, and
    model card so another developer can reproduce or extend the work.

The command line remains the primary interface. A notebook or lightweight demo
may demonstrate the workflow, while FastAPI and Next.js are stretch interfaces
that must reuse the same Python pipeline rather than duplicate its logic.

## Current Status

Phases 1 and 2 are implemented for the selected PLD Kapampangan session
workflow:

- Metadata schema and transcription guidance are documented.
- `PLD/PAM/0400` can be imported as one local recording session.
- Session logs and transcript rows are parsed and matched to PCM WAV files.
- Audio is checked for corruption, emptiness, silence, quiet levels, duration,
  sample rate, channel count, and sample width.
- Readable audio is standardized to mono, 16 kHz, signed 16-bit PCM WAV.
- Output names are assigned deterministically as `pam_000001.wav`,
  `pam_000002.wav`, and so on.
- Clip-level outcomes are recorded without aborting the complete import.

The following stages remain planned: generic transcript import, transcript
normalization, reviewer approval, final dataset construction, speaker-aware
splitting, dataset statistics, baseline ASR inference, WER/CER evaluation,
fine-tuning, release packaging, and optional API or demo interfaces.

## Current CLI Usage

Python 3.10 or newer is required.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

Validate metadata or regenerate the checked-in JSON schema:

```bash
bosesph validate-metadata sample_data/metadata_template.csv
bosesph validate-metadata metadata.csv --format json
bosesph export-metadata-schema --output docs/metadata.schema.json
```

Import a PLD recording session:

```bash
bosesph import-pld PLD/PAM/0400 --output outputs/dataset
```

Use `--overwrite` to replace an existing generated directory:

```bash
bosesph import-pld PLD/PAM/0400 \
  --output outputs/dataset \
  --overwrite
```

The importer currently produces:

```text
outputs/dataset/
  audio_clean/           # standardized pam_*.wav files
  metadata.csv           # pending and needs-review clips
  ingestion_report.json  # accepted, review, and rejected outcomes
```

Non-quiet clips between 5 and 15 seconds are marked `pending`. Other readable
clips are retained as `needs_review`. Corrupt, empty, silent, or unmatched
inputs are reported as `rejected`.

## Planned CLI Workflow

The target end-to-end interface is:

```bash
bosesph init kapampangan-asr
bosesph validate data/raw --transcripts data/transcripts.csv
bosesph clean data/raw --language kapampangan
bosesph split outputs/dataset --train 0.70 --val 0.15 --test 0.15
bosesph transcribe sample.wav --model openai/whisper-small
bosesph evaluate \
  --predictions outputs/benchmark/predictions.csv \
  --references outputs/dataset/test.csv
bosesph train \
  --base-model openai/whisper-small \
  --dataset outputs/dataset
bosesph package --output release
```

These commands describe the intended product flow and are not all implemented
yet. The existing commands are listed in [Current CLI Usage](#current-cli-usage).

## Target Output

When the complete workflow is implemented, a run will produce:

```text
outputs/
  dataset/
    audio/
    metadata.csv
    train.csv
    validation.csv
    test.csv
    statistics.json
    dataset_card.md
  benchmark/
    baseline_predictions.csv
    fine_tuned_predictions.csv
    results.json
    report.md
  model/
    bosesph-kapampangan-v1/
      model files
      model_card.md
```

## Repository Structure

- `src/bosesph/` — reusable pipeline services, schemas, and CLI commands.
- `ml/data/` — dataset preparation and transcript normalization.
- `ml/evaluation/` — WER, CER, prediction, and benchmark utilities.
- `ml/training/` — optional ASR fine-tuning workflows.
- `apps/api/` — optional FastAPI wrapper around the core services.
- `apps/web/` — optional Next.js dashboard.
- `docs/` — architecture, dataset format, and transcription guidance.
- `sample_data/` — small, redistributable fixtures and templates.
- `scripts/` — repeatable setup, conversion, and export utilities.
- `outputs/` — generated datasets, reports, and model artifacts; do not commit
  its contents.

## Development

Run the current verification suite with:

```bash
ruff check .
black --check .
pytest
```

Behavior changes should include deterministic tests. Use synthetic or
explicitly consented audio fixtures and mock external model or storage calls.

## Project Documents

- [Requirements](Requirements.md) — product behavior, architecture, and
  recommended technology.
- [Tasks](Tasks.md) — phased build plan and implementation status.
- [Contributor Guide](AGENTS.md) — repository and development conventions.
- [Dataset Format](docs/dataset_format.md) — metadata fields and validation
  rules.
- [Transcription Guidelines](docs/transcription_guidelines.md) — Kapampangan
  transcription and review policy.

## Data Responsibility

Do not commit private recordings, personally identifying speaker metadata,
secrets, generated datasets, model weights, or unlicensed material. Only small,
redistributable, or explicitly consented fixtures belong in `sample_data/`.
Every released dataset should document its source, consent, license, intended
use, and known limitations.

## License

Licensed under the [Apache License 2.0](LICENSE).
