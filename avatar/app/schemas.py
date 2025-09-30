from __future__ import annotations
from datetime import datetime
from typing import Optional, Literal, List
from uuid import UUID
from pydantic import BaseModel, Field
from typing_extensions import Annotated
from pydantic import StringConstraints

class Preferences(BaseModel):
    answerLength: Optional[Literal["short","medium","long"]] = None
    languageLevel: Optional[Literal["basic","intermediate","advanced"]] = None
    expertiseLevel: Optional[Literal["beginner","intermediate","advanced","expert"]] = None
    includePictures: Optional[Literal["none","few","many"]] = None

class UserProfile(BaseModel):
    id: str
    role: Literal["student","instructor"]
    language: Literal["german","english"]
    preferences: Optional[Preferences] = None
    enrolled_courses: Optional[List[str]] = None

VoiceTrack = Annotated[str, StringConstraints(min_length=1)]

class GenerateRequest(BaseModel):
    voiceTrack: VoiceTrack
    slideNumber: int = Field(..., ge=0)
    promptId: UUID
    courseId: str
    userProfile: UserProfile
    slot: Literal["default","beginning","ending"] = "default"

class ErrorModel(BaseModel):
    code: Optional[str] = None
    message: Optional[str] = None

class GenerationAcceptedResponse(BaseModel):
    promptId: UUID
    createdAt: datetime

class GenerationStatusResponse(BaseModel):
    promptId: UUID
    status: Literal["IN_PROGRESS","FAILED","DONE"]
    lastUpdated: datetime
    resultUrl: str
    estimatedSecondsLeft: int
    error: Optional[ErrorModel] = None

class SlideTask(BaseModel):
    promptId: UUID
    courseId: str
    userProfile: UserProfile
    text: str
    slideNo: int
    slot: Literal["default","beginning","ending"] = "default"

class VideoTask(BaseModel):
    promptId: UUID
    courseId: str
    userProfile: UserProfile
    slideNo: int
    audioPath: str
    slot: Literal["default","beginning","ending"] = "default"
    sourceImagePath: Optional[str] = None

class Job(BaseModel):
    promptId: UUID
    status: Literal["IN_PROGRESS","FAILED","DONE"]
    lastUpdated: datetime
    lastTouched: datetime
    resultUrl: str
    startedAt: datetime
    expectedDurationSec: int
    error: Optional[ErrorModel] = None