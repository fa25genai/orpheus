from langchain_core.language_models import BaseLanguageModel
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, Field
from service_slides.impl.manager.layout_manager import LayoutDescription
from service_slides.models.request_slide_generation_request_assets_inner import (
    RequestSlideGenerationRequestAssetsInner,
)
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


# Example request:
# {
#   "courseId": "abcd-efgh",
#   "lectureId": "d847e33b-f932-498e-a86c-1c895d15f735",
#   "lectureScript": "The lecture has \"for-loops\" as topic. To explain the concepts of loops, fist a real-life example is used. This example is doing push-ups for exercise, which is a repetitive task. The same concept, where one has to repeat the same action a certain amount of times, is also relevant for computer programs. For example, if an action has to be performed for each user in a system. This is shown with the following example program written in Java: `for (int i = 0; i < 10; i++) {\n    System.out.println(i);\n}`.\nThe students are encouraged to think about what output this program may produce. In the following slide the solution \"0\n1\n2\n3\n4\n5\n6\n7\n8\n9\" is shown. It is pointed out, that it starts at 0 and ends at 9. To explain this behaviour, the elements of a for-loop are then examined individually. First the initialization of the loop variable. This is the value, which is used for the first iteration of the loop. Next is the condition. As long as this condition holds we are repeating the loop. This condition is also checked before the first iteration, so the loop will not be entered, if it is initially false. The last element is the modification. This alters the state of the variable, so we eventually get to a terminating state. To wrap up the lecture, the advantages of for loops and potential uses are explained. The advantages are reduction of code, concise syntax for counting and versatile usages. The potential uses are counting, iterating over an array and periodically performing a specific action.",
#   "user": {},
#   "assets": []
# }
async def generate_slide_structure(
    lecture_script: str,
    available_layouts: List[LayoutDescription],
    llm_model: BaseLanguageModel,
) -> DetailedSlideStructure:
    structured_output_model = llm_model.with_structured_output(DetailedSlideStructure)
    detailed_structure = structured_output_model.invoke(
        [
            SystemMessage(
                "You are a lecturer tasked with creating a slideset for a lecture. The lecture is already prepared with all relevant contents, examples and exercises. This is the outline:"
            ),
            HumanMessage(lecture_script),
            SystemMessage(
                "Create the sequence of slides, that should be used for this slideset. Make sure every part of the lecture outline is kept in at least one slides. You must not add any content of your own. If a specific slide should use any asset, do indicate this."
            ),
            SystemMessage("The available slide layouts are as follows: "),
            SystemMessage(
                map(
                    lambda layout: f"Name: {layout.name} ; description: {layout.description}",
                    available_layouts,
                )
            ),
        ]
    )
    return detailed_structure


async def generate_slide(
    llm_model: BaseLanguageModel,
    lecture_script: str,
    slide_layout: str,
    slide_template: str,
    slide_content: str,
    structure: DetailedSlideStructure,
    assets: List[RequestSlideGenerationRequestAssetsInner],
) -> str:
    # TODO
    pass
