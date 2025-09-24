from __future__ import annotations
from typing import Any, Dict, List, Literal, Union
from pydantic import BaseModel


class SlideItem(BaseModel):
    content: str

class SlideStructure(BaseModel):
    pages: List[SlideItem]

class SlidesEnvelope(BaseModel):
    promptId: str
    status: Literal["IN_PROGRESS", "FAILED", "DONE"]
    createdAt: str
    structure: SlideStructure

    # Convenience parser to accept either str JSON or dict
    @classmethod
    def parse_obj_or_json(cls, data: Union[str, Dict[str, Any]]) -> "SlidesEnvelope":
        if isinstance(data, str):
            return cls.model_validate_json(data)
        return cls.model_validate(data)