from typing import Any, List, cast

from langchain_core.language_models import BaseLanguageModel
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)
from pydantic import BaseModel

from service_slides.clients.status.models.slide_structure import SlideItem as SlideItemStatus  # type: ignore[attr-defined]
from service_slides.clients.status.models.slide_structure import SlideStructure as SlideStructureStatus
from service_slides.impl.manager.layout_manager import LayoutDescription
from service_slides.models.slide_item import SlideItem
from service_slides.models.slide_structure import SlideStructure
from langchain_core.output_parsers import StrOutputParser


class DetailedSlideStructureItem(BaseModel):
    content: str = ""
    layout: str = "default"

class DetailedSlideStructure(BaseModel):
    items: List[DetailedSlideStructureItem]

    def as_simple_slide_structure(self) -> SlideStructure:
        return SlideStructure(
            pages=[SlideItem(content=item.content) for item in self.items],
        )

    def as_simple_slide_structure_status(self) -> SlideStructureStatus:
        return SlideStructureStatus(
            pages=[SlideItemStatus(content=item.content) for item in self.items],
        )

# ############################################################################################
#    Stage 1: split the lecture script into logical chunks that can serve as candidate slides.
#    Just natural chunking without structure nor layout assignment.
# ############################################################################################

stage_1_system_prompt = """
You are a presentation assistant tasked with converting lecture scripts into study-friendly slide decks. 

Your goal is to split a given lecture script into a series of slides in Markdown format. Each slide must have:
- **A title**: a brief, descriptive heading prefixed with "# " (single hash and a space). The title should summarize the main idea of that slide.
- **Slide content**: the exact original text from the lecture script that corresponds to that idea. **Do not rephrase or omit** any part of the content. Preserve all wording, examples, and formatting (such as code or emphasis) exactly as in the input.

**Important guidelines:**
- **One idea per slide:** Each slide should cover only one main concept or topic from the lecture script. If the script transitions to a new topic, start a new slide.
- **Slide titles:** Craft a concise title for each slide. Use Title Case or sentence case appropriately, and make it clear what the slide is about (e.g., "For Loops Syntax", "Nesting For Loops"). If the script doesn’t provide an obvious title, infer a short one from the content.
- **Cover and conclusion slides:** If the script begins with an introduction or welcome, make that the "Cover Slide" (e.g., "Cover Slide – Introduction to ___"). If the script has concluding remarks, make those the final slide with a title like "Conclusion" or "Summary".
- **Images or diagrams:** If the script references an image, diagram, or figure, put that reference on a separate slide. For example, if the text says “Here is a diagram (Image: ...filename.png)”, isolate that line on its own slide with an appropriate title (e.g., "Example Diagram").
- **Preserve order and content:** The sequence of slides should follow the order of the script. Ensure that when all slide contents are concatenated (excluding titles), they form the original script word-for-word. Do not add any new commentary or bullet points; just use the script’s exact text.

**Output format:** 
Present the slides in Markdown. Start each slide title with "# ". Follow the title with a line break, then the slide text. Put an empty line after the end of each slide’s content before the next slide title. For example:
```
# Slide Title 1
Slide text for the first idea...

# Slide Title 2
Slide text for the next idea...
```
(Ensure there is a blank line between slides as shown above.)

You will receive the lecture script as input. Apply these instructions to produce a clear, well-structured slide deck. Remember: **do not alter the original text**, only split and title it.
"""

stage_1_human_prompt = """
Here is a lecture script. Convert it into a markdown slide deck following the system prompt rules.

Lecture Script:**Task:** Please split the following lecture script into a sequence of titled slides (in Markdown format), following these requirements:
- Each slide should have a heading title (Markdown `#` format) that you create, encapsulating the main idea of that slide.
- The slide's content should be the exact text from the script for that idea, with no changes or omissions.
- The slides should appear in the same order as the content in the script. Preserve all punctuation and formatting in the content.

**Lecture Script:** 
{lecture_script}
"""

stage_1_prompt = ChatPromptTemplate.from_messages(
    [
        SystemMessagePromptTemplate.from_template(stage_1_system_prompt.strip()),
        HumanMessagePromptTemplate.from_template(stage_1_human_prompt.strip()),
    ]
)

def _get_natural_structure(model: BaseLanguageModel[Any], lecture_script: str) -> str:
    
    chain = stage_1_prompt | model | StrOutputParser()
    return chain.invoke({"lecture_script": lecture_script})

# ##########################################################################
#   Stage 2: turns naturally phrased chunks into structured slide candidates
# ##########################################################################

stage_2_system_prompt = """
You are a precise slide-structuring assistant.

Your job:
- Read a set of slides written in Markdown (each slide starts with a single leading-level Markdown heading: lines beginning with "# ").
- Convert them into a structured representation suitable for downstream processing.
- For each slide, produce an item with:
  1) content: A self-contained chunk that begins with a line of the form "Title: <slide title>" (where <slide title> is the heading text without the "#"). After that line, include the slide's body text verbatim and in order, preserving **all line breaks, punctuation, and formatting exactly**. Do not add, rephrase, or remove information.
  2) layout: The name of the layout template chosen strictly from the provided list of available layouts. Do not invent new layout names.

Layout selection guidelines (apply in this order; choose the first that matches):
1) Cover / Intro / Section
   - Title contains "Cover" → use "cover".
   - Title contains "Introduction" or "Intro" → use "intro".
   - Title indicates a new section/part/chapter → use "section".
2) Image-centric
   - Body is only an image/diagram/figure reference → use "image".
   - Body has both image and substantive text → use "image-right" (preferred) or "image-left".
3) Conclusion / End
   - Title contains "Conclusion", "Summary", "Wrap-up", or "Thanks" → use "end".
4) Code-heavy or technical explanation
   - If the slide contains code examples, syntax, or dense technical explanation → use "full".
5) Single strong assertion or short emphasis
   - If the content is a concise claim or fact → use "statement".
   - If centering makes sense (short idea to emphasize visually) → use "center".
6) Comparisons or dual structure
   - If content clearly splits into two comparable ideas → use "two-cols" or "two-cols-header".
7) Fallback
   - Otherwise → use "default".

Important:
- Never output layouts that are not in the provided list.
- Copy content exactly, including trailing punctuation.
- Keep slide order unchanged.

Output:
- Return a single JSON object conforming to the schema you are given via format instructions.
- You may wrap it in a ```json fenced block or output raw JSON.
- Do not include explanations, comments, or text outside the JSON.
"""

stage_2_human_prompt = """
You will receive:
1) A Markdown slide deck produced in stage 1.
2) A list of available layouts (names and descriptions).
3) Exact format instructions for the expected JSON schema.

Constraints:
- Use only the layouts listed below. Do not invent new layout names.
- For each slide:
  - Start the content with "Title: <slide title>".
  - Copy the slide body **verbatim, with no punctuation dropped or added**.
  - Assign the most appropriate layout using the system guidelines.
- Return only JSON. You may wrap it in a ```json fenced block or output raw JSON.
- Do not include any prose or text outside the JSON.

Available layouts:
{layouts_description}

Markdown slides to structure:
```markdown
{natural_slides}
```

Return your answer using this schema (follow exactly):
{format_instructions}
"""

stage_2_prompt = ChatPromptTemplate.from_messages(
    [
        SystemMessagePromptTemplate.from_template(stage_2_system_prompt.strip()),
        HumanMessagePromptTemplate.from_template(stage_2_human_prompt.strip()),
    ]
)

def _get_typed_structure(
    model: BaseLanguageModel[Any],
    natural_slides: str,
    available_layouts: List[LayoutDescription],
) -> DetailedSlideStructure:
    parser = PydanticOutputParser(pydantic_object=DetailedSlideStructure)

    layout_description = "\n".join([f'"{layout.name}" → Description: {layout.description}' for layout in available_layouts])

    chain = stage_2_prompt | model | parser

    result = chain.invoke({
        "natural_slides": natural_slides,
        "layouts_description": layout_description,
        "format_instructions": parser.get_format_instructions(),
    })

    # drop items with empty content
    result.items = [item for item in result.items if item.content.strip()]

    return result

async def generate_slide_structure(
    model: BaseLanguageModel[Any],
    lecture_script: str,
    available_layouts: List[LayoutDescription],
) -> DetailedSlideStructure:
    """
    Intermediate goal: given a lecture script, produce a structured slide representation
    """

    natural_slides = _get_natural_structure(model, lecture_script)

    structured_slides = _get_typed_structure(model, natural_slides, available_layouts)

    return cast(DetailedSlideStructure, structured_slides)
