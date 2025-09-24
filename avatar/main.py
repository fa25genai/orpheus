import asyncio
from datetime import datetime, timezone
from typing import List, Optional, Literal, Dict, Tuple, Union
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
    promptId: UUID
    courseId: str
    userProfile: UserProfile


class ErrorModel(BaseModel):
    code: Optional[str] = None
    message: Optional[str] = None


class GenerationAcceptedResponse(BaseModel):
    promptId: UUID
    createdAt: datetime
    # status omitted on purpose to match your earlier schema (202 body minimal)


class GenerationStatusResponse(BaseModel):
    promptId: UUID
    status: Literal["IN_PROGRESS", "FAILED", "DONE"]
    lastUpdated: datetime
    resultUrl: str  # always present now
    estimatedSecondsLeft: int  # 0 when DONE/FAILED
    error: Optional[ErrorModel] = None


# ---------------------------
# In-memory job store
# ---------------------------

class Job(BaseModel):
    promptId: UUID
    status: Literal["IN_PROGRESS", "FAILED", "DONE"]
    lastUpdated: datetime
    resultUrl: str
    # ETA bookkeeping
    startedAt: datetime
    expectedDurationSec: int
    error: Optional[ErrorModel] = None

# TODO: check usefullness of this
JOBS: Dict[UUID, Job] = {}

CDN_BASE = "https://cdn.example.com/videos"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _result_url(prompt_id: UUID) -> str:
    return f"{CDN_BASE}/{prompt_id}.mp4"


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

async def generate_audio(slide_text: str, course_id: str, prompt_id: UUID, user_profile: UserProfile, audio_counter: int) -> str:
    """
    Create per-slide audio files from text.
    Returns a list of file paths (one per slide).
    """
    pid = str(prompt_id)
    audio_path = f"/tmp/{pid}_{audio_counter}.wav"
    # TODO: generate real audio in OpenVoice container and save it in the mentioned path
    # use slide_text, course_id, prompt_id and user_profil for this
    return audio_path

async def generate_video(audio_path: str, prompt_id: UUID, course_id: str, user_profile: UserProfile, video_counter: int) -> str:
    """
    Assemble the final video using the audio tracks and slide content.
    Returns a URI (string) to the rendered video file which consists of one video per slide.
    """
    pid = str(prompt_id)
    out_path = f"file:///tmp/{pid}_{video_counter}.mp4"
    # TODO: generate real video in ditto-talkinghead container and save it in the mentioned path
    # use slide_text, course_id, prompt_id and user_profil for this
    return out_path

async def process_generation(payload: GenerateRequest) -> Dict[str, Union[List[Optional[str]], Dict[int, str], None]]:
    # set job to in progress
    job = JOBS.get(payload.promptId)
    if job:
        job.status = "IN_PROGRESS"
        job.lastUpdated = _utcnow()
        JOBS[payload.promptId] = job
    try:
        slides_amount = len(payload.slideMessages)
        audio_urls: List[Optional[str]] = [None] * slides_amount
        video_urls: List[Optional[str]] = [None] * slides_amount
        errors: Dict[int, str] = {} # Dict {slide index: error}
        audio_done_q: asyncio.Queue[Tuple[int, str]] = asyncio.Queue() # consumer for finished audios
        async def audio_producer():
            for i, text in enumerate(payload.slideMessages):
                try:
                    aurl = await generate_audio(
                        slide_text=text,
                        course_id=payload.courseId,
                        prompt_id=payload.promptId,
                        user_profile=payload.userProfile,
                        audio_counter=i,
                    )
                    audio_urls[i] = aurl
                    await audio_done_q.put((i, aurl))
                except Exception as e:
                    errors[i] = f"audio_error: {e!r}"
                    await audio_done_q.put((i, ""))  # consumer diesnt block in case there is no audio
        async def video_consumer():
            processed = 0
            while processed < slides_amount:
                idx, aurl = await audio_done_q.get()
                processed += 1
                if not aurl:
                    continue # audio "" oder not excisting -> no video
                try:
                    vurl = await generate_video(
                        audio_path=aurl,
                        prompt_id=payload.promptId,
                        course_id=payload.courseId,
                        user_profile=payload.userProfile,
                        video_counter=idx,
                    )
                    video_urls[idx] = vurl
                except Exception as e:
                    errors[idx] = f"video_error: {e!r}"
        prod = asyncio.create_task(audio_producer())
        cons = asyncio.create_task(video_consumer())
        await asyncio.gather(prod, cons)
        # set job to done
        if job:
            job.status = "DONE"
            job.lastUpdated = _utcnow()
            JOBS[payload.promptId] = job
        # return results
        return {
            "audioUrls": audio_urls,
            "videoUrls": video_urls,
            "errors": errors or None,
        }
    except Exception as exc:
        # set job to failed
        job = JOBS.get(payload.promptId, None)
        if job:
            job.status = "FAILED"
            job.lastUpdated = _utcnow()
            job.error = ErrorModel(code="GENERATION_FAILED", message=str(exc))
            JOBS[payload.promptId] = job
        # forward error
        raise

# ---------------------------
# Routes
# ---------------------------

@app.post(
    "/v1/video/generate",
    response_model=GenerationAcceptedResponse,
    status_code=202,
    responses={400: {"model": ErrorModel}, 401: {"model": ErrorModel}, 500: {"model": ErrorModel}},
)
async def request_video_generation(payload: GenerateRequest, background: BackgroundTasks, response: Response, request: Request):
    now = _utcnow()
    # pre-compute where the file will live
    url = _result_url(payload.promptId)
    expected = _estimate_total_seconds(len(payload.slideMessages))
    JOBS[payload.promptId] = Job(
        promptId=payload.promptId,
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
    response.headers["Location"] = f"{base}/v1/video/{payload.promptId}/status"
    return GenerationAcceptedResponse(promptId=payload.promptId, createdAt=now)


@app.get(
    "/v1/video/{promptId}/status",
    response_model=GenerationStatusResponse,
    responses={404: {"model": ErrorModel}},
)
def get_generation_status(promptId: UUID):
    job = JOBS.get(promptId)
    if not job:
        return JSONResponse(status_code=404, content={"code": "NOT_FOUND", "message": "Request not found"})
    return GenerationStatusResponse(
        promptId=job.promptId,
        status=job.status,
        lastUpdated=job.lastUpdated,
        resultUrl=job.resultUrl,
        estimatedSecondsLeft=_eta_seconds(job),
        error=job.error,
    )

# Run: uvicorn main:app --host 0.0.0.0 --port 8080 --reload