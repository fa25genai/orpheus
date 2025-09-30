from __future__ import annotations
from datetime import datetime, timedelta, timezone
from pathlib import Path
from queue import Queue
from typing import Dict
from uuid import UUID
from app import config
from app.schemas import Job, SlideTask, VideoTask

AUDIO_QUEUE: "Queue[SlideTask]" = Queue()
VIDEO_QUEUE: "Queue[VideoTask]" = Queue()

JOBS: Dict[UUID, Job] = {}

JOB_TTL = timedelta(hours=24)
CLEANUP_INTERVAL_SECONDS = 900

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

def job_dir(prompt_id: UUID) -> Path:
    d = config.VIDEO_ROOT / str(prompt_id)
    d.mkdir(parents=True, exist_ok=True)
    return d

def folder_url(prompt_id: UUID) -> str:
    return f"{config.PUBLIC_VIDEOS_BASE}/{prompt_id}/"

def estimate_total_seconds_for_new_slide(job: Job) -> None:
    if job.expectedDurationSec == 0:
        job.expectedDurationSec = 8 + 6
    else:
        job.expectedDurationSec += 6

def eta_seconds(job: Job) -> int:
    if job.status in ("DONE","FAILED"):
        return 0
    elapsed = int((utcnow() - job.startedAt).total_seconds())
    remaining = job.expectedDurationSec - elapsed
    return max(0, remaining)

def purge_stale_jobs(now: datetime | None = None) -> None:
    now = now or utcnow()
    for pid, job in list(JOBS.items()):
        last_touched = getattr(job, "lastTouched", job.lastUpdated)
        if now - last_touched > JOB_TTL:
            JOBS.pop(pid, None)