"""Job status endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from bosesph.api.jobs import Job

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=list[Job])
def list_jobs(request: Request) -> list[Job]:
    """Return all registered jobs, newest first."""
    return request.app.state.jobs.list_jobs()


@router.get("/{job_id}", response_model=Job)
def get_job(request: Request, job_id: str) -> Job:
    """Return the current state of a single job."""
    job = request.app.state.jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    return job
