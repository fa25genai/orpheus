import asyncio
from concurrent.futures import ThreadPoolExecutor
from uuid import UUID, uuid4

from fastapi import HTTPException

from ..apis.core_api_base import BaseCoreApi
from ..app_state import app_state
from ..models.prompt_request import PromptRequest
from ..models.prompt_response import PromptResponse
from ..services.client_handler import process_prompt

import logging

logger = logging.getLogger("Core API Implementation")


def get_executor() -> ThreadPoolExecutor:
    with app_state.lock:
        if app_state.executor is None:
            app_state.executor = ThreadPoolExecutor()
    return app_state.executor


class CoreApiImpl(BaseCoreApi):  # type: ignore[no-untyped-call]
    async def create_lecture_from_prompt(
        self, prompt_request: PromptRequest
    ) -> PromptResponse:
        try:
            prompt_id = uuid4()
            executor = get_executor()
            if prompt_request.user_persona is None:
                raise ValueError(
                    "User persona must be defined for prompt requests from client."
                )

            prompt_request.user_persona.id = uuid4()  # TODO: Remove this workaround when client provides user_persona.id
            executor.submit(process_prompt_handler, prompt_id, prompt_request)

            return PromptResponse(promptId=prompt_id)

        except ConnectionError as e:
            raise HTTPException(status_code=503, detail=f"Datastore error: {e}")
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"An unexpected error occurred: {e}"
            )


def process_prompt_handler(prompt_id: UUID, prompt_request: PromptRequest) -> None:
    try:
        asyncio.run(process_prompt(str(prompt_id), prompt_request))
    except Exception as exception:
        logger.error(
            f"An unexpected error occurred for prompt `{prompt_id}`", exc_info=exception
        )
