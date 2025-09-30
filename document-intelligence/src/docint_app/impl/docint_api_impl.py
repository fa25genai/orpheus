import asyncio
import logging
import os
from typing import Dict, Tuple, Union

from pydantic import Field, StrictBytes, StrictStr
from typing_extensions import Annotated

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
        # Check environment variable for debug mode override
        env_debug = os.getenv("ORPHEUS_DEBUG_MODE", "false").lower() == "true"
        # Use environment variable as default, but allow API parameter to override
        
        print(f"Retrieving data for course {courseId} with query {prompt_query}; debug={env_debug}")

        if not env_debug:
            service = get_retrieval_service()
            result = await service.search_simple(prompt_query, courseId)
        else:
            # Return predefined debug response for testing pipeline
            result = {
                "content": [
                    "For Loops let you repeat a block of code a fixed number of times.",
                    "A standard for loop has three parts inside the parentheses:",
                    "(1) initialisation – set the starting value (e.g. int i = 0),",
                    "(2) condition – checked before each iteration (loop runs while condition is true),",
                    "(3) update – changes the loop variable after each iteration (e.g. i++).",

                    "Example:",
                    "for (int i = 0; i < abc.length; i++) {",
                    " System.out.println(abc[i]);",
                    "}",

                    "The loop prints each element of the array one by one.",

                    "A for-each loop is a special form that iterates directly over all elements without an index:",
                    "for (String letter : abc) {",
                    " System.out.println(letter);",
                    "}",

                    "Use a for-each loop when you don’t need the index.",
                    "Use a regular for loop when you need to control the counter or skip elements.",
                ],
                "images": []
            }

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
        tasks = [self.retrieves_data_for_generation(courseId, prompt_query) for prompt_query in batch_retrieval_request.prompt_queries]

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
