
from __future__ import annotations
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel


class VoiceTrackResponse(BaseModel):
    lectureId: str
    courseId: Optional[str] = None
    slideMessages: List[str]
    # In your code you put a string; keeping it flexible:
    userProfile: Union[str, Dict[str, Any]]
    metadata: Optional[str] = None
    