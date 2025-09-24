from datetime import datetime

from concurrent.futures.thread import ThreadPoolExecutor

from fastapi import HTTPException
from langchain_core.language_models import BaseLanguageModel
from pydantic import StrictStr, Field
from service_slides.impl.llm_chain.slide_structure import generate_slide_structure
from service_slides.impl.llm_chain.slide_content import generate_single_slide_content
from service_slides.impl.manager.layout_manager import LayoutManager
from service_slides.impl.manager.slide_output_manager import save_slides_to_file
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
        splitting_model: BaseLanguageModel,
        slidesgen_model: BaseLanguageModel,
    ) -> GenerationAcceptedResponse:
        # 1. Generate the slide structure
        structure = await generate_slide_structure(
            model=splitting_model,
            lecture_script=request_slide_generation_request.lecture_script,
            available_layouts=await layout_manager.get_available_layouts(
                request_slide_generation_request.course_id
            ),
        )

        # 2. Initialize job for tracking progress
        await job_manager.init_job(
            request_slide_generation_request.lecture_id, len(structure.items)
        )

        # 3. Start background slide generation (don't wait for completion)
        # Submit individual slide generation tasks directly to the executor
        slide_futures = []
        for i, item in enumerate(structure.items):

            def generate_item(item_content, item_layout, slide_num, course_id, lecture_id):
                import asyncio

                # Get layout template synchronously within the executor
                async def get_template():
                    return await layout_manager.get_layout_template(course_id, item_layout)

                layout_template = asyncio.run(get_template())

                # Generate slide content
                slide_content = generate_single_slide_content(
                    model=slidesgen_model,
                    text=item_content,
                    layout_template=layout_template,
                    slide_number=slide_num,
                    assets=getattr(item, "assets", []),
                )

                # Update job manager for this completed slide
                async def update_job():
                    await job_manager.finish_page(lecture_id)

                asyncio.run(update_job())

                return slide_content

            future = executor.submit(
                generate_item,
                item.content,
                item.layout,
                i + 1,
                request_slide_generation_request.course_id,
                request_slide_generation_request.lecture_id,
            )
            slide_futures.append(future)

        # Submit a final task to collect all results and save to file
        def finalize_slides(futures, lecture_id):
            slide_contents = []
            for future in futures:
                slide_content = future.result()
                slide_contents.append(slide_content)

            # Save all slides to markdown file
            save_slides_to_file(lecture_id, slide_contents)

        executor.submit(finalize_slides, slide_futures, request_slide_generation_request.lecture_id)

        status = await job_manager.get_status(request_slide_generation_request.lecture_id)
        return GenerationAcceptedResponse(
            lectureId=request_slide_generation_request.lecture_id,
            status="IN_PROGRESS" if status and status.achieved < status.total else "DONE",
            createdAt=datetime.now(),
            structure=structure.as_simple_slide_structure(),
        )
