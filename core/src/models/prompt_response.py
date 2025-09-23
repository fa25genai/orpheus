import uuid
from pydantic import BaseModel, Field

class PromptResponse(BaseModel):
    """Schema for the response after submitting a prompt."""
    lecture_id: uuid.UUID = Field(
        ...,
        description="The unique ID assigned to the generation job."
    )