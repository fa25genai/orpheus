# media/avatar_updates.py
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Sequence, cast
from uuid import UUID

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .avatar_media import (
    AVATARS_OUTPUT_DIR,
    Avatar,
    AvatarAudio,
    AvatarAudioResponse,
    AvatarCreatedResponse,
    AvatarImage,
    AvatarImageResponse,
    CourseAvatarSlot,
    _normalize_slot,
    _save_upload,
)


def _get_avatar_or_404(db: Session, course_id: str, slot: Optional[str]) -> Avatar:
    the_slot = _normalize_slot(slot) if slot is not None else CourseAvatarSlot.default
    avatar = db.query(Avatar).filter(Avatar.course_id == course_id, Avatar.slot == the_slot.value).first()
    if not avatar:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Avatar not found for given courseId and slot",
        )
    return avatar


# ---- Non-generic "latest" helpers (avoid TypeVar/Protocol headaches with mypy) ----


def _ts(dt: Optional[datetime]) -> float:
    """Return a comparable timestamp, handling None and aware/naive datetimes."""
    if dt is None:
        return float("-inf")
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc).timestamp()
    return dt.timestamp()


def _latest_image_or_none(items: Sequence[AvatarImage] | list[AvatarImage]) -> Optional[AvatarImage]:
    seq = list(items)
    if not seq:
        return None
    return max(seq, key=lambda x: _ts(x.created_at))


def _latest_audio_or_none(items: Sequence[AvatarAudio] | list[AvatarAudio]) -> Optional[AvatarAudio]:
    seq = list(items)
    if not seq:
        return None
    return max(seq, key=lambda x: _ts(x.created_at))


# ---- Public operations ----


def replace_avatar_image(
    db: Session,
    course_id: str,
    slot: Optional[str],
    image_file: UploadFile,
    delete_previous: bool = True,
) -> AvatarCreatedResponse:
    """
    Replace the avatar's image for (course_id, slot).
    Optionally deletes the previous latest image row + file.
    """
    avatar = _get_or_create_avatar(db, course_id, slot)
    saved_new_path: Optional[Path] = None

    # capture old latest BEFORE adding the new one
    old_img: Optional[AvatarImage] = _latest_image_or_none(cast(Sequence[AvatarImage], list(avatar.images)))

    try:
        # Save new file to disk
        saved_new_path = _save_upload(AVATARS_OUTPUT_DIR, UUID(avatar.avatar_id), image_file, kind="image")

        # New DB row
        new_img = AvatarImage(
            id=str(uuid.uuid4()),
            avatar_id=avatar.avatar_id,
            file_path=str(saved_new_path),
            mime_type=image_file.content_type,
            size_bytes=saved_new_path.stat().st_size,
            original_filename=image_file.filename,
        )
        db.add(new_img)

        # Mark old row for deletion (unlink after commit)
        if delete_previous and old_img:
            db.delete(old_img)

        db.commit()

        # Ensure collections reflect the commit before reading them
        db.refresh(new_img)
        db.expire(avatar, ["images", "audios"])

        latest_image: Optional[AvatarImage] = _latest_image_or_none(cast(Sequence[AvatarImage], avatar.images))
        latest_audio: Optional[AvatarAudio] = _latest_audio_or_none(cast(Sequence[AvatarAudio], avatar.audios))

        # After commit succeeded, best-effort unlink old file
        if delete_previous and old_img:
            try:
                Path(old_img.file_path).unlink(missing_ok=True)
            except Exception:
                pass

        return AvatarCreatedResponse(
            avatarId=UUID(avatar.avatar_id),
            name=avatar.name,
            courseId=(avatar.course_id) if avatar.course_id else None,
            slot=CourseAvatarSlot(avatar.slot),
            createdAt=avatar.created_at,
            image=(
                AvatarImageResponse(
                    id=UUID(latest_image.id),
                    avatarId=UUID(avatar.avatar_id),
                    filePath=latest_image.file_path,
                    mimeType=latest_image.mime_type,
                    sizeBytes=latest_image.size_bytes,
                    createdAt=latest_image.created_at,
                )
                if latest_image
                else None
            ),
            audio=(
                AvatarAudioResponse(
                    id=UUID(latest_audio.id),
                    avatarId=UUID(avatar.avatar_id),
                    filePath=latest_audio.file_path,
                    mimeType=latest_audio.mime_type,
                    sizeBytes=latest_audio.size_bytes,
                    createdAt=latest_audio.created_at,
                )
                if latest_audio
                else None
            ),
        )

    except Exception:
        db.rollback()
        if saved_new_path:
            try:
                saved_new_path.unlink(missing_ok=True)
            except Exception:
                pass
        raise


def replace_avatar_audio(
    db: Session,
    course_id: str,
    slot: Optional[str],
    audio_file: UploadFile,
    delete_previous: bool = True,
) -> AvatarCreatedResponse:
    """
    Replace the avatar's audio for (course_id, slot).
    Optionally deletes the previous latest audio row + file.
    """
    avatar = _get_or_create_avatar(db, course_id, slot)
    saved_new_path: Optional[Path] = None

    # capture old latest BEFORE adding the new one
    old_aud: Optional[AvatarAudio] = _latest_audio_or_none(cast(Sequence[AvatarAudio], list(avatar.audios)))

    try:
        # Save new file to disk
        saved_new_path = _save_upload(AVATARS_OUTPUT_DIR, UUID(avatar.avatar_id), audio_file, kind="audio")

        # New DB row
        new_aud = AvatarAudio(
            id=str(uuid.uuid4()),
            avatar_id=avatar.avatar_id,
            file_path=str(saved_new_path),
            mime_type=audio_file.content_type,
            size_bytes=saved_new_path.stat().st_size,
            original_filename=audio_file.filename,
        )
        db.add(new_aud)

        # Mark old row for deletion (unlink after commit)
        if delete_previous and old_aud:
            db.delete(old_aud)

        db.commit()

        # Ensure collections reflect the commit before reading them
        db.refresh(new_aud)
        db.expire(avatar, ["images", "audios"])

        latest_image: Optional[AvatarImage] = _latest_image_or_none(cast(Sequence[AvatarImage], avatar.images))
        latest_audio: Optional[AvatarAudio] = _latest_audio_or_none(cast(Sequence[AvatarAudio], avatar.audios))

        # After commit succeeded, best-effort unlink old file
        if delete_previous and old_aud:
            try:
                Path(old_aud.file_path).unlink(missing_ok=True)
            except Exception:
                pass

        return AvatarCreatedResponse(
            avatarId=UUID(avatar.avatar_id),
            name=avatar.name,
            courseId=(avatar.course_id) if avatar.course_id else None,
            slot=CourseAvatarSlot(avatar.slot),
            createdAt=avatar.created_at,
            image=(
                AvatarImageResponse(
                    id=UUID(latest_image.id),
                    avatarId=UUID(avatar.avatar_id),
                    filePath=latest_image.file_path,
                    mimeType=latest_image.mime_type,
                    sizeBytes=latest_image.size_bytes,
                    createdAt=latest_image.created_at,
                )
                if latest_image
                else None
            ),
            audio=(
                AvatarAudioResponse(
                    id=UUID(latest_audio.id),
                    avatarId=UUID(avatar.avatar_id),
                    filePath=latest_audio.file_path,
                    mimeType=latest_audio.mime_type,
                    sizeBytes=latest_audio.size_bytes,
                    createdAt=latest_audio.created_at,
                )
                if latest_audio
                else None
            ),
        )

    except Exception:
        db.rollback()
        if saved_new_path:
            try:
                saved_new_path.unlink(missing_ok=True)
            except Exception:
                pass
        raise


def _get_or_create_avatar(db: Session, course_id: str, slot: Optional[str]) -> Avatar:
    the_slot = _normalize_slot(slot) if slot is not None else CourseAvatarSlot.default
    avatar = db.query(Avatar).filter(Avatar.course_id == course_id, Avatar.slot == the_slot.value).first()
    if avatar:
        return avatar

    # create new avatar with generated UUID
    new_avatar = Avatar(
        avatar_id=str(uuid.uuid4()),
        course_id=course_id,
        slot=the_slot.value,
        name=None,
    )
    db.add(new_avatar)
    try:
        db.commit()
    except IntegrityError:
        # race: someone else created it — fetch it
        db.rollback()
    if not getattr(new_avatar, "created_at", None):
        # either rolled back or not flushed; re-query
        avatar = db.query(Avatar).filter(Avatar.course_id == course_id, Avatar.slot == the_slot.value).first()
        if avatar:
            return avatar
        # fallback: ensure it exists
        db.add(new_avatar)
        db.commit()
    db.refresh(new_avatar)
    return new_avatar
