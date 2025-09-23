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
    lectureId: UUID4
    status: Literal["IN_PROGRESS", "FAILED", "DONE"]
    createdAt: datetime

class GenerationStatusResponse(BaseModel):
    lectureId: UUID4
    status: Literal["IN_PROGRESS", "FAILED", "DONE"]
    lastUpdated: datetime
    error: Optional[ErrorModel] = None

# ---------------------------
# In-memory job store
# ---------------------------

class Job(BaseModel):
    lectureId: UUID4
    status: Literal["IN_PROGRESS", "FAILED", "DONE"]
    lastUpdated: datetime
    error: Optional[ErrorModel] = None

JOBS: Dict[UUID, Job] = {}  # simple in-memory cache; replace with Redis/DB in prod

# ---------------------------
# Your generation functions
# ---------------------------

def generate_audio(
    slide_texts: List[str],
    *,
    course_id: str,
    user_profile: UserProfile,
) -> List[str]:
    """
    Create per-slide audio files from text.

    Returns a list of file paths (one per slide).
    Replace the body with your TTS pipeline (e.g., Coqui, ElevenLabs, local TTS).
    """
    # TODO: implement real TTS.
    # For now, pretend we produced audio files:
    audio_paths = [f"/tmp/{course_id}_slide_{i+1}.wav" for i, _ in enumerate(slide_texts)]
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

    Returns the path to the rendered video file.
    Replace with your real compositor (e.g., moviepy/ffmpeg + avatar renderer).
    """
    # TODO: implement real video assembly.
    video_path = f"/tmp/{lecture_id}_final.mp4"
    return video_path

# ---------------------------
# Background job runner
# ---------------------------

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)

def process_generation(payload: GenerateRequest) -> None:
    """Runs the end-to-end pipeline; updates JOBS accordingly."""
    try:
        # 1) Audio
        audio_paths = generate_audio(
            payload.slideMessages,
            course_id=payload.courseId,
            user_profile=payload.userProfile,
        )

        # 2) Video
        _ = generate_video(
            payload.slideMessages,
            audio_paths,
            lecture_id=payload.lectureId,
            course_id=payload.courseId,
            user_profile=payload.userProfile,
        )

        # 3) Mark as done
        JOBS[payload.lectureId] = Job(
            lectureId=payload.lectureId,
            status="DONE",
            lastUpdated=_utcnow(),
            error=None,
        )
    except Exception as exc:
        JOBS[payload.lectureId] = Job(
            lectureId=payload.lectureId,
            status="FAILED",
            lastUpdated=_utcnow(),
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
    # (Optional) idempotency: if a job with the same lectureId exists and is IN_PROGRESS/DONE, you could short-circuit here.
    now = _utcnow()
    JOBS[payload.lectureId] = Job(
        lectureId=payload.lectureId,
        status="IN_PROGRESS",
        lastUpdated=now,
        error=None,
    )

    # Kick off background processing
    background.add_task(process_generation, payload)

    # Set Location header to the status endpoint
    response.headers["Location"] = f"/v1/video/{payload.lectureId}/status"

    return GenerationAcceptedResponse(
        lectureId=payload.lectureId,
        status="IN_PROGRESS",
        createdAt=now,
    )

@app.get(
    "/v1/video/{lectureId}/status",
    response_model=GenerationStatusResponse,
    responses={404: {"model": ErrorModel}},
)
def get_generation_status(lectureId: UUID4):
    job = JOBS.get(lectureId)
    if not job:
        raise HTTPException(status_code=404, detail="Request not found")
    return GenerationStatusResponse(
        lectureId=job.lectureId,
        status=job.status,
        lastUpdated=job.lastUpdated,
        error=job.error,
    )

# ---------------------------
# Entry point
# ---------------------------

# Run: uvicorn main:app --host 0.0.0.0 --port 8080 --reload
