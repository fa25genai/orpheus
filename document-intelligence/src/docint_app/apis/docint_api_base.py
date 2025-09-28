# coding: utf-8

from typing import ClassVar, Dict, List, Tuple  # noqa: F401

from pydantic import Field, StrictBytes, StrictStr
from typing import Any, Tuple, Union
from typing_extensions import Annotated
from docint_app.models.batch_retrieval_request import BatchRetrievalRequest
from docint_app.models.batch_retrieval_response import BatchRetrievalResponse
from docint_app.models.retrieval_response import RetrievalResponse
from docint_app.models.upload_response import UploadResponse
from docint_app.models.video_upload_response import VideoUploadResponse


class BaseDocintApi:
    subclasses: ClassVar[Tuple] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        BaseDocintApi.subclasses = BaseDocintApi.subclasses + (cls,)
    async def deletes_document(
        self,
        documentId: Annotated[StrictStr, Field(description="The document ID.")],
    ) -> None:
        ...


    async def retrieves_batch_data_for_generation(
        self,
        courseId: Annotated[StrictStr, Field(description="The course ID.")],
        batch_retrieval_request: BatchRetrievalRequest,
    ) -> BatchRetrievalResponse:
        ...


    async def retrieves_data_for_generation(
        self,
        courseId: Annotated[StrictStr, Field(description="The course ID.")],
        prompt_query: Annotated[StrictStr, Field(description="The user's query or prompt.")],
    ) -> RetrievalResponse:
        ...


    async def uploads_document(
        self,
        courseId: Annotated[StrictStr, Field(description="The course ID.")],
        body: Union[StrictBytes, StrictStr, Tuple[StrictStr, StrictBytes]],
    ) -> UploadResponse:
        ...


    async def uploads_video(
        self,
        courseId: Annotated[StrictStr, Field(description="The course ID.")],
        body: Union[StrictBytes, StrictStr, Tuple[StrictStr, StrictBytes]],
    ) -> VideoUploadResponse:
        ...
