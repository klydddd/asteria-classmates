"""Direct single-audio demo endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, File, Form, Request, UploadFile, status

from bosesph.api.demo import (
    discover_demo_options,
    remove_demo_upload,
    run_demo_transcription,
    save_demo_upload,
    select_demo_model,
)
from bosesph.api.jobs import Job
from bosesph.api.models import DemoOptions

router = APIRouter(prefix="/demo", tags=["demo"])


@router.get("/options", response_model=DemoOptions)
def demo_options(request: Request) -> DemoOptions:
    """Return the controlled language and model choices."""
    return discover_demo_options(request.app.state.settings.workspace)


@router.post(
    "/transcribe",
    response_model=Job,
    status_code=status.HTTP_202_ACCEPTED,
)
def transcribe_demo_audio(
    request: Request,
    audio: Annotated[list[UploadFile], File()],
    model_id: Annotated[str, Form()],
    language_id: Annotated[str, Form()],
    reference: Annotated[str | None, Form()] = None,
) -> Job:
    """Validate, save, and enqueue one transient audio transcription."""
    if len(audio) != 1:
        raise ValueError("Exactly one audio upload is required.")

    workspace = request.app.state.settings.workspace.resolve()
    options = discover_demo_options(workspace)
    model, decoding_language = select_demo_model(
        options,
        model_id,
        language_id,
    )
    job_model = model.model_copy(
        update={
            "model_path": (
                str((workspace / model.model_path).resolve())
                if model.id == "finetuned"
                else model.model_path
            )
        }
    )
    audio_path, upload_directory = save_demo_upload(workspace, audio[0])

    try:
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
    except Exception:
        remove_demo_upload(upload_directory)
        raise
