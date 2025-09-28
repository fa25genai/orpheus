# media/avatar_updates.py
from __future__ import annotations
from typing import Optional
from uuid import UUID
from datetime import datetime

from fastapi import HTTPException, status, UploadFile
from sqlalchemy.orm import Session
import uuid


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
    return sorted(items, key=lambda x: x.created_at or datetime.min, reverse=True)[0]

def replace_avatar_image(
    db: Session,
    course_id: UUID,
    slot: Optional[str],
    image_file: UploadFile,
    delete_previous: bool = True,
) -> AvatarCreatedResponse:
    """
    Replaces the avatar's image for (course_id, slot).
    By default deletes the previous image file/row to avoid disk bloat.
    """
    avatar = _get_avatar_or_404(db, course_id, slot)
    saved_new_path = None

    # capture old latest BEFORE adding the new one
    old_img = _latest_or_none(list(avatar.images))

    try:
        saved_new_path = _save_upload(AVATARS_OUTPUT_DIR, UUID(avatar.avatar_id), image_file, kind="image")

        new_img = AvatarImage(
            id=str(uuid.uuid4()),
            avatar_id=avatar.avatar_id,
            file_path=str(saved_new_path),
            mime_type=image_file.content_type,
            size_bytes=saved_new_path.stat().st_size,
            original_filename=image_file.filename,
        )
        db.add(new_img)

        # Delete previous latest (NOT the one we just added)
        if delete_previous and old_img:
            db.delete(old_img)
            try:
                from pathlib import Path
                Path(old_img.file_path).unlink(missing_ok=True)
            except Exception:
                pass

        db.commit()
        db.refresh(avatar); db.refresh(new_img)

        latest_image = _latest_or_none(avatar.images)
        latest_audio = _latest_or_none(avatar.audios)
        if not latest_audio:
            raise HTTPException(status_code=404, detail="Avatar has no audio to pair with")

        return AvatarCreatedResponse(...)

    except Exception:
        db.rollback()
        if saved_new_path:
            try: saved_new_path.unlink(missing_ok=True)
            except Exception: pass
        raise


def replace_avatar_audio(
    db: Session,
    course_id: UUID,
    slot: Optional[str],
    audio_file: UploadFile,
    delete_previous: bool = True,
) -> AvatarCreatedResponse:
    """
    Replaces the avatar's audio for (course_id, slot).
    By default deletes the previous audio file/row.
    """
    avatar = _get_avatar_or_404(db, course_id, slot)
    saved_new_path = None

    old_aud = _latest_or_none(list(avatar.audios))

    try:
        saved_new_path = _save_upload(AVATARS_OUTPUT_DIR, UUID(avatar.avatar_id), audio_file, kind="audio")

        new_aud = AvatarAudio(
            id=str(uuid.uuid4()),
            avatar_id=avatar.avatar_id,
            file_path=str(saved_new_path),
            mime_type=audio_file.content_type,
            size_bytes=saved_new_path.stat().st_size,
            original_filename=audio_file.filename,
        )
        db.add(new_aud)

        if delete_previous and old_aud:
            db.delete(old_aud)
            try:
                from pathlib import Path
                Path(old_aud.file_path).unlink(missing_ok=True)
            except Exception:
                pass

        db.commit()
        db.refresh(avatar); db.refresh(new_aud)

        latest_image = _latest_or_none(avatar.images)
        latest_audio = _latest_or_none(avatar.audios)
        if not latest_image:
            raise HTTPException(status_code=404, detail="Avatar has no image to pair with")

        return AvatarCreatedResponse(...)

    except Exception:
        db.rollback()
        if saved_new_path:
            try: saved_new_path.unlink(missing_ok=True)
            except Exception: pass
        raise