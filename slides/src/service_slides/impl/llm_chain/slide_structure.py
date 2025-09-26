from typing import Any, List, cast

from langchain_core.language_models import BaseLanguageModel
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)
from pydantic import BaseModel, Field

from service_slides.clients.status.models.slide_structure import SlideItem as SlideItemStatus  # type: ignore[attr-defined]
from service_slides.clients.status.models.slide_structure import SlideStructure as SlideStructureStatus
from service_slides.impl.llm_chain.shared_llm import invoke_llm
from service_slides.impl.manager.layout_manager import LayoutDescription
from service_slides.models.slide_item import SlideItem
from service_slides.models.slide_structure import SlideStructure


class DetailedSlideStructureItem(BaseModel):
    content: str = Field(
        description=(
            "A self-contained chunk of the lecture script that could serve as the basis for a slide. "
            "Keep the original information intact (no omissions, no additions). "
            "Begin with a 'Title:' line that summarizes the chunk, followed by bullets or compact sentences. "
            "Preserve tables and code exactly as they appear in the script. "
            "Each chunk should represent one coherent idea and stand alone without referencing other chunks."
        )
    )
    layout: str = Field(description=("The name of the layout template to use for this slide. Choose the best fitting layout from the provided list of available layouts. Do not invent layouts, only pick one that is guaranteed to exist."))


class DetailedSlideStructure(BaseModel):
    items: List[DetailedSlideStructureItem] = Field(
        default=[],
        description="Ordered list of slide candidates representing the lecture script split into logical chunks.",
    )

    def as_simple_slide_structure(self) -> SlideStructure:
        return SlideStructure(
            pages=[SlideItem(content=item.content) for item in self.items],
        )

    def as_simple_slide_structure_status(self) -> SlideStructureStatus:
        return SlideStructureStatus(
            pages=[SlideItemStatus(content=item.content) for item in self.items],
        )


async def generate_slide_structure(
    model: BaseLanguageModel[Any],
    lecture_script: str,
    available_layouts: List[LayoutDescription],
) -> DetailedSlideStructure:
    """
    Intermediate goal: split the lecture script into logical chunks
    that can serve as candidate slides. No optimization beyond chunking.
    """

    layouts_description = "\n".join([f"- Name: '{layout.name}', Description: {layout.description}" for layout in available_layouts])

    parser = PydanticOutputParser(pydantic_object=DetailedSlideStructure)

    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessagePromptTemplate.from_template(
                """
You are a careful academic slide outliner. Your single job is to split one lecture script
into clear, standalone chunks that map 1:1 to slides.

Write in a natural, direct style. Follow these simple rules:
• Stay faithful to the script: never add, remove, or change facts, numbers, examples, or wording beyond light condensation.
• Segment by idea (one coherent idea per chunk). Prefer short, meaningful segments over long, mixed ones.
• Start each chunk with "Title:" (a short, assertive headline derived from the text), then bullets or compact sentences.
• Keep the original order of ideas.
• If the script poses a question and later gives its answer, make them two separate chunks placed consecutively.
• Keep lists/tables/code intact within a single chunk. Reproduce tables as-is (markdown) and code verbatim.
• Each chunk must be self-contained—no cross-references such as “as above/as next slide”.
• Choose a layout from the provided list. If unsure, select the most general content layout. Do not invent layout names.
• Aim for concise, readable content suitable for a slide and voiceover (roughly 60–140 words if prose; lists are fine).
• If an image or asset is mentioned in the script text, keep that mention inside the relevant chunk; do not invent assets.

Available layouts:
{layouts_description}
""".strip()
            ),
            HumanMessagePromptTemplate.from_template(
                """
Lecture script:

{lecture_script}

Split this script into an ordered list of standalone chunks.
Each chunk must include a 'Title:' line and the full content needed for that slide,
and must be assigned a valid layout name from the list above.
""".strip()
            ),
            SystemMessagePromptTemplate.from_template(
                """
Return JSON ONLY, matching this schema exactly:
{format_instructions}
""".strip()
            ),
        ]
    )

    result = invoke_llm(
        model=model,
        prompt=prompt,
        input_data={
            "layouts_description": layouts_description,
            "lecture_script": lecture_script,
            "format_instructions": parser.get_format_instructions(),
        },
        parser=parser,
    )

    # Defensive: if model forgets layout, assign default
    for item in result.items:
        if not item.layout.strip():
            item.layout = "default"

    return cast(DetailedSlideStructure, result)
