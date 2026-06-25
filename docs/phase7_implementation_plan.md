# Phase 7 — API Layer Implementation Plan

## Context

The BosesPH Toolkit pipeline is complete through Phase 6 (ingestion → review →
dataset → baseline ASR → fine-tuning), all driven by the `bosesph` CLI. Every
CLI subcommand is a thin wrapper over a service function in `src/bosesph/` that
returns a Pydantic model. Phase 7 adds a **FastAPI backend** so frontends and
notebooks can drive the pipeline, plus an **in-process background job manager**
so heavy tasks (transcribe, fine-tune, evaluate, build) don't freeze the API.

**Key architectural facts:**
- All service functions live in `src/bosesph/` and return Pydantic `BaseModel` subclasses.
- All service modules raise `ValueError` subclasses for input errors (e.g. `IngestionError`, `DatasetBuildError`, `ASRError`).
- ASR/train deps (`torch`, `transformers`, etc.) are optional extras — imports are **lazy** (done inside function bodies, not at module top).
- The only service function NOT reusable as-is for HTTP is `review.review_dataset` (it's an interactive terminal loop using `input()`/`print()`). We add a new stateless `decide_clip()` function.
- The `apps/api/` directory existed but was empty (just `.gitkeep`). We place code in `src/bosesph/api/` instead, consistent with the existing package structure.

---

## Decisions Made

| Decision | Choice | Rationale |
|---|---|---|
| Framework | FastAPI | Pydantic-native, auto OpenAPI docs, async support |
| Background jobs | In-process `ThreadPoolExecutor` + job registry | No infra deps (Redis/Celery), MVP-appropriate |
| Code location | `src/bosesph/api/` | Inside existing package, clean imports, testable |
| Endpoint scope | Full surface (all pipeline verbs) | Complete API for Phase 8 frontend |
| Dep management | New `[api]` optional extra in `pyproject.toml` | Mirrors `[asr]`/`[train]` pattern |

---

## File Inventory

### Already Created (done)

- [x] **`pyproject.toml`** — Added `[api]` extra (`fastapi`, `uvicorn[standard]`, `python-multipart`) and `bosesph-api` console script entry point.

- [x] **`src/bosesph/api/__init__.py`** — Exports `create_app` from `app.py`.

- [x] **`src/bosesph/api/settings.py`** — `ApiSettings` (Pydantic `BaseSettings` with `BOSESPH_` env prefix): `workspace` (default `outputs/`), `host`, `port`, `max_workers`. `resolve_path(workspace, relative)` helper that joins paths and rejects traversal (`..`, absolute, backslash). Raises `PathTraversalError`.

- [x] **`src/bosesph/api/jobs.py`** — `JobManager` class:
  - `JobStatus` enum: `queued`, `running`, `succeeded`, `failed`.
  - `Job` Pydantic model: `id, type, status, progress, result, error, created_at, updated_at`.
  - `JobManager`: wraps `ThreadPoolExecutor`, thread-safe `dict[str, Job]` registry. Methods: `submit(type, fn, *args, **kwargs) -> Job`, `get(id) -> Job | None`, `list_jobs() -> list[Job]`, `shutdown()`.
  - `submit` passes a `progress_fn` keyword to the wrapped function. The callback accepts either `(done, total)` tuples or plain strings, stored as `job.progress`.

- [x] **`src/bosesph/api/models.py`** — Request and response models:
  - Request bodies: `ImportPldRequest`, `ValidateDatasetRequest`, `NormalizeTranscriptsRequest`, `ReviewDecisionRequest`, `BuildDatasetRequest`, `TranscribeRequest`, `EvaluateRequest`, `TrainRequest`, `CompareRequest`, `DownloadRequest`.
  - Response models: `ReviewDecisionResult`, `ProjectStatus`, `UploadResult`.
  - Existing service report models (`IngestionReport`, `ValidationReport`, etc.) are used directly as response types — NOT re-wrapped.

- [x] **`src/bosesph/api/routes/__init__.py`** — Empty package init.

- [x] **`src/bosesph/api/routes/pipeline.py`** — All pipeline endpoints:
  - **Synchronous** (declared as `def`, Starlette auto-threadpools them):
    - `POST /upload-audio` — accepts `UploadFile` list + `destination` query param. Saves under workspace. Returns `UploadResult`.
    - `POST /import-pld` — calls `ingestion.import_pld_session`. Returns `IngestionReport` JSON.
    - `POST /validate-dataset` — calls `metadata.validate_metadata_csv`. Returns `ValidationReport` JSON.
    - `POST /normalize-transcripts` — calls `transcripts.normalize_dataset`. Returns `NormalizationReport` JSON.
    - `POST /review/decision` — calls new `review.decide_clip`. Returns `ReviewDecisionResult`.
  - **Background jobs** (return `202 Accepted` + `Job` JSON):
    - `POST /build-dataset` — wraps `dataset.build_dataset`.
    - `POST /transcribe` — wraps `asr.load_model` + `asr.transcribe_split`. Bridges `progress_fn(done, total)`.
    - `POST /evaluate` — wraps `asr.evaluate_predictions` + optionally `benchmark.generate_benchmark_report`.
    - `POST /train` — wraps `finetune.finetune_model`. Bridges `progress_fn(msg)`.
    - `POST /compare` — reads two `results.json`, wraps `benchmark.generate_comparison_report`.
  - All heavy-dep imports (`asr`, `benchmark`, `finetune`) are done **inside** the endpoint/job body, keeping them lazy.

- [x] **`src/bosesph/api/routes/jobs.py`** — Job status endpoints:
  - `GET /jobs` — returns `list[Job]`, newest first.
  - `GET /jobs/{job_id}` — returns one `Job` or 404.

- [x] **`src/bosesph/api/routes/files.py`** — File and status endpoints:
  - `GET /project-status` — reads `dataset_stats.json`, `benchmark/**/results.json`, model dirs. Returns `ProjectStatus`.
  - `GET /download-output?path=...` — streams a workspace path (file or directory) as a zip archive.

### Still To Create

- [ ] **`src/bosesph/api/app.py`** — `create_app() -> FastAPI` factory:
  - Instantiate `ApiSettings`.
  - Create `JobManager(max_workers=settings.max_workers)`.
  - Store both on `app.state`.
  - Use a lifespan context manager: `yield`, then `jobs.shutdown()`.
  - Include all three routers: `routes.pipeline.router`, `routes.jobs.router`, `routes.files.router`.
  - Register exception handlers:
    - `PathTraversalError` → **400** `{"detail": str(exc)}`.
    - `FileNotFoundError` → **404** `{"detail": str(exc)}`.
    - Service `ValueError` subclasses (`IngestionError`, `OutputExistsError`, `TranscriptDatasetError`, `ReviewError`, `DatasetBuildError`, `ASRError`, `PldParseError`) → **422** `{"detail": str(exc)}`.
    - Generic `ValueError` catch-all → **422**.
  - Note: import service exceptions at the top of `app.py` — these are lightweight (no torch deps).

- [ ] **`src/bosesph/api/server.py`** — `run()` function:
  - Import `uvicorn` and `ApiSettings`.
  - Call `uvicorn.run("bosesph.api.app:create_app", factory=True, host=settings.host, port=settings.port)`.
  - This is the `bosesph-api` console script target.

- [ ] **`src/bosesph/review.py`** — Add `decide_clip()` function:
  - Signature: `decide_clip(dataset: str | Path, audio_id: str, decision: str, *, note: str | None = None) -> ReviewDecisionResult`.
  - Import `ReviewDecisionResult` from `bosesph.api.models` — **WAIT, circular import risk**. Instead, define a simple return model locally or return a dict and let the route wrap it. Better approach: return a small `ReviewDecisionResult` defined in `review.py` itself to avoid coupling to the API package. The route can construct the API model from it. Alternatively, just have `decide_clip` return a tuple/namedtuple `(audio_id, new_status, remaining_reviewable)`.
  - **Recommended approach**: Define a new `ClipDecisionResult(BaseModel)` in `review.py` with fields `audio_id: str`, `new_status: str`, `remaining_reviewable: int`. The API route maps this to the API response model.
  - Implementation (reuses existing primitives from `review.py`):
    1. Read rows via `_read_rows(metadata_path)` and `_validate_rows(rows)` (same as `review_dataset` line 114-115).
    2. Find the row where `row["audio_id"] == audio_id`. Raise `ReviewError` if not found.
    3. Check row's `quality_status` is in `{pending, needs_review}`. Raise `ReviewError` if already decided.
    4. Apply decision:
       - `"approve"`: check audio file exists (`(dataset / row["file_path"]).is_file()`), set `quality_status = "approved"`.
       - `"needs_fix"`: require `note`, set `quality_status = "needs_review"`, append note via `_append_note`.
       - `"reject"`: require `note`, set `quality_status = "rejected"`, append note via `_append_note`.
    5. Call `_checkpoint(metadata_path, fieldnames, rows)` to atomically persist.
    6. Count remaining reviewable rows via `_remaining(rows)`.
    7. Return `ClipDecisionResult(audio_id=audio_id, new_status=row["quality_status"], remaining_reviewable=count)`.
  - This is all extracted from the interactive loop at `review.py:124-175`, just without the `input()`/`print()` calls.

- [ ] **`tests/test_api.py`** — API integration tests using `fastapi.testclient.TestClient`:
  - `TestClient(create_app())` with `BOSESPH_WORKSPACE` env var pointed at `tmp_path`.
  - Test `POST /upload-audio`: upload a synthetic WAV (from `audio_fixtures.write_pcm_wav`), verify file exists.
  - Test `POST /import-pld`: build a synthetic PLD session dir (a `.log` file + WAV files), import it, assert `IngestionReport` fields.
  - Test `POST /validate-dataset`: validate metadata.csv, assert `ValidationReport` structure.
  - Test `POST /normalize-transcripts`: normalize, assert `NormalizationReport` structure.
  - Test `POST /review/decision`: approve a clip, assert status change and remaining count.
  - Test `POST /build-dataset`: submit job, poll `GET /jobs/{id}` until `succeeded`, verify output files.
  - Test `GET /project-status`: verify `ProjectStatus` shape.
  - Test `GET /download-output`: verify zip bytes are returned.
  - Test error cases: bad traversal path → 400; missing dataset → 404/422.
  - For ASR/train endpoints: use `pytest.importorskip("torch")` for real runs, or monkeypatch to test wiring without heavy deps.
  - Follow existing test patterns in `tests/test_cli.py`: use `tmp_path`, synthetic fixtures from `tests/audio_fixtures.py`, helper functions for building valid metadata CSVs.

- [ ] **`tests/test_jobs.py`** — Unit tests for `JobManager`:
  - Submit a function that returns a Pydantic model → poll until `succeeded`, verify `result` dict.
  - Submit a function that raises → verify `status == "failed"` and `error` contains the message.
  - Test `list_jobs()` returns jobs newest-first.
  - Test `get()` returns `None` for unknown IDs.
  - Test `shutdown()` completes cleanly.

### Files To Edit (updates only)

- [ ] **`Tasks.md`** — Mark Phase 7 sections (§7.1, §7.2) as Complete with status lines matching the format of §5.1–§6.5.
- [ ] **`Simple_Tasks.md`** — Check the two Phase 7 boxes: `[x] Build backend API endpoints`, `[x] Add background jobs for heavy tasks`.
- [ ] **`CLAUDE.md`** — Add `api.py` to the Architecture bullet list: `**api/` package** — FastAPI backend with in-process job manager. Wraps service functions as HTTP endpoints. Optional `[api]` extras.` Also add `bosesph-api` to the Commands section.

---

## Endpoint Summary Table

| Method | Path | Type | Service Function | Returns |
|---|---|---|---|---|
| POST | `/upload-audio` | sync | (file I/O) | `UploadResult` |
| POST | `/import-pld` | sync | `ingestion.import_pld_session` | `IngestionReport` |
| POST | `/validate-dataset` | sync | `metadata.validate_metadata_csv` | `ValidationReport` |
| POST | `/normalize-transcripts` | sync | `transcripts.normalize_dataset` | `NormalizationReport` |
| POST | `/review/decision` | sync | `review.decide_clip` (new) | `ReviewDecisionResult` |
| POST | `/build-dataset` | **job** | `dataset.build_dataset` | `Job` → `DatasetBuildReport` |
| POST | `/transcribe` | **job** | `asr.load_model` + `asr.transcribe_split` | `Job` → predictions info |
| POST | `/evaluate` | **job** | `asr.evaluate_predictions` + `benchmark.generate_benchmark_report` | `Job` → `BenchmarkMetrics` |
| POST | `/train` | **job** | `finetune.finetune_model` | `Job` → `FineTuneReport` |
| POST | `/compare` | **job** | `benchmark.generate_comparison_report` | `Job` → report path |
| GET | `/jobs` | sync | `JobManager.list_jobs` | `list[Job]` |
| GET | `/jobs/{id}` | sync | `JobManager.get` | `Job` |
| GET | `/project-status` | sync | (reads JSON files) | `ProjectStatus` |
| GET | `/download-output` | sync | (zip streaming) | `application/zip` |

## Error Mapping

| Exception | HTTP Status | Source |
|---|---|---|
| `PathTraversalError` | 400 | `settings.py` |
| `FileNotFoundError` | 404 | workspace path doesn't exist |
| `IngestionError` / `OutputExistsError` | 422 | `ingestion.py` |
| `TranscriptDatasetError` | 422 | `transcripts.py` |
| `ReviewError` | 422 | `review.py` |
| `DatasetBuildError` | 422 | `dataset.py` |
| `ASRError` | 422 | `asr.py` (includes missing-dep hints) |
| `PldParseError` | 422 | `pld.py` |
| Generic `ValueError` | 422 | catch-all |

## Key Service Function Signatures (for reference)

```python
# ingestion.py:363
def import_pld_session(source, output, *, overwrite=False) -> IngestionReport

# metadata.py:284
def validate_metadata_csv(path) -> ValidationReport

# transcripts.py:246
def normalize_dataset(dataset) -> NormalizationReport

# dataset.py:238
def build_dataset(dataset, output, *, train_ratio=0.70, val_ratio=0.15, test_ratio=0.15, seed=42, overwrite=False) -> DatasetBuildReport

# asr.py:135
def load_model(model_name, device=None) -> Any  # HF pipeline, cache this

# asr.py:182
def transcribe_split(split_csv, dataset_dir, pipe, *, language=None, output_path, progress_fn=None) -> list[TranscriptionResult]

# asr.py:320
def evaluate_predictions(predictions_csv, *, references_csv=None, model="baseline", language="kapampangan") -> BenchmarkMetrics

# benchmark.py:52
def generate_benchmark_report(metrics, predictions, output_path) -> Path

# benchmark.py:135
def generate_comparison_report(baseline, finetuned, output_path) -> Path

# finetune.py:295
def finetune_model(dataset_dir, output_dir, *, base_model="openai/whisper-tiny", language="tl", epochs=3, max_steps=None, batch_size=8, learning_rate=1e-5, train_split="train", eval_split="validation", progress_fn=None) -> FineTuneReport
```

## Verification Checklist

1. `pip install -e ".[api,dev]"` succeeds.
2. `ruff check . && black --check .` passes (lint + format).
3. `pytest` passes all tests including new `test_api.py` and `test_jobs.py`.
4. `bosesph-api` starts, `GET /docs` shows the OpenAPI UI with all endpoints.
5. Smoke test the sync endpoints (import-pld, validate, normalize) with `curl`.
6. Smoke test a background job (build-dataset) — submit, poll `/jobs/{id}`, see `succeeded`.
7. `GET /project-status` returns the correct shape.
8. `GET /download-output?path=dataset` returns a zip file.
9. If `[asr]`/`[train]` not installed: transcribe/train endpoints return 422 with a clear install hint.

## Important Notes for Implementers

- **Lazy imports**: ASR/train modules (`asr`, `benchmark`, `finetune`) must be imported **inside** endpoint/job function bodies, never at module top level. This matches how `cli.py` does it (lines 351, 406, 472, 516) and keeps the API runnable without `torch`.
- **`pydantic-settings`**: `ApiSettings` uses `pydantic_settings.BaseSettings`. This requires the `pydantic-settings` package. Either add it to the `[api]` extra or use plain `pydantic.BaseModel` with manual env reading. Check if `pydantic-settings` ships with `fastapi` — it does NOT, so add it to the `[api]` extra: `"pydantic-settings>=2.2"`.
- **Thread safety**: Service functions do file I/O (read/write CSV, copy files). Concurrent requests to the same dataset directory could conflict. The existing `_checkpoint` in `review.py` uses atomic temp+rename, which is safe. But `build_dataset` and `normalize_dataset` also write atomically. For the MVP this is acceptable — document that concurrent writes to the same dataset are unsupported.
- **`settings.py` circular import**: `resolve_path` is used by routes, which also import from `models.py`. Keep `settings.py` free of imports from other `bosesph.api` modules.
- **`review.decide_clip` circular import**: Do NOT import `bosesph.api.models` from `review.py`. Define the return type (`ClipDecisionResult`) in `review.py` itself. The API route constructs the API response model from it.
