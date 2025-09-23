# coding: utf-8

from typing import ClassVar, Dict, List, Tuple  # noqa: F401

from pydantic import Field
from typing_extensions import Annotated
from uuid import UUID
from openapi_server.models.data_response import DataResponse
from openapi_server.models.error import Error
from openapi_server.models.prompt_request import PromptRequest
from openapi_server.models.prompt_response import PromptResponse


class BaseCoreApi:
    subclasses: ClassVar[Tuple] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        BaseCoreApi.subclasses = BaseCoreApi.subclasses + (cls,)
    async def create_lecture_from_prompt(
        self,
        prompt_request: Annotated[PromptRequest, Field(description="The user prompt to generate content from.")],
    ) -> PromptResponse:
        """Accepts a user prompt and initiates an asynchronous job to generate lecture content. Returns a unique lecture ID to track the job."""
        ...


    async def get_slides_by_lecture_id(
        self,
        lectureId: Annotated[UUID, Field(description="The unique identifier for the lecture generation job.")],
    ) -> DataResponse:
        """Retrieves the status or result of a slide generation job using the lecture ID."""
        ...


    async def get_video_by_lecture_id(
        self,
        lectureId: Annotated[UUID, Field(description="The unique identifier for the lecture generation job.")],
    ) -> DataResponse:
        """Retrieves the status or result of a video generation job using the lecture ID."""
        ...
