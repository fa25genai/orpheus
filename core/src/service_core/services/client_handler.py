import httpx
import json
import asyncio
import os
from service_core.services import (
    decompose_input,
    script_generation,
    narration_generation,
)

import service_core.services.fetch_mock_data as mock_service
from service_core.impl.tracker import tracker
from service_core.services.user_summary import summarize_and_send

DI_API_URL = "http://docint:25565"
SLIDES_API_URL = "http://slides:30606"
AVATAR_API_URL = "http://avatar-video-producer:9000"
DEBUG = int(os.environ.get("ORPHEUS_DEBUG", "1"))



async def decompose_inputs(prompt_request):
    tracker.log("Decomposing inputs")
    
    # DEBUG HANDLING STARTS
    if (DEBUG):
        return mock_service.create_decomposed_question()
    # DEBUG HANDLING ENDS
    decomposed_questions = decompose_input.decompose_question(prompt_request.prompt)
    return decomposed_questions.get("subqueries", [])

async def query_document_intelligence(subqueries, client):
    tracker.log("Querying document intelligence")
    # DEBUG HANDLING STARTS
    if (DEBUG):
        return mock_service.create_retrieved_content()
    # DEBUG HANDLING ENDS

    di_response = await client.get(
        f"{DI_API_URL}/v1/retrieval/abc",
        params={"courseId": "abc", "promptQuery": str(subquery)},
        timeout=300.0,
    )
    di_response.raise_for_status()
    di_data = di_response.json()
    return di_data

def generate_script(retrieved_content):
    tracker.log("Generating script")
    try:
        # DEBUG HANDLING STARTS
        if (DEBUG):
            return mock_service.create_script()
        # DEBUG HANDLING ENDS

        refined_output = script_generation.generate_script(retrieved_content, mock_service.create_user())
    except Exception as e:
        print(e)
        refined_output = {}
    return refined_output

async def generate_slides(prompt_request, prompt_id, lecture_script, refined_output, client):
    tracker.log("Generating slides")

    # DEBUG HANDLING STARTS
    if (DEBUG):
        return mock_service.create_slides()
    # DEBUG HANDLING ENDS

    slides_context = {
        "courseId": prompt_request.course_id,
        "promptId": str(prompt_id),
        "lectureScript": lecture_script,
        "user": json.loads(
            mock_service.create_user().model_dump_json(
                by_alias=True, exclude_unset=True
            )
        ),
        "assets": refined_output.get("assets", ""),
    }
    print("Slides context: ", slides_context, flush=True)
    slides_response = await client.post(
        f"{SLIDES_API_URL}/v1/slides/generate",
        json=slides_context,
        timeout=300.0,
    )
    slides_response.raise_for_status()
    slides_data = slides_response.json()
    return slides_data

def generate_voice_tracks(lecture_script, slides_data):
    tracker.log("Generating voice tracks")
    try:
        # DEBUG HANDLING STARTS
        if (DEBUG):
            return mock_service.create_voice_track()
        # DEBUG HANDLING ENDS

        voice_track = narration_generation.generate_narrations(lecture_script, slides_data, mock_service.create_user())
    except Exception as e:
        print("Error generating voice track:", e, flush=True)
        voice_track = {}
    return voice_track


async def generate_avatar_video(voice_track, client):
    tracker.log("Calling Avatar API to generate video")
    try:
        avatar_response = await client.post(
            f"{AVATAR_API_URL}/v1/video/generate",
            json=voice_track,
            timeout=300.0,
        )
        print("Avatar API response:", avatar_response, flush=True)
        return avatar_response
    except Exception as e:
        print("Error generating avatar video:", e, flush=True)
        return None
    


async def process_prompt(prompt_id: str, prompt_request: str):
    async with httpx.AsyncClient() as client:
        try:
            subqueries = await decompose_inputs(prompt_request)
            retrieved_content = await query_document_intelligence(subqueries, client)

            # Run summarization and sending in the background
            asyncio.create_task(summarize_and_send(retrieved_content, client))

            # Continue with the rest of the workflow immediately
            refined_output = generate_script(retrieved_content)
            lecture_script = refined_output.get("lectureScript", "")
            slides_data = await generate_slides(prompt_request, prompt_id, lecture_script, refined_output, client)
            voice_track = generate_voice_tracks(lecture_script, slides_data)
            await generate_avatar_video(voice_track, client)
            tracker.log(f"SUCCESS: Completed processing for {prompt_id}")
        except Exception as e:
            tracker.log(f"ERROR: Failed processing for {prompt_id}: {e}")
