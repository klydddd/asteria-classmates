"""Direct single-audio demo endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Request

from bosesph.api.demo import discover_demo_options
from bosesph.api.models import DemoOptions

router = APIRouter(prefix="/demo", tags=["demo"])


@router.get("/options", response_model=DemoOptions)
def demo_options(request: Request) -> DemoOptions:
    """Return the controlled language and model choices."""
    return discover_demo_options(request.app.state.settings.workspace)
