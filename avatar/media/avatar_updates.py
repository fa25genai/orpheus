# media/avatar_updates.py
from __future__ import annotations
from typing import Optional
from uuid import UUID
from datetime import datetime, timezone
from pathlib import Path
import uuid

from fastapi import HTTPException, status, UploadFile
from sqlalchemy.orm import Session

from .avatar_media import (
    Avatar,
    AvatarImage,
    AvatarAudio,
    AvatarCreatedResponse,
    AvatarImageResponse,
    AvatarAudioResponse,
    CourseAvatarSlot,
    _normalize_slot,
    _save_upload,
    AVATARS_OUTPUT_DIR,
)


def _get_avatar_or_404(db: Session, course_id: UUID, slot: Optional[str]) -> Avatar:
    the_slot = _normalize_slot(slot) if slot is not None else CourseAvatarSlot.default
    avatar = (
        db.query(Avatar)
        .filter(Avatar.course_id == str(course_id), Avatar.slot == the_slot.value)
        .first()
    )
    if not avatar:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Avatar not found for given courseId and slot",
        )
    return avatar


def _latest_or_none(items):
    if not items:
        return None
    # timezone-aware fallback so we don't mix aware/naive datetimes
    epoch = datetime.min.replace(tzinfo=timezone.utc)
    return sorted(items, key=lambda x: (x.created_at or epoch), reverse=True)[0]


def replace_avatar_image(
    db: Session,
    course_id: UUID,
    slot: Optional[str],
    image_file: UploadFile,
    delete_previous: bool = True,
) -> AvatarCreatedResponse:
    """
    Replace the avatar's image for (course_id, slot).
    Optionally deletes the previous latest image row + file.
    """
    avatar = _get_avatar_or_404(db, course_id, slot)
    saved_new_path: Optional[Path] = None

    # capture old latest BEFORE adding the new one
    old_img = _latest_or_none(list(avatar.images))

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

        latest_image = _latest_or_none(avatar.images)
        latest_audio = _latest_or_none(avatar.audios)
        if not latest_audio:
            raise HTTPException(status_code=404, detail="Avatar has no audio to pair with")

        # After commit succeeded, best-effort unlink old file
        if delete_previous and old_img:
            try:
                Path(old_img.file_path).unlink(missing_ok=True)
            except Exception:
                pass

        return AvatarCreatedResponse(
            avatarId=UUID(avatar.avatar_id),
            name=avatar.name,
            courseId=UUID(avatar.course_id) if avatar.course_id else None,
            slot=CourseAvatarSlot(avatar.slot),
            createdAt=avatar.created_at,
            image=AvatarImageResponse(
                id=UUID(latest_image.id),
                avatarId=UUID(avatar.avatar_id),
                filePath=latest_image.file_path,
                mimeType=latest_image.mime_type,
                sizeBytes=latest_image.size_bytes,
                createdAt=latest_image.created_at,
            ),
            audio=AvatarAudioResponse(
                id=UUID(latest_audio.id),
                avatarId=UUID(avatar.avatar_id),
                filePath=latest_audio.file_path,
                mimeType=latest_audio.mime_type,
                SizeBytes=latest_audio.size_bytes,
                createdAt=latest_audio.created_at,
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
    course_id: UUID,
    slot: Optional[str],
    audio_file: UploadFile,
    delete_previous: bool = True,
) -> AvatarCreatedResponse:
    """
    Replace the avatar's audio for (course_id, slot).
    Optionally deletes the previous latest audio row + file.
    """
    avatar = _get_avatar_or_404(db, course_id, slot)
    saved_new_path: Optional[Path] = None

    # capture old latest BEFORE adding the new one
    old_aud = _latest_or_none(list(avatar.audios))

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

        latest_image = _latest_or_none(avatar.images)
        latest_audio = _latest_or_none(avatar.audios)
        if not latest_image:
            raise HTTPException(status_code=404, detail="Avatar has no image to pair with")

        # After commit succeeded, best-effort unlink old file
        if delete_previous and old_aud:
            try:
                Path(old_aud.file_path).unlink(missing_ok=True)
            except Exception:
                pass

        return AvatarCreatedResponse(
            avatarId=UUID(avatar.avatar_id),
            name=avatar.name,
            courseId=UUID(avatar.course_id) if avatar.course_id else None,
            slot=CourseAvatarSlot(avatar.slot),
            createdAt=avatar.created_at,
            image=AvatarImageResponse(
                id=UUID(latest_image.id),
                avatarId=UUID(avatar.avatar_id),
                filePath=latest_image.file_path,
                mimeType=latest_image.mime_type,
                sizeBytes=latest_image.size_bytes,
                createdAt=latest_image.created_at,
            ),
            audio=AvatarAudioResponse(
                id=UUID(latest_audio.id),
                avatarId=UUID(avatar.avatar_id),
                filePath=latest_audio.file_path,
                mimeType=latest_audio.mime_type,
                sizeBytes=latest_audio.size_bytes,
                createdAt=latest_audio.created_at,
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