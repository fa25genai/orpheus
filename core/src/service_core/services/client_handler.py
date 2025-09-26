import json
from typing import Any, Callable, Dict, List, Optional, cast

import httpx
from httpx import AsyncClient, Response

from service_core.impl.tracker import tracker
from service_core.models.prompt_request import PromptRequest
from service_core.models.user_profile import UserProfile as _UserProfile
from service_core.services import (
    decompose_input,
    narration_generation,
    script_generation,
)
from service_core.services.fetch_mock_data import (
    create_demo_user as _create_demo_user,
)
from service_core.services.fetch_mock_data import (
    create_demoretrieved_content as _create_demo_content,
)

create_demoretrieved_content: Callable[[], List[Dict[str, Any]]] = cast(
    Callable[[], List[Dict[str, Any]]], _create_demo_content
)
create_demo_user = cast(Callable[[], _UserProfile], _create_demo_user)

DI_API_URL = "http://docint:25565"
SLIDES_API_URL = "http://slides:30606"
AVATAR_API_URL = "http://avatar-video-producer:9000"


async def decompose_inputs(prompt_request: PromptRequest) -> List[str]:
    tracker.log("Decomposing inputs")
    decomposed_questions = decompose_input.decompose_question(prompt_request.prompt)
    subs = decomposed_questions.get("subqueries", [])
    return [str(s) for s in subs] if isinstance(subs, list) else []


async def query_document_intelligence(subqueries: List[str], client: AsyncClient) -> List[Dict[str, Any]]:
    tracker.log("Querying document intelligence")
    retrieved_content = []
    for idx, subquery in enumerate(subqueries):
        di_response = await client.get(
            f"{DI_API_URL}/v1/retrieval/abc",
            params={"courseId": "abc", "promptQuery": str(subquery)},
            timeout=300.0,
        )
        di_response.raise_for_status()
        di_data = di_response.json()
        tracker.log(f"di_data received: {di_data}")
        retrieved_content.append(di_data)
    return retrieved_content


def generate_script(retrieved_content: List[Dict[str, Any]]) -> Dict[str, Any]:
    tracker.log("Generating script")
    try:
        refined_output = script_generation.generate_script(retrieved_content, create_demo_user())
    except Exception as e:
        print(e)
        refined_output = {}
    return refined_output


async def generate_slides(
    prompt_request: PromptRequest,
    prompt_id: str,
    lecture_script: str,
    refined_output: Dict[str, Any],
    client: AsyncClient,
) -> Dict[str, Any]:
    tracker.log("Generating slides")
    slides_context = {
        "courseId": prompt_request.course_id,
        "promptId": str(prompt_id),
        "lectureScript": lecture_script,
        "user": json.loads(create_demo_user().model_dump_json(by_alias=True, exclude_unset=True)),
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
    return cast(Dict[str, Any], slides_data)


def generate_voice_tracks(lecture_script: str, slides_data: Dict[str, Any]) -> Dict[str, Any]:
    tracker.log("Generating voice tracks")
    try:
        voice_track = narration_generation.generate_narrations(
            lecture_script, slides_data, create_demo_user()
        )
    except Exception as e:
        print("Error generating voice track:", e, flush=True)
        voice_track = {}
    return voice_track


async def generate_avatar_video(voice_track: Dict[str, Any], client: AsyncClient) -> Optional[Response]:
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


async def process_prompt(prompt_id: str, prompt_request: PromptRequest) -> None:
    async with httpx.AsyncClient() as client:
        _subqueries = await decompose_inputs(prompt_request)
        # retrieved_content = await query_document_intelligence(subqueries, client)
        retrieved_content = create_demoretrieved_content()  # Using mock data instead of actual DI call
        refined_output = generate_script(retrieved_content)
        lecture_script = refined_output.get("lectureScript", "")
        slides_data = await generate_slides(prompt_request, prompt_id, lecture_script, refined_output, client)
        voice_track = generate_voice_tracks(lecture_script, slides_data)
        await generate_avatar_video(voice_track, client)
