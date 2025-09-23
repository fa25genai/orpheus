from typing import Optional
from pydantic import BaseModel, Field, HttpUrl
from generation_status import GenerationStatus

class SlideResponse(BaseModel):
    """Schema for the slide generation status and result."""
    status: GenerationStatus
    slides_url: Optional[HttpUrl] = Field(
        default=None,
        description="The URL to the generated slide deck. Only present if status is 'completed'."
    )