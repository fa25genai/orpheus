# media/avatar_queries.py
from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Union, cast
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from .avatar_media import (
    Avatar,
    AvatarAudio,
    AvatarAudioResponse,
    AvatarCreatedResponse,
    AvatarImage,
    AvatarImageResponse,
    CourseAvatarSlot,
    _normalize_slot,
)


def get_latest_image_for_course_slot(db: Session, course_id: Union[str, UUID], slot: Optional[str]) -> AvatarImage:
    the_slot = _normalize_slot(slot) if slot is not None else _normalize_slot("default")
    avatar = db.query(Avatar).filter(Avatar.course_id == str(course_id), Avatar.slot == the_slot.value).first()
    if not avatar or not avatar.images:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No image found for given courseId and slot")
    return sorted(avatar.images, key=lambda i: i.created_at or datetime.min, reverse=True)[0]


def get_latest_audio_for_course_slot(db: Session, course_id: Union[str, UUID], slot: Optional[str]) -> AvatarAudio | None:
    the_slot = _normalize_slot(slot) if slot is not None else _normalize_slot("default")
    avatar = db.query(Avatar).filter(Avatar.course_id == str(course_id), Avatar.slot == the_slot.value).first()
    if not avatar or not getattr(avatar, "audios", None):
        print("No audio found for given courseId and slot")
        return None

    # If the relationship isn't statically typed, cast it for mypy
    audios: List[AvatarAudio] = cast(List[AvatarAudio], list(avatar.audios))

    # pick latest audio
    return sorted(audios, key=lambda a: a.created_at or datetime.min, reverse=True)[0]


def get_avatars_by_course(
    db: Session,
    course_id: UUID,
    slot: Optional[str] = None,
) -> List[AvatarCreatedResponse]:
    # Base query
    q = db.query(Avatar).filter(Avatar.course_id == str(course_id))

    # Optional slot filter
    if slot is not None:
        the_slot = _normalize_slot(slot)
        q = q.filter(Avatar.slot == the_slot.value)

    avatars = q.order_by(Avatar.created_at.desc()).all()

    if not avatars:
        raise HTTPException(status_code=404, detail="No avatars found for the given criteria")

    results: List[AvatarCreatedResponse] = []
    for a in avatars:
        if not a.images or not a.audios:
            continue
        image = sorted(a.images, key=lambda x: x.created_at or datetime.min, reverse=True)[0]
        audio = sorted(a.audios, key=lambda x: x.created_at or datetime.min, reverse=True)[0]

        results.append(
            AvatarCreatedResponse(
                avatarId=UUID(a.avatar_id),
                name=a.name,
                courseId=UUID(a.course_id) if a.course_id else None,
                slot=CourseAvatarSlot(a.slot),
                createdAt=a.created_at,
                image=AvatarImageResponse(
                    id=UUID(image.id),
                    avatarId=UUID(a.avatar_id),
                    filePath=image.file_path,
                    mimeType=image.mime_type,
                    sizeBytes=image.size_bytes,
                    createdAt=image.created_at,
                ),
                audio=AvatarAudioResponse(
                    id=UUID(audio.id),
                    avatarId=UUID(a.avatar_id),
                    filePath=audio.file_path,
                    mimeType=audio.mime_type,
                    sizeBytes=audio.size_bytes,
                    createdAt=audio.created_at,
                ),
            )
        )

    if not results:
        raise HTTPException(status_code=404, detail="Avatars exist but no complete media found")

    return results
