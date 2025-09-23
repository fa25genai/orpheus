from typing import List, Optional, Literal
from pydantic import BaseModel

# ----- User -----
class UserPreferences(BaseModel):
    answerLength: Optional[Literal["short", "medium", "long"]] = None
    languageLevel: Optional[Literal["basic", "intermediate", "advanced"]] = None
    expertiseLevel: Optional[Literal["beginner", "intermediate", "advanced", "expert"]] = None
    includePictures: Optional[Literal["none", "few", "many"]] = None

class UserProfile(BaseModel):
    id: str
    role: Literal["student", "instructor"]
    language: str
    preferences: UserPreferences
    enrolledCourses: List[str]

# ----- Slides -----
class SlideItem(BaseModel):
    content: str

class SlideStructure(BaseModel):
    pages: List[SlideItem]

class SlideGenerationResponse(BaseModel):
    lectureId: str
    status: Literal["IN_PROGRESS", "FAILED", "DONE"]
    createdAt: str
    structure: SlideStructure

# ----- Flexible wrapper (any combo) -----
class VoiceTrackDataRequest(BaseModel):
    lecture_script: Optional[str] = None
    slides: Optional[SlideGenerationResponse] = None
    user_profile: Optional[UserProfile] = None
