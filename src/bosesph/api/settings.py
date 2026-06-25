"""API configuration backed by environment variables."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


class ApiSettings(BaseSettings):
    """Central API settings, overridable via ``BOSESPH_*`` environment vars."""

    model_config = {"env_prefix": "BOSESPH_"}

    workspace: Path = Field(
        default=Path("outputs"),
        description="Root directory for all pipeline inputs and outputs.",
    )
    host: str = Field(default="0.0.0.0", description="Bind address.")
    port: int = Field(default=8000, description="Bind port.")
    max_workers: int = Field(
        default=2,
        ge=1,
        description="Thread pool size for background jobs.",
    )


class PathTraversalError(ValueError):
    """Raised when a client-supplied path escapes the workspace root."""


def resolve_path(workspace: Path, relative: str) -> Path:
    """Join *relative* under *workspace* and reject traversal attempts.

    Raises :class:`PathTraversalError` if the resolved path escapes the
    workspace root (``..`` components, absolute paths, or symlink escapes).
    """
    if not relative or relative.startswith("/") or "\\" in relative:
        raise PathTraversalError(
            f"Path must be a non-empty relative POSIX path: {relative!r}"
        )
    parts = relative.split("/")
    if any(part in {".", ".."} for part in parts):
        raise PathTraversalError(
            f"Path must not contain traversal components: {relative!r}"
        )
    resolved = (workspace / relative).resolve()
    workspace_resolved = workspace.resolve()
    if (
        not str(resolved).startswith(str(workspace_resolved) + "/")
        and resolved != workspace_resolved
    ):
        raise PathTraversalError(f"Resolved path escapes workspace root: {relative!r}")
    return resolved
