# Phase 8 Dashboard and Demo Design

## Goal

Build a focused Next.js dashboard and a direct single-audio ASR demo backed by
the existing FastAPI services. The experience must show real project outputs,
complete a judge-ready transcription flow in under two minutes, and avoid
retaining uploaded private audio.

## Scope

Phase 8 includes two functional pages:

- `/` provides the project dashboard.
- `/demo` provides upload, preview, transcription, and optional evaluation.

Dedicated Collect, Annotate, Dataset, Train, Evaluate, and Docs pages are
future implementations. Phase 8 does not expose arbitrary model identifiers,
persist demo history, or duplicate pipeline logic in the frontend.

## Architecture

`apps/web/` will contain a Next.js App Router application written in
TypeScript. Browser components will call the FastAPI application directly
through a configured public API base URL.

FastAPI will add demo-specific endpoints while continuing to use the existing
`JobManager` for long-running inference:

- `GET /demo/options` returns the controlled language and model choices.
- `POST /demo/transcribe` accepts one audio file, a model choice, a language
  mode, and an optional reference transcript.
- `GET /jobs/{job_id}` remains the polling endpoint for progress and results.

The API will enable configurable CORS origins for local frontend development.
The web app will not add a second proxy or backend layer.

## Frontend Structure

The shared application shell will provide BosesPH branding and navigation
between Dashboard and Demo. It will use an intentional light visual system
inspired by field notes and audio analysis rather than a generic admin
template. The layout must remain usable on desktop and mobile.

The frontend will separate responsibilities into:

- API client functions and response types.
- Shared shell, navigation, status, and error components.
- Dashboard status-card mapping and display.
- Demo upload form, browser audio preview, waveform visualization, progress,
  and result display.

The waveform is a client-side preview only. It does not alter or preprocess
the uploaded audio.

## Dashboard

The Dashboard will request `GET /project-status` and derive these cards from
real API data:

- Dataset Clips
- Approved Clips
- Speakers
- Total Minutes
- Baseline WER
- Fine-tuned WER
- Model Version

Missing outputs or fields will display `Not available`. The frontend will not
substitute sample values. The existing status response may be extended where
necessary so baseline and fine-tuned metrics are represented independently
and the card mapping does not depend on ambiguous file ordering.

The Dashboard will include a clear action leading to the Demo and a concise
pipeline overview without implementing the deferred pipeline pages.

## Demo Flow

The Demo will guide the user through:

1. Select one supported audio file.
2. Preview playback and its waveform locally.
3. Choose Kapampangan or automatic language handling.
4. Choose a controlled model option.
5. Optionally enter the correct human transcript.
6. Submit the file for transcription.
7. Observe queued and transcribing progress.
8. Read the predicted transcript and model used.
9. View WER and CER when a reference transcript was supplied.

The controlled model list contains:

- Baseline `openai/whisper-small`.
- The local fine-tuned model when its required files are available.

Unavailable choices will not be submitted. Arbitrary Hugging Face model IDs
are outside the scope because they could trigger unexpected downloads.

For the baseline model, both Kapampangan and Auto use automatic Whisper
decoding because Whisper has no native Kapampangan language token. The local
fine-tuned model uses its persisted language configuration, currently the
Tagalog proxy used during training.

## API Data Contracts

`GET /demo/options` will return:

- Language options with stable IDs, labels, and explanatory text.
- Model options with stable IDs, labels, model paths, availability, and an
  optional unavailable reason.
- Defaults for language and model selection.

`POST /demo/transcribe` will use multipart form data containing:

- One audio file.
- A controlled model ID.
- A controlled language ID.
- An optional reference transcript.

The endpoint will validate the choices, save the upload under a unique
temporary directory inside the configured workspace, and enqueue a background
job. The completed job result will contain:

- Predicted transcript.
- Model ID and display name.
- Language mode.
- WER and CER when a non-empty reference was supplied.

Metric calculation will reuse the existing normalization and `jiwer`-backed
evaluation behavior rather than implementing scoring in TypeScript.

## File Lifecycle And Privacy

Each submission will use a unique temporary directory under the API workspace.
The background job will remove that directory in a `finally` block after
inference succeeds or fails.

The API will reject missing, empty, unsupported, or invalid audio before model
inference where practical. Demo audio, transcripts, and results will not be
added to permanent datasets or a demo history.

If cleanup fails, the API will log the cleanup failure without replacing the
original inference result or error.

## Error Handling

The frontend will represent idle, validating, uploading, queued, transcribing,
completed, and failed states. Submission will be disabled when required input
is missing or a selected model is unavailable.

User-facing failures will distinguish:

- Invalid or unsupported audio.
- Unavailable model selection.
- API connectivity failure.
- Background inference failure.
- Job-not-found or malformed API responses.

FastAPI will return structured errors without exposing stack traces. The UI
will preserve the selected local file and form choices after recoverable
failures so the user can retry.

## Configuration

The frontend will use an environment variable for the FastAPI base URL and
document it in an example environment file. FastAPI settings will accept an
explicit list of allowed CORS origins, defaulting to the local Next.js
development origin.

No secrets are required for the local dashboard. Generated frontend build
artifacts and environment files remain untracked.

## Testing And Verification

Backend tests will cover:

- Controlled model and language option discovery.
- Local fine-tuned model availability detection.
- Rejection of unknown or unavailable model choices.
- Direct single-file transcription through a mocked ASR service.
- Optional reference scoring.
- Temporary-file cleanup after success and failure.
- Configured CORS behavior.
- Unambiguous project-status metrics for dashboard cards.

Frontend tests will cover:

- Status-card mapping with real values and missing-value states.
- Demo input validation and controlled option rendering.
- Job submission and polling transitions.
- Successful transcription with and without WER/CER.
- API, validation, and job failure states.

The implementation is complete when these commands pass:

```bash
ruff check .
black --check .
pytest
pnpm --dir apps/web lint
pnpm --dir apps/web test
pnpm --dir apps/web build
```

The final manual smoke test will run the API and web app together, load both
pages at mobile and desktop widths, and complete one transcription without
leaving the uploaded audio in the workspace.
