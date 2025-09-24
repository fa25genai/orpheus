import asyncio
from datetime import datetime

from concurrent.futures.thread import ThreadPoolExecutor
from typing import Any

from fastapi import HTTPException
from langchain_core.language_models import BaseLanguageModel
from pydantic import StrictStr, Field

from service_slides.clients.configurations import get_postprocessing_api_config
from service_slides.clients.postprocessing import ApiClient
from service_slides.clients.postprocessing.api.postprocessing_api import PostprocessingApi
from service_slides.clients.postprocessing.models.error import Error
from service_slides.clients.postprocessing.models.slideset_with_id import SlidesetWithId
from service_slides.clients.postprocessing.models.store_slideset_request import StoreSlidesetRequest
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
    def __init_subclass__(cls: Any, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)

    async def get_content_url(self, promptId: Annotated[StrictStr, Field(description="The promptId returned by /v1/slides/generate")],
                              job_manager: JobManager) -> GenerationStatusResponse:
        raise HTTPException(status_code=500, detail="Not yet implemented")

    async def get_generation_status(
            self,
            promptId: Annotated[
                StrictStr, Field(description="The promptId returned by /v1/slides/generate")
            ],
            job_manager: JobManager,
    ) -> GenerationStatusResponse:
        status = await job_manager.get_status(promptId)
        if status is None:
            async with ApiClient(get_postprocessing_api_config()) as api_client:
                postprocessing_api = PostprocessingApi(api_client)
                resp = await postprocessing_api.get_slideset(promptId)
                if resp is Error:
                    raise HTTPException(status_code=404, detail="Slideset not found")
                return GenerationStatusResponse(
                    promptId=promptId,
                    status="DONE",
                    totalPages=0,
                    generatedPages=0,
                    lastUpdated=datetime.now(),
                    webUrl=resp.webUrl,
                    pdfUrl=resp.pdfUrl,
                )
        return GenerationStatusResponse(
            promptId=promptId,
            status="IN_PROGRESS" if (status.achieved < status.total or not status.uploaded) else "DONE",
            totalPages=status.total,
            generatedPages=status.achieved,
            lastUpdated=status.updated_at,
            webUrl=status.web_url,
            pdfUrl=status.pdf_url,
        )

    async def request_slide_generation(
            self,
            request_slide_generation_request: RequestSlideGenerationRequest,
            executor: ThreadPoolExecutor,
            job_manager: JobManager,
            layout_manager: LayoutManager,
            splitting_model: BaseLanguageModel[Any],
            slidesgen_model: BaseLanguageModel[Any],
    ) -> GenerationAcceptedResponse:
        # 1. Generate the slide structure
        structure = await generate_slide_structure(
            model=splitting_model,
            lecture_script=request_slide_generation_request.lecture_script,
            available_layouts=await layout_manager.get_available_layouts(
                request_slide_generation_request.course_id
            )
        )

        # 2. Initialize job for tracking progress
        await job_manager.init_job(request_slide_generation_request.prompt_id, len(structure.items))

        # 3. Start background slide generation (don't wait for completion)
        # Submit individual slide generation tasks directly to the executor
        slide_futures = []
        for i, item in enumerate(structure.items):
            def generate_item(
                    item_content: str, item_layout: str, slide_num: int, course_id: str, prompt_id: str
            ) -> str:
                import asyncio

                # Get layout template synchronously within the executor
                async def get_template() -> Any:
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
                async def update_job() -> None:
                    await job_manager.finish_page(prompt_id)

                asyncio.run(update_job())

                return str(slide_content)

            future = executor.submit(
                generate_item,
                item.content,
                item.layout,
                i + 1,
                request_slide_generation_request.course_id,
                request_slide_generation_request.prompt_id,
            )
            slide_futures.append(future)

        # Submit a final task to collect all results and save to file
        def finalize_slides(futures: Any, prompt_id: str) -> None:
            slide_contents = []
            for future in futures:
                slide_content = future.result()
                slide_contents.append(slide_content)

            async def store_upload_info():
                # Save all slides to markdown file
                async with ApiClient(get_postprocessing_api_config()) as api_client:
                    postprocessor = PostprocessingApi(api_client)
                    response = await postprocessor.store_slideset(
                        StoreSlidesetRequest(
                            slideset=SlidesetWithId(
                                promptId=prompt_id,
                                slideset=slide_contents,
                                assets=[]  # TODO: Add assets if necessary
                            )
                        )
                    )

                await job_manager.finish_upload(prompt_id, response.web_url, response.pdf_url)

            asyncio.run(store_upload_info())

        executor.submit(finalize_slides, slide_futures, request_slide_generation_request.prompt_id)

        status = await job_manager.get_status(request_slide_generation_request.prompt_id)
        return GenerationAcceptedResponse(
            promptId=request_slide_generation_request.prompt_id,
            status="IN_PROGRESS" if status and status.achieved < status.total else "DONE",
            createdAt=datetime.now(),
            structure=structure.as_simple_slide_structure(),
        )
