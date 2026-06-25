"""File download and project-status endpoints."""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from bosesph.api.models import ProjectStatus
from bosesph.api.settings import PathTraversalError, resolve_path

router = APIRouter(tags=["files"])


@router.get("/project-status", response_model=ProjectStatus)
def project_status(request: Request) -> ProjectStatus:
    """Return an aggregated snapshot of available pipeline outputs."""
    ws: Path = request.app.state.settings.workspace.resolve()
    status = ProjectStatus()

    # Dataset
    dataset_stats_path = ws / "dataset" / "dataset_stats.json"
    if dataset_stats_path.is_file():
        status.dataset_available = True
        status.dataset_stats = json.loads(
            dataset_stats_path.read_text(encoding="utf-8")
        )

    # Benchmark — look for any results.json under benchmark/
    benchmark_dir = ws / "benchmark"
    if benchmark_dir.is_dir():
        for results_file in sorted(benchmark_dir.rglob("results.json")):
            status.benchmark_available = True
            status.benchmark_results = json.loads(
                results_file.read_text(encoding="utf-8")
            )
            break  # use the first one found

    # Model
    model_dir = ws / "model"
    if model_dir.is_dir():
        # Find the first subdirectory containing model files
        for child in sorted(model_dir.iterdir()):
            if child.is_dir() and (child / "model_card.md").is_file():
                status.model_available = True
                status.model_dir = str(child.relative_to(ws))
                break

    return status


@router.get("/download-output")
def download_output(
    request: Request,
    path: str = Query(description="Relative path under workspace to download."),
) -> StreamingResponse:
    """Stream a workspace path as a zip archive.

    If *path* points to a file, the zip contains that single file.
    If *path* points to a directory, the zip contains its full tree.
    """
    ws: Path = request.app.state.settings.workspace
    try:
        target = resolve_path(ws, path)
    except PathTraversalError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not target.exists():
        raise HTTPException(status_code=404, detail=f"Not found: {path}")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        if target.is_file():
            zf.write(target, target.name)
        else:
            for child in sorted(target.rglob("*")):
                if child.is_file():
                    zf.write(child, str(child.relative_to(target)))
    buf.seek(0)

    filename = f"{target.name}.zip"
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
