from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import List, Optional, Literal, Dict
from uuid import UUID

from fastapi import FastAPI, BackgroundTasks, HTTPException, Response
from pydantic import BaseModel, Field, UUID4, constr

app = FastAPI(
    title="Service Video-Generation APIs",
    version="0.1",
    description=(
        "API for the Orpheus video generation. Transforms fluent texts into "
        "interactive lecture videos with lifelike professor avatars."
    ),
)


# ---------------------------
# Pydantic models (from spec)
# ---------------------------

class Preferences(BaseModel):
    answerLength: Optional[Literal["short", "medium", "long"]] = None
    languageLevel: Optional[Literal["basic", "intermediate", "advanced"]] = None
    expertiseLevel: Optional[Literal["beginner", "intermediate", "advanced", "expert"]] = None
    includePictures: Optional[Literal["none", "few", "many"]] = None


class UserProfile(BaseModel):
    id: str
    role: Literal["student", "instructor"]
    language: Literal["german", "english"]
    preferences: Optional[Preferences] = None
    enrolledCourses: Optional[List[str]] = None


class GenerateRequest(BaseModel):
    slideMessages: List[constr(min_length=1)] = Field(..., min_items=1)
    lectureId: UUID4
    courseId: str
    userProfile: UserProfile


class ErrorModel(BaseModel):
    code: Optional[str] = None
    message: Optional[str] = None


class GenerationAcceptedResponse(BaseModel):
    # NOTE: your spec's enum omits "IN_PROGRESS"; the implementation returns it.
    lectureId: UUID4
    status: Literal["IN_PROGRESS", "FAILED", "DONE"]
    createdAt: datetime


class GenerationStatusResponse(BaseModel):
    lectureId: UUID4
    status: Literal["IN_PROGRESS", "FAILED", "DONE"]
    lastUpdated: datetime
    resultUrl: Optional[str] = None  # uri when DONE
    error: Optional[ErrorModel] = None


# ---------------------------
# In-memory job store
# ---------------------------

class Job(BaseModel):
    lectureId: UUID4
    status: Literal["IN_PROGRESS", "FAILED", "DONE"]
    lastUpdated: datetime
    resultUrl: Optional[str] = None
    error: Optional[ErrorModel] = None


JOBS: Dict[UUID, Job] = {}  # simple in-memory cache; replace with Redis/DB in prod


# ---------------------------
# Generation functions (stubs)
# ---------------------------

def generate_audio(
        slide_texts: List[str],
        *,
        lecture_id: UUID4,  # <-- added
        course_id: str,
        user_profile: UserProfile,
) -> List[str]:
    """
    Create per-slide audio files from text.

    Returns a list of file paths (one per slide).
    Replace the body with your TTS pipeline (e.g., Coqui, ElevenLabs, local TTS).
    """
    # Name pattern: {lecture_id}_slide_{i+1}.wav
    lid = str(lecture_id)
    audio_paths = [f"/tmp/{lid}_slide_{i + 1}.wav" for i, _ in enumerate(slide_texts)]

    # TODO: generate real audio; for now this just returns target paths.
    # If you want to materialize placeholder files, uncomment:
    # from pathlib import Path
    # for p in audio_paths: Path(p).touch()

    return audio_paths


def generate_video(
        slide_texts: List[str],
        audio_paths: List[str],
        *,
        lecture_id: UUID4,
        course_id: str,
        user_profile: UserProfile,
) -> str:
    """
    Assemble the final video using the audio tracks and slide content.

    Returns a URI (string) to the rendered video file.
    Replace with your real compositor (e.g., moviepy/ffmpeg + avatar renderer).
    """
    # Use a file:// URI so it validates as a URI per the spec.
    return f"file:///tmp/{lecture_id}_final.mp4"


# ---------------------------
# Background job runner
# ---------------------------

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def process_generation(payload: GenerateRequest) -> None:
    """Runs the end-to-end pipeline; updates JOBS accordingly."""
    try:
        audio_paths = generate_audio(
            payload.slideMessages,
            lecture_id=payload.lectureId,
            course_id=payload.courseId,
            user_profile=payload.userProfile,
        )

        result_uri = generate_video(
            payload.slideMessages,
            audio_paths,
            lecture_id=payload.lectureId,
            course_id=payload.courseId,
            user_profile=payload.userProfile,
        )

        JOBS[payload.lectureId] = Job(
            lectureId=payload.lectureId,
            status="DONE",
            lastUpdated=_utcnow(),
            resultUrl=result_uri,
            error=None,
        )
    except Exception as exc:
        JOBS[payload.lectureId] = Job(
            lectureId=payload.lectureId,
            status="FAILED",
            lastUpdated=_utcnow(),
            resultUrl=None,
            error=ErrorModel(code="GENERATION_FAILED", message=str(exc)),
        )


# ---------------------------
# Routes
# ---------------------------

@app.post(
    "/v1/video/generate",
    response_model=GenerationAcceptedResponse,
    status_code=202,
    responses={
        400: {"model": ErrorModel},
        401: {"model": ErrorModel},
        500: {"model": ErrorModel},
    },
)
def request_video_generation(payload: GenerateRequest, background: BackgroundTasks, response: Response):
    # (Optional) idempotency: if a job with the same lectureId exists and is IN_PROGRESS/DONE, short-circuit here.
    now = _utcnow()
    JOBS[payload.lectureId] = Job(
        lectureId=payload.lectureId,
        status="IN_PROGRESS",
        lastUpdated=now,
        resultUrl=None,
        error=None,
    )

    background.add_task(process_generation, payload)

    # Set Location header to the result endpoint (same path in your spec)
    response.headers["Location"] = f"/v1/video/{payload.lectureId}/status"

    return GenerationAcceptedResponse(
        lectureId=payload.lectureId,
        status="IN_PROGRESS",  # matches your example payload
        createdAt=now,
    )


@app.get(
    "/v1/video/{lectureId}/status",
    response_model=GenerationStatusResponse,
    responses={404: {"model": ErrorModel}},
)
def get_generation_result(lectureId: UUID4):
    """
    Blocks until the job is DONE or FAILED, then returns the final result.

    NOTE: This intentionally waits indefinitely to match the spec. If you want
    a timeout, add one (e.g., env var ORPHEUS_STATUS_TIMEOUT_SECONDS) and raise 202/204.
    """
    job = JOBS.get(lectureId)
    if not job:
        raise HTTPException(status_code=404, detail="Request not found")

    # Busy-wait with a small sleep to avoid pegging the CPU.
    while job.status == "IN_PROGRESS":
        time.sleep(0.2)
        job = JOBS.get(lectureId)
        if not job:
            raise HTTPException(status_code=404, detail="Request not found")

    # At this point: DONE or FAILED
    return GenerationStatusResponse(
        lectureId=job.lectureId,
        status=job.status,
        lastUpdated=job.lastUpdated,
        resultUrl=job.resultUrl,
        error=job.error,
    )

# ---------------------------
# Entry point
# ---------------------------
# Run: uvicorn main:app --host 0.0.0.0 --port 8080 --reload
