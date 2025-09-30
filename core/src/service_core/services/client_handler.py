import asyncio
import os
from typing import Any, Dict, List, Union
import logging

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
from service_core.services.user_summary import summarize_content_with_llama
from service_status.models.status_patch import StatusPatch
from service_status.models.step_status import StepStatus
from service_core.services.services_models.voice_track import VoiceTrackResponse

load_dotenv()

DI_API_URL = "http://docint:25565"
SLIDES_API_URL = "http://slides:30606"
AVATAR_API_URL = "http://avatar-video-producer:9000"
STATUS_API_URL = "http://status-service:19910"

# Use this when you start the service locally outside a docker container
# DI_API_URL = "http://localhost:25565"
# SLIDES_API_URL = "http://localhost:30606"
# AVATAR_API_URL = "http://localhost:9000"
# STATUS_API_URL = "http://localhost:19910"

DEBUG = int(os.getenv("ORPHEUS_DEBUG", "0"))  # DEBUG enabled by default

logger = logging.getLogger("Client Handler")


async def update_status(
    prompt_id: str, patch: StatusPatch, client: httpx.AsyncClient
) -> None:
    logger.info(f"Updating status for {prompt_id} with patch: {patch.to_json()}")
    await client.patch(
        f"{STATUS_API_URL}/status/{prompt_id}/update",
        json=patch.to_dict(),
        timeout=300.0,
    )


async def retrieve_subqueries_from_prompt(
    prompt_request: PromptRequest, prompt_id: str, client: httpx.AsyncClient
) -> List[str]:
    tracker.log("Decomposing inputs")
    await update_status(
        prompt_id, StatusPatch(stepUnderstanding=StepStatus.IN_PROGRESS), client
    )

    subqueries: List[str]
    if DEBUG:
        subqueries = mock_service.create_decomposed_question().get("subqueries", [])
        await update_status(
            prompt_id, StatusPatch(stepUnderstanding=StepStatus.DONE), client
        )
        return subqueries

    subqueries = decompose_input.decompose_question(prompt_request.prompt).get(
        "subqueries", []
    )

    logger.debug(f"subqueries retrieved from prompt: {subqueries}")

    # FIX: [no-any-return]
    await update_status(
        prompt_id, StatusPatch(stepUnderstanding=StepStatus.DONE), client
    )
    return subqueries


async def send_summary_to_endpoint(
    prompt_id: str, summary: str, client: httpx.AsyncClient
) -> None:
    try:
        await update_status(prompt_id, StatusPatch(lectureSummary=summary), client)
        logger.info(f"Summary sent for prompt {prompt_id}")
    except Exception as exception:
        logger.error(
            f"Error sending summary for prompt {prompt_id}", exc_info=exception
        )


async def summarize_and_send(
    prompt_id: str,
    content: List[Dict[str, Any]],
    client: httpx.AsyncClient,
    user_prompt: str,
) -> None:
    try:
        summary: str
        if DEBUG:
            summary = "A for loop is a control flow statement that allows code to be executed repeatedly, typically used to iterate over sequences or iterable objects.\n\nIt features a basic syntax that specifies an item variable and an iterable collection of objects, such as a list or tuple.\n\nFor loops can be nested.\n\nThey often utilize functions like range() to generate number sequences.\n\nFlow control options include break to exit the loop prematurely, and continue to skip the current iteration.\n\nAn else block can be added, which executes after the loop finishes unless the loop was terminated by a break."
            await send_summary_to_endpoint(prompt_id, summary, client)
            return
        summary = summarize_content_with_llama(content, user_prompt)
        await send_summary_to_endpoint(prompt_id, summary, client)
    except Exception as e:
        logger.error(f"Error summarizing content for prompt {prompt_id}", exc_info=e)


async def query_document_intelligence(
    subqueries: List[str],
    client: httpx.AsyncClient,
    prompt_id: str,
    prompt_request: PromptRequest,
) -> List[Dict[str, Any]]:
    tracker.log("Querying document intelligence")
    try:
        await update_status(
            prompt_id, StatusPatch(stepLookup=StepStatus.IN_PROGRESS), client
        )

        di_response = await client.post(
            f"{DI_API_URL}/v1/retrieval/{prompt_request.course_id}/batch",
            json={"promptQueries": subqueries},
            timeout=300.0,
        )
        di_response.raise_for_status()
        di_data: List[Dict[str, Any]] = di_response.json().get("results", [])
        await update_status(prompt_id, StatusPatch(stepLookup=StepStatus.DONE), client)
        return di_data
    except Exception as exception:
        logger.error(
            f"Error querying Document Intelligence for prompt {prompt_id}",
            exc_info=exception,
        )
        await update_status(
            prompt_id, StatusPatch(stepLookup=StepStatus.FAILED), client
        )
        return []


async def generate_script(
    retrieved_content: List[Dict[str, Any]],
    prompt_id: str,
    prompt_request: PromptRequest,
    client: httpx.AsyncClient,
) -> Dict[str, Any]:
    try:
        tracker.log("Generating script")
        await update_status(
            prompt_id,
            StatusPatch(stepLectureScriptGeneration=StepStatus.IN_PROGRESS),
            client,
        )

        if prompt_request.user_persona is None:
            logger.error("User persona must be defined for voice scripts.")
            raise ValueError("User persona must be defined")

        if DEBUG:
            output: Dict[str, Any] = mock_service.create_script()
            await update_status(
                prompt_id,
                StatusPatch(stepLectureScriptGeneration=StepStatus.DONE),
                client,
            )
            return output

        refined_output: Dict[str, Any] = script_generation.generate_script(
            retrieved_content, prompt_request.user_persona
        )
        await update_status(
            prompt_id, StatusPatch(stepLectureScriptGeneration=StepStatus.DONE), client
        )
    except Exception as exception:
        logger.error(
            f"Error generating script for prompt {prompt_id}", exc_info=exception
        )
        refined_output = {}
        await update_status(
            prompt_id,
            StatusPatch(stepLectureScriptGeneration=StepStatus.FAILED),
            client,
        )

    return refined_output


async def generate_slides(
    prompt_request: PromptRequest,
    prompt_id: str,
    lecture_script: str,
    refined_output: Dict[str, Any],
    client: httpx.AsyncClient,
) -> Dict[str, Any]:
    tracker.log("Generating slides")
    try:
        if prompt_request.user_persona is None:
            logger.error("User persona must be defined for voice scripts.")
            raise ValueError("User persona must be defined")

        generate_slides_request_body = {
            "courseId": prompt_request.course_id,
            "promptId": str(prompt_id),
            "lectureScript": lecture_script,
            "user": prompt_request.user_persona.model_dump(mode="json"),
            "assets": refined_output.get("assets", []),
        }

        logger.debug(f"generated slides request body: {generate_slides_request_body}")

        slides_response = await client.post(
            f"{SLIDES_API_URL}/v1/slides/generate",
            json=generate_slides_request_body,
            timeout=300.0,
        )
        slides_response.raise_for_status()
        slides_data: Dict[str, Any] = slides_response.json()
        return slides_data
    except Exception as exception:
        logger.error(
            f"Error generating slides for prompt {prompt_id}", exc_info=exception
        )
        await update_status(
            prompt_id,
            StatusPatch(stepSlideStructureGeneration=StepStatus.FAILED),
            client,
        )
        return {}


async def generate_voice_scripts(
    lecture_script: str,
    slides_data: Dict[str, Any],
    user: UserProfile,
    client: httpx.AsyncClient,
    prompt_id: str,
    course_id: str,
) -> List[asyncio.Task[httpx.Response]]:
    tracker.log("Generating voice script")
    try:
        voice_track: Dict[str, Any]
        tasks: List[asyncio.Task[httpx.Response]] = []
        if DEBUG:
            for i in range(14):
                voice_track = mock_service.create_voice_script(i)
                logger.debug(f"voice track: {voice_track}")
                task = generate_avatar_video(voice_track, i, client)
                if task:
                    tasks.append(task)
            return tasks

        logger.info(f"Generating voice track for prompt {prompt_id}")
        logger.debug(f"lecture script: {lecture_script}")
        logger.debug(f"slides data: {slides_data}")

        voice_track = narration_generation.generate_narrations(
            lecture_script, slides_data, user
        )

        slides = voice_track.get("slideMessages", [])
        voice_track_request = VoiceTrackResponse(
            promptId=prompt_id,
            courseId=course_id,
            voiceTrack="",
            slideNumber=0,
            userProfile=user,
        )
        for index, slide_data in enumerate(slides):
            voice_track_request.slideNumber = index
            voice_track_request.voiceTrack = slide_data
            task = generate_avatar_video(
                voice_track_request.model_dump(mode="json"), index, client
            )
            if task:
                tasks.append(task)
        return tasks

    except Exception as exception:
        logger.error("Voice track generation failed", exc_info=exception)
        return []


async def avatar_video_producer(
    voice_track: Dict[str, Any], client: httpx.AsyncClient
) -> httpx.Response:
    try:
        avatar_response = await client.post(
            f"{AVATAR_API_URL}/v1/video/generate",
            json=voice_track,
            timeout=300.0,
        )
        return avatar_response
    except Exception as exception:
        logger.error("Generating avatar video failed", exc_info=exception)
        raise


# TODO return Optional instead of response
def generate_avatar_video(
    voice_track: Dict[str, Any], index: int, client: httpx.AsyncClient
) -> Union[asyncio.Task[httpx.Response], None]:
    logger.info(f"Generating avatar video for slide {index}")
    try:
        task: asyncio.Task[httpx.Response] = asyncio.create_task(
            avatar_video_producer(voice_track, client)
        )
        return task
    except Exception as exception:
        logger.error("Error generating avatar video", exc_info=exception)
        return None


async def process_prompt(prompt_id: str, prompt_request: PromptRequest) -> None:
    try:
        async with httpx.AsyncClient() as client:
            subqueries = await retrieve_subqueries_from_prompt(
                prompt_request, prompt_id, client
            )
            retrieved_content = await query_document_intelligence(
                subqueries, client, prompt_id, prompt_request
            )

            asyncio.create_task(
                summarize_and_send(
                    prompt_id, retrieved_content, client, prompt_request.prompt
                )
            )

            refined_output = await generate_script(
                retrieved_content, prompt_id, prompt_request, client
            )
            lecture_script = refined_output.get("lectureScript", "")
            slides_data: Dict[str, Any] = await generate_slides(
                prompt_request, prompt_id, lecture_script, refined_output, client
            )

            if prompt_request.user_persona is None:
                logger.error("User persona must be defined for voice scripts.")
                raise ValueError("User persona must be defined for voice scripts.")

            avatar_tasks: List[
                asyncio.Task[httpx.Response]
            ] = await generate_voice_scripts(
                lecture_script,
                slides_data,
                prompt_request.user_persona,
                client,
                prompt_id,
                prompt_request.course_id,
            )

            if avatar_tasks:
                await asyncio.gather(*avatar_tasks)

            tracker.log(f"SUCCESS: Completed processing for {prompt_id}")
    except Exception as exception:
        logger.error(
            f"Failed processing for {prompt_id}: {exception}", exc_info=exception
        )

        if "[Errno 8] nodename nor servname provided, or not known" in str(exception):
            logger.error(
                "This usually means the service hostname is incorrect or unreachable. "
                "If you started the server as docker component make sure the URLs for DI_API_URL are referencing docker addresses (e.g. http://docint:25565). "
                "If you started the server as standalone make sure the URLs for DI_API_URL are pointing to the correct host and port (e.g. http://localhost:25565)."
            )
