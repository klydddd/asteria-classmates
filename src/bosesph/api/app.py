"""FastAPI application factory for the BosesPH pipeline."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from bosesph.api.jobs import JobManager
from bosesph.api.routes import files, jobs, pipeline
from bosesph.api.settings import ApiSettings, PathTraversalError
from bosesph.asr import ASRError
from bosesph.dataset import DatasetBuildError
from bosesph.ingestion import IngestionError, OutputExistsError
from bosesph.pld import PldParseError
from bosesph.review import ReviewError
from bosesph.transcripts import TranscriptDatasetError

SERVICE_ERRORS = (
    IngestionError,
    OutputExistsError,
    TranscriptDatasetError,
    ReviewError,
    DatasetBuildError,
    ASRError,
    PldParseError,
)


def _error_response(status_code: int, error: Exception) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"detail": str(error)})


def create_app() -> FastAPI:
    """Create an API application with isolated settings and job state."""
    settings = ApiSettings()
    job_manager = JobManager(max_workers=settings.max_workers)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        yield
        app.state.jobs.shutdown()

    app = FastAPI(title="BosesPH Toolkit API", lifespan=lifespan)
    app.state.settings = settings
    app.state.jobs = job_manager

    @app.exception_handler(PathTraversalError)
    async def handle_path_traversal(
        request: Request,
        error: PathTraversalError,
    ) -> JSONResponse:
        return _error_response(400, error)

    @app.exception_handler(FileNotFoundError)
    async def handle_missing_file(
        request: Request,
        error: FileNotFoundError,
    ) -> JSONResponse:
        return _error_response(404, error)

    for error_type in SERVICE_ERRORS:
        app.add_exception_handler(
            error_type,
            lambda request, error: _error_response(422, error),
        )

    @app.exception_handler(ValueError)
    async def handle_value_error(
        request: Request,
        error: ValueError,
    ) -> JSONResponse:
        return _error_response(422, error)

    app.include_router(pipeline.router)
    app.include_router(jobs.router)
    app.include_router(files.router)
    return app
