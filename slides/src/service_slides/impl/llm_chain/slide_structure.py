from typing import List, Any, cast
from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import SystemMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
from pydantic import BaseModel, Field

from service_slides.impl.llm_chain.shared_llm import invoke_llm
from service_slides.models.slide_item import SlideItem
from service_slides.models.slide_structure import SlideStructure
from service_slides.impl.manager.layout_manager import LayoutDescription


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
    layout: str = Field(
        description=(
            "For now, always assign a neutral or general-purpose layout from the provided list. "
            "Do not invent layouts, only pick one that is guaranteed to exist."
        )
    )


class DetailedSlideStructure(BaseModel):
    items: List[DetailedSlideStructureItem] = Field(
        default=[],
        description="Ordered list of slide candidates representing the lecture script split into logical chunks.",
    )

    def as_simple_slide_structure(self) -> SlideStructure:
        return SlideStructure(
            pages=[SlideItem(content=item.content) for item in self.items],
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

    # Pick a safe default layout (e.g., the first one in the list).
    default_layout = available_layouts[0].name if available_layouts else "Default"

    layouts_description = "\n".join(
        [f"- Name: '{layout.name}', Description: {layout.description}" for layout in available_layouts]
    )

    parser = PydanticOutputParser(pydantic_object=DetailedSlideStructure)

    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessage(
                "You are an expert academic slide designer. "
                "Your ONLY task is to split a lecture script into logical, self-contained chunks. "
                "Each chunk corresponds to one slide."
            ),
            SystemMessage(
                "RULES:\n"
                "- Do NOT add, remove, or invent content.\n"
                "- Preserve the original order of ideas.\n"
                "- Each chunk should focus on one coherent idea or example.\n"
                "- If the script contains a question and later its answer, make them two separate chunks.\n"
                "- If the script contains lists, tables, or code, keep them intact in the same chunk.\n"
                "- Each chunk must be standalone (avoid references to other slides).\n"
                "- Begin each chunk with 'Title:' followed by the main idea.\n"
                "- Assign the layout field with a valid name from the provided list (use the most general layout if unsure).\n"
                f"Available layouts:\n{layouts_description}"
            ),
            HumanMessagePromptTemplate.from_template(
                "Lecture script:\n\n{lecture_script}\n\nNow split this into logical chunks."
            ),
            SystemMessagePromptTemplate.from_template(
                "Return JSON ONLY, conforming to this schema:\n{format_instructions}"
            ),
        ]
    )

    result = invoke_llm(
        model=model,
        prompt=prompt,
        input_data={
            "lecture_script": lecture_script,
            "format_instructions": parser.get_format_instructions(),
        },
        parser=parser,
    )

    # Defensive: if model forgets layout, assign default
    for item in result.items:
        if not item.layout.strip():
            item.layout = default_layout

    return cast(DetailedSlideStructure, result)
