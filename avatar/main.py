import asyncio

import requests
from datetime import datetime, timezone
from typing import List, Optional, Literal, Dict, Tuple, Union
import os
import shutil
import uuid
from uuid import UUID
from pathlib import Path

import httpx

from fastapi import FastAPI, BackgroundTasks, Response, Request
from fastapi import UploadFile, File, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, String, DateTime, Text, Integer, func, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker, Session
from pydantic import BaseModel, Field, constr

from fastapi.middleware.cors import CORSMiddleware

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


def get_db() -> Session:
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
    size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 👈 add Integer
    original_filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    avatar: Mapped["Avatar"] = relationship(back_populates="images")


@app.on_event("startup")
def _startup_create_tables() -> None:
    Base.metadata.create_all(engine)


# ---------- Saving helpers ----------
def job_dir(prompt_id: UUID) -> Path:
    d = VIDEO_ROOT / str(prompt_id)
    d.mkdir(parents=True, exist_ok=True)
    return d

def slide_paths(prompt_id: UUID, idx_one_based: int) -> tuple[Path, Path]:
    d = job_dir(prompt_id)
    temp = d / f".{idx_one_based}.mp4.part"   # render/download into this temp file
    final = d / f"{idx_one_based}.mp4"        # publish atomically
    return temp, final

def public_video_url(prompt_id: UUID, idx_one_based: int) -> str:
    return f"{PUBLIC_VIDEOS_BASE}/{prompt_id}/{idx_one_based}.mp4"

def folder_url(prompt_id: UUID) -> str:
    return f"{PUBLIC_VIDEOS_BASE}/{prompt_id}/"


# ---------------------------
# Avatars API 
# ---------------------------

ALLOWED_IMAGE_MIMES = {"image/png", "image/jpeg", "image/webp"}


class AvatarCreatedResponse(BaseModel):
    avatarId: UUID
    image: Optional[Dict] = None  # { id, filePath, mimeType, sizeBytes, createdAt }


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
):
    # Create avatar id and persist
    avatar_id = uuid.uuid4()
    db_avatar = Avatar(avatar_id=str(avatar_id))
    db.add(db_avatar)

    image_payload = None
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
        image_payload = {
            "id": db_img.id,
            "filePath": db_img.file_path,
            "mimeType": db_img.mime_type,
            "sizeBytes": db_img.size_bytes,
            "createdAt": db_img.created_at or datetime.now(timezone.utc),
        }

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
):
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
# to be stored in a db
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

async def generate_audio(
        slide_text: Optional[str] = "Hello students! I want you to drink coffe.",
        course_id: Optional[str] = "course_123",
        voice_sample: str = r"C:\Users\julia\Desktop\Ferienakademie\orpheus\avatar\OpenVoice\kursche_voice.mp3",
        prompt_id: Optional[UUID] = "default123",
        user_profile: Optional[UserProfile] = None,
        audio_counter: Optional[int] = 5) -> str:
    """
    Create per-slide audio files from text.
    Returns a list of file paths (one per slide).
    """
    audio_api_url = os.getenv("GEN_AUDIO", "http://localhost:8000/v1/audio/generate")
    timeout = httpx.Timeout(connect=5.0, read=120.0, write=30.0, pool=5.0)

    output_wav = f"blabla_{audio_counter}.wav"

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            with open(voice_sample, "rb") as f:
                # slide_text as simple form field, voice file as file field
                data = {"slide_text": slide_text}
                files = {"voice_file": (os.path.basename(voice_sample), f, "audio/mpeg")}

                resp = await client.post(audio_api_url, data=data, files=files)
                resp.raise_for_status()

        # assume API returns WAV bytes directly
        Path(output_wav).write_bytes(resp.content)
        print(f"[generate_audio] OK -> saved to {output_wav}")
        return output_wav

    except httpx.HTTPStatusError as e:
        print(f"[generate_audio] HTTP {e.response.status_code}: {e.response.text[:200]}")
        return None
    except httpx.RequestError as e:
        print(f"[generate_audio] Request error: {e}")
        return None


async def generate_video(
    audio_path: Optional[str] = None,
    prompt_id: Optional[UUID] = None,
    course_id: Optional[str] = None,
    user_profile: Optional[UserProfile] = None,
    video_counter: Optional[int] = None,
) -> Optional[str]:
    """
    Calls the renderer which returns video BYTES, streams them to /data/jobs/<promptId>/.N.mp4.part,
    then atomically publishes to N.mp4. Returns the absolute final path on success.
    """
    if prompt_id is None or video_counter is None:
        print("generate_video: prompt_id and video_counter are required.")
        return None

    slide_no = video_counter + 1  # 1-based
    temp_path, final_path = slide_paths(prompt_id, slide_no)
    temp_path.parent.mkdir(parents=True, exist_ok=True)

    # Resolve inputs
    resolved_audio = audio_path or "/data/example/krusche_voice.wav"
    source_path = "/data/example/image_michal.png"

    video_api_url = os.getenv("GEN_VIDEO", "http://localhost:8000/infer")

    # Prepare multipart files (renderer expects uploads and returns raw MP4 bytes)
    files = {
        "audio": ("audio.wav", open(resolved_audio, "rb"), "audio/wav"),
        "source": ("image.png", open(source_path, "rb"), "image/png"),
    }

    timeout = httpx.Timeout(connect=5.0, read=600.0, write=60.0, pool=5.0)

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            req = client.build_request("POST", video_api_url, files=files)
            async with client.send(req, stream=True) as resp:
                if resp.status_code >= 400:
                    body = await resp.aread()
                    print(f"[generate_video] HTTP {resp.status_code}: {body[:500]!r}")
                    return None

                ctype = resp.headers.get("Content-Type", "").lower()
                if "application/json" in ctype:
                    # Unexpected here; renderer should return bytes
                    data = await resp.json()
                    print(f"[generate_video] Unexpected JSON: {str(data)[:500]}")
                    return None

                # Stream to temp file
                with temp_path.open("wb") as f:
                    async for chunk in resp.aiter_bytes(chunk_size=1024 * 256):
                        if chunk:
                            f.write(chunk)
                    f.flush()
                    os.fsync(f.fileno())
    except Exception as e:
        print(f"[generate_video] stream/write error: {e!r}")
        return None
    finally:
        # close file handles from 'files'
        for v in files.values():
            try:
                v[1].close()
            except Exception:
                pass

    # Validate non-empty
    try:
        if temp_path.stat().st_size == 0:
            print("[generate_video] empty file received")
            return None
    except OSError as e:
        print(f"[generate_video] stat failed: {e!r}")
        return None

    # Atomic publish
    try:
        temp_path.replace(final_path)
    except OSError as e:
        print(f"[generate_video] publish rename failed: {e!r}")
        return None

    print(f"[generate_video] OK -> {final_path}")
    return str(final_path)


# TODO: maybe remove return
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
        errors: Dict[int, str] = {}  # Dict {slide index: error}
        audio_done_q: asyncio.Queue[Tuple[int, str]] = asyncio.Queue()  # consumer for finished audios

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
                    await audio_done_q.put((i, ""))  # consumer doesnt block in case there is no audio

        async def video_consumer():
            processed = 0
            while processed < slides_amount:
                idx, aurl = await audio_done_q.get()
                processed += 1
                if not aurl:
                    continue  # audio "" oder not excisting -> no video
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
def _run_process_generation(payload: "GenerateRequest") -> None:
    # Runs the async coroutine in a fresh event loop, safe for BackgroundTasks
    # can't run in the same loop context

    loop = asyncio.get_event_loop()
    '''
    BackgroundTasks executes after the response in the same event loop context;
    calling asyncio.run() from a running loop raises: 
    “asyncio.run() cannot be called from a running event loop”.
    '''
    loop.create_task(process_generation(payload))


@app.post(
    "/v1/video/generate",
    response_model=GenerationAcceptedResponse,
    status_code=202,
    responses={400: {"model": ErrorModel}, 401: {"model": ErrorModel}, 500: {"model": ErrorModel}},
    tags=["video"],
)
async def request_video_generation(payload: GenerateRequest, background: BackgroundTasks, response: Response, request: Request):
    now = _utcnow()

    # create the per-job output folder now and compute its public URL
    job_dir(payload.promptId)
    folder = folder_url(payload.promptId)

    expected = _estimate_total_seconds(len(payload.slideMessages))
    # set resultUrl to the folder so /status points somewhere real
    JOBS[payload.promptId] = Job(
        promptId=payload.promptId,
        status="IN_PROGRESS",
        lastUpdated=now,
        resultUrl=folder,
        startedAt=now,
        expectedDurationSec=expected,
        error=None,
    )

    # fire-and-forget
    background.add_task(_run_process_generation, payload)

    base = str(request.base_url).rstrip("/")
    response.headers["Location"] = f"{base}/v1/video/{payload.promptId}/status"
    return GenerationAcceptedResponse(promptId=payload.promptId, createdAt=now)


@app.get(
    "/v1/video/{promptId}/status",
    response_model=GenerationStatusResponse,
    responses={404: {"model": ErrorModel}},
    tags=["video"],
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
