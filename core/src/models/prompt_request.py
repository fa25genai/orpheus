from pydantic import BaseModel, Field

class PromptRequest(BaseModel):
    """Schema for the initial prompt request."""
    prompt: str = Field(
        ...,
        description="The user's educational prompt."
    )