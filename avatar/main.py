from datetime import datetime, timezone
from typing import List, Optional, Literal, Dict
from uuid import UUID

from fastapi import FastAPI, BackgroundTasks, Response, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, constr

app = FastAPI(title="Service Video-Generation APIs", version="0.1")


# ---------------------------
# Models
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
    lectureId: UUID
    courseId: str
    userProfile: UserProfile


class ErrorModel(BaseModel):
    code: Optional[str] = None
    message: Optional[str] = None


class GenerationAcceptedResponse(BaseModel):
    lectureId: UUID
    createdAt: datetime
    # status omitted on purpose to match your earlier schema (202 body minimal)


class GenerationStatusResponse(BaseModel):
    lectureId: UUID
    status: Literal["IN_PROGRESS", "FAILED", "DONE"]
    lastUpdated: datetime
    resultUrl: str  # always present now
    estimatedSecondsLeft: int  # 0 when DONE/FAILED
    error: Optional[ErrorModel] = None


# ---------------------------
# In-memory job store
# ---------------------------

class Job(BaseModel):
    lectureId: UUID
    status: Literal["IN_PROGRESS", "FAILED", "DONE"]
    lastUpdated: datetime
    resultUrl: str
    # ETA bookkeeping
    startedAt: datetime
    expectedDurationSec: int
    error: Optional[ErrorModel] = None


JOBS: Dict[UUID, Job] = {}

CDN_BASE = "https://cdn.example.com/videos"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _result_url(lecture_id: UUID) -> str:
    return f"{CDN_BASE}/{lecture_id}.mp4"


def _estimate_total_seconds(slide_count: int) -> int:
    # Heuristic: 8s overhead + 6s per slide (tweak as you learn)
    return 8 + 6 * slide_count


def _eta_seconds(job: Job) -> int:
    if job.status in ("DONE", "FAILED"):
        return 0
    elapsed = int((_utcnow() - job.startedAt).total_seconds())
    remaining = job.expectedDurationSec - elapsed
    return max(0, remaining)


# ---------------------------
# Fake pipeline
# ---------------------------

def generate_audio(slide_texts: List[str], course_id: str, lecture_id: UUID, user_profile: UserProfile) -> List[str]:
    """
    Create per-slide audio files from text.
    Returns a list of file paths (one per slide).
    """
    lid = str(lecture_id)
    audio_paths = [f"/tmp/{lid}_{i}.wav" for i, _ in enumerate(slide_texts)]
    # TODO: generate real audio in OpenVoice container and save it in the mentioned path
    return audio_paths


def generate_video(audio_paths: List[str], lecture_id: UUID, course_id: str, user_profile: UserProfile) -> str:
    """
    Assemble the final video using the audio tracks and slide content.
    Returns a URI (string) to the rendered video file which consists of one video per slide.
    """
    lid = str(lecture_id)
    # TODO: generate real video in ditto-talkinghead container and save it in the mentioned path
    return f"file:///tmp/{lid}_final.mp4"


def process_generation(payload: GenerateRequest) -> None:
    try:
        audio_paths = generate_audio(payload.slideMessages, course_id=payload.courseId, user_profile=payload.userProfile)
        _ = generate_video(payload.slideMessages, audio_paths, lecture_id=payload.lectureId, course_id=payload.courseId, user_profile=payload.userProfile)
        # Mark done
        job = JOBS[payload.lectureId]
        job.status = "DONE"
        job.lastUpdated = _utcnow()
        JOBS[payload.lectureId] = job
    except Exception as exc:
        job = JOBS[payload.lectureId]
        job.status = "FAILED"
        job.lastUpdated = _utcnow()
        job.error = ErrorModel(code="GENERATION_FAILED", message=str(exc))
        JOBS[payload.lectureId] = job


# ---------------------------
# Routes
# ---------------------------

@app.post(
    "/v1/video/generate",
    response_model=GenerationAcceptedResponse,
    status_code=202,
    responses={400: {"model": ErrorModel}, 401: {"model": ErrorModel}, 500: {"model": ErrorModel}},
)
def request_video_generation(payload: GenerateRequest, background: BackgroundTasks, response: Response, request: Request):
    now = _utcnow()
    # pre-compute where the file will live
    url = _result_url(payload.lectureId)
    expected = _estimate_total_seconds(len(payload.slideMessages))
    JOBS[payload.lectureId] = Job(
        lectureId=payload.lectureId,
        status="IN_PROGRESS",
        lastUpdated=now,
        resultUrl=url,
        startedAt=now,
        expectedDurationSec=expected,
        error=None,
    )
    # fire-and-forget
    background.add_task(process_generation, payload)
    # absolute Location per spec
    base = str(request.base_url).rstrip("/")
    response.headers["Location"] = f"{base}/v1/video/{payload.lectureId}/status"
    return GenerationAcceptedResponse(lectureId=payload.lectureId, createdAt=now)


@app.get(
    "/v1/video/{lectureId}/status",
    response_model=GenerationStatusResponse,
    responses={404: {"model": ErrorModel}},
)
def get_generation_status(lectureId: UUID):
    job = JOBS.get(lectureId)
    if not job:
        return JSONResponse(status_code=404, content={"code": "NOT_FOUND", "message": "Request not found"})
    return GenerationStatusResponse(
        lectureId=job.lectureId,
        status=job.status,
        lastUpdated=job.lastUpdated,
        resultUrl=job.resultUrl,
        estimatedSecondsLeft=_eta_seconds(job),
        error=job.error,
    )

# Run: uvicorn main:app --host 0.0.0.0 --port 8080 --reload
