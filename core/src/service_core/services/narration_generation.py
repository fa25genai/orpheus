################################################################################
#                                                                              #
#                      ####### BADEN-WÜRTTEMBERG #######                       #
#                                                                              #
#          A tribute to the land of poets, thinkers, and engineers.            #
#          Home of the Black Forest, Porsche, Mercedes, and Spätzle.           #
#                                                                              #
#                         o__      o__      o__                                #
#                        / < \_   / < \_   / < \_                              #
#                       (*)/ (*) (*)/ (*) (*)/ (*)                             #
#                                                                              #
#                  "Wir können alles. Außer Hochdeutsch."                      #
#                                                                              #
################################################################################
import json
from typing import AsyncGenerator
import asyncio

from service_core.models.prompt_request import PromptRequest
from service_core.models.slides.generation_accepted_response import (
    GenerationAcceptedResponse,
)
from service_core.services.helpers.debug import debug_print, enable_debug
from service_core.services.helpers.llm import ask_llm
from service_core.services.helpers.loaders import load_prompt
from service_core.services.services_models.voice_track import VoiceTrackResponse


async def generate_narrations(
    lecture_script: str,
    example_slides: GenerationAcceptedResponse,
    prompt_request: PromptRequest,
    prompt_id: str,
    debug: bool = False,
) -> AsyncGenerator[VoiceTrackResponse, None]:
    """
    Generates narrations for lecture slides based on a script and user profile.

    Args:
        lecture_script (str): The script for the entire lecture.
        example_slides (GenerationAcceptedResponse): An object representing the slide structure.
        prompt_request (PromptRequest): An object containing the user's profile and request data.
        prompt_id (str): The prompt identifier.
        debug (bool, optional): If True, enables debug output.
    ---\n### RULES & GUIDELINES\n---\n\n
        * Text Formatting: The voice script should be human readable. Rewrite this to be readable by a tts module. Don't change content or meaning.\n\n
        * Symbols: Spell out symbols to ensure clarity in narration. For example, "&" should be read as "and", "%" as "percent", and "$" as "dollars".\n\n
        * Special characters: remove any commas, periods, brackets, and other special Characters.\n\n
        * Coding text: If the lecture script contains code snippets, reformat them in an actual text that resembles code instead of code. Example: "System.out.println(abc[i])" should be read as "system dot out dot print line a b c index i".\n\n
        * Math text: If the lecture script contains mathematical expressions, reformat them in an actual text. Example "- should be minus", "> should be greater than", and so on.\n\n
        * Image References: When referring to images in the lectureScript, use the exact filenames provided in the Images list. For example, say "Here you can see filename_1" to reference an image named filename_1.jpg.\n\n
    ---\n### OUTPUT FORMAT\n---\n\n
    Your response MUST be a single, valid JSON object and nothing else. Do not include any introductory text, explanations, or markdown formatting
    Yields:
        VoiceTrackResponse: The generated narration for each slide.
    """

    if debug:
        enable_debug()

    # slides_data = json.loads(example_slides.model_dump_json())
    if not example_slides.structure:
        raise Exception("No slide structure available")

    pages = example_slides.structure.pages if example_slides.structure.pages else []
    narration_history = ""

    # Get prompt templates JSON string
    prompt_templates_json = await asyncio.to_thread(
        load_prompt, "src/service_core/services/prompts/narration.json"
    )

    # Load the prompt templates
    prompt_templates = json.loads(prompt_templates_json)
    print("\n\nGenerating page narrations:", len(pages), flush=True)
    for index, page in enumerate(pages):
        page_content = page.content
        # Build the prompt using the templates
        prompt_parts = [
            prompt_templates["base_prompt"].format(
                user_profile=prompt_request.user_persona
            ),
            prompt_templates["lecture_script_section"].format(
                lecture_script=lecture_script
            ),
            prompt_templates["narration_history_section"].format(
                narration_history=narration_history
            ),
            prompt_templates["slide_content_section"].format(page_content=page_content),
        ]

        # Add specific instructions for the first or last slide
        if index == 0:
            prompt_parts.append(prompt_templates["first_slide_instruction"])
        elif index == len(pages) - 1:
            prompt_parts.append(prompt_templates["last_slide_instruction"])

        # Add the narration request
        prompt_parts.append(prompt_templates["narration_request"])

        # Join all parts with newlines
        prompt = "\n\n".join(prompt_parts)
        narration = await asyncio.to_thread(ask_llm, prompt)

        debug_print(f"--- Slide {index + 1} ---")
        debug_print(f"Content: {page_content}")
        debug_print(f"Generated Narration: {narration}\n")

        narration_history += f"Slide {index + 1} Narration: {narration}\n"

        if not prompt_request.user_persona:
            raise ValueError("User persona must be defined")

        voice_script_request = VoiceTrackResponse(
            promptId=prompt_id,
            courseId=prompt_request.course_id,
            voiceTrack=narration,
            slideNumber=index,
            userProfile=prompt_request.user_persona,
        )

        yield voice_script_request
