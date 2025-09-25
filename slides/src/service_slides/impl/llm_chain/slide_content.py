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
    # Create fields for the Pydantic model based on the template schema
    fields = {}
    for field_name, field_description in layout_template.schema.items():
        fields[field_name] = (str, Field(description=field_description))

    # Dynamically create the Pydantic model
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

    # Create parser for this specific layout
    parser = create_layout_parser(layout_template)

    system = SystemMessagePromptTemplate.from_template(
        """
        You are a senior academic slide writer. Produce structured JSON to populate a slide template.

        NON-NEGOTIABLES:
        - Output: JSON ONLY (no prose, no code fences), exactly matching the schema below.
        - Fidelity: Use ONLY information from the provided text. Do NOT invent facts, numbers, dates, citations, code, images, or URLs.
        - Self-contained: The slide must be understandable without any other slide.
        - Brevity & clarity: Prefer concise bullet points over long prose. Target ~60–120 words total where appropriate.
        - Numeric & order fidelity: Preserve exact values, orders, ranks, thresholds, and terminology from the text.
        - Tables: If the text contains a table, reproduce it COMPLETELY as markdown within the appropriate field. If it’s too long for this single slide per the layout, include the complete table as given (do not drop rows/columns). Do not summarize unless the source text itself is a summary.
        - Code: Include code ONLY if present in the text, verbatim, fenced with a language tag when known (e.g., ```java ...```), preserving indentation.
        - Assets/links: If a field would require an image/URL/author and the text does not provide it, leave that field as an empty string. Never invent assets.
        - Style: Follow assertion–evidence principles. Use a short, informative title if the layout expects one; support it with compact bullets or the required content type.
        - Formatting hygiene: Do not include templating tokens. Escape quotes normally within JSON strings.

        The JSON must conform to the following schema:
        {format_instructions}
        """
    )

    user = ChatPromptTemplate.from_template(
        """
        Create slide content from this text (use only what appears below):
        <BEGIN_TEXT>
        {text}
        <END_TEXT>

        Layout: {layout_name}
        Layout guidance: Fill every required field appropriately for a {layout_name} slide. 
        If a field is not applicable or the text provides no content for it, return an empty string for that field.

        Template schema explanation (field purposes):
        {schema_explanation}

        Authoring guidelines (apply if relevant to the fields):
        - Titles: short and assertive (≈6–12 words), no terminal punctuation.
        - Bullets: 3–6 bullets where relevant, 5–14 words each, parallel grammar, domain terms preserved.
        - Definitions/examples: keep explanation adjacent to the item it explains (same field if applicable).
        - Do not add transitions like “as seen earlier” or “in the next slide”.
        - Keep any bracketed reference markers present in the text (e.g., [1], [2]) when you quote or closely paraphrase the relevant line.

        Return JSON ONLY that matches the schema above.
        """
    )

    prompt = ChatPromptTemplate.from_messages([system, user])

    # Create schema explanation
    schema_explanation = "\n".join(
        [f"- {field}: {description}" for field, description in layout_template.schema.items()]
    )

    input_data = {
        "text": text,
        "layout_name": layout_template.name,
        "schema_explanation": schema_explanation,
        "format_instructions": parser.get_format_instructions(),
    }

    # Get structured output from LLM
    # Since we provide a parser, invoke_llm will return a parsed Pydantic model
    structured_data = invoke_llm(model, prompt, input_data, parser)

    # Extract values from the Pydantic model
    # Since the parser was successful, we can assume it's a valid model
    template_vars: Dict[str, Any] = {}

    # Use model_dump() for Pydantic v2 or dict() for v1
    if hasattr(structured_data, "model_dump"):
        # Pydantic v2
        template_vars = structured_data.model_dump()
    elif hasattr(structured_data, "dict"):
        # Pydantic v1
        template_vars = structured_data.dict()
    else:
        # Fallback for dynamic models - use __dict__
        template_vars = structured_data.__dict__

    # Generate the final slide using the template
    try:
        final_slide = layout_template.template.substitute(**template_vars)
    except KeyError:
        # Try with safe_substitute for missing variables
        final_slide = layout_template.template.safe_substitute(**template_vars)

    return str(final_slide)
