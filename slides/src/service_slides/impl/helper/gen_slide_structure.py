import os

from typing import Any, List
from src.service_slides.impl.llm_chain.slide_structure import DetailedSlideStructure, generate_slide_structure
from src.service_slides.impl.manager.layout_manager import LayoutDescription
from src.service_slides.impl.mock.slide_mock_objects import make_mock_slide_structure
from langchain_core.language_models.base import BaseLanguageModel


ORPHEUS_DEBUG = os.getenv("ORPHEUS_DEBUG", "false").lower() in ("1", "true", "yes")

async def generate_slide_structure_or_mock(
    splitting_model: BaseLanguageModel[Any],
    lecture_script: str,
    available_layouts: List[LayoutDescription],
) -> DetailedSlideStructure:
    if ORPHEUS_DEBUG:
        return make_mock_slide_structure()
    else: return await generate_slide_structure(
            model=splitting_model,
            lecture_script=lecture_script,
            available_layouts=available_layouts,
        )