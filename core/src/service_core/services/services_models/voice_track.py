from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from service_core.models.user_profile import UserProfile


class VoiceTrackResponse(BaseModel):
    promptId: str
    courseId: Optional[str] = None
    voiceTrack: str
    slideNumber: int
    # In your code you put a string; keeping it flexible:
    userProfile: UserProfile
    metadata: Optional[str] = None
