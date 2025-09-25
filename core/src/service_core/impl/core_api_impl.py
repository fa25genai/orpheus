from fastapi import HTTPException
from uuid import UUID, uuid4

from ..apis.core_api_base import BaseCoreApi
from ..models.prompt_request import PromptRequest
from ..models.prompt_response import PromptResponse
from ..services.client_handler import process_prompt
from concurrent.futures import ThreadPoolExecutor
import asyncio

from ..app_state import app_state

def get_executor() -> ThreadPoolExecutor:
    with app_state.lock:
        if app_state.executor is None:
            print("✅ Initializing CoreThreadPoolExecutor for this worker process...")
            app_state.executor = ThreadPoolExecutor()
    return app_state.executor

class CoreApiImpl(BaseCoreApi):
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
            executor = get_executor()
            executor.submit(process_prompt_handler, prompt_id, prompt_request)

            return PromptResponse(promptId=str(prompt_id))

        except ConnectionError as e:
            raise HTTPException(status_code=503, detail=f"Datastore error: {e}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

def process_prompt_handler(prompt_id: UUID, prompt_request: PromptRequest):
    try:
        asyncio.run(process_prompt(prompt_id, prompt_request))
    except Exception as e:
        print(f"A critical error occurred for prompt [{prompt_id}]: {e}")