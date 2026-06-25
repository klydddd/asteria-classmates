"""Console entry point for the BosesPH API server."""

from __future__ import annotations

import uvicorn

from bosesph.api.settings import ApiSettings


def run() -> None:
    """Run the FastAPI application through Uvicorn."""
    settings = ApiSettings()
    uvicorn.run(
        "bosesph.api.app:create_app",
        factory=True,
        host=settings.host,
        port=settings.port,
    )
