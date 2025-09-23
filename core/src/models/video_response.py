from typing import Optional
from pydantic import BaseModel, Field, HttpUrl
from generation_status import GenerationStatus

class VideoResponse(BaseModel):
    """Schema for the video generation status and result."""
    status: GenerationStatus
    video_url: Optional[HttpUrl] = Field(
        default=None,
        description="The URL to the generated video. Only present if status is 'completed'."
    )