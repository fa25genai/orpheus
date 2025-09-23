# Multiple slides-specific texts
# For each text, generate a slide in parallel
# Return all generated slides

import asyncio
from concurrent.futures import ThreadPoolExecutor
from langchain_core.language_models.base import BaseLanguageModel
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate
from service_slides.llm_chain.shared_llm import invoke_llm
from service_slides.models.slide_structure import SlideStructure


def generate_slide(model: BaseLanguageModel, text: str, slide_number: int) -> str:
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
        """
    )

    prompt = ChatPromptTemplate.from_messages([system, user])

    input_data = {"text": text, "slide_number": slide_number}
    response = invoke_llm(model, prompt, input_data)
    return response


async def generate_slides_markdown(
    model: BaseLanguageModel,
    slide_structure: SlideStructure,
    executor: ThreadPoolExecutor
) -> str:
    """
    Generate multiple slides from SlideStructure in parallel and combine them into a single markdown string.

    Args:
        model: The language model to use for generation
        slide_structure: SlideStructure containing the slide items with content
        executor: ThreadPoolExecutor for parallel execution

    Returns:
        Combined markdown string with all slides separated by ---
    """
    if not slide_structure.pages:
        return ""

    # Prepare slide generation tasks
    tasks = []
    for i, slide_item in enumerate(slide_structure.pages, 1):
        if slide_item.content:
            # Create a task for each slide generation
            task = asyncio.get_event_loop().run_in_executor(
                executor,
                generate_slide,
                model,
                slide_item.content,
                i
            )
            tasks.append(task)

    # Execute all tasks in parallel
    slides = await asyncio.gather(*tasks)

    # Combine all slides with slide separators
    combined_markdown = "\n---\n".join(slides)

    return combined_markdown

