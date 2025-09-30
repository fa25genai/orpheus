import asyncio
from typing import Tuple, Union

from pydantic import Field, StrictBytes, StrictStr
from typing_extensions import Annotated

import logging

from docint_app.apis.docint_api_base import BaseDocintApi
from docint_app.models.batch_retrieval_request import BatchRetrievalRequest
from docint_app.models.batch_retrieval_response import BatchRetrievalResponse
from docint_app.models.retrieval_response import RetrievalResponse
from docint_app.models.upload_response import UploadResponse
from docint_app.models.video_upload_response import VideoUploadResponse
from docint_app.services.mock_video_upload_service import get_video_upload_service
from docint_app.services.pdf_upload_service import get_upload_pdf_service
from docint_app.services.retrieval_service import get_retrieval_service

logger = logging.getLogger("Document Intelligence Request Handler")

class DocintApiImpl(BaseDocintApi):  # type: ignore[no-untyped-call]
    async def retrieves_data_for_generation(
        self,
        courseId: Annotated[StrictStr, Field(description="The course ID.")],
        prompt_query: Annotated[StrictStr, Field(description="The user's query or prompt.")],
    ) -> RetrievalResponse:

        logger.debug(f"Retrieving data for course {courseId} with query {prompt_query}")

        service = get_retrieval_service()
        result = await service.search_simple(prompt_query, courseId)

        logger.debug(f"Retrieved data for course {courseId} with query {prompt_query}: {result}")

        return RetrievalResponse.from_dict(result)

    async def uploads_document(
        self,
        courseId: Annotated[StrictStr, Field(description="The course ID.")],
        body: Union[StrictBytes, StrictStr, Tuple[StrictStr, StrictBytes]],
    ) -> UploadResponse:
        service = get_upload_pdf_service()

        document_id = await service.upload_pdf(courseId, body)
        return UploadResponse(documentId=document_id)
    
    async def retrieves_batch_data_for_generation(
        self,
        courseId: Annotated[StrictStr, Field(description="The course ID.")],
        batch_retrieval_request: BatchRetrievalRequest,
    ) -> BatchRetrievalResponse:
        # Process all queries in parallel
        tasks = [
            self.retrieves_data_for_generation(courseId, prompt_query)
            for prompt_query in batch_retrieval_request.prompt_queries
        ]
        
        results = await asyncio.gather(*tasks)
        
        return BatchRetrievalResponse(results=results)
    
    async def uploads_video(
        self,
        courseId: Annotated[StrictStr, Field(description="The course ID.")],
        body: Union[StrictBytes, StrictStr, Tuple[StrictStr, StrictBytes]],
    ) -> VideoUploadResponse:
        service = get_video_upload_service()
        
        video_id = await service.upload_video(courseId, body)
        return VideoUploadResponse(videoId=video_id)
