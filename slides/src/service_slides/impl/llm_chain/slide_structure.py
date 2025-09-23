from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate
from pydantic import BaseModel, Field
from service_slides.impl.manager.layout_manager import LayoutDescription
from service_slides.impl.llm_chain.shared_llm import invoke_llm
from service_slides.models.slide_item import SlideItem
from service_slides.models.slide_structure import SlideStructure
from typing import List


class DetailedSlideStructureItem(BaseModel):
    content: str = Field(
        description="Detailed description of what content the slide should contain. This must contain all relevant information for the slide. It does not have to follow a specific format and may be a human readable description. It will later be used to create the specific slide contents. It should contain details for the layout as well as the relevant original section from the lecture outline."
    )
    layout: str = Field(
        description="Layout name to use for that slide. Must be the exact name of one of the available slide layouts."
    )


class DetailedSlideStructure(BaseModel):
    items: List[DetailedSlideStructureItem] = Field(
        default=[], description="List of the slides which are used to support the lecture"
    )

    def as_simple_slide_structure(self) -> SlideStructure:
        return SlideStructure(
            pages=list(map(lambda item: SlideItem(content=item.content), self.items)),
        )


async def generate_slide_structure(
        model: BaseLanguageModel,
        lecture_script: str,
        available_layouts: List[LayoutDescription]
) -> DetailedSlideStructure:
    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessagePromptTemplate.from_template(
                "You must *only* return JSON, **no prose**, in exactly this shape and conforming to the schema definition:\n{format_instructions}",
            ),
            SystemMessage(
                "You are a lecturer tasked with creating a slideset for a lecture. The lecture is already prepared with all relevant contents, examples and exercises. The slideset must not be empty. This is the outline:"
            ),
            HumanMessage(lecture_script),
            SystemMessage(
                "Create the sequence of slides, that should be used for this slideset. Make sure every part of the lecture outline is kept in at least one slides. You must not add any content of your own. If a specific slide should use any asset, do indicate this."
            ),
            SystemMessage("The available slide layouts are as follows: "),
            SystemMessage(
                list(map(
                    lambda layout: f"Name: {layout.name} ; description: {layout.description}",
                    available_layouts,
                ))
            )
        ]
    )

    parser = PydanticOutputParser(pydantic_object=DetailedSlideStructure)

    detailed_structure = invoke_llm(
        model=model,
        prompt=prompt,
        input_data={"format_instructions": parser.get_format_instructions()},
        parser=parser
    )

    return detailed_structure
