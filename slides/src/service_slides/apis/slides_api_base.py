# coding: utf-8

from typing import ClassVar, Dict, List, Tuple  # noqa: F401

from pydantic import Field, StrictStr
from typing_extensions import Annotated
from service_slides.models.generation_accepted_response import GenerationAcceptedResponse
from service_slides.models.generation_status_response import GenerationStatusResponse
from service_slides.models.request_slide_generation_request import RequestSlideGenerationRequest


class BaseSlidesApi:
    subclasses: ClassVar[Tuple] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        BaseSlidesApi.subclasses = BaseSlidesApi.subclasses + (cls,)
    async def get_generation_status(
        self,
        lectureId: Annotated[StrictStr, Field(description="The lectureId returned by /v1/slides/generate")],
    ) -> GenerationStatusResponse:
        ...


    async def request_slide_generation(
        self,
        request_slide_generation_request: RequestSlideGenerationRequest,
    ) -> GenerationAcceptedResponse:
        """Accepts a concept and supporting assets (images, graphs, tables, code listings, equations). The request returns immediately with a request_id and status (typically IN_PROGRESS). Final slide deck (PDF) is produced asynchronously; the client can poll the status endpoint and fetch the resulting deck when complete. """
        ...
