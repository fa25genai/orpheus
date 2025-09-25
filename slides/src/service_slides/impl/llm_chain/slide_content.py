from typing import List, Dict, Any
from langchain_core.language_models.base import BaseLanguageModel
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
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
You create clean academic slide content for sli.dev.

Return JSON only that matches the schema below.
Use only the provided text. Do not invent facts, numbers, or assets.
Slides must be self-contained and scannable.

Markdown:
- Bullets: "- " prefix, one idea each.
- Code: only if present; fenced with a language tag; keep spacing.
- Tables: reproduce fully as Markdown (no dropped rows/cols).
- Inline code: single backticks.

Titles: short and assertive (≈6–12 words).
Preserve numbers, units, order, and terminology exactly.
For image fields: copy image names exactly as given in the text (no changes).
If a field has no content, use "".

Schema:
{format_instructions}
"""
    )

    user = ChatPromptTemplate.from_template(
        """
Create content for a {layout_name} slide.

Text (use only this):
<BEGIN_TEXT>
{text}
<END_TEXT>

Use fields as intended for a {layout_name} slide.
Prefer concise bullets over long prose.
If a field has no relevant content, set it to "".

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
