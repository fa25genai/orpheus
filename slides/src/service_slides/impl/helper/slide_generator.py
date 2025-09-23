from langchain_core.language_models import BaseChatModel
from service_slides.impl.manager.layout_manager import LayoutDescription
from service_slides.models.request_slide_generation_request_assets_inner import (
    RequestSlideGenerationRequestAssetsInner,
)
from service_slides.models.slide_item import SlideItem
from service_slides.models.slide_structure import SlideStructure
from typing import List


class DetailedSlideStructureItem:
    content: str
    layout: str

    def __init__(self, content: str, layout: str):
        self.content = content
        self.layout = layout


class DetailedSlideStructure:
    items: List[DetailedSlideStructureItem] = []

    def as_simple_slide_structure(self) -> SlideStructure:
        return SlideStructure(
            pages=map(lambda item: SlideItem(item.content), self.items),
        )


async def generate_slide_structure(
    lecture_script: str,
    available_layouts: List[LayoutDescription],
    llm_model: BaseChatModel,
) -> DetailedSlideStructure:
    # TODO
    return DetailedSlideStructure()


async def generate_slide(
    lecture_script: str,
    slide_layout: str,
    slide_template: str,
    slide_content: str,
    structure: DetailedSlideStructure,
    assets: List[RequestSlideGenerationRequestAssetsInner],
) -> None:
    # TODO
    pass
