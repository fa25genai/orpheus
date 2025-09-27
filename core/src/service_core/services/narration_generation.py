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
from typing import Any, Dict

from service_core.models.user_profile import UserProfile
from service_core.services.helpers.debug import debug_print, enable_debug
from service_core.services.helpers.llm import getLLM
from service_core.services.helpers.loaders import load_prompt
from service_core.services.services_models.slides import SlidesEnvelope


def generate_narrations(
    lecture_script: str,
    example_slides: Dict[str, Any],
    user_profile: UserProfile,
    debug: bool = False,
) -> Dict[str, Any]:
    """
    Generates narrations for lecture slides based on a script and user profile.

    Args:
        lecture_script (str): The script for the entire lecture.
        example_slides (SlidesEnvelope): An object representing the slide structure.
        user_profile (UserProfile): An object containing the user's profile.
        debug (bool): If True, enables debug output.

    Returns:
        str: A JSON string containing the generated slide narrations.
    """

    if debug:
        enable_debug()

    llm = getLLM()

    # slides_data = json.loads(example_slides.model_dump_json())
    pages = example_slides["structure"]["pages"]
    # print("\n\npages:", pages, flush=True)
    narration_history = ""
    slide_messages = []

    # Get prompt templates JSON string
    prompt_templates_json = load_prompt("src/service_core/services/prompts/narration.json")

    # Load the prompt templates
    prompt_templates = json.loads(prompt_templates_json)
    for i, page in enumerate(pages):
        # print("\n\npage:", page, flush=True)
        page_content = page["content"]
        # Build the prompt using the templates
        prompt_parts = [
            prompt_templates["base_prompt"].format(user_profile=user_profile),
            prompt_templates["lecture_script_section"].format(lecture_script=lecture_script),
            prompt_templates["narration_history_section"].format(narration_history=narration_history),
            prompt_templates["slide_content_section"].format(page_content=page_content),
        ]

        # Add specific instructions for first or last slide
        if i == 0:
            prompt_parts.append(prompt_templates["first_slide_instruction"])
        elif i == len(pages) - 1:
            prompt_parts.append(prompt_templates["last_slide_instruction"])

        # Add the narration request
        prompt_parts.append(prompt_templates["narration_request"])

        # Join all parts with newlines
        prompt = "\n\n".join(prompt_parts)
        response = llm.invoke(prompt)
        narration = response.content

        debug_print(f"--- Slide {i + 1} ---")
        debug_print(f"Content: {page_content}")
        debug_print(f"Generated Narration: {narration}\n")

        narration_history += f"Slide {i + 1} Narration: {narration}\n"
        slide_messages.append(narration)
    # Prepare output data with actual user profile
    output_data: Dict[str, Any] = {
        "slideMessages": slide_messages,
        "promptId": example_slides["promptId"],
        "courseId": user_profile.enrolled_courses[0] if user_profile.enrolled_courses else None,
        "userProfile": json.loads(user_profile.model_dump_json(by_alias=False, exclude_unset=True)),
    }
    return output_data
