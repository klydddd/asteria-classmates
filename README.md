# BosesPH Toolkit

BosesPH Toolkit is an open-source developer pipeline for turning raw Philippine-language speech recordings, transcripts, and metadata into clean datasets, benchmark splits, evaluation results, and optional fine-tuned automatic speech recognition models.

## Status

Phase 1.1 and 1.2 dataset design are implemented. The repository now provides a
Python package, metadata model, aggregate CSV validator, JSON Schema export,
sample templates, and Kapampangan transcription guidance. Audio ingestion
remains Phase 2 work, and Phase 1.3 remains pending until consented clips and
matching metadata are prepared.

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
