from concurrent.futures.thread import ThreadPoolExecutor

from fastapi import HTTPException, Depends
from langchain_core.language_models import BaseChatModel
from pydantic import StrictStr, Field
from typing_extensions import Annotated

from service_slides.apis.slides_api import router as router
from service_slides.apis.slides_api_base import BaseSlidesApi
from service_slides.impl.manager.job_manager import JobManager
from service_slides.models.generation_accepted_response import GenerationAcceptedResponse
from service_slides.models.generation_status_response import GenerationStatusResponse
from service_slides.models.request_slide_generation_request import RequestSlideGenerationRequest


class SlidesApiImpl(BaseSlidesApi):
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

    async def get_generation_status(
        self,
        lectureId: Annotated[
            StrictStr, Field(description="The lectureId returned by /v1/slides/generate")
        ],
        job_manager: JobManager,
    ) -> GenerationStatusResponse:
        status = await job_manager.get_status(lectureId)
        if status is None:
            raise HTTPException(
                status_code=404
            )  # TODO: Check if lecture is present on CDN and then we have to return done
        return GenerationStatusResponse(
            lectureId=lectureId,
            status="IN_PROGRESS",
            totalPages=status.total,
            generatedPages=status.achieved,
            lastUpdated=status.updated_at,
        )

    async def request_slide_generation(
        self,
        request_slide_generation_request: RequestSlideGenerationRequest,
        executor: ThreadPoolExecutor,
        job_manager: JobManager,
        llm_model: BaseChatModel,
    ) -> GenerationAcceptedResponse:
        await job_manager.init_job(request_slide_generation_request.lecture_id, 30)
        raise HTTPException(status_code=500, detail="Not implemented")
