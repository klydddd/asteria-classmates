# Repository Guidelines

## Project Structure & Module Organization

`Requirements.md` defines the BosesPH Toolkit architecture; `Tasks.md` tracks implementation. As the project is scaffolded, use:

- `apps/web/` — Next.js App Router dashboard and UI tests.
- `apps/api/` — FastAPI routes, schemas, services, and API tests.
- `ml/` — dataset processing, training, and evaluation code.
- `scripts/` — repeatable setup, conversion, and export utilities.
- `sample_data/` — small, redistributable fixtures only.
- `docs/` — architecture, metadata, and transcription guidance.
- `outputs/` — generated datasets, reports, and models; do not commit large artifacts.

Keep reusable logic out of route handlers and UI components. Place tests near the code they cover or in component-level `tests/` directories.

## Build, Test, and Development Commands

Create a Python 3.10+ virtual environment and install the package with
`python -m pip install -e ".[dev]"`. Current Python commands are:

```bash
bosesph validate-metadata sample_data/metadata_template.csv
bosesph export-metadata-schema --output docs/metadata.schema.json
ruff check .
black --check .
pytest
```

When adding the planned web or API components, expose these commands and
document deviations in `README.md`:

```bash
pnpm install && pnpm dev       # install and run the Next.js app
pnpm lint && pnpm test         # lint and test frontend code
pnpm build                     # create a production frontend build
uvicorn app.main:app --reload  # run FastAPI locally from apps/api
pytest                         # run Python API and ML tests
```

## Coding Style & Naming Conventions

Use TypeScript with two-space indentation, ESLint, and Prettier in `apps/web`. Use Python 3.10+, four-space indentation, type hints, Ruff, and Black in backend and ML code. Name React components `PascalCase`, TypeScript functions `camelCase`, Python modules and functions `snake_case`, and tests `*.test.ts(x)` or `test_*.py`. Use descriptive dataset IDs such as `kap_000001.wav`.

## Testing Guidelines

Add tests with every behavior change. Cover API validation, transcript normalization, dataset splitting, metric calculation, and failure cases. Use small synthetic or consented audio fixtures; never include private recordings. Keep tests deterministic by fixing random seeds and mocking external model or storage calls.

## Commit & Pull Request Guidelines

Git history is not available yet, so adopt concise imperative commits, optionally using Conventional Commit prefixes, for example `feat(api): validate audio metadata`. Pull requests should explain scope, verification commands, related issues, and data or model impacts. Include screenshots for UI changes and sample output summaries for pipeline changes.

## Security & Data Handling

Never commit secrets, `.env` files, personal speaker metadata, raw private audio, model weights, or generated `outputs/`. Document required environment variables in `.env.example` and record dataset licensing and consent requirements.
