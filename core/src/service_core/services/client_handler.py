import asyncio
import json
import os
from typing import Any, Dict, List, Union

import httpx
from dotenv import load_dotenv

import service_core.services.fetch_mock_data as mock_service
from service_core.impl.tracker import tracker
from service_core.models.prompt_request import PromptRequest
from service_core.models.user_profile import UserProfile
from service_core.services import (
    decompose_input,
    narration_generation,
    script_generation,
)
from service_core.services.services_models.slides import SlidesEnvelope
from service_core.services.user_summary import summarize_and_send

load_dotenv()

DI_API_URL = "http://docint:25565"
SLIDES_API_URL = "http://slides:30606"
AVATAR_API_URL = "http://avatar-video-producer:9000"
STATUS_API_URL = "http://status-service:19910"
DEBUG = int(os.environ.get("ORPHEUS_DEBUG", "1"))


async def decompose_inputs(prompt_request: PromptRequest) -> List[str]:
    tracker.log("Decomposing inputs")

    decomposed_questions: List[str]
    if DEBUG:
        decomposed_questions = mock_service.create_decomposed_question().get("subqueries", [])
        return decomposed_questions

    decomposed_questions = decompose_input.decompose_question(prompt_request.prompt).get("subqueries", [])
    # FIX: [no-any-return]
    return decomposed_questions


async def query_document_intelligence(subqueries: List[str], client: httpx.AsyncClient) -> Dict[str, Any]:
    tracker.log("Querying document intelligence")

    if DEBUG:
        return mock_service.create_retrieved_content()

    subquery_for_api = subqueries[0] if subqueries else ""

    di_response = await client.get(
        f"{DI_API_URL}/v1/retrieval/abc",
        params={"courseId": "abc", "promptQuery": str(subquery_for_api)},
        timeout=300.0,
    )
    di_response.raise_for_status()
    di_data: Dict[str, Any] = di_response.json()
    return di_data


def generate_script(retrieved_content: Dict[str, Any]) -> Dict[str, Any]:
    tracker.log("Generating script")
    try:
        if DEBUG:
            output: Dict[str, Any] = mock_service.create_script()
            return output

        refined_output: Dict[str, Any] = script_generation.generate_script(retrieved_content, mock_service.create_user())
    except Exception as e:
        print(e)
        refined_output = {}

    return refined_output


async def generate_slides(prompt_request: PromptRequest, prompt_id: str, lecture_script: str, refined_output: Dict[str, Any], client: httpx.AsyncClient) -> Dict[str, Any]:
    tracker.log("Generating slides")

    # FIX: [no-any-return], [no-untyped-call]
    if DEBUG:
        return mock_service.create_slides()

    slides_context = {
        "courseId": prompt_request.course_id,
        "promptId": str(prompt_id),
        "lectureScript": lecture_script,
        # FIX: [no-untyped-call]
        "user": json.loads(mock_service.create_user().model_dump_json(by_alias=True, exclude_unset=True)),
        "assets": refined_output.get("assets", ""),
    }

    slides_response = await client.post(
        f"{SLIDES_API_URL}/v1/slides/generate",
        json=slides_context,
        timeout=300.0,
    )
    slides_response.raise_for_status()
    slides_data: Dict[str, Any] = slides_response.json()
    return slides_data


def generate_voice_scripts(lecture_script: str, slides_data: Dict[str, Any], user: UserProfile, client: httpx.AsyncClient) -> List[asyncio.Task[httpx.Response]]:
    tracker.log("Generating voice script")
    try:
        voice_track: Dict[str, Any]
        tasks: List[asyncio.Task[httpx.Response]] = []
        if DEBUG:
            for i in range(14):
                voice_track = mock_service.create_voice_script(i)
                print("Voice track: ", voice_track)
                task = generate_avatar_video(voice_track, i, client)
                if task:
                    tasks.append(task)
            return tasks

        voice_track = narration_generation.generate_narrations(lecture_script, slides_data, user)

        slides = voice_track.get("slides", [])
        for index, slide_data in enumerate(slides):
            task = generate_avatar_video(slide_data, index, client)
            if task:
                tasks.append(task)
        return tasks

    except Exception as e:
        print("Error generating voice track:", e, flush=True)
        return []


async def avatar_video_producer(voice_track: Dict[str, Any], client: httpx.AsyncClient) -> httpx.Response:
    try:
        avatar_response = await client.post(
            f"{AVATAR_API_URL}/v1/video/generate",
            json=voice_track,
            timeout=300.0,
        )
        #print("Avatar API response:", avatar_response.json(), flush=True)
        return avatar_response
    except Exception as e:
        print("Error occured during avatar generation: ", e, flush=True)
        raise


def generate_avatar_video(voice_track: Dict[str, Any], index: int, client: httpx.AsyncClient) -> Union[asyncio.Task[httpx.Response], None]:
    print(f"Calling Avatar API to generate video for slide {index}", flush=True)
    try:
        task: asyncio.Task[httpx.Response] = asyncio.create_task(avatar_video_producer(voice_track, client))
        return task
    except Exception as e:
        print("Error generating avatar video:", e, flush=True)
        return None


async def process_prompt(prompt_id: str, prompt_request: PromptRequest) -> None:
    async with httpx.AsyncClient() as client:
        try:
            subqueries = await decompose_inputs(prompt_request)
            retrieved_content = await query_document_intelligence(subqueries, client)

            asyncio.create_task(summarize_and_send(retrieved_content, client))

            refined_output = generate_script(retrieved_content)
            lecture_script = refined_output.get("lectureScript", "")
            slides_data: Dict[str, Any] = await generate_slides(prompt_request, prompt_id, lecture_script, refined_output, client)
            assert prompt_request.user_persona is not None, "User profile must be defined for voice scripts."

            avatar_tasks: List[asyncio.Task[httpx.Response]] = generate_voice_scripts(
                lecture_script,
                slides_data,
                prompt_request.user_persona,
                client,
            )

            if avatar_tasks:
                await asyncio.gather(*avatar_tasks)

            tracker.log(f"SUCCESS: Completed processing for {prompt_id}")
        except Exception as e:
            tracker.log(f"ERROR: Failed processing for {prompt_id}: {e}")
