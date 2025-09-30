# avatar_media.py
from __future__ import annotations

import os
import shutil
import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship


class CourseAvatarSlot(str, Enum):
    default = "default"
    beginning = "beginning"
    ending = "ending"


# ----- Config -----
AVATARS_OUTPUT_DIR = Path(os.getenv("AVATARS_OUTPUT_DIR", "data/avatars")).resolve()
AVATARS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_IMAGE = {"image/png", "image/jpeg", "image/webp"}
ALLOWED_AUDIO = {"audio/mpeg", "audio/wav", "audio/x-wav", "audio/flac", "audio/x-flac", "audio/webm"}
EXT = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/webp": "webp",
    "audio/mpeg": "mp3",
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "audio/flac": "flac",
    "audio/x-flac": "flac",
    "audio/webm": "webm",
}


# ----- SQLAlchemy models -----
# If you already have a Base, remove this and from your_module import Base
class Base(DeclarativeBase):
    pass


class Avatar(Base):
    __tablename__ = "avatars"
    __table_args__ = (
        UniqueConstraint("course_id", "slot", name="uq_course_slot"),  # at most 1 per slot per course
    )

    avatar_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    name: Mapped[Optional[str]] = mapped_column(String(120), nullable=True, index=True)
    course_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    slot: Mapped[str] = mapped_column(String(64), nullable=False, index=True, default=CourseAvatarSlot.default.value, server_default=text("'default'"))

    images: Mapped[list["AvatarImage"]] = relationship(back_populates="avatar", cascade="all, delete-orphan")
    audios: Mapped[list["AvatarAudio"]] = relationship(back_populates="avatar", cascade="all, delete-orphan")


class AvatarImage(Base):
    __tablename__ = "avatar_images"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    avatar_id: Mapped[str] = mapped_column(String(36), ForeignKey("avatars.avatar_id", ondelete="CASCADE"), index=True)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)  # absolute path on disk (or CDN path if you prefer)
    mime_type: Mapped[Optional[str]] = mapped_column(String(64))
    size_bytes: Mapped[Optional[int]] = mapped_column(Integer)
    original_filename: Mapped[Optional[str]] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    avatar: Mapped["Avatar"] = relationship(back_populates="images")


class AvatarAudio(Base):
    __tablename__ = "avatar_audios"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    avatar_id: Mapped[str] = mapped_column(String(36), ForeignKey("avatars.avatar_id", ondelete="CASCADE"), index=True)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    mime_type: Mapped[Optional[str]] = mapped_column(String(64))
    size_bytes: Mapped[Optional[int]] = mapped_column(Integer)
    original_filename: Mapped[Optional[str]] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    avatar: Mapped["Avatar"] = relationship(back_populates="audios")


# ----- Pydantic responses (optional but nice) -----
class AvatarImageResponse(BaseModel):
    id: UUID
    avatarId: UUID
    filePath: str
    mimeType: Optional[str] = None
    sizeBytes: Optional[int] = None
    createdAt: datetime


class AvatarAudioResponse(BaseModel):
    id: UUID
    avatarId: UUID
    filePath: str
    mimeType: Optional[str] = None
    sizeBytes: Optional[int] = None
    createdAt: datetime


class AvatarCreatedResponse(BaseModel):
    avatarId: UUID
    name: Optional[str] = None
    courseId: Optional[str] = None
    slot: CourseAvatarSlot = CourseAvatarSlot.default
    createdAt: datetime
    image: Optional[AvatarImageResponse] = None
    audio: Optional[AvatarAudioResponse] = None


# ----- file helpers -----
def _save_upload(root: Path, avatar_id: UUID, upload: UploadFile, kind: str) -> Path:
    if kind == "image":
        allowed = ALLOWED_IMAGE
        sub = "images"
    elif kind == "audio":
        allowed = ALLOWED_AUDIO
        sub = "audios"
    else:
        raise ValueError("kind must be 'image' or 'audio'")

    ct = upload.content_type or ""
    if ct not in allowed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported {kind} type: {ct}")

    media_id = uuid.uuid4()
    folder = root / str(avatar_id) / sub
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / f"{media_id}.{EXT.get(ct, 'bin')}"
    with target.open("wb") as out:
        shutil.copyfileobj(upload.file, out)
    return target


# --- tiny helper to accept minor typos like 'defualt' and 'begining' ---
def _normalize_slot(value: Optional[str]) -> CourseAvatarSlot:
    if not value:
        return CourseAvatarSlot.default
    v = value.strip().lower()
    aliases = {
        "defualt": "default",
        "begining": "beginning",
        "start": "beginning",
        "end": "ending",
        "final": "ending",
    }
    v = aliases.get(v, v)
    try:
        return CourseAvatarSlot(v)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"slot must be one of: {', '.join(s.value for s in CourseAvatarSlot)}")


# ----- service function (call from your route) -----
def create_avatar_with_media(
    db: Session,
    image_file: UploadFile,
    audio_file: UploadFile,
    course_id: str,
    name: Optional[str] = None,
    slot: Optional[str] = None,  # <--- new
) -> AvatarCreatedResponse:
    avatar_uuid = uuid.uuid4()
    saved_paths: list[Path] = []

    the_slot = _normalize_slot(slot)

    try:
        avatar = Avatar(
            avatar_id=str(avatar_uuid),
            name=name,
            course_id=str(course_id),
            slot=the_slot.value,  # <--- save
        )
        db.add(avatar)
        db.flush()

        img_path = _save_upload(AVATARS_OUTPUT_DIR, avatar_uuid, image_file, "image")
        saved_paths.append(img_path)
        aud_path = _save_upload(AVATARS_OUTPUT_DIR, avatar_uuid, audio_file, "audio")
        saved_paths.append(aud_path)

        img = AvatarImage(
            id=str(uuid.uuid4()),
            avatar_id=str(avatar_uuid),
            file_path=str(img_path),
            mime_type=image_file.content_type,
            size_bytes=img_path.stat().st_size,
            original_filename=image_file.filename,
        )
        aud = AvatarAudio(
            id=str(uuid.uuid4()),
            avatar_id=str(avatar_uuid),
            file_path=str(aud_path),
            mime_type=audio_file.content_type,
            size_bytes=aud_path.stat().st_size,
            original_filename=audio_file.filename,
        )
        db.add_all([img, aud])
        db.commit()
        db.refresh(avatar)
        db.refresh(img)
        db.refresh(aud)

        return AvatarCreatedResponse(
            avatarId=UUID(avatar.avatar_id),
            name=avatar.name,
            courseId=(avatar.course_id) if avatar.course_id else None,
            slot=CourseAvatarSlot(avatar.slot),  # <--- expose in response
            createdAt=avatar.created_at,
            image=AvatarImageResponse(
                id=UUID(img.id),
                avatarId=UUID(avatar.avatar_id),
                filePath=img.file_path,
                mimeType=img.mime_type,
                sizeBytes=img.size_bytes,
                createdAt=img.created_at,
            ),
            audio=AvatarAudioResponse(
                id=UUID(aud.id),
                avatarId=UUID(avatar.avatar_id),
                filePath=aud.file_path,
                mimeType=aud.mime_type,
                sizeBytes=aud.size_bytes,
                createdAt=aud.created_at,
            ),
        )
    except IntegrityError:
        db.rollback()
        for p in saved_paths:
            try:
                p.unlink(missing_ok=True)
            except Exception:
                pass
        # (course_id, slot) is already taken
        raise HTTPException(status_code=409, detail="An avatar for this courseId and slot already exists.")
    except Exception:
        db.rollback()
        for p in saved_paths:
            try:
                p.unlink(missing_ok=True)
            except Exception:
                pass
        raise
