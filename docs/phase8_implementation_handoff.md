# Phase 8 Dashboard and Demo Implementation Handoff

**Last updated:** June 25, 2026  
**Status:** Tasks 1 and 2 are complete and approved. Task 3 has not started.

This document is the operational handoff for another LLM or developer. Read it
before changing Phase 8 code.

## Objective

Implement the active Phase 8 scope:

- A functional Next.js Dashboard at `/`.
- A functional direct single-audio Demo at `/demo`.
- Real status cards backed by FastAPI output data.
- Controlled baseline and local fine-tuned model selection.
- Kapampangan and Auto language modes.
- Optional human reference transcript for immediate WER/CER scoring.
- Temporary demo audio deletion after every successful or failed job.

The following pages are explicitly deferred to future implementation:

- Collect
- Annotate
- Dataset
- Train
- Evaluate
- Docs

## Approved Product Decisions

The user approved these decisions:

1. Build only Dashboard and Demo now.
2. Transcribe a directly uploaded single audio file, not a generated one-clip
   dataset.
3. Allow an optional reference transcript. When present, calculate WER and
   CER; when absent, return transcription only.
4. Offer controlled model selection:
   - Baseline `openai/whisper-small`.
   - Local fine-tuned model when a valid package exists.
5. Do not accept arbitrary model IDs because they could trigger unexpected
   downloads.
6. Language options are Kapampangan and Auto-detect.
7. Baseline Kapampangan decoding remains automatic because Whisper has no
   native Kapampangan language token.
8. The fine-tuned model uses its persisted language configuration, currently
   the Tagalog proxy by default.
9. Dashboard cards must show real API data only. Missing values display
   `Not available`; never fabricate demo metrics.
10. Delete uploaded demo files after inference completes or fails.
11. Next.js calls FastAPI directly with explicit CORS configuration. Do not add
    a Next.js proxy backend.

## Authoritative Documents

- Approved design:
  `docs/superpowers/specs/2026-06-25-phase-8-dashboard-demo-design.md`
- Detailed implementation plan:
  `docs/superpowers/plans/2026-06-25-phase-8-dashboard-demo.md`
- Task roadmaps:
  `Tasks.md` and `Simple_Tasks.md`

The detailed plan is exhaustive and contains exact test cases, code shapes,
commands, CSS, and commit boundaries. This handoff records execution state and
does not replace that plan.

## Repository And Worktree State

Phase 8 implementation must continue in:

```text
/Users/klydu/PersonalProjects/Asteria/.worktrees/phase8-dashboard-demo
```

Feature branch:

```text
phase8-dashboard-demo
```

Current feature-branch HEAD:

```text
c62d9da fix(api): reject symlinked demo model files
```

The feature branch was created from:

```text
98bb91e docs: plan Phase 8 dashboard demo
```

The main checkout is:

```text
/Users/klydu/PersonalProjects/Asteria
```

Do not implement Phase 8 directly on `main`.

### Important Main-Checkout Warning

At handoff time, `main` contains unrelated user changes. Do not revert, stage,
commit, or overwrite them as part of Phase 8:

```text
M  src/bosesph/api/models.py
M  src/bosesph/api/routes/pipeline.py
M  src/bosesph/review.py
M  tests/test_review.py
?? IDEAS.md
?? scripts/prepare_30speakers.py
?? src/bosesph_toolkit.egg-info/
?? test-piepline/
?? test-pipeline/
```

These main-checkout changes are not present in the Phase 8 worktree and were
not created by the Phase 8 implementation agents.

## Workflow Requirements

Execution uses `superpowers:subagent-driven-development`:

1. A fresh implementer agent performs one task using strict TDD.
2. A separate agent reviews specification compliance.
3. Only after spec approval, a separate agent reviews code quality.
4. Important or critical findings return to the same implementer.
5. Reviews repeat until approved.
6. Do not start the next task while review findings remain open.
7. After all tasks, run a whole-feature review and use
   `superpowers:finishing-a-development-branch`.

Tests in the worktree require:

```bash
PYTHONPATH=src /Users/klydu/PersonalProjects/Asteria/.venv/bin/pytest
```

The shared virtual environment's editable package points to the main checkout,
so `PYTHONPATH=src` is required to test worktree code reliably.

## Baseline Verification

Before implementation, the isolated worktree was clean and passed:

```text
178 passed in 2.57s
```

Command:

```bash
/Users/klydu/PersonalProjects/Asteria/.venv/bin/pytest -q
```

## Documentation Completed Before Implementation

### Design

Committed on `main`:

```text
e2dbf80 docs: design Phase 8 dashboard demo
```

The design covers:

- Two-route frontend scope.
- Direct browser-to-FastAPI data flow.
- Dashboard card mapping.
- Controlled model/language discovery.
- Multipart single-audio submission.
- Existing JobManager polling.
- Optional reference scoring.
- Temporary upload lifecycle and privacy.
- Error states and frontend/backend tests.

### Implementation Plan

Committed on `main`:

```text
98bb91e docs: plan Phase 8 dashboard demo
```

The plan contains nine tasks:

1. Make project status deterministic.
2. Add controlled demo options.
3. Add transient single-audio transcription.
4. Configure explicit CORS.
5. Scaffold the Next.js application.
6. Add typed API client and dashboard mapping.
7. Build the Dashboard.
8. Build the direct audio Demo.
9. Update documentation, mark Phase 8 complete, and run final verification.

## Task 1: Deterministic Project Status

**Status:** Complete, committed, specification-approved, and quality-approved.

Commits:

```text
630eaf6 feat(api): expose dashboard project metrics
d2d127a fix(api): ignore invalid status artifacts
68ee63d fix(api): reject overflowing project metrics
```

Changed files:

```text
src/bosesph/api/models.py
src/bosesph/api/routes/files.py
tests/test_api.py
```

Implemented behavior:

- Replaced ambiguous `benchmark_available` and `benchmark_results` fields.
- Added `MetricSummary` with `wer` and `cer`.
- Added independent `baseline_metrics` and `finetuned_metrics`.
- Added `model_version`.
- Reads only these deterministic paths:
  - `dataset/dataset_stats.json`
  - `benchmark/baseline/results.json`
  - `benchmark/finetuned/results.json`
  - First sorted model directory containing `model_card.md`
- Missing outputs return `None` and false availability flags.
- Invalid JSON and wrong-shaped metric artifacts are ignored independently.
- String and boolean metric values are rejected.
- NaN, infinity, and overflowing huge integers are rejected without crashing
  `/project-status`.

Task 1 review history:

- Specification review: approved.
- Initial quality review found malformed JSON shape and non-finite metric
  crashes.
- First fix added invalid-artifact handling.
- Second review found huge JSON integers could still raise `OverflowError`.
- Final fix rejected overflowing values safely.
- Final quality review: approved.

Final Task 1 review verification:

```text
190 tests passed
Ruff passed
Black passed
git diff --check passed
```

One minor review suggestion was intentionally deferred: replacing
`dataset_stats: dict[str, Any]` with a fully typed dashboard statistics model.
That was outside Task 1 scope and is not currently required.

## Task 2: Controlled Demo Options

**Status:** Complete, committed, specification-approved, and quality-approved.

Commits:

```text
3f886b5 feat(api): publish controlled demo options
877ffe7 fix(api): secure demo model discovery
c62d9da fix(api): reject symlinked demo model files
```

Implemented behavior currently present in the worktree:

- Added `DemoLanguageOption`, `DemoModelOption`, and `DemoOptions`.
- Added `GET /demo/options`.
- Registered the demo router in `create_app()`.
- Returns language options in stable order:
  - Kapampangan
  - Auto-detect
- Returns model options in stable order:
  - Baseline `openai/whisper-small`, always available.
  - Local fine-tuned model when available.
- Fine-tuned discovery uses the first sorted directory under `workspace/model`
  containing both:
  - `model_card.md`
  - `model/config.json`
- Fine-tuned paths are workspace-relative.
- Reads the decoding language from `training_config.json`.
- Defaults malformed, missing, non-object, non-string, or blank language
  configuration to `tl`.
- Disabled fine-tuned option uses:
  `No local fine-tuned model found.`
- `select_demo_model()` rejects:
  - Unknown model IDs.
  - Unavailable models.
  - Unknown language IDs.
- Baseline and Auto decoding return `None`.
- Fine-tuned Kapampangan decoding returns the model's configured language.

Task 2 tests currently cover:

- Complete local model discovery.
- Missing fine-tuned model.
- First sorted complete candidate.
- Incomplete candidate exclusion.
- Missing or malformed training configuration fallback.
- Baseline, fine-tuned, and Auto decoding behavior.
- Unknown and unavailable choice validation.

Task 2 review history:

- Specification review: approved.
- Initial quality review found workspace escape through candidate/model
  symlinks, invalid UTF-8 configuration handling, and untrimmed language
  values.
- The first fix resolved directory-level symlink escapes, invalid UTF-8
  fallback, and trimming.
- Re-review found a symlinked file inside the loadable model tree could still
  resolve outside the workspace.
- The final fix rejects all symlinks anywhere under a candidate's `model/`
  tree, including internal, external, nested, and dangling links.
- Final quality review: approved.

Final Task 2 review verification:

```text
207 tests passed
Ruff passed
Black passed
git diff --check passed
```

Residual risk noted by the reviewer is limited to filesystem TOCTOU races
between discovery and model loading.

## Remaining Implementation Plan

The exact implementation details and code examples are in
`docs/superpowers/plans/2026-06-25-phase-8-dashboard-demo.md`.

### Task 3: Transient Single-Audio Transcription

Planned files:

```text
src/bosesph/api/demo.py
src/bosesph/api/models.py
src/bosesph/api/routes/demo.py
tests/test_api.py
```

Required behavior:

- `POST /demo/transcribe` accepts multipart:
  - `audio`
  - `model_id`
  - `language_id`
  - Optional `reference`
- Accept only PCM WAV uploads.
- Reject missing, empty, unsupported, unknown, and unavailable inputs.
- Save under a unique `workspace/.demo_uploads/<uuid>/audio.wav`.
- Resolve the controlled fine-tuned model path against the workspace before
  loading it.
- Submit a `demo-transcribe` JobManager job.
- Reuse:
  - `bosesph.asr.load_model`
  - `bosesph.asr.transcribe_file`
  - `bosesph.asr.calculate_metrics`
- Return prediction, model ID/label, language ID, and optional WER/CER.
- Delete the unique temporary directory in a `finally` block on success and
  failure.
- Remove the empty `.demo_uploads` root.
- Log cleanup errors without replacing the inference result or error.
- Commit target:
  `feat(api): add transient audio demo jobs`

### Task 4: Explicit CORS And Upload Limit

Planned files:

```text
src/bosesph/api/settings.py
src/bosesph/api/app.py
src/bosesph/api/demo.py
src/bosesph/api/routes/demo.py
tests/test_api.py
```

Required behavior:

- Add default allowed origins:
  - `http://localhost:3000`
  - `http://127.0.0.1:3000`
- Add configurable `BOSESPH_CORS_ORIGINS`.
- Add a positive `demo_max_upload_bytes`, default 25 MiB.
- Add `CORSMiddleware` with GET/POST and all headers.
- Reject oversized uploads and clean partial temporary files.
- Test configured and rejected origins.
- Commit target:
  `feat(api): configure dashboard CORS`

### Task 5: Next.js Scaffold

Planned location:

```text
apps/web/
```

Required tooling:

- Next.js 16 App Router.
- React 19.
- TypeScript.
- pnpm 10.17.1 through Corepack.
- ESLint.
- Prettier.
- Vitest and Testing Library.
- wavesurfer.js 7.
- Manrope variable and Newsreader variable fonts.

Required initial files include:

```text
package.json
pnpm-lock.yaml
next.config.ts
tsconfig.json
eslint.config.mjs
prettier.config.mjs
.prettierignore
vitest.config.ts
vitest.setup.ts
.env.example
app/layout.tsx
app/globals.css
app/page.tsx
```

The public API URL is:

```dotenv
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

Commit target:

```text
feat(web): scaffold Next.js dashboard
```

### Task 6: Typed Frontend API And Dashboard Mapping

Planned files:

```text
apps/web/lib/api.ts
apps/web/lib/dashboard.ts
apps/web/lib/format.ts
apps/web/tests/dashboard.test.ts
```

Required behavior:

- Type the project status, demo options, jobs, and demo results.
- Directly call FastAPI using `NEXT_PUBLIC_API_BASE_URL`.
- Submit multipart demo data.
- Poll `/jobs/{id}` every 750 ms with abort support.
- Map seven cards:
  - Dataset Clips
  - Approved Clips
  - Speakers
  - Total Minutes
  - Baseline WER
  - Fine-tuned WER
  - Model Version
- Missing values must display `Not available`.
- Commit target:
  `feat(web): add typed API client`

### Task 7: Dashboard UI

Planned files:

```text
apps/web/components/app-shell.tsx
apps/web/components/status-card.tsx
apps/web/components/dashboard.tsx
apps/web/app/page.tsx
apps/web/app/globals.css
apps/web/tests/dashboard-page.test.tsx
```

Required behavior:

- Shared BosesPH shell and Dashboard/Demo navigation.
- Real `/project-status` loading.
- Loading and actionable API error states.
- Seven responsive status cards.
- CTA to `/demo`.
- Intentional light visual design using field-note/audio-analysis cues.
- No Tailwind or component library.
- Desktop and mobile layouts.
- Commit target:
  `feat(web): build project dashboard`

### Task 8: Direct Audio Demo UI

Planned files:

```text
apps/web/components/waveform.tsx
apps/web/components/demo-form.tsx
apps/web/app/demo/page.tsx
apps/web/app/globals.css
apps/web/tests/demo-form.test.tsx
```

Required behavior:

- Load controlled options from `GET /demo/options`.
- Select one WAV file.
- Preview a waveform with wavesurfer.js.
- Select language and model.
- Disable unavailable models.
- Enter optional reference transcript.
- Submit to `POST /demo/transcribe`.
- Poll queued/running jobs.
- Display prediction, model, WER, and CER.
- Display `Not available` for metrics without a reference.
- Preserve input after recoverable errors.
- Show actionable validation, API, and job failures.
- Revoke browser object URLs and destroy WaveSurfer instances.
- Commit target:
  `feat(web): add direct audio transcription demo`

### Task 9: Documentation And Final Verification

Planned files:

```text
README.md
Tasks.md
Simple_Tasks.md
```

Required work:

- Document Corepack, pnpm install, API run, and frontend run commands.
- Document `/` and `/demo`.
- Document temporary upload deletion.
- Run all Python and frontend tests, lint, format, and build commands.
- Smoke test API and frontend together.
- Confirm `outputs/.demo_uploads` is absent after completed and failed jobs.
- Mark only the three active Phase 8 tasks complete.
- Leave deferred additional pages unchecked.
- Commit target:
  `docs: complete Phase 8 dashboard demo`

## Final Verification Commands

Run from the Phase 8 worktree:

```bash
PYTHONPATH=src /Users/klydu/PersonalProjects/Asteria/.venv/bin/pytest -q
/Users/klydu/PersonalProjects/Asteria/.venv/bin/ruff check .
/Users/klydu/PersonalProjects/Asteria/.venv/bin/black --check .
pnpm --dir apps/web test
pnpm --dir apps/web lint
pnpm --dir apps/web format
pnpm --dir apps/web format:check
pnpm --dir apps/web build
git diff --check
git status --short
```

Manual smoke test:

```bash
BOSESPH_WORKSPACE=outputs \
  /Users/klydu/PersonalProjects/Asteria/.venv/bin/bosesph-api

pnpm --dir apps/web dev
```

Verify:

1. `http://localhost:3000` loads real values or `Not available`.
2. `http://localhost:3000/demo` displays controlled choices.
3. WAV preview and transcription work.
4. Optional reference displays WER/CER.
5. No reference displays unavailable metrics.
6. Temporary upload storage is removed:

   ```bash
   test ! -d outputs/.demo_uploads
   ```

## Completion Workflow

After all nine tasks:

1. Dispatch a final whole-feature code-review agent.
2. Resolve every critical or important finding.
3. Re-run the complete verification suite.
4. Use `superpowers:finishing-a-development-branch`.
5. Offer merge, PR, keep-branch, or discard options.
6. Do not merge or delete the worktree without the user's choice.

## Immediate Next Action

Resume at Task 3: transient single-audio transcription. Tasks 1 and 2 must not
be reimplemented.
