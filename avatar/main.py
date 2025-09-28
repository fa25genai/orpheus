import os
from collections.abc import Generator
from datetime import datetime, timedelta, timezone
from pathlib import Path
from queue import Queue
from threading import Event, Thread
from time import sleep
from typing import Dict, List, Literal, Optional
from uuid import UUID

import requests
from fastapi import Depends, FastAPI, File, Form, Query, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, StringConstraints
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from typing_extensions import Annotated

import media.avatar_media as media
import media.avatar_queries as avatar_queries
import media.avatar_updates as avatar_updates

app = FastAPI(title="Service Video-Generation APIs", version="0.1")
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------
# Config (env-driven)
# ---------------------------
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")
IMAGES_OUTPUT_DIR = Path(os.getenv("IMAGES_OUTPUT_DIR", "data/avatars")).resolve()
IMAGES_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

VIDEO_ROOT = Path(os.getenv("VIDEO_ROOT", "/data/jobs")).resolve()
PUBLIC_VIDEOS_BASE = os.getenv("PUBLIC_VIDEOS_BASE", "/videos/jobs")
VIDEO_ROOT.mkdir(parents=True, exist_ok=True)

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
    enrolled_courses: Optional[List[str]] = None


VoiceTrack = Annotated[str, StringConstraints(min_length=1)]


class GenerateRequest(BaseModel):
    voiceTrack: VoiceTrack
    slideNumber: int = Field(..., ge=0)
    promptId: UUID
    courseId: str
    userProfile: UserProfile
    slot: Literal["default", "beginning", "ending"] = "default"  # NEW

class ErrorModel(BaseModel):
    code: Optional[str] = None
    message: Optional[str] = None


class GenerationAcceptedResponse(BaseModel):
    promptId: UUID
    createdAt: datetime


class GenerationStatusResponse(BaseModel):
    promptId: UUID
    status: Literal["IN_PROGRESS", "FAILED", "DONE"]
    lastUpdated: datetime
    resultUrl: str  # always present now
    estimatedSecondsLeft: int  # 0 when DONE/FAILED
    error: Optional[ErrorModel] = None

class SlideTask(BaseModel):
    promptId: UUID
    courseId: str
    userProfile: UserProfile
    text: str
    slideNo: int  # 1-based numbering
    slot: Literal["default", "beginning", "ending"] = "default"



# ---------------------------
# DB layer (SQLAlchemy 2.x)
# ---------------------------


engine = create_engine(
    DATABASE_URL,
    future=True,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.on_event("startup")
def _startup_create_tables() -> None:
    media.Base.metadata.create_all(engine)
    _start_worker_once()


# ---------- Saving helpers ----------
def job_dir(prompt_id: UUID) -> Path:
    d = VIDEO_ROOT / str(prompt_id)
    d.mkdir(parents=True, exist_ok=True)
    return d


def folder_url(prompt_id: UUID) -> str:
    return f"{PUBLIC_VIDEOS_BASE}/{prompt_id}/"


# ---------------------------
# Avatars API
# ---------------------------


@app.post(
    "/v1/avatars",
    status_code=201,
    response_model=media.AvatarCreatedResponse,
    tags=["avatar"],
)
def create_avatar(
    name: Optional[str] = Form(None),
    courseId: UUID = Form(...),
    slot: Optional[str] = Form('default'),  # accepts "default", "beginning", "ending" (+ minor typos)
    image_file: UploadFile = File(..., description="png/jpeg/webp"),
    audio_file: UploadFile = File(..., description="mp3/wav/flac/webm"),
    db: Session = Depends(get_db),
) -> media.AvatarCreatedResponse:
    return media.create_avatar_with_media(
        db=db,
        image_file=image_file,
        audio_file=audio_file,
        name=name,
        course_id=courseId,
        slot=slot,  # new
    )


@app.get(
    "/v1/avatars/by-course/{courseId}",
    response_model=List[media.AvatarCreatedResponse],
    tags=["avatar"],
)
def get_avatars_by_course_endpoint(
    courseId: UUID,
    slot: Optional[str] = Query(None, description="optional: default | beginning | ending"),
    db: Session = Depends(get_db),
):
    return avatar_queries.get_avatars_by_course(db=db, course_id=courseId, slot=slot)


# Replace only IMAGE
@app.post(
    "/v1/avatars/{courseId}/{slot}/image",
    response_model=media.AvatarCreatedResponse,
    tags=["avatar"],
)
def replace_avatar_image_endpoint(
    courseId: UUID,
    slot: str,
    image_file: UploadFile = File(..., description="png/jpeg/webp"),
    db: Session = Depends(get_db),
) -> media.AvatarCreatedResponse:
    return avatar_updates.replace_avatar_image(
        db=db, course_id=courseId, slot=slot, image_file=image_file, delete_previous=True
    )

# Replace only AUDIO
@app.post(
    "/v1/avatars/{courseId}/{slot}/audio",
    response_model=media.AvatarCreatedResponse,
    tags=["avatar"],
)
def replace_avatar_audio_endpoint(
    courseId: UUID,
    slot: str,
    audio_file: UploadFile = File(..., description="mp3/wav/flac/webm"),
    db: Session = Depends(get_db),
) -> media.AvatarCreatedResponse:
    return avatar_updates.replace_avatar_audio(
        db=db, course_id=courseId, slot=slot, audio_file=audio_file, delete_previous=True
    )
# ---------------------------
# In-memory job store & queue
# ---------------------------


class Job(BaseModel):
    promptId: UUID
    status: Literal["IN_PROGRESS", "FAILED", "DONE"]
    lastUpdated: datetime
    lastTouched: datetime
    resultUrl: str
    startedAt: datetime
    expectedDurationSec: int
    error: Optional[ErrorModel] = None


JOBS: Dict[UUID, Job] = {}

# Remove jobs after 24h of inactivity
JOB_TTL = timedelta(hours=24)
CLEANUP_INTERVAL_SECONDS = 900


# FIFO Queue für einzelne Slides
class SlideTask(BaseModel):
    promptId: UUID
    courseId: str
    userProfile: UserProfile
    text: str
    slideNo: int  # 1-based numbering
    slot: Literal["default", "beginning", "ending"] = "default"  # NEW


SLIDE_QUEUE: "Queue[SlideTask]" = Queue()
_WORKER_STARTED = Event()
_CLEANUP_STARTED = Event()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _estimate_total_seconds_for_new_slide(job: Job) -> None:
    """
    Erhöhe die ETA heuristisch um ~6s pro Slide. Beim ersten Slide +8s Overhead.
    """
    if job.expectedDurationSec == 0:
        job.expectedDurationSec = 8 + 6  # first slide
    else:
        job.expectedDurationSec += 6


def _eta_seconds(job: Job) -> int:
    if job.status in ("DONE", "FAILED"):
        return 0
    elapsed = int((_utcnow() - job.startedAt).total_seconds())
    remaining = job.expectedDurationSec - elapsed
    return max(0, remaining)


def _purge_stale_jobs(now: Optional[datetime] = None) -> None:
    """Drop job entries that have been idle longer than JOB_TTL."""
    now = now or _utcnow()
    for pid, job in list(JOBS.items()):
        last_touched = getattr(job, "lastTouched", job.lastUpdated)
        if now - last_touched > JOB_TTL:
            JOBS.pop(pid, None)


# ---------------------------
# Audio / Video Generators
# ---------------------------


# imports you’ll need at top of file
from pathlib import Path

from sqlalchemy.orm import Session


def generate_audio(
    slide_text: Optional[str],
    course_id: Optional[str],
    prompt_id: Optional[UUID],
    user_profile: Optional[UserProfile],
    audio_counter: int,
    *,
    db: Session,                 # NEW: DB session
    slot: str = "default",       # NEW: optional slot
) -> Optional[str]:
    """
    Generate a WAV file for one slide using the avatar audio stored in DB.
    Saves under /data/jobs/<promptId>/<N>.wav
    """
    if prompt_id is None:
        print("[generate_audio] prompt_id is required"); return None

    audio_api_url = os.getenv("GEN_AUDIO", "http://localhost:7000/v1/audio/generate")
    job_folder = job_dir(prompt_id)
    wav_path = job_folder / f"{audio_counter}.wav"

    try:
        # 1) Fetch reference voice from DB by (course_id, slot)
        ref = avatar_queries.get_latest_audio_for_course_slot(db, course_id, slot)
        ref_path = Path(ref.file_path)
        if not ref_path.is_file():
            print(f"[generate_audio] DB voice not found on disk: {ref_path}")
            return None

        # 2) Call TTS with the DB audio as voice_file
        is_debug = os.getenv("DEBUG", "not debug")
        data = {"slide_text": slide_text, "debug": is_debug}
        with ref_path.open("rb") as f:
            files = {"voice_file": (ref_path.name, f, ref.mime_type or "audio/mpeg")}
            print(f"[generate_audio] Posting to {audio_api_url}")
            resp = requests.post(audio_api_url, data=data, files=files, timeout=(5, 600))
        resp.raise_for_status()

        # 3) Save returned WAV
        wav_path.write_bytes(resp.content)
        print(f"[generate_audio] OK -> {wav_path}")
        return str(wav_path)

    except requests.RequestException as e:
        print(f"[generate_audio] Request error: {e}"); return None
    except Exception as e:
        print(f"[generate_audio] Unexpected error: {e}"); return None

def generate_video(
    audio_path: Optional[str] = None,
    prompt_id: Optional[UUID] = None,
    course_id: Optional[str] = None,
    user_profile: Optional[UserProfile] = None,
    video_counter: int = 0,
    source_image_path: Optional[str] = None,
) -> Optional[str]:
    """
    Render MP4 video for one slide using audio and a static image.
    Saves under /data/jobs/<promptId>/<N>.mp4
    """
    if prompt_id is None or video_counter is None:
        print("[generate_video] prompt_id and video_counter are required")
        return None

    video_api_url = os.getenv("GEN_VIDEO", "http://localhost:8000/infer")
    job_folder = job_dir(prompt_id)
    temp_path = job_folder / f".{video_counter}.mp4.part"
    final_path = job_folder / f"{video_counter}.mp4"

    resolved_audio = audio_path or f"{job_folder}/{video_counter}.wav"
    if not Path(resolved_audio).is_file():
        print(f"[generate_video] Audio file not found: {resolved_audio}")
        return None

    # choose your static image
    source_path = source_image_path
    if not source_path or not Path(source_path).is_file():
        print(f"[generate_video] Source image not found: {source_path}")
        source_path = "/app/database/avatar_sample/image_michal.png"
    if not Path(source_path).is_file():
        print(f"[generate_video] Source image not found: {source_path}")
        return None
    files = {
        "audio": ("audio.wav", open(resolved_audio, "rb"), "audio/wav"),
        "source": ("image.png", open(source_path, "rb"), "image/png"),
    }
    is_debug = os.getenv("DEBUG", "not debug")
    data = {"debug": is_debug}

    try:
        print(f"[generate_video] Posting to {video_api_url}")
        with requests.post(video_api_url, files=files, data=data, stream=True, timeout=(5, 600)) as resp:
            if resp.status_code >= 400:
                print(f"[generate_video] HTTP {resp.status_code}: {resp.text[:200]}")
                return None

            # Stream MP4 to temp file
            with temp_path.open("wb") as f:
                for chunk in resp.iter_content(chunk_size=1024 * 256):
                    if chunk:
                        f.write(chunk)
                f.flush()
                os.fsync(f.fileno())

        if temp_path.stat().st_size == 0:
            print("[generate_video] empty file received")
            return None

        temp_path.replace(final_path)
        print(f"[generate_video] OK -> {final_path}")
        return str(final_path)

    except requests.RequestException as e:
        print(f"[generate_video] Request error: {e}")
        return None
    except Exception as e:
        print(f"[generate_video] Unexpected error: {e}")
        return None
    finally:
        for v in files.values():
            try:
                v[1].close()
            except Exception:
                pass


# ---------------------------
# Cleanup Thread
# ---------------------------


def _cleanup_loop() -> None:
    while True:
        _purge_stale_jobs()
        sleep(CLEANUP_INTERVAL_SECONDS)


# ---------------------------
# Worker-Thread
# ---------------------------


def _worker_loop() -> None:
    print("[worker] started")
    while True:
        task: SlideTask = SLIDE_QUEUE.get()
        pid = task.promptId
        now = _utcnow()
        _purge_stale_jobs(now)
        job = JOBS.get(pid)

        if not job:
            job = Job(
                promptId=pid,
                status="IN_PROGRESS",
                lastUpdated=now,
                lastTouched=now,
                resultUrl=folder_url(pid),
                startedAt=now,
                expectedDurationSec=0,
                error=None,
            )
            JOBS[pid] = job
        else:
            job.lastTouched = now

        job.status = "IN_PROGRESS"
        job.lastUpdated = now
        job.lastTouched = now
        _estimate_total_seconds_for_new_slide(job)
        JOBS[pid] = job

        try:
            with SessionLocal() as db:
                aurl = generate_audio(
                    slide_text=task.text,
                    course_id=task.courseId,
                    prompt_id=pid,
                    user_profile=task.userProfile,
                    audio_counter=task.slideNo,
                    db=db,
                    slot=getattr(task, "slot", "default"),
                )

                # fetch the image while DB session is open
                source_path = None
                try:
                    img = avatar_queries.get_latest_image_for_course_slot(
                        db, course_id=task.courseId, slot=getattr(task, "slot", "default")
                    )
                    source_path = img.file_path
                except Exception as e:
                    print(f"[worker] no image for course/slot: {e!r}")
                    source_path = None

            if aurl:
                generate_video(
                    audio_path=aurl,
                    prompt_id=pid,
                    course_id=task.courseId,
                    user_profile=task.userProfile,
                    video_counter=task.slideNo,
                    source_image_path=source_path,   # ✅ pass image path here
                )

        except Exception as e:
            print(f"[worker] error on slide {task.slideNo} for {pid}: {e!r}")
            job = JOBS.get(pid)
            if job:
                fail_time = _utcnow()
                job.status = "FAILED"
                job.lastUpdated = fail_time
                job.lastTouched = fail_time
                job.error = ErrorModel(code="GENERATION_FAILED", message=str(e))
                JOBS[pid] = job
        finally:
            SLIDE_QUEUE.task_done()
            job = JOBS.get(pid)
            if job and job.status != "FAILED":
                done_time = _utcnow()
                job.lastUpdated = done_time
                job.lastTouched = done_time
                JOBS[pid] = job


def _start_worker_once() -> None:
    if not _WORKER_STARTED.is_set():
        worker_thread = Thread(target=_worker_loop, name="slide-worker", daemon=True)
        worker_thread.start()
        _WORKER_STARTED.set()
    if not _CLEANUP_STARTED.is_set():
        cleanup_thread = Thread(target=_cleanup_loop, name="job-cleanup", daemon=True)
        cleanup_thread.start()
        _CLEANUP_STARTED.set()


# ---------------------------
# Routes
# ---------------------------


@app.post(
    "/v1/video/generate",
    response_model=GenerationAcceptedResponse,
    status_code=202,
    responses={400: {"model": ErrorModel}, 401: {"model": ErrorModel}, 500: {"model": ErrorModel}},
    tags=["video"],
)
def request_video_generation(payload: GenerateRequest, response: Response, request: Request) -> JSONResponse | GenerationAcceptedResponse:
    """
    Nimmt einen einzelnen Slide entgegen (payload.voiceTrack),
    erwartet eine explizite Slide-Nummer (payload.slideNumber) und enqueued die Aufgabe.
    """
    now = _utcnow()
    _purge_stale_jobs(now)

    # Validierung: Voice Track
    text = payload.voiceTrack.strip()
    if not text:
        return JSONResponse(
            status_code=400,
            content={"code": "BAD_REQUEST", "message": "voiceTrack must not be empty"},
        )

    # Ordner existieren lassen
    job_dir(payload.promptId)
    folder = folder_url(payload.promptId)

    # Job anlegen/aktualisieren
    job = JOBS.get(payload.promptId)
    if not job:
        job = Job(
            promptId=payload.promptId,
            status="IN_PROGRESS",
            lastUpdated=now,
            lastTouched=now,
            resultUrl=folder,
            startedAt=now,
            expectedDurationSec=0,  # wird im Worker beim ersten Slide erhöht
            error=None,
        )
        JOBS[payload.promptId] = job
    else:
        job.lastTouched = now
        JOBS[payload.promptId] = job

    slide_no = payload.slideNumber

    # Enqueue
    SLIDE_QUEUE.put(
        SlideTask(
            promptId=payload.promptId,
            courseId=payload.courseId,
            userProfile=payload.userProfile,
            text=text,
            slideNo=slide_no,
            slot=getattr(payload, "slot", "default"),  # NEW
        )
    )

    base = str(request.base_url).rstrip("/")
    response.headers["Location"] = f"{base}/v1/video/{payload.promptId}/status"
    return GenerationAcceptedResponse(promptId=payload.promptId, createdAt=now)


@app.get(
    "/v1/video/{promptId}/status",
    response_model=GenerationStatusResponse,
    responses={404: {"model": ErrorModel}},
    tags=["video"],
)
def get_generation_status(promptId: UUID) -> GenerationStatusResponse | JSONResponse:
    _purge_stale_jobs()
    job = JOBS.get(promptId)
    if not job:
        return JSONResponse(status_code=404, content={"code": "NOT_FOUND", "message": "Request not found"})
    job.lastTouched = _utcnow()
    JOBS[promptId] = job
    return GenerationStatusResponse(
        promptId=job.promptId,
        status=job.status,
        lastUpdated=job.lastUpdated,
        resultUrl=job.resultUrl,
        estimatedSecondsLeft=_eta_seconds(job),
        error=job.error,
    )


# Run: uvicorn main:app --host 0.0.0.0 --port 8080 --reload
