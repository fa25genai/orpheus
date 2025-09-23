# coding: utf-8

from typing import Dict, List  # noqa: F401
import importlib
import pkgutil

from docint_app.apis.docint_api_base import BaseDocintApi
import docint_app.impl

from fastapi import (  # noqa: F401
    APIRouter,
    Body,
    Cookie,
    Depends,
    Form,
    Header,
    HTTPException,
    Path,
    Query,
    Response,
    Security,
    status,
)

from docint_app.models.extra_models import TokenModel  # noqa: F401
from pydantic import Field, StrictBytes, StrictStr
from typing import Any, Tuple, Union
from typing_extensions import Annotated
from docint_app.models.retrieval_response import RetrievalResponse
from docint_app.models.upload_response import UploadResponse


router = APIRouter()

ns_pkg = docint_app.impl
for _, name, _ in pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + "."):
    importlib.import_module(name)


@router.delete(
    "/v1/delete/{documentId}",
    responses={
        200: {"description": "Successful deletion."},
        400: {"description": "Bad Request – missing file or parameters."},
        404: {"description": "Not Found – resource not found."},
    },
    tags=["docint"],
    summary="Deletes a document",
    response_model_by_alias=True,
)
async def deletes_document(
    documentId: Annotated[StrictStr, Field(description="The document ID.")] = Path(..., description="The document ID."),
) -> None:
    if not BaseDocintApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseDocintApi.subclasses[0]().deletes_document(documentId)


@router.get(
    "/v1/retrieval/{courseId}",
    responses={
        200: {"model": RetrievalResponse, "description": "Content and images."},
        400: {"description": "Bad Request – missing file or parameters."},
        404: {"description": "Not Found – resource not found."},
    },
    tags=["docint"],
    summary="Provides relevant textual content and images",
    response_model_by_alias=True,
)
async def retrieves_data_for_generation(
    courseId: Annotated[StrictStr, Field(description="The course ID.")] = Path(..., description="The course ID."),
    prompt_query: Annotated[StrictStr, Field(description="The user's query or prompt.")] = Query(None, description="The user&#39;s query or prompt.", alias="promptQuery"),
) -> RetrievalResponse:
    if not BaseDocintApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseDocintApi.subclasses[0]().retrieves_data_for_generation(courseId, prompt_query)


@router.post(
    "/v1/upload/{courseId}",
    responses={
        201: {"model": UploadResponse, "description": "Successfully uploaded. Returns created ID."},
        400: {"description": "Bad Request – missing file or parameters."},
        404: {"description": "Not Found – resource not found."},
        413: {"description": "Payload Too Large."},
        415: {"description": "Unsupported Media Type (only PDFs accepted)."},
    },
    tags=["docint"],
    summary="uploads a PDF document",
    response_model_by_alias=True,
)
async def uploads_document(
    courseId: Annotated[StrictStr, Field(description="The course ID.")] = Path(..., description="The course ID."),
    body: Union[StrictBytes, StrictStr, Tuple[StrictStr, StrictBytes]] = Body(None, description=""),
) -> UploadResponse:
    if not BaseDocintApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseDocintApi.subclasses[0]().uploads_document(courseId, body)
