import asyncio
from concurrent.futures.thread import ThreadPoolExecutor
from datetime import datetime
from logging import getLogger
from typing import Any, List

from fastapi import HTTPException
from langchain_core.language_models import BaseLanguageModel
from pydantic import StrictStr, Field
from typing_extensions import Annotated

from service_slides.apis.slides_api_base import BaseSlidesApi
from service_slides.clients.configurations import get_postprocessing_api_config
from service_slides.clients.postprocessing import ApiClient, ApiException, SlidesetWithIdAssetsInner
from service_slides.clients.postprocessing.api.postprocessing_api import PostprocessingApi
from service_slides.clients.postprocessing.models.slideset_with_id import SlidesetWithId
from service_slides.clients.postprocessing.models.store_slideset_request import StoreSlidesetRequest
from service_slides.impl.llm_chain.slide_content import generate_single_slide_content
from service_slides.impl.llm_chain.slide_structure import generate_slide_structure
from service_slides.impl.manager.job_manager import JobManager, JobStatus
from service_slides.impl.manager.layout_manager import LayoutManager
from service_slides.models.generation_accepted_response import GenerationAcceptedResponse
from service_slides.models.generation_status_response import GenerationStatusResponse
from service_slides.models.request_slide_generation_request import RequestSlideGenerationRequest

_log = getLogger("slides_impl")


class SlidesApiImpl(BaseSlidesApi):
    def __init_subclass__(cls: Any, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)

    async def get_generation_status(
        self,
        promptId: Annotated[
            StrictStr, Field(description="The promptId returned by /v1/slides/generate")
        ],
        job_manager: JobManager,
    ) -> GenerationStatusResponse:
        status = await job_manager.get_status(promptId)
        if status is None:
            try:
                async with ApiClient(get_postprocessing_api_config()) as api_client:
                    postprocessing_api = PostprocessingApi(api_client)
                    resp = await postprocessing_api.get_slideset(promptId)
                    return GenerationStatusResponse(
                        promptId=promptId,
                        status="DONE",
                        totalPages=0,
                        generatedPages=0,
                        lastUpdated=datetime.now(),
                        webUrl=resp.web_url,
                        pdfUrl=resp.pdf_url,
                    )
            except ApiException as ex:
                if ex.status == 404:
                    raise HTTPException(404, detail="Slideset not found")
                _log.warning(
                    "Failed to get generation status for %s. Error %d: %s",
                    promptId,
                    ex.status,
                    ex.reason,
                )
                raise HTTPException(500, detail="Slideset API call failed") from ex
            except Exception as e:
                _log.error(
                    "Error when calling the postprocessing API for request %s",
                    promptId,
                    exc_info=e,
                )
                raise HTTPException(500, detail="Slideset API call failed") from e
        return GenerationStatusResponse(
            promptId=promptId,
            status=status.get_status_text(),
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
        _log.info(
            "Starting slide generation request %s", request_slide_generation_request.prompt_id
        )
        # 1. Generate the slide structure
        structure = await generate_slide_structure(
            model=splitting_model,
            lecture_script=request_slide_generation_request.lecture_script,
            available_layouts=await layout_manager.get_available_layouts(
                request_slide_generation_request.course_id
            ),
        )
        _log.debug("Structure generated for request %s", request_slide_generation_request.prompt_id)

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
                _log.debug(
                    "Slide number %d generated for request %s",
                    slide_num,
                    request_slide_generation_request.prompt_id,
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

            asyncio.run(
                store_upload_info(
                    job_manager,
                    prompt_id,
                    "\n".join(slide_contents),
                    list(map(
                        lambda asset: SlidesetWithIdAssetsInner(
                            path=f"assets/{asset.name}",
                            data=asset.data,
                        ),
                        request_slide_generation_request.assets,
                    )),
                )
            )

        executor.submit(finalize_slides, slide_futures, request_slide_generation_request.prompt_id)

        status = await job_manager.get_status(request_slide_generation_request.prompt_id)
        if status is None:
            status = JobStatus(error=True)
        return GenerationAcceptedResponse(
            promptId=request_slide_generation_request.prompt_id,
            status=status.get_status_text(),
            createdAt=datetime.now(),
            structure=structure.as_simple_slide_structure(),
        )


async def store_upload_info(
    job_manager: JobManager, prompt_id: str, content: str, assets: List[SlidesetWithIdAssetsInner]
) -> None:
    # Save all slides to markdown file
    async with ApiClient(get_postprocessing_api_config()) as api_client:
        postprocessor = PostprocessingApi(api_client)
        try:
            response = await postprocessor.store_slideset(
                StoreSlidesetRequest(
                    theme="tum",
                    slideset=SlidesetWithId(
                        promptId=prompt_id,
                        slideset=content,
                        assets=assets,
                    ),
                )
            )
        except ApiException as ex:
            _log.error(
                "Error when calling the postprocessing API for request %s: %d %s",
                prompt_id,
                ex.status,
                ex.reason,
            )
            await job_manager.fail(prompt_id)
        except Exception as e:
            _log.error(
                "Error when calling the postprocessing API for request %s", prompt_id, exc_info=e
            )
            await job_manager.fail(prompt_id)
        await job_manager.finish_upload(prompt_id, response.web_url, response.pdf_url)
