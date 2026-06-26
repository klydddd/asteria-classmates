# Phase 8 Hackathon MVP Design

## Goal

Deliver a reliable two-page showcase that lets judges understand project
progress and transcribe one WAV clip in under two minutes.

This specification supersedes the broader frontend scope in
`2026-06-25-phase-8-dashboard-demo-design.md`. The secure demo API already
implemented on the feature branch remains in scope.

## Scope

Phase 8 contains two pages:

- `/` is a compact project dashboard.
- `/demo` is a direct single-audio transcription flow.

Collect, Annotate, Dataset, Train, Evaluate, and Docs pages remain future work.

## Dashboard

The Dashboard displays four cards using only `GET /project-status` data:

- Dataset Clips
- Speakers
- Baseline WER
- Fine-tuned WER

Missing values display `Not available`. The page includes one clear action to
open the Demo.

Model-version, approved-clip, and duration cards are omitted from the hackathon
MVP. Their API fields may remain available.

## Demo

The Demo supports:

1. Select one PCM WAV file.
2. Preview it with the browser's native audio player.
3. Choose Kapampangan or Auto-detect.
4. Choose the baseline model or an available local fine-tuned model.
5. Optionally enter a human reference transcript.
6. Submit the transcription job.
7. Show queued, loading-model, and transcribing states.
8. Display the predicted transcript and model label.
9. Display WER and CER when a nonblank reference was supplied.

The page uses the existing endpoints:

- `GET /demo/options`
- `POST /demo/transcribe`
- `GET /jobs/{job_id}`

No waveform library is used.

## Existing Backend

The following completed backend behavior remains:

- Deterministic baseline and fine-tuned dashboard metrics.
- Controlled model and language options.
- Workspace-confined fine-tuned model discovery.
- Rejection of symlinked model packages.
- Direct WAV transcription through background jobs.
- Optional WER/CER scoring through existing ASR services.
- Unique temporary upload directories.
- Upload deletion after successful or failed jobs.

Phase 8 does not add arbitrary model IDs, persistent demo history, or dataset
creation from demo uploads.

## Local Browser Access

FastAPI will allow the two standard local frontend origins:

- `http://localhost:3000`
- `http://127.0.0.1:3000`

Broad production CORS configuration and a configurable upload-size setting are
deferred. The API continues to accept one WAV file per demo request.

## Frontend Structure

`apps/web` will use Next.js App Router, React, TypeScript, plain CSS, and pnpm.
The frontend contains:

- A shared header with Dashboard and Demo links.
- A small typed API client.
- A four-card Dashboard component.
- A Demo form with native audio preview, polling, result, and error states.

The visual direction is a clean light interface with clear typography and
strong contrast. Elaborate animation, component libraries, charting, and a
large design system are out of scope.

## Error Handling

The UI distinguishes:

- API connection failure.
- Invalid or empty WAV selection.
- Unavailable model.
- Queued or running job.
- Failed transcription job.
- Successful result with or without metrics.

The selected file and form values remain available after a recoverable
failure.

## Testing

Backend tests retain coverage for:

- Project status.
- Controlled options.
- Input validation.
- Successful transcription with and without metrics.
- Failed inference.
- Temporary-file cleanup.

Frontend tests focus on:

- Dashboard real-value and `Not available` mapping.
- Demo controlled options and disabled unavailable model.
- Successful job polling and result rendering.
- Failed job rendering.

Required verification:

```bash
PYTHONPATH=src /Users/klydu/PersonalProjects/Asteria/.venv/bin/pytest -q
/Users/klydu/PersonalProjects/Asteria/.venv/bin/ruff check .
/Users/klydu/PersonalProjects/Asteria/.venv/bin/black --check .
pnpm --dir apps/web test
pnpm --dir apps/web lint
pnpm --dir apps/web build
```

The final smoke test loads both pages and completes one WAV transcription
without leaving `outputs/.demo_uploads` behind.
