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


system_prompt = """
You write student-friendly slides for sli.dev (16:9).

Goal
- One main idea per slide, supported by compact bullets/table/code or a short paragraph.
- Keep cognitive load low: simple wording, short lines, logical order.

Hard rules
- Return JSON only (no prose, no code fences around JSON) that matches the schema below.
- Use ONLY the given text; do not invent facts, numbers, images, or URLs.
- Slides must be self-contained (understandable without other slides).
- Preserve exact numbers, terms, order, and code formatting. You may rephrase for readability/engagement, but do not drop ideas.
- If a field has no support in the text, set it to "".

Titles (when a title/headline field exists)
- Topic-centered, short, learner-facing (≈6–12 words), no trailing period.
- **Remove generic labels** like “Cover Slide”, “Slide”, “Section”, and any numbering (e.g., “Slide 1 – …”).

16:9 density guardrails
- Prefer 4–8 top-level bullets; **≤18 words per bullet** (aim 8–16). Avoid deep nesting; use sub-bullets only when essential.
- For text-heavy content, a compact paragraph is allowed (≤3 short sentences) if the layout suits it.
- If the source has more points than fit, **compress wording** (merge near-duplicates with “;” or “,”) while **keeping the idea order**.
- Code blocks ONLY if present; ≤10 lines; keep whitespace; add language tag if evident (```python ...```).
- Tables: reproduce fully as Markdown (no dropped rows/columns).

Markdown (inside content fields)
- Bullets start with “- ”. Sub-points: two spaces then “- ”.
- Inline code with backticks.
- Light emphasis (**bold**/*italics*) only for terms already in the text.
- **Avoid redundancy**: do not repeat the same idea in multiple bullets; merge overlapping bullets.

Images
- If the text names an image, copy the filename EXACTLY as written (no prefixes/suffixes/paths). Otherwise use "".
- If an image/background sizing field exists and the text doesn’t specify it, leave it "" (renderer may apply a default like “contain”).

Voice track alignment
- Keep the **idea order** consistent with the input so a separate voice track can align even without slide context.
"""

user_prompt = """
Create content for a {layout_name} slide that helps a student learn the idea quickly.

Use only this text:
<BEGIN_TEXT>
{text}
<END_TEXT>

How to write it
- Use the fields as they are intended for a {layout_name} slide (see purposes below).
- Prefer bullets over long prose unless the layout suits a short paragraph.
- Keep **item order** from the text for steps/ranks/values.
- Do not add new information; do not remove ideas. You may **compress wording** to fit 16:9.
- Respect 16:9 density: 4–8 bullets, ≤18 words per bullet; code blocks ≤10 lines.
- **Titles:** remove generic labels (“Cover Slide”, “Slide”, “Section”, numbering); make the title topic-centered.
- **No redundancy:** merge overlapping bullets; do not repeat the same idea.
- If a field is not applicable or not supported by the text, set it to "".

Field purposes:
{schema_explanation}

Return JSON in the following schema only:
{format_instructions}
"""

prompt = ChatPromptTemplate.from_messages(
    [
        SystemMessagePromptTemplate.from_template(system_prompt.strip()),
        ChatPromptTemplate.from_template(user_prompt.strip()),
    ]
)


def generate_single_slide_content(
    model: BaseLanguageModel[Any],
    text: str,
    layout_template: LayoutTemplate,
    slide_number: int,
    assets: List[RequestSlideGenerationRequestAssetsInner],
) -> str:
    """Generate a single slide from text using structured output."""

    parser = create_layout_parser(layout_template)

    schema_explanation = "\n".join([f'"{field}" {description}' for field, description in layout_template.schema.items()])

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
