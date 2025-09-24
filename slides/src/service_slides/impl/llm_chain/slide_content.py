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

def create_layout_parser(layout_template: LayoutTemplate) -> PydanticOutputParser:
    """Create a dynamic Pydantic parser for a specific layout template."""
    # Create fields for the Pydantic model based on the template schema
    fields = {}
    for field_name, field_description in layout_template.schema.items():
        fields[field_name] = (str, Field(description=field_description))
    
    # Dynamically create the Pydantic model
    DynamicSlideModel = create_model(
        f"{layout_template.name.title()}SlideModel",
        **fields
    )
    
    return PydanticOutputParser(pydantic_object=DynamicSlideModel)


def generate_single_slide_content(
        model: BaseLanguageModel,
        text: str,
        layout_template: LayoutTemplate,
        slide_number: int,
        assets: List[RequestSlideGenerationRequestAssetsInner]
    ) -> str:
    """Generate a single slide from text using structured output."""
    
    # Create parser for this specific layout
    parser = create_layout_parser(layout_template)

    system = SystemMessagePromptTemplate.from_template(
        """
        You are a helpful assistant that creates concise and engaging presentation slides.

        The slide should be clear and to the point.
        Use bullet points where appropriate for content fields.

        We are using sli.dev for slide rendering.
        
        You must return structured JSON data that will be used to populate a slide template.
        The JSON must conform to the following schema:
        {format_instructions}
        """
    )

    user = ChatPromptTemplate.from_template(
        """
        Create slide content based on the following text:
        {text}
        
        This is slide number {slide_number}.
        
        Layout: {layout_name}
        Layout description: Each field in the output should contain appropriate content for a {layout_name} slide.
        
        Template schema explanation:
        {schema_explanation}
        """
    )

    prompt = ChatPromptTemplate.from_messages([system, user])

    # Create schema explanation
    schema_explanation = "\n".join([
        f"- {field}: {description}" 
        for field, description in layout_template.schema.items()
    ])

    input_data = {
        "text": text, 
        "slide_number": slide_number,
        "layout_name": layout_template.name,
        "schema_explanation": schema_explanation,
        "format_instructions": parser.get_format_instructions()
    }
    
    # Get structured output from LLM
    # Since we provide a parser, invoke_llm will return a parsed Pydantic model
    structured_data = invoke_llm(model, prompt, input_data, parser)

    # Extract values from the Pydantic model
    # Since the parser was successful, we can assume it's a valid model
    template_vars: Dict[str, Any] = {}
    
    # Use model_dump() for Pydantic v2 or dict() for v1
    if hasattr(structured_data, 'model_dump'):
        # Pydantic v2
        template_vars = structured_data.model_dump()  # type: ignore
    elif hasattr(structured_data, 'dict'):
        # Pydantic v1
        template_vars = structured_data.dict()  # type: ignore
    else:
        # Fallback for dynamic models - use __dict__
        template_vars = structured_data.__dict__  # type: ignore
    
    
    # Generate the final slide using the template
    try:
        final_slide = layout_template.template.substitute(**template_vars)
    except KeyError as e:
        # Try with safe_substitute for missing variables
        final_slide = layout_template.template.safe_substitute(**template_vars)

    return final_slide
