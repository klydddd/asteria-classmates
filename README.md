# BosesPH Toolkit

BosesPH Toolkit is an open-source developer pipeline for turning raw Philippine-language speech recordings, transcripts, and metadata into clean datasets, benchmark splits, evaluation results, and optional fine-tuned automatic speech recognition models.

## Status

The project is currently at the repository foundation stage. The directory boundaries and project policies are defined, but the Next.js application, FastAPI service, Python ML pipeline, dependencies, and executable commands have not yet been scaffolded.

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

## Project Documents

- [Requirements](Requirements.md) — technical requirements and recommended stack.
- [Tasks](Tasks.md) — phased implementation roadmap.
- [Contributor Guide](AGENTS.md) — repository conventions and data-handling rules.

## Data Responsibility

Do not commit private recordings, personally identifying speaker metadata, secrets, generated datasets, or model weights. Only redistributable or explicitly consented fixtures belong in `sample_data/`.

## License

Licensed under the [Apache License 2.0](LICENSE).
