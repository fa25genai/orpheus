from fastapi import HTTPException
from uuid import UUID, uuid4
from typing import Dict
# Import the base class you are inheriting from
from ..apis.core_api_base import BaseCoreApi
# Import the generated Pydantic models
from ..models.prompt_request import PromptRequest
from ..models.prompt_response import PromptResponse
from ..models.data_response import DataResponse
# Import your custom service layer where the real work happens
from ..services import decompose_input, fetch_mock_data, generate_lecture_content
import json
import asyncio
lecture_store: Dict[UUID, Dict] = {}

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
            decomposed_questions = decompose_input.decompose_question(prompt_request.prompt)
            #print("Decomposed Questions:", decomposed_questions)
            print("Simulating async processing delay...")
            await asyncio.sleep(5)
            refined_output = generate_lecture_content.refine_lecture_content(fetch_mock_data.retrieved_content, fetch_mock_data.demo_user)
            #print(json.dumps(refined_output, indent=2, ensure_ascii=False))
            
            lecture_id = uuid4()
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
        Returns a static, dummy response for slides.
        This endpoint is stateless and does not use the lectureId to look up data.
        """
        # Since no data is stored, we return a generic successful response.
        # The URL is generated using the provided lectureId for consistency.
        try:
            response = ''   # Do a call to slideHandler

            return DataResponse(
                slidesUrl=response['url']
            )
        except ConnectionError as e:
            raise HTTPException(status_code=503, detail=f"Datastore error: {e}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

    async def get_video_by_lecture_id(
        self,
        lectureId: UUID,
    ) -> DataResponse:
        """
        Returns a static, dummy response for a video.
        This endpoint is stateless and does not use the lectureId to look up data.
        """
        # Since no data is stored, we return a generic successful response.
        # The URL is generated using the provided lectureId for consistency.
        return DataResponse(
            videoUrl=f"https://storage.example.com/videos/{lectureId}.mp4"
        )