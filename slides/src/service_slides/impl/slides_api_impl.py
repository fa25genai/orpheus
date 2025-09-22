from fastapi import HTTPException
from pydantic import StrictStr, Field
from typing_extensions import Annotated

from service_slides.apis.slides_api_base import BaseSlidesApi
from service_slides.models.generation_accepted_response import GenerationAcceptedResponse
from service_slides.models.generation_status_response import GenerationStatusResponse
from service_slides.models.request_slide_generation_request import RequestSlideGenerationRequest


class SlidesApiImpl(BaseSlidesApi):
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

    async def get_generation_status(self, lectureId: Annotated[
        StrictStr, Field(description="The lectureId returned by /v1/slides/generate")]) -> GenerationStatusResponse:
        raise HTTPException(status_code=500, detail="Not implemented")

    async def request_slide_generation(self, request_slide_generation_request: RequestSlideGenerationRequest) -> GenerationAcceptedResponse:
        raise HTTPException(status_code=500, detail="Not implemented")