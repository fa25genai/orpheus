import os
import shutil
import uuid
from collections.abc import Generator
from datetime import datetime, timedelta, timezone
from pathlib import Path
from queue import Queue
from threading import Event, Thread
from time import sleep
from typing import Dict, List, Literal, Optional
from uuid import UUID

import requests
from fastapi import Depends, FastAPI, File, HTTPException, Request, Response, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, StringConstraints
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, create_engine, func
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker
from typing_extensions import Annotated

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


class AvatarImagePayload(BaseModel):
    id: UUID
    filePath: str
    mimeType: Optional[str] = None
    sizeBytes: Optional[int] = None
    createdAt: datetime


class AvatarCreatedResponse(BaseModel):
    avatarId: UUID
    image: Optional[AvatarImagePayload] = None


# ---------------------------
# DB layer (SQLAlchemy 2.x)
# ---------------------------


class Base(DeclarativeBase):
    pass


engine = create_engine(DATABASE_URL, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class Avatar(Base):
    __tablename__ = "avatars"
    avatar_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    images: Mapped[list["AvatarImage"]] = relationship(back_populates="avatar", cascade="all, delete-orphan")


class AvatarImage(Base):
    __tablename__ = "avatar_images"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    avatar_id: Mapped[str] = mapped_column(String(36), ForeignKey("avatars.avatar_id", ondelete="CASCADE"), index=True)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)  # absolute path on disk
    mime_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    original_filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    avatar: Mapped["Avatar"] = relationship(back_populates="images")


@app.on_event("startup")
def _startup_create_tables() -> None:
    Base.metadata.create_all(engine)
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

ALLOWED_IMAGE_MIMES = {"image/png", "image/jpeg", "image/webp"}


class AvatarImageResponse(BaseModel):
    id: UUID
    avatarId: UUID
    filePath: str
    mimeType: Optional[str] = None
    sizeBytes: Optional[int] = None
    createdAt: datetime


def _ext_from_mime(mime: str) -> str:
    return {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}.get(mime, "bin")


def _save_upload_to_disk(avatar_id: UUID, upload: UploadFile) -> Path:
    if upload.content_type not in ALLOWED_IMAGE_MIMES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported image type: {upload.content_type}",
        )
    image_id = uuid.uuid4()
    avatar_dir = IMAGES_OUTPUT_DIR / str(avatar_id)
    avatar_dir.mkdir(parents=True, exist_ok=True)
    ext = _ext_from_mime(upload.content_type or "")
    target = avatar_dir / f"{image_id}.{ext}"
    # stream copy to avoid loading entire file in memory
    with target.open("wb") as out:
        shutil.copyfileobj(upload.file, out)
    return target


@app.post(
    "/v1/avatars",
    status_code=201,
    response_model=AvatarCreatedResponse,
    tags=["avatar"],
)
def create_avatar(
    file: Optional[UploadFile] = File(default=None),
    db: Session = Depends(get_db),
) -> AvatarCreatedResponse:
    # Create avatar id and persist
    avatar_id = uuid.uuid4()
    db_avatar = Avatar(avatar_id=str(avatar_id))
    db.add(db_avatar)

    image_payload: Optional[AvatarImagePayload] = None
    if file is not None:
        saved_path = _save_upload_to_disk(avatar_id, file)
        size = saved_path.stat().st_size
        db_img = AvatarImage(
            id=str(uuid.uuid4()),
            avatar_id=str(avatar_id),
            file_path=str(saved_path),
            mime_type=file.content_type,
            size_bytes=size,
            original_filename=file.filename,
        )
        db.add(db_img)
        db.flush()  # populate server defaults like created_at
        image_payload = AvatarImagePayload(
            id=UUID(db_img.id),
            filePath=db_img.file_path,
            mimeType=db_img.mime_type,
            sizeBytes=db_img.size_bytes,
            createdAt=db_img.created_at or datetime.now(timezone.utc),
        )

    db.commit()
    return AvatarCreatedResponse(avatarId=avatar_id, image=image_payload)


@app.post(
    "/v1/avatars/{avatarId}/images",
    status_code=201,
    response_model=AvatarImageResponse,
    tags=["avatar"],
)
def add_avatar_image(
    avatarId: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> AvatarImageResponse:
    # Strict: avatar must exist
    avatar = db.get(Avatar, str(avatarId))
    if not avatar:
        raise HTTPException(status_code=404, detail="Avatar not found")

    saved_path = _save_upload_to_disk(avatarId, file)
    size = saved_path.stat().st_size
    db_img = AvatarImage(
        id=str(uuid.uuid4()),
        avatar_id=str(avatarId),
        file_path=str(saved_path),
        mime_type=file.content_type,
        size_bytes=size,
        original_filename=file.filename,
    )
    db.add(db_img)
    db.commit()
    db.refresh(db_img)

    return AvatarImageResponse(
        id=UUID(db_img.id),
        avatarId=avatarId,
        filePath=db_img.file_path,
        mimeType=db_img.mime_type,
        sizeBytes=db_img.size_bytes,
        createdAt=db_img.created_at,
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


def generate_audio(
    slide_text: Optional[str] = "Hello students! I want you to drink coffee.",
    course_id: Optional[str] = "course_123",
    voice_sample: str = "/app/database/voice_sample/kursche_voice.mp3",
    prompt_id: Optional[UUID] = None,
    user_profile: Optional[UserProfile] = None,
    audio_counter: int = 0,
) -> Optional[str]:
    """
    Generate a WAV file for one slide.
    Saves under /data/jobs/<promptId>/<N>.wav
    """
    if prompt_id is None:
        print("[generate_audio] prompt_id is required")
        return None

    audio_api_url = os.getenv("GEN_AUDIO", "http://localhost:7000/v1/audio/generate")

    job_folder = job_dir(prompt_id)
    wav_path = job_folder / f"{audio_counter}.wav"

    try:
        if not Path(voice_sample).is_file():
            print(f"[generate_audio] Voice sample not found: {voice_sample}")
            return None

        with open(voice_sample, "rb") as f:
            is_debug = os.getenv("DEBUG", "not debug")
            data = {"slide_text": slide_text, "debug": is_debug}
            files = {"voice_file": (os.path.basename(voice_sample), f, "audio/mpeg")}
            print(f"[generate_audio] Posting to {audio_api_url}")
            resp = requests.post(audio_api_url, data=data, files=files, timeout=(5, 600))
        resp.raise_for_status()

        wav_path.write_bytes(resp.content)
        print(f"[generate_audio] OK -> {wav_path}")
        return str(wav_path)

    except requests.RequestException as e:
        print(f"[generate_audio] Request error: {e}")
        return None
    except Exception as e:
        print(f"[generate_audio] Unexpected error: {e}")
        return None


def generate_video(
    audio_path: Optional[str] = None,
    prompt_id: Optional[UUID] = None,
    course_id: Optional[str] = None,
    user_profile: Optional[UserProfile] = None,
    video_counter: int = 0,
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
        task: SlideTask = SLIDE_QUEUE.get()  # blocking
        pid = task.promptId
        now = _utcnow()
        _purge_stale_jobs(now)
        job = JOBS.get(pid)

        # Sicherheit: Job-Eintrag muss existieren
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

        # Status/ETA Update vor Start dieses Slides
        job.status = "IN_PROGRESS"
        job.lastUpdated = now
        job.lastTouched = now
        _estimate_total_seconds_for_new_slide(job)
        JOBS[pid] = job

        # Audio -> Video für genau diesen Slide
        try:
            # TODO send status in progress for voice for audio with slide number (one based?) and pid
            aurl = generate_audio(
                slide_text=task.text,
                course_id=task.courseId,
                prompt_id=pid,
                user_profile=task.userProfile,
                audio_counter=task.slideNo,
            )
            # TODO send status done for voice with slide number (one based?) and pid
            if aurl:
                # TODO send status in progress for video for audio with slide number (one based?) and pid
                generate_video(
                    audio_path=aurl,
                    prompt_id=pid,
                    course_id=task.courseId,
                    user_profile=task.userProfile,
                    video_counter=task.slideNo,
                )
                # TODO send status done for video with slide number (one based?) and pid
        except Exception as e:
            print(f"[worker] error on slide {task.slideNo} for {pid}: {e!r}")
            # mark job as failed but keep queue going for other jobs
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
            # Nach jedem Slide die lastUpdated Zeit aktualisieren
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
