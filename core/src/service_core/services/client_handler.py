import httpx
import logging
from service_core.services import (
    decompose_input,
    fetch_mock_data,
    script_generation,
    narration_generation,
)
from service_core.services.fetch_mock_data import create_context_mock
import json
from service_core.impl.tracker import tracker

client = httpx.AsyncClient()

DI_API_URL = "http://docint:25565"
SLIDES_API_URL = "http://slides:30606"
AVATAR_API_URL = "http://avatar-video-producer:9000"


async def process_prompt(
    prompt_id: str, prompt_request: str
):  # TODO: type prompt_request
    """
    Asynchronously calls the appropriate external API to get the final result.
    """
    tracker.log("Decomposing inputs")
    decomposed_questions = decompose_input.decompose_question(prompt_request.prompt)
    subqueries = decomposed_questions.get("subqueries", [])
    # print("Subqueries:", subqueries)
    i = 0

    retrieved_content = []
    tracker.log("Querying document intelligence")
    for idx, subquery in enumerate(subqueries):
        # print(f"\nProcessing subquery {idx + 1}/{len(subqueries)}: {subquery}")
        # Call Decompose Input API
        di_response = await client.get(
            f"{DI_API_URL}/v1/retrieval/abc",
            params={"courseId": "abc", "promptQuery": str(subquery)},
            timeout=300.0,
        )
        di_response.raise_for_status()
        di_data = di_response.json()
        # print(f"Input Decomposed for {prompt_id}", flush=True)
        # print(di_data.get("content", [])[:10], flush=True)
        entry = {
            "Question": subquery,
            "retrieved_content": di_data.get("content", []),
            "retrieved_images_descriptions": [
                img.get("description", "") for img in di_data.get("images", [])
            ],
        }

        retrieved_content.append(di_data)

    # print("\nAll retrieved content:", retrieved_content, flush=True)

    # print("Simulating async processing delay...")
    # await asyncio.sleep(5)
    tracker.log("Generating script")
    try:
        refined_output = script_generation.generate_script(
            retrieved_content, fetch_mock_data.create_demo_user()
        )
    except Exception as e:
        print(e)
    # print(refined_output)
    lecture_script = refined_output.get("lectureScript", "")
    # lecture_script = "A for loop is a fundamental control flow statement in programming that executes a block of code repeatedly until a specified condition is met. It's ideal for situations where the number of iterations is known in advance, automating repetitive tasks by processing data structures or iterating through sequences. A typical for loop has a header with initialization, a condition to check at the start of each cycle, and an update operation at the end of each cycle, often involving a loop variable."
    # print("Lecture generated", flush=True)
    # print('user:', fetch_mock_data.create_demo_user().model_dump_json(by_alias=True, exclude_unset=True), flush=True)
    tracker.log("Generating slides")
    slides_context = {
        "courseId": prompt_request.course_id,
        "promptId": str(prompt_id),
        "lectureScript": lecture_script,
        "user": json.loads(
            fetch_mock_data.create_demo_user().model_dump_json(
                by_alias=True, exclude_unset=True
            )
        ),
        "assets": refined_output.get("assets", ""),
    }
    print("Slides context: ", slides_context, flush=True)
    # context_mock = create_context_mock(prompt_request.course_id, prompt_id, lecture_script, fetch_mock_data.create_demo_user())
    # print(context_mock)
    slides_response = await client.post(
        f"{SLIDES_API_URL}/v1/slides/generate",
        json=slides_context,
        timeout=300.0,
    )
    slides_response.raise_for_status()
    slides_data = slides_response.json()
    # print("Slides API returned:", slides_data, flush=True)
    # print("Slides API response:", slides_response, flush=True)
    tracker.log("Generating voice tracks")
    # print("\n\nGenerated Lecture Script:", lecture_script)
    # example_slides = fetch_mock_data.create_demo_slides()
    # print("\nExample Slides:", example_slides)
    try:
        voice_track = narration_generation.generate_narrations(
            lecture_script, slides_data, fetch_mock_data.create_demo_user()
        )
        avatar_response = await client.post(
            f"{AVATAR_API_URL}/v1/video/generate",
            json=voice_track,
            timeout=300.0,
        )
        print("Avatar API response:", avatar_response, flush=True)
        # print("\nvoice_track:", voice_track, flush=True)
    except Exception as e:
        print("Error generating voice track:", e, flush=True)
