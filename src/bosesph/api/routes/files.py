"""File download and project-status endpoints."""

from __future__ import annotations

import io
import json
import math
import zipfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from bosesph.api.models import ProjectStatus
from bosesph.api.settings import PathTraversalError, resolve_path

router = APIRouter(tags=["files"])


def _read_json(path: Path) -> dict[str, object] | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _finite_float(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        converted = float(value)
    except OverflowError:
        return None
    return converted if math.isfinite(converted) else None


def _metric_summary(path: Path) -> dict[str, float] | None:
    data = _read_json(path)
    if data is None or "wer" not in data or "cer" not in data:
        return None
    wer = _finite_float(data["wer"])
    cer = _finite_float(data["cer"])
    if wer is None or cer is None:
        return None
    return {"wer": wer, "cer": cer}


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
