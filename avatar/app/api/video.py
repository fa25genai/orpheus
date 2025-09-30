from __future__ import annotations
from fastapi import APIRouter, Response, Request
from fastapi.responses import JSONResponse
from app.schemas import (
    GenerateRequest, GenerationAcceptedResponse, GenerationStatusResponse, ErrorModel, Job, SlideTask
)
from app.workers.queues import AUDIO_QUEUE, JOBS, utcnow, purge_stale_jobs, folder_url, eta_seconds

router = APIRouter(prefix="/v1/video", tags=["video"])

@router.post("/generate",
    response_model=GenerationAcceptedResponse,
    status_code=202,
    responses={400: {"model": ErrorModel}, 401: {"model": ErrorModel}, 500: {"model": ErrorModel}},
)
def request_video_generation(payload: GenerateRequest, response: Response, request: Request):
    now = utcnow()
    purge_stale_jobs(now)

    text = payload.voiceTrack.strip()
    if not text:
        return JSONResponse(status_code=400, content={"code": "BAD_REQUEST", "message": "voiceTrack must not be empty"})

    folder = folder_url(payload.promptId)
    job = JOBS.get(payload.promptId)
    if not job:
        job = Job(
            promptId=payload.promptId,
            status="IN_PROGRESS",
            lastUpdated=now,
            lastTouched=now,
            resultUrl=folder,
            startedAt=now,
            expectedDurationSec=0,
            error=None,
        )
        JOBS[payload.promptId] = job
    else:
        job.lastTouched = now
        JOBS[payload.promptId] = job

    AUDIO_QUEUE.put(
        SlideTask(
            promptId=payload.promptId,
            courseId=payload.courseId,
            userProfile=payload.userProfile,
            text=text,
            slideNo=payload.slideNumber,
            slot=getattr(payload, "slot", "default"),
        )
    )

    base = str(request.base_url).rstrip("/")
    response.headers["Location"] = f"{base}/v1/video/{payload.promptId}/status"
    return GenerationAcceptedResponse(promptId=payload.promptId, createdAt=now)

@router.get("/{promptId}/status", response_model=GenerationStatusResponse, responses={404: {"model": ErrorModel}})
def get_generation_status(promptId):
    purge_stale_jobs()
    job = JOBS.get(promptId)
    if not job:
        return JSONResponse(status_code=404, content={"code": "NOT_FOUND", "message": "Request not found"})
    job.lastTouched = utcnow()
    JOBS[promptId] = job
    return GenerationStatusResponse(
        promptId=job.promptId,
        status=job.status,
        lastUpdated=job.lastUpdated,
        resultUrl=job.resultUrl,
        estimatedSecondsLeft=eta_seconds(job),
        error=job.error,
    )