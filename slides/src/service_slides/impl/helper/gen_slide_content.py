import os
from typing import Any, List
from src.service_slides.impl.llm_chain.slide_content import generate_single_slide_content
from src.service_slides.impl.manager.layout_manager import LayoutTemplate
from src.service_slides.impl.mock.slide_mock_objects import make_mock_slide_content
from langchain_core.language_models.base import BaseLanguageModel
from src.service_slides.models.request_slide_generation_request_assets_inner import \
    RequestSlideGenerationRequestAssetsInner


ORPHEUS_DEBUG = os.getenv("ORPHEUS_DEBUG", "false").lower() in ("1", "true", "yes")

def generate_slide_content_or_mock(
    slidesgen_model: BaseLanguageModel[Any],
    text: str,
    layout_template: LayoutTemplate,
    slide_number: int,
    assets: List[RequestSlideGenerationRequestAssetsInner],
) -> str:
    if ORPHEUS_DEBUG:
        return make_mock_slide_content(
            text=text,
            layout_template=layout_template,
        )
    else: return generate_single_slide_content(
        model=slidesgen_model,
        text=text,
        layout_template=layout_template,
        slide_number=slide_number,
        assets=assets,
        )