import asyncio
from concurrent.futures import ThreadPoolExecutor
from uuid import UUID, uuid4

from fastapi import HTTPException

from ..apis.core_api_base import BaseCoreApi
from ..app_state import app_state
from ..models.prompt_request import PromptRequest
from ..models.prompt_response import PromptResponse
from ..services.client_handler import process_prompt
from .tracker import tracker


def get_executor(prompt_id: UUID) -> ThreadPoolExecutor:
    with app_state.lock:
        if app_state.executor is None:
            # print(f"")
            app_state.executor = ThreadPoolExecutor()
    return app_state.executor


class CoreApiImpl(BaseCoreApi):  # type: ignore[no-untyped-call]
    async def create_lecture_from_prompt(self, prompt_request: PromptRequest) -> PromptResponse:
        try:
            prompt_id = uuid4()
            # with ThreadPoolExecutor(max_workers=3) as executor:
            #     print(executor)
            #     if executor is None:
            #         raise RuntimeError("The ProcessPoolExecutor is not available. Check the application startup logs.")
            #     # loop = asyncio.get_event_loop()
            #     executor.submit(process_prompt_handler, prompt_id, prompt_request)
            #     print(prompt_id)
            executor = get_executor(prompt_id)
            tracker.log(f"Initializing CoreThreadPoolExecutor for {prompt_id}")
            executor.submit(process_prompt_handler, prompt_id, prompt_request)

            return PromptResponse(promptId=prompt_id)

        except ConnectionError as e:
            raise HTTPException(status_code=503, detail=f"Datastore error: {e}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")


def process_prompt_handler(prompt_id: UUID, prompt_request: PromptRequest) -> None:
    try:
        asyncio.run(process_prompt(str(prompt_id), prompt_request))
        tracker.log(f"SUCCESS: Closing CoreThreadPoolExecutor for {prompt_id}")
    except Exception as e:
        print(f"A critical error occurred for prompt [{prompt_id}]: {e}")
