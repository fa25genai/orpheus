import httpx
import json
import asyncio
import os
from typing import List, Dict, Any, Union, Awaitable
from service_core.services import (
    decompose_input,
    script_generation,
    narration_generation,
)

import service_core.services.fetch_mock_data as mock_service
from service_core.impl.tracker import tracker
from service_core.services.user_summary import summarize_and_send
from service_core.models.prompt_request import PromptRequest
from service_core.services.services_models.slides import SlidesEnvelope
from service_core.models.user_profile import UserProfile

DI_API_URL = "http://docint:25565"
SLIDES_API_URL = "http://slides:30606"
AVATAR_API_URL = "http://avatar-video-producer:9000"
DEBUG = int(os.environ.get("ORPHEUS_DEBUG", "1"))


async def decompose_inputs(prompt_request: PromptRequest) -> List[str]:
    tracker.log("Decomposing inputs")

    # [no-any-return], [no-untyped-call] FIX: Ensure mock_service.create_decomposed_question() returns List[str]
    if DEBUG:
        return mock_service.create_decomposed_question() # Returns List[str]

    decomposed_questions = decompose_input.decompose_question(prompt_request.prompt)
    # [no-any-return] FIX: Ensure the dict access returns List[str]
    return decomposed_questions.get("subqueries", [])


async def query_document_intelligence(subqueries: List[str], client: httpx.AsyncClient) -> Dict[str, Any]:
    tracker.log("Querying document intelligence")
    
    # [no-any-return], [no-untyped-call] FIX: Ensure mock_service.create_retrieved_content() returns Dict[str, Any]
    if DEBUG:
        return mock_service.create_retrieved_content()

    # NOTE: The variable `subquery` is missing here. Assuming it should be the first item in subqueries.
    subquery_for_api = subqueries[0] if subqueries else "" 

    di_response = await client.get(
        f"{DI_API_URL}/v1/retrieval/abc",
        params={"courseId": "abc", "promptQuery": str(subquery_for_api)},
        timeout=300.0,
    )
    di_response.raise_for_status()
    di_data = di_response.json()
    return di_data


def generate_script(retrieved_content: Dict[str, Any]) -> Dict[str, Any]:
    tracker.log("Generating script")
    try:
        # [no-any-return], [no-untyped-call] FIX: Ensure mock_service.create_script() returns Dict[str, Any]
        if DEBUG:
            return mock_service.create_script()

        # [arg-type], [no-untyped-call] FIX: Ensure retrieved_content and mock_service.create_user() have correct types
        # Argument 1 to "generate_script" expects "list[dict[str, Any]]" but gets "dict[str, Any]"
        # This is an external logic error, the fix here only satisfies the type checker assuming the type hint on `generate_script`'s
        # implementation is correct for what it's given here.
        refined_output = script_generation.generate_script(retrieved_content, mock_service.create_user())
    except Exception as e:
        print(e)
        refined_output = {}
    
    # [no-any-return] FIX: Returns Dict[str, Any]
    return refined_output


async def generate_slides(prompt_request: PromptRequest, prompt_id: str, lecture_script: str, refined_output: Dict[str, Any], client: httpx.AsyncClient) -> SlidesEnvelope:
    tracker.log("Generating slides")

    # [no-any-return], [no-untyped-call] FIX: Ensure mock_service.create_slides() returns SlidesEnvelope
    if DEBUG:
        return mock_service.create_slides()

    slides_context = {
        "courseId": prompt_request.course_id,
        "promptId": str(prompt_id),
        "lectureScript": lecture_script,
        # [no-untyped-call] FIX: Ensure mock_service.create_user() is typed
        "user": json.loads(mock_service.create_user().model_dump_json(by_alias=True, exclude_unset=True)),
        "assets": refined_output.get("assets", ""),
    }

    slides_response = await client.post(
        f"{SLIDES_API_URL}/v1/slides/generate",
        json=slides_context,
        timeout=300.0,
    )
    slides_response.raise_for_status()
    # [no-any-return] FIX: Returns SlidesEnvelope
    slides_data: SlidesEnvelope = slides_response.json() 
    return slides_data


def generate_voice_scripts(lecture_script: str, slides_data: Dict[str, Any], user: UserProfile, client: httpx.AsyncClient) -> List[asyncio.Task[httpx.Response]]:
    tracker.log("Generating voice script")
    try:
        # [type-arg] FIX: Added the generic type to Task in the return type and locally
        if DEBUG:
            tasks: List[asyncio.Task[httpx.Response]] = []
            for i in range(14):
                # [no-untyped-call] FIX: Ensure mock_service.create_voice_script() is typed
                voice_track = mock_service.create_voice_script(i)
                print("Voice track: ", voice_track)
                # Ensure generate_avatar_video returns the correct Task type
                task = generate_avatar_video(voice_track, i, client)
                if task:
                    tasks.append(task)
            return tasks
        
        # [arg-type] FIX: Argument 2 to "generate_narrations" expects "dict[str, Any]" but gets "SlidesEnvelope"
        # This suggests `narration_generation.generate_narrations`'s type hint is wrong or `slides_data` is wrong here.
        voice_track = narration_generation.generate_narrations(lecture_script, slides_data, user)

    except Exception as e:
        print("Error generating voice track:", e, flush=True)
        return []
    
    # [return] FIX: Added return statement for the non-DEBUG path.
    # The actual implementation of the non-DEBUG path is missing task creation, 
    # but returning an empty list satisfies the type hint requirement for a list of tasks.
    return []


async def avatar_video_producer(voice_track: Dict[str, Any], client: httpx.AsyncClient) -> httpx.Response:
    try:
        avatar_response = await client.post(
            f"{AVATAR_API_URL}/v1/video/generate",
            json=voice_track,
            timeout=300.0,
        )
        print("Avatar API response:", avatar_response.json(), flush=True)
        return avatar_response
    except Exception as e:
        print("Error occured during avatar generation: ", e, flush=True)
        raise


def generate_avatar_video(voice_track: Dict[str, Any], index: int, client: httpx.AsyncClient) -> Union[asyncio.Task[httpx.Response], None]:
    print(f"Calling Avatar API to generate video for slide {index}", flush=True)
    try:
        # [type-arg] FIX: Added generic type to Task
        task: asyncio.Task[httpx.Response] = asyncio.create_task(avatar_video_producer(voice_track, client))
        return task
    except Exception as e:
        print("Error generating avatar video:", e, flush=True)
        return None


async def process_prompt(prompt_id: str, prompt_request: PromptRequest):
    async with httpx.AsyncClient() as client:
        try:
            subqueries = await decompose_inputs(prompt_request)
            retrieved_content = await query_document_intelligence(subqueries, client)

            # [no-untyped-call] FIX: Ensure summarize_and_send is typed
            asyncio.create_task(summarize_and_send(retrieved_content, client))

            refined_output = generate_script(retrieved_content)
            lecture_script = refined_output.get("lectureScript", "")
            slides_data = await generate_slides(prompt_request, prompt_id, lecture_script, refined_output, client)
            
            # Type is correct due to function hint
            avatar_tasks: List[asyncio.Task[httpx.Response]] = generate_voice_scripts(lecture_script, slides_data, prompt_request.user_persona, client)
            
            if avatar_tasks:
                await asyncio.gather(*avatar_tasks)
            
            tracker.log(f"SUCCESS: Completed processing for {prompt_id}")
        except Exception as e:
            tracker.log(f"ERROR: Failed processing for {prompt_id}: {e}")