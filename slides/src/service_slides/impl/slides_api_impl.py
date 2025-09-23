from concurrent.futures.thread import ThreadPoolExecutor

from fastapi import HTTPException, Depends
from langchain_core.language_models import BaseChatModel
from pydantic import StrictStr, Field
from service_slides.impl.helper.slide_generator import generate_slide_structure
from service_slides.impl.manager.layout_manager import LayoutManager
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
            status="IN_PROGRESS" if status.achieved < status.total else "DONE",
            totalPages=status.total,
            generatedPages=status.achieved,
            lastUpdated=status.updated_at,
        )

    async def request_slide_generation(
        self,
        request_slide_generation_request: RequestSlideGenerationRequest,
        executor: ThreadPoolExecutor,
        job_manager: JobManager,
        layout_manager: LayoutManager,
        llm_model: BaseChatModel,
    ) -> GenerationAcceptedResponse:
        structure = await generate_slide_structure(
            lecture_script=request_slide_generation_request.lecture_script,
            layouts=await layout_manager.get_available_layouts(
                request_slide_generation_request.course_id
            ),
            llm_model=llm_model,
        )

        await job_manager.init_job(
            request_slide_generation_request.lecture_id, len(structure.items)
        )
        for item in structure.items:

            async def generate_item():
                await generate_slide(
                    lecture_script=request_slide_generation_request.lecture_script,
                    slide_layout=request_slide_generation_request.slide_layout,
                    slide_template=layout_manager.get_layout_template(
                        request_slide_generation_request.course_id, item.layout
                    ),
                    slide_content=item.content,
                    structure=structure,
                    assets=item.assets,
                )
                await job_manager.finish_page(request_slide_generation_request.lecture_id)

            executor.submit(generate_item)

        status = await job_manager.get_status(request_slide_generation_request.lecture_id)
        return GenerationAcceptedResponse(
            lectureId=request_slide_generation_request.lecture_id,
            status="IN_PROGRESS" if status.achieved < status.total else "DONE",
            createdAt=datetime.now(),
            structure=structure.as_simple_slide_structure(),
        )
