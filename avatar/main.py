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
#to be stored in a db
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

    # hard_code
    return f"/data/example/krusche_voice.wav"

    # return audio_path


async def generate_video(
    audio_path: Optional[str] = None,
    prompt_id: Optional[UUID] = None,
    course_id: Optional[str] = None,
    user_profile: Optional[UserProfile] = None,
    video_counter: Optional[int] = None,
) -> Optional[str]:
    """
    Assemble the final video using the audio track and a source image.
    Returns the path/URL of the rendered video, or None on failure.
    """
    if prompt_id is None or video_counter is None:
        print("generate_video: prompt_id and video_counter are required.")
        return None

    pid = str(prompt_id)

    # Defaults for your MVP; swap with course-specific assets later
    out_path = f"/data/{pid}_{video_counter}.mp4"
    resolved_audio = audio_path or "/data/example/krusche_voice.wav"
    source_path = "/data/example/image_michal.png"  # could be derived from course_id/user_profile

    # Call to API
    video_api_url = os.getenv("GEN_VIDEO", "http://localhost:8000/video/infer")

    payload = {
        "audio_path": resolved_audio,
        "source_path": source_path,
        "output_path": out_path,
    }


    print(f"[generate_video] POST {api_url} payload={payload}")

    # Reasonable timeouts for an internal service call
    timeout = httpx.Timeout(connect=5.0, read=120.0, write=30.0, pool=5.0)

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(video_api_url, json=payload)
            resp.raise_for_status()

        # The infer API is expected to return JSON with "output_path"
        data = resp.json()
        result = data.get("output_path") or out_path
        print(f"[generate_video] OK -> {result}")
        return result

    except httpx.HTTPStatusError as e:
        # Server returned non-2xx
        body = e.response.text[:500]
        print(f"[generate_video] HTTP {e.response.status_code}: {body}")
        return None
    except (httpx.RequestError, ValueError) as e:
        # Network error or JSON parse issue
        print(f"[generate_video] request/json error: {e!r}")
        return None



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
    #can't run in the same loop context

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
    background.add_task(_run_process_generation, payload)    # absolute Location per spec
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
