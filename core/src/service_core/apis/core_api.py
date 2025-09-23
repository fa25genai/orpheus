# coding: utf-8

from typing import Dict, List  # noqa: F401
import importlib
import pkgutil

from openapi_server.apis.core_api_base import BaseCoreApi
import openapi_server.impl

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

from openapi_server.models.extra_models import TokenModel  # noqa: F401
from pydantic import Field
from typing_extensions import Annotated
from uuid import UUID
from openapi_server.models.data_response import DataResponse
from openapi_server.models.error import Error
from openapi_server.models.prompt_request import PromptRequest
from openapi_server.models.prompt_response import PromptResponse


router = APIRouter()

ns_pkg = openapi_server.impl
for _, name, _ in pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + "."):
    importlib.import_module(name)


@router.post(
    "/core/prompt",
    responses={
        202: {"model": PromptResponse, "description": "Accepted. The generation job has been successfully created."},
        400: {"model": Error, "description": "Bad Request. The request body is invalid."},
    },
    tags=["core"],
    summary="Submit a prompt to generate a lecture",
    response_model_by_alias=True,
)
async def create_lecture_from_prompt(
    prompt_request: Annotated[PromptRequest, Field(description="The user prompt to generate content from.")] = Body(None, description="The user prompt to generate content from."),
) -> PromptResponse:
    """Accepts a user prompt and initiates an asynchronous job to generate lecture content. Returns a unique lecture ID to track the job."""
    if not BaseCoreApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseCoreApi.subclasses[0]().create_lecture_from_prompt(prompt_request)


@router.get(
    "/core/getSlides/{lectureId}",
    responses={
        200: {"model": DataResponse, "description": "Success. Returns the status and URL of the generated slides."},
        404: {"model": Error, "description": "Not Found. No lecture job found with the provided ID."},
    },
    tags=["core"],
    summary="Get the generated slides",
    response_model_by_alias=True,
)
async def get_slides_by_lecture_id(
    lectureId: Annotated[UUID, Field(description="The unique identifier for the lecture generation job.")] = Path(..., description="The unique identifier for the lecture generation job."),
) -> DataResponse:
    """Retrieves the status or result of a slide generation job using the lecture ID."""
    if not BaseCoreApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseCoreApi.subclasses[0]().get_slides_by_lecture_id(lectureId)


@router.get(
    "/core/getVideo/{lectureId}",
    responses={
        200: {"model": DataResponse, "description": "Success. Returns the status and URL of the generated video."},
        404: {"model": Error, "description": "Not Found. No lecture job found with the provided ID."},
    },
    tags=["core"],
    summary="Get the generated video",
    response_model_by_alias=True,
)
async def get_video_by_lecture_id(
    lectureId: Annotated[UUID, Field(description="The unique identifier for the lecture generation job.")] = Path(..., description="The unique identifier for the lecture generation job."),
) -> DataResponse:
    """Retrieves the status or result of a video generation job using the lecture ID."""
    if not BaseCoreApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseCoreApi.subclasses[0]().get_video_by_lecture_id(lectureId)
