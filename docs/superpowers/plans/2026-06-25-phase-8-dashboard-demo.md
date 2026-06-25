# Phase 8 Dashboard and Demo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a two-page Next.js dashboard and direct single-audio ASR demo using real FastAPI data, controlled model choices, optional WER/CER scoring, and automatic upload cleanup.

**Architecture:** Extend FastAPI with explicit dashboard and demo contracts, keeping inference in the existing in-process job manager. Build `apps/web` as a Next.js App Router client that calls FastAPI directly, polls jobs, renders real status cards, and previews audio with wavesurfer.js.

**Tech Stack:** Python 3.10+, FastAPI, Pydantic, pytest, Next.js 16 App Router, React 19, TypeScript, CSS, wavesurfer.js 7, Vitest, Testing Library, ESLint, Prettier, pnpm.

---

## File Map

### Backend

- Modify `src/bosesph/api/settings.py`: CORS origins and demo upload limits.
- Modify `src/bosesph/api/app.py`: CORS middleware and demo router registration.
- Modify `src/bosesph/api/models.py`: dashboard, option, and demo-result contracts.
- Create `src/bosesph/api/demo.py`: controlled language/model discovery and temporary upload lifecycle helpers.
- Create `src/bosesph/api/routes/demo.py`: demo options and transient transcription endpoints.
- Modify `src/bosesph/api/routes/files.py`: deterministic baseline/fine-tuned dashboard metrics.
- Modify `tests/test_api.py`: endpoint, CORS, status, scoring, and cleanup tests.

### Frontend

- Delete `apps/web/.gitkeep`.
- Create `apps/web/package.json`: scripts and dependencies.
- Create `apps/web/pnpm-lock.yaml`: generated lockfile.
- Create `apps/web/next.config.ts`, `tsconfig.json`, `eslint.config.mjs`,
  `prettier.config.mjs`, `vitest.config.ts`,
  `vitest.setup.ts`: application and tooling configuration.
- Create `apps/web/.prettierignore`: generated-file exclusions.
- Create `apps/web/.env.example`: public API base URL.
- Create `apps/web/app/layout.tsx`, `app/globals.css`: shell and visual system.
- Create `apps/web/app/page.tsx`: dashboard route.
- Create `apps/web/app/demo/page.tsx`: demo route.
- Create `apps/web/components/app-shell.tsx`: shared navigation.
- Create `apps/web/components/status-card.tsx`: status metric presentation.
- Create `apps/web/components/dashboard.tsx`: dashboard data state.
- Create `apps/web/components/demo-form.tsx`: upload and job workflow.
- Create `apps/web/components/waveform.tsx`: wavesurfer lifecycle.
- Create `apps/web/lib/api.ts`: typed FastAPI client and polling.
- Create `apps/web/lib/dashboard.ts`: status-card mapping.
- Create `apps/web/lib/format.ts`: display formatting.
- Create `apps/web/tests/dashboard.test.ts`,
  `tests/dashboard-page.test.tsx`, `tests/demo-form.test.tsx`: frontend tests.

### Documentation

- Modify `README.md`: frontend setup and run commands.
- Modify `Tasks.md`, `Simple_Tasks.md`: mark Phase 8 completed only after final verification.

---

### Task 1: Make Project Status Deterministic

**Files:**
- Modify: `src/bosesph/api/models.py`
- Modify: `src/bosesph/api/routes/files.py`
- Modify: `tests/test_api.py`

- [ ] **Step 1: Write failing status-contract tests**

Add tests that create explicit baseline and fine-tuned result files and assert
that both are returned independently:

```python
def test_project_status_returns_dashboard_metrics(
    client: tuple[TestClient, Path],
) -> None:
    test_client, workspace = client
    dataset = workspace / "dataset"
    baseline = workspace / "benchmark" / "baseline"
    finetuned = workspace / "benchmark" / "finetuned"
    model = workspace / "model" / "bosesph-kapampangan-v1"
    dataset.mkdir(parents=True)
    baseline.mkdir(parents=True)
    finetuned.mkdir(parents=True)
    model.mkdir(parents=True)

    (dataset / "dataset_stats.json").write_text(
        json.dumps(
            {
                "total_clips": 68,
                "total_duration_seconds": 612.0,
                "total_duration_display": "10m 12s",
                "total_speakers": 4,
                "source_counts": {"approved": 68},
            }
        ),
        encoding="utf-8",
    )
    (baseline / "results.json").write_text(
        json.dumps({"wer": 0.91, "cer": 0.52}),
        encoding="utf-8",
    )
    (finetuned / "results.json").write_text(
        json.dumps({"wer": 0.75, "cer": 0.34}),
        encoding="utf-8",
    )
    (model / "model_card.md").write_text("# Model", encoding="utf-8")
    (model / "training_config.json").write_text(
        json.dumps({"base_model": "openai/whisper-tiny"}),
        encoding="utf-8",
    )

    response = test_client.get("/project-status")

    assert response.status_code == 200
    assert response.json() == {
        "dataset_available": True,
        "dataset_stats": {
            "total_clips": 68,
            "total_duration_seconds": 612.0,
            "total_duration_display": "10m 12s",
            "total_speakers": 4,
            "source_counts": {"approved": 68},
        },
        "baseline_metrics": {"wer": 0.91, "cer": 0.52},
        "finetuned_metrics": {"wer": 0.75, "cer": 0.34},
        "model_available": True,
        "model_dir": "model/bosesph-kapampangan-v1",
        "model_version": "bosesph-kapampangan-v1",
    }


def test_project_status_uses_none_for_missing_outputs(
    client: tuple[TestClient, Path],
) -> None:
    test_client, _ = client

    response = test_client.get("/project-status")

    assert response.status_code == 200
    assert response.json() == {
        "dataset_available": False,
        "dataset_stats": None,
        "baseline_metrics": None,
        "finetuned_metrics": None,
        "model_available": False,
        "model_dir": None,
        "model_version": None,
    }
```

Add `import json` to `tests/test_api.py`.

- [ ] **Step 2: Run the new tests and verify failure**

Run:

```bash
.venv/bin/pytest tests/test_api.py::test_project_status_returns_dashboard_metrics tests/test_api.py::test_project_status_uses_none_for_missing_outputs -v
```

Expected: FAIL because `ProjectStatus` still exposes one ambiguous
`benchmark_results` field.

- [ ] **Step 3: Replace the status model**

Replace `ProjectStatus` in `src/bosesph/api/models.py` with:

```python
class MetricSummary(BaseModel):
    """WER/CER values displayed by the dashboard."""

    wer: float
    cer: float


class ProjectStatus(BaseModel):
    """Aggregated project state for ``GET /project-status``."""

    dataset_available: bool = False
    dataset_stats: dict[str, Any] | None = None
    baseline_metrics: MetricSummary | None = None
    finetuned_metrics: MetricSummary | None = None
    model_available: bool = False
    model_dir: str | None = None
    model_version: str | None = None
```

- [ ] **Step 4: Implement deterministic status discovery**

Replace `project_status()` in `src/bosesph/api/routes/files.py` with:

```python
def _read_json(path: Path) -> dict[str, object] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _metric_summary(path: Path) -> dict[str, float] | None:
    data = _read_json(path)
    if data is None or "wer" not in data or "cer" not in data:
        return None
    return {"wer": float(data["wer"]), "cer": float(data["cer"])}


@router.get("/project-status", response_model=ProjectStatus)
def project_status(request: Request) -> ProjectStatus:
    """Return deterministic dashboard data from conventional output paths."""
    ws: Path = request.app.state.settings.workspace.resolve()
    dataset_stats = _read_json(ws / "dataset" / "dataset_stats.json")
    model_root = ws / "model"
    model_dir: Path | None = None

    if model_root.is_dir():
        model_dir = next(
            (
                child
                for child in sorted(model_root.iterdir())
                if child.is_dir() and (child / "model_card.md").is_file()
            ),
            None,
        )

    return ProjectStatus(
        dataset_available=dataset_stats is not None,
        dataset_stats=dataset_stats,
        baseline_metrics=_metric_summary(
            ws / "benchmark" / "baseline" / "results.json"
        ),
        finetuned_metrics=_metric_summary(
            ws / "benchmark" / "finetuned" / "results.json"
        ),
        model_available=model_dir is not None,
        model_dir=str(model_dir.relative_to(ws)) if model_dir else None,
        model_version=model_dir.name if model_dir else None,
    )
```

- [ ] **Step 5: Run status and API regression tests**

Run:

```bash
.venv/bin/pytest tests/test_api.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/bosesph/api/models.py src/bosesph/api/routes/files.py tests/test_api.py
git commit -m "feat(api): expose dashboard project metrics"
```

---

### Task 2: Add Controlled Demo Options

**Files:**
- Create: `src/bosesph/api/demo.py`
- Create: `src/bosesph/api/routes/demo.py`
- Modify: `src/bosesph/api/models.py`
- Modify: `src/bosesph/api/app.py`
- Modify: `tests/test_api.py`

- [ ] **Step 1: Write failing option-discovery tests**

```python
def test_demo_options_return_controlled_choices(
    client: tuple[TestClient, Path],
) -> None:
    test_client, workspace = client
    model_dir = workspace / "model" / "bosesph-kapampangan-v1"
    saved_model = model_dir / "model"
    saved_model.mkdir(parents=True)
    (saved_model / "config.json").write_text("{}", encoding="utf-8")
    (model_dir / "model_card.md").write_text("# Model", encoding="utf-8")
    (model_dir / "training_config.json").write_text(
        json.dumps({"language": "tl"}),
        encoding="utf-8",
    )

    response = test_client.get("/demo/options")

    assert response.status_code == 200
    payload = response.json()
    assert payload["default_model_id"] == "baseline"
    assert payload["default_language_id"] == "kapampangan"
    assert payload["languages"] == [
        {
            "id": "kapampangan",
            "label": "Kapampangan",
            "description": "Kapampangan speech with model-specific decoding.",
        },
        {
            "id": "auto",
            "label": "Auto-detect",
            "description": "Let the selected model determine decoding language.",
        },
    ]
    assert payload["models"][0]["id"] == "baseline"
    assert payload["models"][0]["available"] is True
    assert payload["models"][1]["id"] == "finetuned"
    assert payload["models"][1]["available"] is True
    assert payload["models"][1]["model_path"] == "model/bosesph-kapampangan-v1/model"


def test_demo_options_disable_missing_finetuned_model(
    client: tuple[TestClient, Path],
) -> None:
    test_client, _ = client

    response = test_client.get("/demo/options")

    assert response.status_code == 200
    finetuned = response.json()["models"][1]
    assert finetuned["available"] is False
    assert finetuned["unavailable_reason"] == "No local fine-tuned model found."
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
.venv/bin/pytest tests/test_api.py::test_demo_options_return_controlled_choices tests/test_api.py::test_demo_options_disable_missing_finetuned_model -v
```

Expected: FAIL with `404 Not Found`.

- [ ] **Step 3: Add option response models**

Append to `src/bosesph/api/models.py`:

```python
class DemoLanguageOption(BaseModel):
    id: str
    label: str
    description: str


class DemoModelOption(BaseModel):
    id: str
    label: str
    model_path: str
    available: bool
    unavailable_reason: str | None = None
    decoding_language: str | None = None


class DemoOptions(BaseModel):
    languages: list[DemoLanguageOption]
    models: list[DemoModelOption]
    default_language_id: str
    default_model_id: str
```

- [ ] **Step 4: Implement option discovery**

Create `src/bosesph/api/demo.py`:

```python
"""Controlled model options and transient demo helpers."""

from __future__ import annotations

import json
from pathlib import Path

from bosesph.api.models import (
    DemoLanguageOption,
    DemoModelOption,
    DemoOptions,
)


def discover_demo_options(workspace: Path) -> DemoOptions:
    model_root = workspace.resolve() / "model"
    candidate = next(
        (
            child
            for child in sorted(model_root.iterdir())
            if child.is_dir()
            and (child / "model_card.md").is_file()
            and (child / "model" / "config.json").is_file()
        ),
        None,
    ) if model_root.is_dir() else None

    language = "tl"
    if candidate is not None:
        config_path = candidate / "training_config.json"
        if config_path.is_file():
            config = json.loads(config_path.read_text(encoding="utf-8"))
            language = str(config.get("language") or "tl")

    return DemoOptions(
        languages=[
            DemoLanguageOption(
                id="kapampangan",
                label="Kapampangan",
                description="Kapampangan speech with model-specific decoding.",
            ),
            DemoLanguageOption(
                id="auto",
                label="Auto-detect",
                description="Let the selected model determine decoding language.",
            ),
        ],
        models=[
            DemoModelOption(
                id="baseline",
                label="Whisper Small (baseline)",
                model_path="openai/whisper-small",
                available=True,
            ),
            DemoModelOption(
                id="finetuned",
                label="BosesPH fine-tuned model",
                model_path=(
                    str((candidate / "model").relative_to(workspace.resolve()))
                    if candidate
                    else ""
                ),
                available=candidate is not None,
                unavailable_reason=(
                    None if candidate else "No local fine-tuned model found."
                ),
                decoding_language=language if candidate else None,
            ),
        ],
        default_language_id="kapampangan",
        default_model_id="baseline",
    )


def select_demo_model(
    options: DemoOptions,
    model_id: str,
    language_id: str,
) -> tuple[DemoModelOption, str | None]:
    model = next((item for item in options.models if item.id == model_id), None)
    if model is None:
        raise ValueError(f"Unknown demo model: {model_id}")
    if not model.available:
        raise ValueError(model.unavailable_reason or "Selected model is unavailable.")
    if language_id not in {item.id for item in options.languages}:
        raise ValueError(f"Unknown demo language: {language_id}")
    if language_id == "auto" or model.id == "baseline":
        return model, None
    return model, model.decoding_language
```

- [ ] **Step 5: Add and register the options route**

Create `src/bosesph/api/routes/demo.py`:

```python
"""Direct single-audio demo endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Request

from bosesph.api.demo import discover_demo_options
from bosesph.api.models import DemoOptions

router = APIRouter(prefix="/demo", tags=["demo"])


@router.get("/options", response_model=DemoOptions)
def demo_options(request: Request) -> DemoOptions:
    return discover_demo_options(request.app.state.settings.workspace)
```

Import `demo` in `src/bosesph/api/app.py` and register:

```python
from bosesph.api.routes import demo, files, jobs, pipeline

# ...
app.include_router(demo.router)
```

- [ ] **Step 6: Run tests**

Run:

```bash
.venv/bin/pytest tests/test_api.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/bosesph/api/demo.py src/bosesph/api/routes/demo.py src/bosesph/api/models.py src/bosesph/api/app.py tests/test_api.py
git commit -m "feat(api): publish controlled demo options"
```

---

### Task 3: Add Transient Single-Audio Transcription

**Files:**
- Modify: `src/bosesph/api/demo.py`
- Modify: `src/bosesph/api/models.py`
- Modify: `src/bosesph/api/routes/demo.py`
- Modify: `tests/test_api.py`

- [ ] **Step 1: Write failing success and cleanup tests**

```python
def test_demo_transcribe_scores_reference_and_deletes_upload(
    client: tuple[TestClient, Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    test_client, workspace = client
    wav_path = tmp_path / "clip.wav"
    write_pcm_wav(wav_path, duration=0.1)
    seen_paths: list[Path] = []

    monkeypatch.setattr("bosesph.asr.load_model", lambda model: object())

    def fake_transcribe(
        pipe: object,
        audio_path: Path,
        *,
        language: str | None,
    ) -> str:
        seen_paths.append(audio_path)
        assert audio_path.is_file()
        assert language is None
        return "Masanting ya ing aldo"

    monkeypatch.setattr("bosesph.asr.transcribe_file", fake_transcribe)

    response = test_client.post(
        "/demo/transcribe",
        data={
            "model_id": "baseline",
            "language_id": "kapampangan",
            "reference": "Masanting ya ing aldo.",
        },
        files={"audio": ("clip.wav", wav_path.read_bytes(), "audio/wav")},
    )
    job = poll_job(test_client, response.json()["id"])

    assert response.status_code == 202
    assert job["status"] == "succeeded"
    assert job["result"] == {
        "prediction": "Masanting ya ing aldo",
        "model_id": "baseline",
        "model_label": "Whisper Small (baseline)",
        "language_id": "kapampangan",
        "wer": 0.0,
        "cer": 0.0,
    }
    assert seen_paths
    assert not seen_paths[0].parent.exists()
    assert not (workspace / ".demo_uploads").exists()


def test_demo_transcribe_deletes_upload_after_failure(
    client: tuple[TestClient, Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    test_client, workspace = client
    wav_path = tmp_path / "clip.wav"
    write_pcm_wav(wav_path, duration=0.1)

    monkeypatch.setattr("bosesph.asr.load_model", lambda model: object())
    monkeypatch.setattr(
        "bosesph.asr.transcribe_file",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("inference failed")),
    )

    response = test_client.post(
        "/demo/transcribe",
        data={"model_id": "baseline", "language_id": "auto"},
        files={"audio": ("clip.wav", wav_path.read_bytes(), "audio/wav")},
    )
    job = poll_job(test_client, response.json()["id"])

    assert job["status"] == "failed"
    assert job["error"] == "inference failed"
    assert not (workspace / ".demo_uploads").exists()
```

- [ ] **Step 2: Write failing validation tests**

```python
@pytest.mark.parametrize(
    ("data", "filename", "content", "expected"),
    [
        (
            {"model_id": "unknown", "language_id": "auto"},
            "clip.wav",
            b"RIFF",
            "Unknown demo model",
        ),
        (
            {"model_id": "baseline", "language_id": "unknown"},
            "clip.wav",
            b"RIFF",
            "Unknown demo language",
        ),
        (
            {"model_id": "baseline", "language_id": "auto"},
            "clip.mp3",
            b"audio",
            "Only PCM WAV uploads are supported",
        ),
        (
            {"model_id": "baseline", "language_id": "auto"},
            "clip.wav",
            b"",
            "Uploaded audio is empty",
        ),
    ],
)
def test_demo_transcribe_rejects_invalid_input(
    client: tuple[TestClient, Path],
    data: dict[str, str],
    filename: str,
    content: bytes,
    expected: str,
) -> None:
    test_client, _ = client

    response = test_client.post(
        "/demo/transcribe",
        data=data,
        files={"audio": (filename, content, "audio/wav")},
    )

    assert response.status_code == 422
    assert expected in response.json()["detail"]
```

- [ ] **Step 3: Run tests and verify failure**

Run:

```bash
.venv/bin/pytest tests/test_api.py -k "demo_transcribe" -v
```

Expected: FAIL with `405 Method Not Allowed`.

- [ ] **Step 4: Add the result model**

Append to `src/bosesph/api/models.py`:

```python
class DemoTranscriptionResult(BaseModel):
    prediction: str
    model_id: str
    model_label: str
    language_id: str
    wer: float | None = None
    cer: float | None = None
```

- [ ] **Step 5: Add upload and inference helpers**

Append to `src/bosesph/api/demo.py`:

```python
import logging
import shutil
import uuid
from collections.abc import Callable

from fastapi import UploadFile

from bosesph.api.models import DemoTranscriptionResult

LOGGER = logging.getLogger(__name__)
CHUNK_SIZE = 256 * 1024


def save_demo_upload(workspace: Path, upload: UploadFile) -> tuple[Path, Path]:
    filename = upload.filename or ""
    if Path(filename).suffix.lower() != ".wav":
        raise ValueError("Only PCM WAV uploads are supported.")

    root = workspace.resolve() / ".demo_uploads"
    directory = root / uuid.uuid4().hex
    directory.mkdir(parents=True)
    target = directory / "audio.wav"
    size = 0
    with target.open("wb") as handle:
        while chunk := upload.file.read(CHUNK_SIZE):
            size += len(chunk)
            handle.write(chunk)
    if size == 0:
        shutil.rmtree(directory, ignore_errors=True)
        if root.is_dir() and not any(root.iterdir()):
            root.rmdir()
        raise ValueError("Uploaded audio is empty.")
    return target, directory


def remove_demo_upload(directory: Path) -> None:
    root = directory.parent
    try:
        shutil.rmtree(directory)
        if root.is_dir() and not any(root.iterdir()):
            root.rmdir()
    except OSError:
        LOGGER.exception("Failed to remove demo upload directory %s", directory)


def run_demo_transcription(
    *,
    audio_path: Path,
    upload_directory: Path,
    model: DemoModelOption,
    language_id: str,
    decoding_language: str | None,
    reference: str | None,
    progress_fn: Callable[[object], None],
) -> DemoTranscriptionResult:
    try:
        from bosesph.asr import calculate_metrics, load_model, transcribe_file

        progress_fn("loading-model")
        pipe = load_model(model.model_path)
        progress_fn("transcribing")
        prediction = transcribe_file(
            pipe,
            audio_path,
            language=decoding_language,
        )
        wer: float | None = None
        cer: float | None = None
        if reference and reference.strip():
            metrics = calculate_metrics(
                [reference],
                [prediction],
                model=model.id,
                language=language_id,
            )
            wer = metrics.wer
            cer = metrics.cer
        return DemoTranscriptionResult(
            prediction=prediction,
            model_id=model.id,
            model_label=model.label,
            language_id=language_id,
            wer=wer,
            cer=cer,
        )
    finally:
        remove_demo_upload(upload_directory)
```

- [ ] **Step 6: Add the multipart endpoint**

Extend imports and append to `src/bosesph/api/routes/demo.py`:

```python
from typing import Annotated

from fastapi import File, Form, UploadFile, status

from bosesph.api.demo import (
    run_demo_transcription,
    save_demo_upload,
    select_demo_model,
)
from bosesph.api.jobs import Job


@router.post(
    "/transcribe",
    response_model=Job,
    status_code=status.HTTP_202_ACCEPTED,
)
def transcribe_demo_audio(
    request: Request,
    audio: Annotated[UploadFile, File()],
    model_id: Annotated[str, Form()],
    language_id: Annotated[str, Form()],
    reference: Annotated[str | None, Form()] = None,
) -> Job:
    workspace = request.app.state.settings.workspace
    options = discover_demo_options(workspace)
    model, decoding_language = select_demo_model(
        options,
        model_id,
        language_id,
    )
    job_model = model.model_copy(
        update={
            "model_path": (
                str(workspace.resolve() / model.model_path)
                if model.id == "finetuned"
                else model.model_path
            )
        }
    )
    audio_path, upload_directory = save_demo_upload(workspace, audio)

    return request.app.state.jobs.submit(
        "demo-transcribe",
        run_demo_transcription,
        audio_path=audio_path,
        upload_directory=upload_directory,
        model=job_model,
        language_id=language_id,
        decoding_language=decoding_language,
        reference=reference,
    )
```

- [ ] **Step 7: Run demo and API tests**

Run:

```bash
.venv/bin/pytest tests/test_api.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add src/bosesph/api/demo.py src/bosesph/api/models.py src/bosesph/api/routes/demo.py tests/test_api.py
git commit -m "feat(api): add transient audio demo jobs"
```

---

### Task 4: Configure Explicit CORS

**Files:**
- Modify: `src/bosesph/api/settings.py`
- Modify: `src/bosesph/api/app.py`
- Modify: `tests/test_api.py`

- [ ] **Step 1: Write failing CORS tests**

```python
def test_api_allows_configured_frontend_origin(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BOSESPH_WORKSPACE", str(tmp_path / "workspace"))
    monkeypatch.setenv(
        "BOSESPH_CORS_ORIGINS",
        '["http://localhost:3000","http://127.0.0.1:3000"]',
    )
    with TestClient(create_app()) as test_client:
        response = test_client.options(
            "/project-status",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_api_rejects_unconfigured_frontend_origin(
    client: tuple[TestClient, Path],
) -> None:
    test_client, _ = client
    response = test_client.options(
        "/project-status",
        headers={
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
.venv/bin/pytest tests/test_api.py -k "frontend_origin" -v
```

Expected: FAIL because CORS middleware is absent.

- [ ] **Step 3: Add settings and middleware**

Add to `ApiSettings`:

```python
cors_origins: list[str] = Field(
    default=["http://localhost:3000", "http://127.0.0.1:3000"],
    description="Browser origins allowed to call the API.",
)
demo_max_upload_bytes: int = Field(
    default=25 * 1024 * 1024,
    gt=0,
    description="Maximum accepted demo upload size.",
)
```

In `src/bosesph/api/app.py`, import and register middleware immediately after
creating the app:

```python
from fastapi.middleware.cors import CORSMiddleware

# ...
app = FastAPI(title="BosesPH Toolkit API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

Update the helper signature:

```python
def save_demo_upload(
    workspace: Path,
    upload: UploadFile,
    *,
    max_bytes: int,
) -> tuple[Path, Path]:
```

Fail once `size` exceeds the limit:

```python
if size > max_bytes:
    shutil.rmtree(directory, ignore_errors=True)
    if root.is_dir() and not any(root.iterdir()):
        root.rmdir()
    raise ValueError(f"Uploaded audio exceeds the {max_bytes}-byte limit.")
```

Update the route call:

```python
audio_path, upload_directory = save_demo_upload(
    workspace,
    audio,
    max_bytes=request.app.state.settings.demo_max_upload_bytes,
)
```

- [ ] **Step 4: Run tests**

Run:

```bash
.venv/bin/pytest tests/test_api.py -q
.venv/bin/ruff check src/bosesph/api tests/test_api.py
.venv/bin/black --check src/bosesph/api tests/test_api.py
```

Expected: all commands pass.

- [ ] **Step 5: Commit**

```bash
git add src/bosesph/api/settings.py src/bosesph/api/app.py src/bosesph/api/demo.py src/bosesph/api/routes/demo.py tests/test_api.py
git commit -m "feat(api): configure dashboard CORS"
```

---

### Task 5: Scaffold the Next.js Application

**Files:**
- Delete: `apps/web/.gitkeep`
- Create: `apps/web/package.json`
- Create: `apps/web/pnpm-lock.yaml`
- Create: `apps/web/next.config.ts`
- Create: `apps/web/tsconfig.json`
- Create: `apps/web/eslint.config.mjs`
- Create: `apps/web/prettier.config.mjs`
- Create: `apps/web/.prettierignore`
- Create: `apps/web/vitest.config.ts`
- Create: `apps/web/vitest.setup.ts`
- Create: `apps/web/.env.example`
- Create: `apps/web/app/layout.tsx`
- Create: `apps/web/app/globals.css`
- Create: `apps/web/app/page.tsx`

- [ ] **Step 1: Enable Corepack and verify pnpm**

Run:

```bash
corepack enable
corepack prepare pnpm@10.17.1 --activate
pnpm --version
```

Expected: `10.17.1`.

- [ ] **Step 2: Create package metadata**

Create `apps/web/package.json`:

```json
{
  "name": "@bosesph/web",
  "version": "0.1.0",
  "private": true,
  "packageManager": "pnpm@10.17.1",
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "eslint .",
    "format": "prettier --write .",
    "format:check": "prettier --check .",
    "test": "vitest run --passWithNoTests"
  },
  "dependencies": {
    "@fontsource-variable/manrope": "^5.2.8",
    "@fontsource-variable/newsreader": "^5.2.8",
    "next": "16.2.9",
    "react": "^19.2.0",
    "react-dom": "^19.2.0",
    "wavesurfer.js": "7.12.6"
  },
  "devDependencies": {
    "@testing-library/jest-dom": "^6.9.1",
    "@testing-library/react": "^16.3.0",
    "@testing-library/user-event": "^14.6.1",
    "@types/node": "^24.0.0",
    "@types/react": "^19.2.0",
    "@types/react-dom": "^19.2.0",
    "eslint": "^9.0.0",
    "eslint-config-next": "16.2.9",
    "jsdom": "^27.0.0",
    "prettier": "^3.6.0",
    "typescript": "^5.9.0",
    "vitest": "^4.0.0"
  }
}
```

- [ ] **Step 3: Create application and tool configuration**

Create `apps/web/next.config.ts`:

```typescript
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
};

export default nextConfig;
```

Create `apps/web/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2017",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": false,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "react-jsx",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": { "@/*": ["./*"] }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

Create `apps/web/eslint.config.mjs`:

```javascript
import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTypeScript from "eslint-config-next/typescript";

export default defineConfig([
  ...nextVitals,
  ...nextTypeScript,
  globalIgnores([".next/**", "coverage/**", "next-env.d.ts"]),
]);
```

Create `apps/web/prettier.config.mjs`:

```javascript
export default {
  semi: true,
  singleQuote: false,
  trailingComma: "all",
};
```

Create `apps/web/.prettierignore`:

```text
.next
coverage
node_modules
pnpm-lock.yaml
```

Create `apps/web/vitest.config.ts`:

```typescript
import { defineConfig } from "vitest/config";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  test: {
    environment: "jsdom",
    setupFiles: ["./vitest.setup.ts"],
    restoreMocks: true,
  },
  resolve: {
    alias: {
      "@": root,
    },
  },
});
```

Create `apps/web/vitest.setup.ts`:

```typescript
import "@testing-library/jest-dom/vitest";
```

Create `apps/web/.env.example`:

```dotenv
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

- [ ] **Step 4: Create the minimum App Router shell**

Create `apps/web/app/layout.tsx`:

```tsx
import "@fontsource-variable/manrope";
import "@fontsource-variable/newsreader";
import "./globals.css";
import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "BosesPH Toolkit",
  description: "Build and evaluate Philippine-language speech resources.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
```

Create `apps/web/app/page.tsx`:

```tsx
export default function DashboardPage() {
  return <main>BosesPH Toolkit</main>;
}
```

Create `apps/web/app/globals.css`:

```css
:root {
  --ink: #15231d;
  --muted: #5c6b63;
  --paper: #f2efe6;
  --card: #fffdf6;
  --line: #c9c6b8;
  --leaf: #1d5945;
  --sun: #e8a33b;
  --coral: #d8684f;
  --font-sans: "Manrope Variable", sans-serif;
  --font-serif: "Newsreader Variable", serif;
}

* {
  box-sizing: border-box;
}

html {
  background: var(--paper);
}

body {
  margin: 0;
  color: var(--ink);
  font-family: var(--font-sans);
  background:
    radial-gradient(circle at 12% 8%, rgb(232 163 59 / 18%), transparent 28rem),
    linear-gradient(135deg, #f7f3e8 0%, #e8eee7 100%);
  min-height: 100vh;
}

button,
input,
select,
textarea {
  font: inherit;
}

a {
  color: inherit;
}
```

- [ ] **Step 5: Install dependencies and generate the lockfile**

Run:

```bash
cd apps/web
pnpm install
pnpm format
pnpm lint
pnpm test
pnpm build
```

Expected: install succeeds, lint and build pass, Vitest exits successfully with
no test files.

- [ ] **Step 6: Commit**

```bash
git add apps/web
git commit -m "feat(web): scaffold Next.js dashboard"
```

---

### Task 6: Add Typed API Client and Dashboard Mapping

**Files:**
- Create: `apps/web/lib/api.ts`
- Create: `apps/web/lib/dashboard.ts`
- Create: `apps/web/lib/format.ts`
- Create: `apps/web/tests/dashboard.test.ts`

- [ ] **Step 1: Write failing dashboard mapping tests**

Create `apps/web/tests/dashboard.test.ts`:

```typescript
import { describe, expect, it } from "vitest";
import { toStatusCards } from "@/lib/dashboard";

describe("toStatusCards", () => {
  it("maps real project status values", () => {
    const cards = toStatusCards({
      dataset_available: true,
      dataset_stats: {
        total_clips: 68,
        total_duration_seconds: 612,
        total_duration_display: "10m 12s",
        total_speakers: 4,
        source_counts: { approved: 68 },
      },
      baseline_metrics: { wer: 0.91, cer: 0.52 },
      finetuned_metrics: { wer: 0.75, cer: 0.34 },
      model_available: true,
      model_dir: "model/bosesph-kapampangan-v1",
      model_version: "bosesph-kapampangan-v1",
    });

    expect(cards.map((card) => card.value)).toEqual([
      "68",
      "68",
      "4",
      "10.2",
      "91.0%",
      "75.0%",
      "bosesph-kapampangan-v1",
    ]);
  });

  it("does not fabricate missing values", () => {
    const cards = toStatusCards({
      dataset_available: false,
      dataset_stats: null,
      baseline_metrics: null,
      finetuned_metrics: null,
      model_available: false,
      model_dir: null,
      model_version: null,
    });

    expect(cards.every((card) => card.value === "Not available")).toBe(true);
  });
});
```

- [ ] **Step 2: Run and verify failure**

Run:

```bash
pnpm --dir apps/web test tests/dashboard.test.ts
```

Expected: FAIL because `@/lib/dashboard` does not exist.

- [ ] **Step 3: Create API types and client**

Create `apps/web/lib/api.ts`:

```typescript
export type MetricSummary = { wer: number; cer: number };

export type ProjectStatus = {
  dataset_available: boolean;
  dataset_stats: {
    total_clips?: number;
    total_duration_seconds?: number;
    total_duration_display?: string;
    total_speakers?: number;
    source_counts?: { approved?: number };
  } | null;
  baseline_metrics: MetricSummary | null;
  finetuned_metrics: MetricSummary | null;
  model_available: boolean;
  model_dir: string | null;
  model_version: string | null;
};

export type DemoLanguageOption = {
  id: string;
  label: string;
  description: string;
};

export type DemoModelOption = {
  id: string;
  label: string;
  model_path: string;
  available: boolean;
  unavailable_reason: string | null;
  decoding_language: string | null;
};

export type DemoOptions = {
  languages: DemoLanguageOption[];
  models: DemoModelOption[];
  default_language_id: string;
  default_model_id: string;
};

export type DemoResult = {
  prediction: string;
  model_id: string;
  model_label: string;
  language_id: string;
  wer: number | null;
  cer: number | null;
};

export type Job = {
  id: string;
  type: string;
  status: "queued" | "running" | "succeeded" | "failed";
  progress: string | null;
  result: DemoResult | null;
  error: string | null;
};

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, init);
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as
      | { detail?: string }
      | null;
    throw new Error(payload?.detail ?? `API request failed (${response.status}).`);
  }
  return (await response.json()) as T;
}

export function getProjectStatus(): Promise<ProjectStatus> {
  return requestJson<ProjectStatus>("/project-status", { cache: "no-store" });
}

export function getDemoOptions(): Promise<DemoOptions> {
  return requestJson<DemoOptions>("/demo/options", { cache: "no-store" });
}

export function submitDemo(formData: FormData): Promise<Job> {
  return requestJson<Job>("/demo/transcribe", {
    method: "POST",
    body: formData,
  });
}

export function getJob(jobId: string): Promise<Job> {
  return requestJson<Job>(`/jobs/${jobId}`, { cache: "no-store" });
}

export async function waitForJob(
  jobId: string,
  onUpdate: (job: Job) => void,
  signal: AbortSignal,
): Promise<Job> {
  while (!signal.aborted) {
    const job = await getJob(jobId);
    onUpdate(job);
    if (job.status === "succeeded" || job.status === "failed") {
      return job;
    }
    await new Promise<void>((resolve, reject) => {
      const timeout = window.setTimeout(resolve, 750);
      signal.addEventListener(
        "abort",
        () => {
          window.clearTimeout(timeout);
          reject(new DOMException("Polling aborted", "AbortError"));
        },
        { once: true },
      );
    });
  }
  throw new DOMException("Polling aborted", "AbortError");
}
```

- [ ] **Step 4: Implement formatting and card mapping**

Create `apps/web/lib/format.ts`:

```typescript
export function formatPercent(value: number | undefined): string {
  return value === undefined ? "Not available" : `${(value * 100).toFixed(1)}%`;
}

export function formatMinutes(seconds: number | undefined): string {
  return seconds === undefined ? "Not available" : (seconds / 60).toFixed(1);
}
```

Create `apps/web/lib/dashboard.ts`:

```typescript
import type { ProjectStatus } from "@/lib/api";
import { formatMinutes, formatPercent } from "@/lib/format";

export type StatusCardData = {
  label: string;
  value: string;
  note: string;
  tone: "leaf" | "sun" | "coral";
};

export function toStatusCards(status: ProjectStatus): StatusCardData[] {
  const stats = status.dataset_stats ?? {};
  const value = (input: number | undefined) =>
    input === undefined ? "Not available" : String(input);

  return [
    {
      label: "Dataset Clips",
      value: value(stats.total_clips),
      note: "Packaged speech clips",
      tone: "leaf",
    },
    {
      label: "Approved Clips",
      value: value(stats.source_counts?.approved),
      note: "Passed human review",
      tone: "leaf",
    },
    {
      label: "Speakers",
      value: value(stats.total_speakers),
      note: "Distinct speaker IDs",
      tone: "sun",
    },
    {
      label: "Total Minutes",
      value: formatMinutes(stats.total_duration_seconds),
      note: "Approved audio duration",
      tone: "sun",
    },
    {
      label: "Baseline WER",
      value: formatPercent(status.baseline_metrics?.wer),
      note: "Whisper baseline",
      tone: "coral",
    },
    {
      label: "Fine-tuned WER",
      value: formatPercent(status.finetuned_metrics?.wer),
      note: "Local model result",
      tone: "coral",
    },
    {
      label: "Model Version",
      value: status.model_version ?? "Not available",
      note: "Detected local package",
      tone: "leaf",
    },
  ];
}
```

- [ ] **Step 5: Run tests and checks**

Run:

```bash
pnpm --dir apps/web test tests/dashboard.test.ts
pnpm --dir apps/web lint
pnpm --dir apps/web format
pnpm --dir apps/web format:check
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add apps/web/lib apps/web/tests/dashboard.test.ts
git commit -m "feat(web): add typed API client"
```

---

### Task 7: Build the Dashboard

**Files:**
- Create: `apps/web/components/app-shell.tsx`
- Create: `apps/web/components/status-card.tsx`
- Create: `apps/web/components/dashboard.tsx`
- Modify: `apps/web/app/page.tsx`
- Modify: `apps/web/app/globals.css`
- Create: `apps/web/tests/dashboard-page.test.tsx`

- [ ] **Step 1: Write failing dashboard component tests**

Create `apps/web/tests/dashboard-page.test.tsx`:

```tsx
import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import Dashboard from "@/components/dashboard";
import * as api from "@/lib/api";

vi.mock("@/lib/api");

describe("Dashboard", () => {
  beforeEach(() => vi.resetAllMocks());

  it("renders real API status cards", async () => {
    vi.mocked(api.getProjectStatus).mockResolvedValue({
      dataset_available: true,
      dataset_stats: {
        total_clips: 68,
        total_duration_seconds: 612,
        total_speakers: 4,
        source_counts: { approved: 68 },
      },
      baseline_metrics: { wer: 0.91, cer: 0.52 },
      finetuned_metrics: { wer: 0.75, cer: 0.34 },
      model_available: true,
      model_dir: "model/bosesph-kapampangan-v1",
      model_version: "bosesph-kapampangan-v1",
    });

    render(<Dashboard />);

    expect(await screen.findAllByText("68")).toHaveLength(2);
    expect(screen.getByText("91.0%")).toBeInTheDocument();
    expect(screen.getByText("75.0%")).toBeInTheDocument();
  });

  it("shows an actionable API failure", async () => {
    vi.mocked(api.getProjectStatus).mockRejectedValue(
      new Error("Unable to reach the API."),
    );

    render(<Dashboard />);

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(
        "Unable to reach the API.",
      ),
    );
  });
});
```

- [ ] **Step 2: Run and verify failure**

Run:

```bash
pnpm --dir apps/web test tests/dashboard-page.test.tsx
```

Expected: FAIL because `Dashboard` does not exist.

- [ ] **Step 3: Create shared shell and cards**

Create `apps/web/components/app-shell.tsx`:

```tsx
import Link from "next/link";
import type { ReactNode } from "react";

export default function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="shell">
      <header className="topbar">
        <Link className="brand" href="/">
          <span className="brand-mark" aria-hidden="true">B</span>
          <span>
            <strong>BosesPH</strong>
            <small>Speech resource toolkit</small>
          </span>
        </Link>
        <nav aria-label="Primary navigation">
          <Link href="/">Dashboard</Link>
          <Link className="nav-accent" href="/demo">Open Demo</Link>
        </nav>
      </header>
      {children}
    </div>
  );
}
```

Create `apps/web/components/status-card.tsx`:

```tsx
import type { StatusCardData } from "@/lib/dashboard";

export default function StatusCard({ card }: { card: StatusCardData }) {
  return (
    <article className={`status-card status-card--${card.tone}`}>
      <span>{card.label}</span>
      <strong>{card.value}</strong>
      <p>{card.note}</p>
    </article>
  );
}
```

- [ ] **Step 4: Implement dashboard state and page**

Create `apps/web/components/dashboard.tsx`:

```tsx
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import StatusCard from "@/components/status-card";
import { getProjectStatus, type ProjectStatus } from "@/lib/api";
import { toStatusCards } from "@/lib/dashboard";

export default function Dashboard() {
  const [status, setStatus] = useState<ProjectStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    getProjectStatus()
      .then((value) => {
        if (!controller.signal.aborted) setStatus(value);
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(reason instanceof Error ? reason.message : "Unable to load status.");
        }
      });
    return () => controller.abort();
  }, []);

  return (
    <main>
      <section className="hero">
        <p className="eyebrow">Kapampangan ASR workspace</p>
        <h1>From community recordings to measurable speech models.</h1>
        <p>
          Track the dataset, benchmark, and local model package generated by
          the BosesPH pipeline.
        </p>
        <Link className="primary-action" href="/demo">
          Transcribe one clip
        </Link>
      </section>

      <section className="dashboard-section" aria-labelledby="status-heading">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Live workspace data</p>
            <h2 id="status-heading">Pipeline status</h2>
          </div>
          <span className="live-chip">API connected</span>
        </div>
        {error ? <p className="error-panel" role="alert">{error}</p> : null}
        {!status && !error ? <p className="loading-panel">Reading outputs...</p> : null}
        {status ? (
          <div className="status-grid">
            {toStatusCards(status).map((card) => (
              <StatusCard key={card.label} card={card} />
            ))}
          </div>
        ) : null}
      </section>
    </main>
  );
}
```

Replace `apps/web/app/page.tsx`:

```tsx
import AppShell from "@/components/app-shell";
import Dashboard from "@/components/dashboard";

export default function DashboardPage() {
  return (
    <AppShell>
      <Dashboard />
    </AppShell>
  );
}
```

- [ ] **Step 5: Add responsive dashboard styling**

Append to `apps/web/app/globals.css`:

```css
.shell {
  width: min(1180px, calc(100% - 40px));
  margin: 0 auto;
  padding-bottom: 72px;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 24px 0;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  text-decoration: none;
}

.brand-mark {
  display: grid;
  width: 42px;
  height: 42px;
  place-items: center;
  border-radius: 50% 50% 42% 58%;
  color: white;
  background: var(--leaf);
  font-family: var(--font-serif);
  font-size: 1.6rem;
}

.brand strong,
.brand small {
  display: block;
}

.brand small {
  color: var(--muted);
  font-size: 0.72rem;
  letter-spacing: 0.04em;
}

.topbar nav {
  display: flex;
  align-items: center;
  gap: 10px;
}

.topbar nav a {
  padding: 10px 14px;
  border-radius: 999px;
  text-decoration: none;
  font-size: 0.9rem;
  font-weight: 700;
}

.nav-accent,
.primary-action {
  color: white;
  background: var(--leaf);
}

.hero {
  position: relative;
  overflow: hidden;
  padding: clamp(44px, 8vw, 96px);
  border: 1px solid var(--line);
  border-radius: 34px 10px 34px 10px;
  background:
    linear-gradient(115deg, rgb(255 253 246 / 96%), rgb(225 235 225 / 88%)),
    repeating-linear-gradient(
      90deg,
      transparent 0 36px,
      rgb(29 89 69 / 7%) 36px 37px
    );
  box-shadow: 0 28px 80px rgb(21 35 29 / 10%);
}

.hero::after {
  position: absolute;
  right: -60px;
  bottom: -110px;
  width: 320px;
  height: 320px;
  border: 54px solid rgb(232 163 59 / 34%);
  border-radius: 50%;
  content: "";
}

.hero h1,
.page-heading h1 {
  max-width: 820px;
  margin: 8px 0 18px;
  font-family: var(--font-serif);
  font-size: clamp(3rem, 7vw, 6.7rem);
  font-weight: 520;
  line-height: 0.92;
  letter-spacing: -0.045em;
}

.hero > p:not(.eyebrow),
.page-heading > p:not(.eyebrow) {
  max-width: 650px;
  color: var(--muted);
  font-size: clamp(1rem, 2vw, 1.2rem);
  line-height: 1.7;
}

.eyebrow {
  margin: 0;
  color: var(--coral);
  font-size: 0.74rem;
  font-weight: 800;
  letter-spacing: 0.15em;
  text-transform: uppercase;
}

.primary-action {
  position: relative;
  z-index: 1;
  display: inline-flex;
  margin-top: 20px;
  padding: 14px 20px;
  border-radius: 999px;
  text-decoration: none;
  font-weight: 800;
}

.dashboard-section {
  padding: 64px 0 0;
}

.section-heading {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 22px;
}

.section-heading h2 {
  margin: 4px 0 0;
  font-family: var(--font-serif);
  font-size: clamp(2rem, 5vw, 3.7rem);
  font-weight: 540;
}

.live-chip {
  padding: 8px 12px;
  border: 1px solid #91aa9c;
  border-radius: 999px;
  color: var(--leaf);
  background: #edf5ef;
  font-size: 0.74rem;
  font-weight: 800;
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.status-card {
  min-height: 190px;
  padding: 22px;
  border: 1px solid var(--line);
  border-radius: 22px 5px 22px 5px;
  background: rgb(255 253 246 / 82%);
  animation: card-in 480ms both;
}

.status-card:nth-child(2) { animation-delay: 50ms; }
.status-card:nth-child(3) { animation-delay: 100ms; }
.status-card:nth-child(4) { animation-delay: 150ms; }
.status-card:nth-child(5) { animation-delay: 200ms; }
.status-card:nth-child(6) { animation-delay: 250ms; }
.status-card:nth-child(7) { animation-delay: 300ms; }

.status-card--leaf { border-top: 5px solid var(--leaf); }
.status-card--sun { border-top: 5px solid var(--sun); }
.status-card--coral { border-top: 5px solid var(--coral); }

.status-card > span {
  color: var(--muted);
  font-size: 0.76rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.status-card strong {
  display: block;
  overflow-wrap: anywhere;
  margin: 24px 0 10px;
  font-family: var(--font-serif);
  font-size: clamp(2rem, 4vw, 3.4rem);
  font-weight: 560;
  line-height: 0.96;
}

.status-card p {
  margin: 0;
  color: var(--muted);
  font-size: 0.86rem;
}

.error-panel,
.loading-panel {
  padding: 18px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: var(--card);
}

.error-panel {
  color: #7d2c1e;
  border-color: #d9a293;
  background: #fff2ed;
}

@keyframes card-in {
  from {
    opacity: 0;
    transform: translateY(12px);
  }
}

@media (max-width: 850px) {
  .status-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 600px) {
  .shell {
    width: min(100% - 24px, 1180px);
  }

  .topbar {
    align-items: flex-start;
  }

  .topbar nav a:first-child,
  .brand small {
    display: none;
  }

  .hero {
    padding: 42px 24px 64px;
  }

  .section-heading {
    align-items: flex-start;
    flex-direction: column;
  }

  .status-grid {
    grid-template-columns: 1fr;
  }
}
```

- [ ] **Step 6: Run tests, lint, and build**

Run:

```bash
pnpm --dir apps/web test tests/dashboard-page.test.tsx
pnpm --dir apps/web lint
pnpm --dir apps/web format
pnpm --dir apps/web format:check
pnpm --dir apps/web build
```

Expected: PASS and both `/` and static metadata compile.

- [ ] **Step 7: Commit**

```bash
git add apps/web/app apps/web/components apps/web/tests/dashboard-page.test.tsx
git commit -m "feat(web): build project dashboard"
```

---

### Task 8: Build the Direct Audio Demo

**Files:**
- Create: `apps/web/components/waveform.tsx`
- Create: `apps/web/components/demo-form.tsx`
- Create: `apps/web/app/demo/page.tsx`
- Modify: `apps/web/app/globals.css`
- Create: `apps/web/tests/demo-form.test.tsx`

- [ ] **Step 1: Write failing form tests**

Create `apps/web/tests/demo-form.test.tsx`:

```tsx
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import DemoForm from "@/components/demo-form";
import * as api from "@/lib/api";

vi.mock("@/lib/api");
vi.mock("@/components/waveform", () => ({
  default: () => <div data-testid="waveform" />,
}));

const options: api.DemoOptions = {
  languages: [
    { id: "kapampangan", label: "Kapampangan", description: "Default" },
    { id: "auto", label: "Auto-detect", description: "Automatic" },
  ],
  models: [
    {
      id: "baseline",
      label: "Whisper Small (baseline)",
      model_path: "openai/whisper-small",
      available: true,
      unavailable_reason: null,
      decoding_language: null,
    },
    {
      id: "finetuned",
      label: "BosesPH fine-tuned model",
      model_path: "",
      available: false,
      unavailable_reason: "No local fine-tuned model found.",
      decoding_language: null,
    },
  ],
  default_language_id: "kapampangan",
  default_model_id: "baseline",
};

describe("DemoForm", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(api.getDemoOptions).mockResolvedValue(options);
  });

  it("renders controlled choices and disables unavailable models", async () => {
    render(<DemoForm />);

    expect(await screen.findByText("Whisper Small (baseline)")).toBeInTheDocument();
    expect(screen.getByRole("option", { name: /fine-tuned/i })).toBeDisabled();
  });

  it("submits audio and displays optional metrics", async () => {
    const user = userEvent.setup();
    vi.mocked(api.submitDemo).mockResolvedValue({
      id: "job-1",
      type: "demo-transcribe",
      status: "queued",
      progress: null,
      result: null,
      error: null,
    });
    vi.mocked(api.waitForJob).mockImplementation(async (_id, onUpdate) => {
      const job: api.Job = {
        id: "job-1",
        type: "demo-transcribe",
        status: "succeeded",
        progress: "transcribing",
        result: {
          prediction: "Masanting ya ing aldo",
          model_id: "baseline",
          model_label: "Whisper Small (baseline)",
          language_id: "kapampangan",
          wer: 0,
          cer: 0,
        },
        error: null,
      };
      onUpdate(job);
      return job;
    });

    render(<DemoForm />);
    await screen.findByText("Whisper Small (baseline)");
    await user.upload(
      screen.getByLabelText("Audio file"),
      new File(["audio"], "clip.wav", { type: "audio/wav" }),
    );
    await user.type(
      screen.getByLabelText("Reference transcript (optional)"),
      "Masanting ya ing aldo.",
    );
    await user.click(screen.getByRole("button", { name: "Transcribe audio" }));

    expect(await screen.findByText("Masanting ya ing aldo")).toBeInTheDocument();
    expect(screen.getAllByText("0.0%")).toHaveLength(2);
  });

  it("shows a background job failure", async () => {
    const user = userEvent.setup();
    vi.mocked(api.submitDemo).mockResolvedValue({
      id: "job-2",
      type: "demo-transcribe",
      status: "queued",
      progress: null,
      result: null,
      error: null,
    });
    vi.mocked(api.waitForJob).mockResolvedValue({
      id: "job-2",
      type: "demo-transcribe",
      status: "failed",
      progress: null,
      result: null,
      error: "inference failed",
    });

    render(<DemoForm />);
    await screen.findByText("Whisper Small (baseline)");
    await user.upload(
      screen.getByLabelText("Audio file"),
      new File(["audio"], "clip.wav", { type: "audio/wav" }),
    );
    await user.click(screen.getByRole("button", { name: "Transcribe audio" }));

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent("inference failed"),
    );
  });
});
```

- [ ] **Step 2: Run and verify failure**

Run:

```bash
pnpm --dir apps/web test tests/demo-form.test.tsx
```

Expected: FAIL because the demo components do not exist.

- [ ] **Step 3: Implement waveform lifecycle**

Create `apps/web/components/waveform.tsx`:

```tsx
"use client";

import { useEffect, useRef } from "react";
import WaveSurfer from "wavesurfer.js";

export default function Waveform({ file }: { file: File }) {
  const container = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!container.current) return;
    const url = URL.createObjectURL(file);
    const waveform = WaveSurfer.create({
      container: container.current,
      url,
      height: 92,
      waveColor: "#9bad9f",
      progressColor: "#1d5945",
      cursorColor: "#d8684f",
      barWidth: 3,
      barGap: 2,
      barRadius: 3,
    });
    waveform.on("click", () => void waveform.playPause());
    return () => {
      waveform.destroy();
      URL.revokeObjectURL(url);
    };
  }, [file]);

  return <div className="waveform" ref={container} aria-label="Audio waveform" />;
}
```

- [ ] **Step 4: Implement demo form and polling**

Create `apps/web/components/demo-form.tsx` with these complete behaviors:

```tsx
"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import Waveform from "@/components/waveform";
import {
  getDemoOptions,
  submitDemo,
  waitForJob,
  type DemoOptions,
  type DemoResult,
  type Job,
} from "@/lib/api";
import { formatPercent } from "@/lib/format";

export default function DemoForm() {
  const [options, setOptions] = useState<DemoOptions | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [modelId, setModelId] = useState("");
  const [languageId, setLanguageId] = useState("");
  const [reference, setReference] = useState("");
  const [job, setJob] = useState<Job | null>(null);
  const [result, setResult] = useState<DemoResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const controller = useRef<AbortController | null>(null);

  useEffect(() => {
    getDemoOptions()
      .then((value) => {
        setOptions(value);
        setModelId(value.default_model_id);
        setLanguageId(value.default_language_id);
      })
      .catch((reason: unknown) =>
        setError(reason instanceof Error ? reason.message : "Unable to load options."),
      );
    return () => controller.current?.abort();
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) {
      setError("Choose a WAV audio file before transcribing.");
      return;
    }
    setError(null);
    setResult(null);
    controller.current?.abort();
    controller.current = new AbortController();

    const formData = new FormData();
    formData.append("audio", file);
    formData.append("model_id", modelId);
    formData.append("language_id", languageId);
    if (reference.trim()) formData.append("reference", reference.trim());

    try {
      const submitted = await submitDemo(formData);
      setJob(submitted);
      const completed = await waitForJob(
        submitted.id,
        setJob,
        controller.current.signal,
      );
      if (completed.status === "failed") {
        throw new Error(completed.error ?? "Transcription failed.");
      }
      if (!completed.result) {
        throw new Error("The transcription job returned no result.");
      }
      setResult(completed.result);
    } catch (reason: unknown) {
      if (reason instanceof DOMException && reason.name === "AbortError") return;
      setError(reason instanceof Error ? reason.message : "Transcription failed.");
    }
  }

  const busy = job?.status === "queued" || job?.status === "running";

  return (
    <div className="demo-grid">
      <form className="demo-form" onSubmit={handleSubmit}>
        <label>
          <span>Audio file</span>
          <input
            accept=".wav,audio/wav"
            disabled={busy}
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            type="file"
          />
        </label>
        {file ? (
          <div className="audio-preview">
            <div>
              <strong>{file.name}</strong>
              <span>{(file.size / 1024 / 1024).toFixed(2)} MB</span>
            </div>
            <Waveform file={file} />
          </div>
        ) : null}

        <div className="field-row">
          <label>
            <span>Language</span>
            <select
              disabled={!options || busy}
              value={languageId}
              onChange={(event) => setLanguageId(event.target.value)}
            >
              {options?.languages.map((item) => (
                <option key={item.id} value={item.id}>{item.label}</option>
              ))}
            </select>
          </label>
          <label>
            <span>Model</span>
            <select
              disabled={!options || busy}
              value={modelId}
              onChange={(event) => setModelId(event.target.value)}
            >
              {options?.models.map((item) => (
                <option
                  disabled={!item.available}
                  key={item.id}
                  value={item.id}
                >
                  {item.label}{item.available ? "" : " (unavailable)"}
                </option>
              ))}
            </select>
          </label>
        </div>

        <label>
          <span>Reference transcript (optional)</span>
          <textarea
            disabled={busy}
            onChange={(event) => setReference(event.target.value)}
            placeholder="Enter the correct human transcript to calculate WER and CER."
            rows={4}
            value={reference}
          />
        </label>

        <button disabled={!options || busy} type="submit">
          {busy ? "Transcribing..." : "Transcribe audio"}
        </button>
        {job && busy ? (
          <p className="job-status" role="status">
            {job.status === "queued" ? "Queued" : job.progress ?? "Transcribing"}
          </p>
        ) : null}
        {error ? <p className="error-panel" role="alert">{error}</p> : null}
      </form>

      <aside className="result-panel" aria-live="polite">
        <p className="eyebrow">Model output</p>
        <h2>Transcript</h2>
        {result ? (
          <>
            <blockquote>{result.prediction}</blockquote>
            <dl>
              <div><dt>Model</dt><dd>{result.model_label}</dd></div>
              <div><dt>WER</dt><dd>{formatPercent(result.wer ?? undefined)}</dd></div>
              <div><dt>CER</dt><dd>{formatPercent(result.cer ?? undefined)}</dd></div>
            </dl>
          </>
        ) : (
          <p>Select a clip and run transcription to see the model output.</p>
        )}
      </aside>
    </div>
  );
}
```

- [ ] **Step 5: Add the route**

Create `apps/web/app/demo/page.tsx`:

```tsx
import AppShell from "@/components/app-shell";
import DemoForm from "@/components/demo-form";

export default function DemoPage() {
  return (
    <AppShell>
      <main className="demo-page">
        <header className="page-heading">
          <p className="eyebrow">Direct single-audio inference</p>
          <h1>Hear the model work.</h1>
          <p>
            Upload one PCM WAV clip. The API removes it after the transcription
            job succeeds or fails.
          </p>
        </header>
        <DemoForm />
      </main>
    </AppShell>
  );
}
```

- [ ] **Step 6: Add responsive demo styling**

Append to `apps/web/app/globals.css`:

```css
.demo-page {
  padding-top: 42px;
}

.page-heading {
  max-width: 920px;
  margin-bottom: 40px;
}

.demo-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(300px, 0.65fr);
  gap: 18px;
  align-items: start;
}

.demo-form,
.result-panel {
  border: 1px solid var(--line);
  background: rgb(255 253 246 / 88%);
  box-shadow: 0 24px 64px rgb(21 35 29 / 8%);
}

.demo-form {
  display: grid;
  gap: 22px;
  padding: clamp(22px, 5vw, 42px);
  border-radius: 30px 7px 30px 7px;
}

.demo-form label {
  display: grid;
  gap: 9px;
  color: var(--muted);
  font-size: 0.82rem;
  font-weight: 800;
}

.demo-form input,
.demo-form select,
.demo-form textarea {
  width: 100%;
  min-height: 48px;
  padding: 12px 14px;
  border: 1px solid #aeb6af;
  border-radius: 12px;
  color: var(--ink);
  background: #fffef9;
}

.demo-form textarea {
  resize: vertical;
}

.demo-form input:focus-visible,
.demo-form select:focus-visible,
.demo-form textarea:focus-visible,
.demo-form button:focus-visible,
.topbar a:focus-visible,
.primary-action:focus-visible {
  outline: 3px solid rgb(232 163 59 / 62%);
  outline-offset: 3px;
}

.field-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

.audio-preview {
  padding: 16px;
  border: 1px dashed #9cab9f;
  border-radius: 16px;
  background: #eef4ed;
}

.audio-preview > div:first-child {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 10px;
  color: var(--muted);
  font-size: 0.78rem;
}

.waveform {
  min-height: 92px;
}

.demo-form button {
  min-height: 50px;
  border: 0;
  border-radius: 999px;
  color: white;
  background: var(--leaf);
  font-weight: 850;
  cursor: pointer;
}

.demo-form button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.job-status {
  margin: -8px 0 0;
  color: var(--leaf);
  font-size: 0.84rem;
  font-weight: 800;
}

.result-panel {
  position: sticky;
  top: 24px;
  min-height: 410px;
  padding: 30px;
  border-radius: 7px 30px 7px 30px;
}

.result-panel h2 {
  margin: 5px 0 24px;
  font-family: var(--font-serif);
  font-size: 2.5rem;
  font-weight: 540;
}

.result-panel blockquote {
  margin: 0 0 28px;
  padding: 22px 0 22px 22px;
  border-left: 5px solid var(--sun);
  font-family: var(--font-serif);
  font-size: clamp(1.5rem, 3vw, 2.3rem);
  line-height: 1.15;
}

.result-panel dl {
  display: grid;
  gap: 1px;
  overflow: hidden;
  margin: 0;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: var(--line);
}

.result-panel dl div {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
  background: var(--card);
}

.result-panel dt {
  color: var(--muted);
}

.result-panel dd {
  margin: 0;
  font-weight: 850;
  text-align: right;
}

@media (max-width: 850px) {
  .demo-grid {
    grid-template-columns: 1fr;
  }

  .result-panel {
    position: static;
    min-height: 280px;
  }
}

@media (max-width: 600px) {
  .field-row {
    grid-template-columns: 1fr;
  }

  .audio-preview > div:first-child {
    align-items: flex-start;
    flex-direction: column;
  }
}
```

- [ ] **Step 7: Run frontend verification**

Run:

```bash
pnpm --dir apps/web test
pnpm --dir apps/web lint
pnpm --dir apps/web format
pnpm --dir apps/web format:check
pnpm --dir apps/web build
```

Expected: all tests pass and Next.js builds `/` and `/demo`.

- [ ] **Step 8: Commit**

```bash
git add apps/web/app apps/web/components apps/web/tests/demo-form.test.tsx
git commit -m "feat(web): add direct audio transcription demo"
```

---

### Task 9: Documentation, Status, and Final Verification

**Files:**
- Modify: `README.md`
- Modify: `Tasks.md`
- Modify: `Simple_Tasks.md`

- [ ] **Step 1: Document frontend setup**

Update `README.md` with:

````markdown
Install frontend dependencies:

```bash
corepack enable
corepack prepare pnpm@10.17.1 --activate
pnpm --dir apps/web install
cp apps/web/.env.example apps/web/.env.local
```

Run the API and web app in separate terminals:

```bash
bosesph-api
pnpm --dir apps/web dev
```

Open `http://localhost:3000` for the dashboard or
`http://localhost:3000/demo` for direct single-audio transcription. Demo
uploads are removed after each background job finishes.
````

- [ ] **Step 2: Run the complete automated suite**

Run:

```bash
.venv/bin/pytest -q
.venv/bin/ruff check .
.venv/bin/black --check .
pnpm --dir apps/web test
pnpm --dir apps/web lint
pnpm --dir apps/web format
pnpm --dir apps/web format:check
pnpm --dir apps/web build
```

Expected: every command passes.

- [ ] **Step 3: Run the API and frontend smoke test**

Start the API:

```bash
BOSESPH_WORKSPACE=outputs .venv/bin/bosesph-api
```

Start Next.js separately:

```bash
pnpm --dir apps/web dev
```

Verify:

1. `/` loads real output values or `Not available`.
2. `/demo` lists the baseline model and the local fine-tuned model only when
   its package exists.
3. A PCM WAV can be previewed and submitted.
4. A supplied reference displays WER and CER.
5. A submission without a reference displays `Not available` for metrics.
6. The upload directory is absent after job completion:

```bash
test ! -d outputs/.demo_uploads
```

- [ ] **Step 4: Mark Phase 8 complete**

In `Tasks.md`, add completion statuses to sections 8.1, 8.2, and 8.3 describing
the Dashboard, direct demo flow, real status cards, controlled models, optional
metrics, and temporary upload deletion.

In `Simple_Tasks.md`, mark the three active Phase 8 checkboxes `[x]`. Leave the
additional Dashboard pages under Future Implementations unchecked.

- [ ] **Step 5: Re-run documentation and repository checks**

Run:

```bash
git diff --check
git status --short
```

Expected: no whitespace errors; only intended Phase 8 files are modified.

- [ ] **Step 6: Commit**

```bash
git add README.md Tasks.md Simple_Tasks.md apps/web src/bosesph tests
git commit -m "docs: complete Phase 8 dashboard demo"
```
