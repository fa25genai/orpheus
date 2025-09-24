from fastapi import HTTPException
from uuid import UUID, uuid4
from ..apis.core_api_base import BaseCoreApi
from ..models.prompt_request import PromptRequest
from ..models.prompt_response import PromptResponse

from service_core.services.client_handler import process_prompt
from ..main import app

class CoreApiImpl(BaseCoreApi):
    """
    This is the implementation of the Core API.
    The router in core_api.py will discover this class and call its methods.
    """
    async def create_lecture_from_prompt(
        self,
        prompt_request: PromptRequest,
    ) -> PromptResponse:
        """
        Accepts a user prompt and initiates a job to generate lecture content.
        """
        try:
            prompt_id = uuid4()

            executor = app.state.executor
            executor.submit(process_prompt, prompt_id, prompt_request.prompt)
        
            return PromptResponse(promptId=prompt_id)
        except ConnectionError as e:
            raise HTTPException(status_code=503, detail=f"Datastore error: {e}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")
    
    