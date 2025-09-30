from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy.orm import Session

from app.db import engine, get_db
from media import avatar_media as media
from media import avatar_queries, avatar_updates

router = APIRouter(prefix="/v1/avatars", tags=["avatar"])

@router.on_event("startup")
def _startup_create_tables() -> None:
    media.Base.metadata.create_all(engine)

@router.post("", status_code=201, response_model=media.AvatarCreatedResponse)
def create_avatar(
    name: Optional[str] = Form(None),
    courseId: str = Form(...),
    slot: Optional[str] = Form("default"),
    image_file: UploadFile = File(..., description="png/jpeg/webp"),
    audio_file: UploadFile = File(..., description="mp3/wav/flac/webm"),
    db: Session = Depends(get_db),
) -> media.AvatarCreatedResponse:
    return media.create_avatar_with_media(
        db=db, image_file=image_file, audio_file=audio_file, name=name, course_id=courseId, slot=slot
    )

@router.get("/by-course/{courseId}", response_model=List[media.AvatarCreatedResponse])
def get_avatars_by_course_endpoint(
    courseId: str,
    slot: Optional[str] = Query(None, description="optional: default | beginning | ending"),
    db: Session = Depends(get_db),
) -> List[media.AvatarCreatedResponse]:
    return avatar_queries.get_avatars_by_course(db=db, course_id=courseId, slot=slot)

@router.post("/{courseId}/{slot}/image", response_model=media.AvatarCreatedResponse)
def replace_avatar_image_endpoint(
    courseId: str,
    slot: str,
    image_file: UploadFile = File(..., description="png/jpeg/webp"),
    db: Session = Depends(get_db),
) -> media.AvatarCreatedResponse:
    return avatar_updates.replace_avatar_image(db=db, course_id=courseId, slot=slot, image_file=image_file, delete_previous=True)

@router.post("/{courseId}/{slot}/audio", response_model=media.AvatarCreatedResponse)
def replace_avatar_audio_endpoint(
    courseId: str,
    slot: str,
    audio_file: UploadFile = File(..., description="mp3/wav/flac/webm"),
    db: Session = Depends(get_db),
) -> media.AvatarCreatedResponse:
    return avatar_updates.replace_avatar_audio(db=db, course_id=courseId, slot=slot, audio_file=audio_file, delete_previous=True)