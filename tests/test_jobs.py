from __future__ import annotations

import time
from pathlib import Path

from pydantic import BaseModel

from bosesph.api.jobs import JobManager, JobStatus


class ExampleResult(BaseModel):
    path: Path
    count: int


def wait_for_terminal_status(manager: JobManager, job_id: str) -> JobStatus:
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        job = manager.get(job_id)
        assert job is not None
        if job.status in {JobStatus.SUCCEEDED, JobStatus.FAILED}:
            return job.status
        time.sleep(0.01)
    raise AssertionError(f"job did not finish: {job_id}")


def test_job_manager_serializes_pydantic_result_and_progress(
    tmp_path: Path,
) -> None:
    manager = JobManager(max_workers=1)

    def work(*, progress_fn: object) -> ExampleResult:
        progress_fn((1, 2))  # type: ignore[operator]
        return ExampleResult(path=tmp_path / "result.json", count=2)

    try:
        submitted = manager.submit("example", work)
        assert wait_for_terminal_status(manager, submitted.id) == JobStatus.SUCCEEDED
        job = manager.get(submitted.id)
        assert job is not None
        assert job.progress == "1/2"
        assert job.result == {
            "path": str(tmp_path / "result.json"),
            "count": 2,
        }
    finally:
        manager.shutdown()


def test_job_manager_records_failures() -> None:
    manager = JobManager(max_workers=1)

    def fail(*, progress_fn: object) -> ExampleResult:
        raise RuntimeError("expected failure")

    try:
        submitted = manager.submit("failure", fail)
        assert wait_for_terminal_status(manager, submitted.id) == JobStatus.FAILED
        job = manager.get(submitted.id)
        assert job is not None
        assert job.error == "expected failure"
        assert job.result is None
    finally:
        manager.shutdown()


def test_job_manager_lists_newest_first_and_handles_unknown_ids() -> None:
    manager = JobManager(max_workers=1)

    def work(*, progress_fn: object) -> ExampleResult:
        return ExampleResult(path=Path("result.json"), count=1)

    try:
        first = manager.submit("first", work)
        time.sleep(0.001)
        second = manager.submit("second", work)
        assert [job.id for job in manager.list_jobs()] == [second.id, first.id]
        assert manager.get("unknown") is None
    finally:
        manager.shutdown()
