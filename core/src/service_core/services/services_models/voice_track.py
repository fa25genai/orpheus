
from __future__ import annotations
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel
from service_core.models.user_profile import UserProfile


class VoiceTrackResponse(BaseModel):
    promptId: str
    courseId: Optional[str] = None
    slideMessages: List[str]
    # In your code you put a string; keeping it flexible:
    userProfile: UserProfile
    metadata: Optional[str] = None
    