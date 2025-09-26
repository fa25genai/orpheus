# coding: utf-8

from typing import ClassVar, Dict, List, Tuple  # noqa: F401

from pydantic import Field
from typing_extensions import Annotated

from service_core.models.prompt_request import PromptRequest
from service_core.models.prompt_response import PromptResponse


class BaseCoreApi:
    subclasses: ClassVar[Tuple] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        BaseCoreApi.subclasses = BaseCoreApi.subclasses + (cls,)
    async def create_lecture_from_prompt(
        self,
        prompt_request: Annotated[PromptRequest, Field(description="The user prompt to generate content from.")],
    ) -> PromptResponse:
        """Accepts a user prompt and initiates an asynchronous job to generate lecture content. Returns a unique prompt ID to track the job."""
        ...
