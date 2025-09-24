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
from core.src.service_core.models.user_profile import UserProfile
from core.src.service_core.models.user_profile_preferences import UserProfilePreferences
from services_models.slides import SlidesEnvelope
import json
import logging
from helpers.llm import getLLM
from helpers.debug import enable_debug, debug_print
from helpers.loaders import load_prompt

enable_debug()

lecture_script = """The lecture has \"for-loops\" as topic. To explain the concepts of loops, fist a real-life example is used. This example is doing push-ups for exercise, which is a repetitive task. The same concept, where one has to repeat the same action a certain amount of times, is also relevant for computer programs. For example, if an action has to be performed for each user in a system. This is shown with the following example program written in Java: `for (int i = 0; i < 10; i++) {\n    System.out.println(i);\n}`.\nThe students are encouraged to think about what output this program may produce. In the following slide the solution \"0\n1\n2\n3\n4\n5\n6\n7\n8\n9\" is shown. It is pointed out, that it starts at 0 and ends at 9. To explain this behaviour, the elements of a for-loop are then examined individually. First the initialization of the loop variable. This is the value, which is used for the first iteration of the loop. Next is the condition. As long as this condition holds we are repeating the loop. This condition is also checked before the first iteration, so the loop will not be entered, if it is initially false. The last element is the modification. This alters the state of the variable, so we eventually get to a terminating state. To wrap up the lecture, the advantages of for loops and potential uses are explained. The advantages are reduction of code, concise syntax for counting and versatile usages. The potential uses are counting, iterating over an array and periodically performing a specific action."""
example_slides_data = """
{
    "lectureId": "d847e33b-f932-498e-a86c-1c895d15f735",
    "status": "IN_PROGRESS",
    "createdAt": "2025-09-23T11:22:04.876434",
    "structure": {
        "pages": [
            {
                "content": "For-Loops: Repeating Actions in Programming"
            },
            {
                "content": "Repetitive Tasks in Real Life: The Push-up Example. Doing push-ups for exercise - repeating the same action multiple times."
            },
            {
                "content": "Repetition in Computer Programs. Performing an action for each user in a system. The need to repeat the same action a certain amount of times."
            },
            {
                "content": "Example: A Java For-Loop\\n\\n`for (int i = 0; i < 10; i++) {\\n    System.out.println(i);\\n}`"
            },
            {
                "content": "What output may this program produce? Take a moment to think."
            },
            {
                "content": "Output:\\n0\\n1\\n2\\n3\\n4\\n5\\n6\\n7\\n8\\n9"
            },
            {
                "content": "Understanding the Output: It starts at 0 and ends at 9."
            },
            {
                "content": "Section: Elements of a For-Loop"
            },
            {
                "content": "Element 1: Initialization\\n\\nThis is the value, which is used for the first iteration of the loop."
            },
            {
                "content": "Element 2: Condition\\n\\nAs long as this condition holds, we are repeating the loop. This condition is also checked before the first iteration, so the loop will not be entered, if it is initially false."
            },
            {
                "content": "Element 3: Modification\\n\\nThis alters the state of the variable, so we eventually get to a terminating state."
            },
            {
                "content": "Advantages of For-Loops:\\n- Reduction of code\\n- Concise syntax for counting\\n- Versatile usages"
            },
            {
                "content": "Potential Uses of For-Loops:\\n- Counting\\n- Iterating over an array\\n- Periodically performing a specific action"
            },
            {
                "content": "Thank you!"
            }
        ]
    }
}
"""
example_slides = SlidesEnvelope.parse_obj_or_json(example_slides_data)


user_profile = UserProfile(
    id="f0a1b2c3-d4e5-f6a7-b8c9-d0e1f2a3b4c5",
    role="student",
    language="german",
    preferences=UserProfilePreferences(
        answerLength="short",
        languageLevel="intermediate",
        expertiseLevel="expert",
        includePictures="many"
    ),
    enrolledCourses=["CS101", "PHY201"]
)
def generate_narrations(lecture_script, example_slides, user_profile):
    """
    Generates narrations for lecture slides based on a script and user profile.

    Args:
        lecture_script (str): The script for the entire lecture.
        example_slides (SlidesEnvelope): An object representing the slide structure.
        user_profile (UserProfile): An object containing the user's profile.

    Returns:
        str: A JSON string containing the generated slide narrations.
    """
    llm = getLLM()

    slides_data = json.loads(example_slides.model_dump_json())
    pages = slides_data['structure']['pages']
    narration_history = ""
    slide_messages = []
    
    # Get prompt templates JSON string
    prompt_templates_json = load_prompt("prompt/narration.json")
    
    # Load the prompt templates
    prompt_templates = json.loads(prompt_templates_json)
    
    for i, page in enumerate(pages):
        page_content = page['content']
        
        # Build the prompt using the templates
        prompt_parts = [
            prompt_templates["base_prompt"].format(user_profile=user_profile.model_dump_json()),
            prompt_templates["lecture_script_section"].format(lecture_script=lecture_script),
            prompt_templates["narration_history_section"].format(narration_history=narration_history),
            prompt_templates["slide_content_section"].format(page_content=page_content)
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

        debug_print(f"--- Slide {i+1} ---")
        debug_print(f"Content: {page_content}")
        debug_print(f"Generated Narration: {narration}\n")

        narration_history += f"Slide {i+1} Narration: {narration}\n"
        slide_messages.append(narration)

    # Prepare output data with actual user profile
    output_data = {
        "lectureId": slides_data.get("lectureId"),
        "courseId": user_profile.enrolledCourses[0] if user_profile.enrolledCourses else None,
        "slideMessages": slide_messages,
        "userProfile": json.loads(user_profile.model_dump_json()),
        "metadata": "Text generated by AI Core Narration Service"
    }

    return json.dumps(output_data, indent=2)

if __name__ == '__main__':
    generated_json = generate_narrations(lecture_script, example_slides, user_profile)
    debug_print(f"Final output JSON:\n{generated_json}")
