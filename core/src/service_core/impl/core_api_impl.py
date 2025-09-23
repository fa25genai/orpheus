from fastapi import HTTPException
from uuid import UUID, uuid4
# Import the base class you are inheriting from
from ..apis.core_api_base import BaseCoreApi
# Import the generated Pydantic models
from ..models.prompt_request import PromptRequest
from ..models.prompt_response import PromptResponse
from ..models.data_response import DataResponse
# Import your custom service layer where the real work happens
from ..services import decompose_input

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
            response = decompose_input.decompose_question(prompt_request.prompt)
            lecture_id = uuid4()  #
            return PromptResponse(lectureId=lecture_id)
        except ConnectionError as e:
            raise HTTPException(status_code=503, detail=f"Datastore error: {e}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")
    async def get_slides_by_lecture_id(
        self,
        lectureId: UUID,
    ) -> DataResponse:
        """
        Retrieves the result of a slide generation job.
        """
        try:
            return lecture_service.get_lecture_slides(str(lectureId))
        except ConnectionError as e:
            raise HTTPException(status_code=503, detail=f"Datastore error: {e}")
        except KeyError:
            raise HTTPException(status_code=404, detail="Lecture job not found.")
    async def get_video_by_lecture_id(
        self,
        lectureId: UUID,
    ) -> DataResponse:
        """
        Retrieves the result of a video generation job.
        """
        try:
            return lecture_service.get_lecture_video(str(lectureId))
        except ConnectionError as e:
            raise HTTPException(status_code=503, detail=f"Datastore error: {e}")
        except KeyError:
            raise HTTPException(status_code=404, detail="Lecture job not found.")