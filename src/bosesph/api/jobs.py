"""In-process background job manager backed by a ThreadPoolExecutor."""

from __future__ import annotations

import threading
import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel


class JobStatus(str, Enum):
    """Lifecycle states for a background job."""

    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class Job(BaseModel):
    """Snapshot of a background job visible to API clients."""

    id: str
    type: str
    status: JobStatus
    progress: str | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: str
    updated_at: str


class JobManager:
    """Thread-safe in-memory job registry with a fixed-size worker pool.

    Not persistent — all state is lost on process restart.  Suitable for a
    hackathon MVP.
    """

    def __init__(self, max_workers: int = 2) -> None:
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._lock = threading.Lock()
        self._jobs: dict[str, Job] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def submit(
        self,
        job_type: str,
        fn: Callable[..., BaseModel],
        *args: Any,
        **kwargs: Any,
    ) -> Job:
        """Submit *fn* for background execution and return the new job."""
        job_id = uuid.uuid4().hex[:12]
        now = _now_iso()
        job = Job(
            id=job_id,
            type=job_type,
            status=JobStatus.QUEUED,
            created_at=now,
            updated_at=now,
        )
        with self._lock:
            self._jobs[job_id] = job

        def _progress_callback(value: Any) -> None:
            """Bridge service ``progress_fn`` into the job's progress string."""
            if isinstance(value, tuple) and len(value) == 2:
                done, total = value
                text = f"{done}/{total}"
            else:
                text = str(value)
            with self._lock:
                stored = self._jobs[job_id]
                self._jobs[job_id] = stored.model_copy(
                    update={"progress": text, "updated_at": _now_iso()},
                )

        def _run() -> None:
            with self._lock:
                stored = self._jobs[job_id]
                self._jobs[job_id] = stored.model_copy(
                    update={
                        "status": JobStatus.RUNNING,
                        "updated_at": _now_iso(),
                    },
                )
            try:
                result = fn(*args, progress_fn=_progress_callback, **kwargs)
                result_dict = (
                    result.model_dump(mode="json")
                    if isinstance(result, BaseModel)
                    else {"value": str(result)}
                )
                with self._lock:
                    stored = self._jobs[job_id]
                    self._jobs[job_id] = stored.model_copy(
                        update={
                            "status": JobStatus.SUCCEEDED,
                            "result": result_dict,
                            "updated_at": _now_iso(),
                        },
                    )
            except Exception as exc:
                with self._lock:
                    stored = self._jobs[job_id]
                    self._jobs[job_id] = stored.model_copy(
                        update={
                            "status": JobStatus.FAILED,
                            "error": str(exc),
                            "updated_at": _now_iso(),
                        },
                    )

        self._executor.submit(_run)
        return job

    def get(self, job_id: str) -> Job | None:
        """Return the current snapshot of *job_id*, or ``None``."""
        with self._lock:
            return self._jobs.get(job_id)

    def list_jobs(self) -> list[Job]:
        """Return snapshots of all registered jobs, newest first."""
        with self._lock:
            return sorted(
                self._jobs.values(),
                key=lambda j: j.created_at,
                reverse=True,
            )

    def shutdown(self, *, wait: bool = True) -> None:
        """Shut down the worker pool (called on app shutdown)."""
        self._executor.shutdown(wait=wait)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
