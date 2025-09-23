from typing import ClassVar, Dict, List, Tuple  # noqa: F401

from pydantic import Field, StrictBytes, StrictStr
from typing import Any, Tuple, Union
from typing_extensions import Annotated
from docint_app.apis.docint_api_base import BaseDocintApi
from docint_app.models.retrieval_response import RetrievalResponse
from docint_app.services.retrieve_data_for_generation_service import RetrievalService, get_retrieval_service


class DocintApiImpl(BaseDocintApi):
    
    async def retrieves_data_for_generation(
        self,
        courseId: Annotated[StrictStr, Field(description="The course ID.")],
        prompt_query: Annotated[StrictStr, Field(description="The user's query or prompt.")],
    ) -> RetrievalResponse:
        service = get_retrieval_service()

        return await service.get_content(courseId, prompt_query)