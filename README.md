# BosesPH Toolkit

BosesPH Toolkit is an open-source developer pipeline for turning raw Philippine-language speech recordings, transcripts, and metadata into clean datasets, benchmark splits, evaluation results, and optional fine-tuned automatic speech recognition models.

## Status

Phase 1 dataset design and Phase 2 PLD audio ingestion are implemented. The
toolkit parses PLD session logs, matches transcripts to WAV files, validates
audio, standardizes usable clips to mono 16 kHz 16-bit PCM, assigns
deterministic IDs, and generates metadata and ingestion reports.

## Python Setup

Python 3.10 or newer is required.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

Validate metadata or regenerate the checked-in schema:

```bash
bosesph validate-metadata sample_data/metadata_template.csv
bosesph validate-metadata metadata.csv --format json
bosesph export-metadata-schema --output docs/metadata.schema.json
```

Import one PLD recording session:

```bash
bosesph import-pld PLD/PAM/0400 --output outputs/dataset
```

Use `--overwrite` to replace a previously generated output directory:

```bash
bosesph import-pld PLD/PAM/0400 \
  --output outputs/dataset \
  --overwrite
```

Generated output contains:

```text
outputs/dataset/
  audio_clean/           # standardized pam_*.wav files
  metadata.csv           # pending and needs-review clips
  ingestion_report.json  # all accepted, review, and rejected results
```

Non-quiet clips between 5 and 15 seconds are marked `pending`. Other readable
clips are preserved as `needs_review`; corrupt, empty, silent, or unmatched
inputs are recorded as `rejected`.

Development verification:

```bash
ruff check .
black --check .
pytest
```

## Planned Architecture

- `apps/web/` — Next.js App Router dashboard.
- `apps/api/` — FastAPI service for ingestion, validation, evaluation, and exports.
- `ml/data/` — dataset preparation and transcript normalization.
- `ml/training/` — ASR fine-tuning workflows.
- `ml/evaluation/` — WER, CER, and benchmark utilities.
- `docs/` — architecture and contributor documentation.
- `sample_data/` — small, redistributable test and demonstration fixtures.
- `scripts/` — repeatable development and data-processing utilities.
- `outputs/` — generated datasets, reports, and model artifacts; contents are ignored.
- `src/bosesph/` — reusable metadata models, validators, and CLI.

## Project Documents

- [Requirements](Requirements.md) — technical requirements and recommended stack.
- [Tasks](Tasks.md) — phased implementation roadmap.
- [Contributor Guide](AGENTS.md) — repository conventions and data-handling rules.
- [Dataset Format](docs/dataset_format.md) — CSV fields, validation rules, and examples.
- [Transcription Guidelines](docs/transcription_guidelines.md) — Kapampangan transcription and review policy.

## Data Responsibility

Do not commit private recordings, personally identifying speaker metadata, secrets, generated datasets, or model weights. Only redistributable or explicitly consented fixtures belong in `sample_data/`.

## License

Licensed under the [Apache License 2.0](LICENSE).
