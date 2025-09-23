from typing import List
from langchain_core.language_models.base import BaseLanguageModel
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate
from service_slides.impl.llm_chain.shared_llm import invoke_llm
from service_slides.models.request_slide_generation_request_assets_inner import (
    RequestSlideGenerationRequestAssetsInner,
)

async def generate_single_slide_content(
        model: BaseLanguageModel,
        text: str,
        slide_template: str,
        slide_number: int,
        assets: List[RequestSlideGenerationRequestAssetsInner]
    ) -> str:
    """Generate a single slide from text."""
    system = SystemMessagePromptTemplate.from_template(
        """
        You are a helpful assistant that creates concise and engaging presentation slides.

        The slide should be clear and to the point.
        Use bullet points where appropriate.

        We are using sli.dev for slide rendering.
        Make sure to format the slide for this single slide only as all slides will be combined later.
        """
    )

    user = ChatPromptTemplate.from_template(
        """
        Create a slide based on the following text:
        {text}
        The slide number is {slide_number}.

        Fill all missing values in the provided slide template:
        {slide_template}
        """
    )

    prompt = ChatPromptTemplate.from_messages([system, user])

    input_data = {"text": text, "slide_number": slide_number, "slide_template": slide_template}
    response = invoke_llm(model, prompt, input_data)
    return response


# async def generate_slides_content(
#     model: BaseLanguageModel,
#     lecture_script: str,
#     slide_template: str,
#     structure: DetailedSlideStructure,
#     assets: List[RequestSlideGenerationRequestAssetsInner],
#     executor: ThreadPoolExecutor
# ) -> str:
#     if not structure.items:
#         return ""

#     # Generate slides concurrently using ThreadPoolExecutor
#     futures = [
#         executor.submit(
#             _generate_single_slide_content,
#             model=model,
#             text=item.content,
#             slide_layout=slide_template,
#             slide_number=i + 1,  # Slide numbers start from 1
#             assets=assets
#         )
#         for i, item in enumerate(structure.items)
#     ]

#     # Wait for all futures to complete and get results
#     slides = [future.result() for future in futures]

#     # Combine all slides with slide separators
#     combined_markdown = "\n---\n".join(slides)

#     return combined_markdown