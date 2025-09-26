from typing import Any, Dict, List

from langchain_core.language_models.base import BaseLanguageModel
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate
from pydantic import Field, create_model

from service_slides.impl.llm_chain.shared_llm import invoke_llm
from service_slides.impl.manager.layout_manager import LayoutTemplate
from service_slides.models.request_slide_generation_request_assets_inner import (
    RequestSlideGenerationRequestAssetsInner,
)


def create_layout_parser(layout_template: LayoutTemplate) -> PydanticOutputParser[Any]:
    """Create a dynamic Pydantic parser for a specific layout template."""
    fields = {}
    for field_name, field_description in layout_template.schema.items():
        fields[field_name] = (str, Field(description=field_description))

    DynamicSlideModel = create_model(f"{layout_template.name.title()}SlideModel", **fields)  # type: ignore
    return PydanticOutputParser(pydantic_object=DynamicSlideModel)


def generate_single_slide_content(
    model: BaseLanguageModel[Any],
    text: str,
    layout_template: LayoutTemplate,
    slide_number: int,
    assets: List[RequestSlideGenerationRequestAssetsInner],
) -> str:
    """Generate a single slide from text using structured output."""

    parser = create_layout_parser(layout_template)

    system = SystemMessagePromptTemplate.from_template(
        """
You write student-friendly slides for sli.dev.

Goal
- Produce clear, learnable content: one main idea per slide, supported by compact evidence (bullets/table/code).
- Keep cognitive load low: simple wording, short lines, logical order.

Hard rules
- Return JSON only (no prose, no code fences around JSON) that matches the schema below.
- Use ONLY the given text; do not invent facts, numbers, images, or URLs.
- Slides must be self-contained (understandable without other slides).
- Preserve exact numbers, terms, order, and code formatting.
- If a field has no support in the text, set it to "".

Markdown (inside content fields)
- Bullets start with "- " (3–6 bullets ideal; one idea each). Sub-points allowed with two spaces then "- ".
- Inline code with backticks.
- Code blocks ONLY if present; keep whitespace; add language tag if known (```python ...```).
- Tables: reproduce fully as Markdown (no dropped rows/columns).
- Light emphasis (**bold**/*italics*) is ok for key terms present in the text.

Titles (when a title/headline field exists)
- Short, assertive, learner-facing (≈6–12 words), no trailing period.

Images
- If the text names an image, copy the filename EXACTLY as written (no prefixes/suffixes/paths). Otherwise use "".

Schema:
{format_instructions}
"""
    )

    user = ChatPromptTemplate.from_template(
        """
Create content for a {layout_name} slide that helps a student learn the idea quickly.

Use only this text:
<BEGIN_TEXT>
{text}
<END_TEXT>

How to write it
- Use the fields as they are intended for a {layout_name} slide (see purposes below).
- Prefer bullets over long prose; group example with its explanation.
- Keep item order and wording from the text when listing steps/ranks/values.
- Define terms only if the definition is in the text; do not add new information.
- If a field is not applicable or not supported by the text, set it to "".

Field purposes:
{schema_explanation}

Return JSON only.
"""
    )

    prompt = ChatPromptTemplate.from_messages([system, user])

    schema_explanation = "\n".join(
        [f"- {field}: {description}" for field, description in layout_template.schema.items()]
    )

    input_data = {
        "text": text,
        "layout_name": layout_template.name,
        "schema_explanation": schema_explanation,
        "format_instructions": parser.get_format_instructions(),
    }

    structured_data = invoke_llm(model, prompt, input_data, parser)

    template_vars: Dict[str, Any] = {}
    if hasattr(structured_data, "model_dump"):
        template_vars = structured_data.model_dump()
    elif hasattr(structured_data, "dict"):
        template_vars = structured_data.dict()
    else:
        template_vars = structured_data.__dict__

    try:
        final_slide = layout_template.template.substitute(**template_vars)
    except KeyError:
        final_slide = layout_template.template.safe_substitute(**template_vars)

    return str(final_slide)
