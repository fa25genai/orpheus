# coding: utf-8

from typing import ClassVar, Tuple  # noqa: F401

from pydantic import Field, StrictBytes, StrictStr
from typing import Tuple, Union
from typing_extensions import Annotated
from docint_app.models.retrieval_response import RetrievalResponse
from docint_app.models.upload_response import UploadResponse


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
