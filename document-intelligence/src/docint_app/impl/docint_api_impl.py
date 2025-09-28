from typing import Tuple, Union

from pydantic import Field, StrictBytes, StrictStr
from typing_extensions import Annotated

from docint_app.apis.docint_api_base import BaseDocintApi
from docint_app.models.retrieval_response import RetrievalResponse
from docint_app.models.upload_response import UploadResponse
from docint_app.services.pdf_upload_service import get_upload_pdf_service
from docint_app.services.retrieval_service import get_retrieval_service


class DocintApiImpl(BaseDocintApi):  # type: ignore[no-untyped-call]
    async def retrieves_data_for_generation(
        self,
        courseId: Annotated[StrictStr, Field(description="The course ID.")],
        prompt_query: Annotated[StrictStr, Field(description="The user's query or prompt.")],
    ) -> RetrievalResponse:
        service = get_retrieval_service()
        result = await service.search_simple(prompt_query, courseId)
        return RetrievalResponse.from_dict(result)

    async def uploads_document(
        self,
        courseId: Annotated[StrictStr, Field(description="The course ID.")],
        body: Union[StrictBytes, StrictStr, Tuple[StrictStr, StrictBytes]],
    ) -> UploadResponse:
        service = get_upload_pdf_service()

        document_id = await service.upload_pdf(courseId, body)
        return UploadResponse(documentId=document_id)
