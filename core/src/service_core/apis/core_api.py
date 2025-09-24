# coding: utf-8

from typing import Dict, List  # noqa: F401
import importlib
import pkgutil

from service_core.apis.core_api_base import BaseCoreApi
import service_core.impl

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

from service_core.models.extra_models import TokenModel  # noqa: F401
from pydantic import Field
from typing_extensions import Annotated
from service_core.models.error import Error
from service_core.models.prompt_request import PromptRequest
from service_core.models.prompt_response import PromptResponse


router = APIRouter()

ns_pkg = service_core.impl
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
    """Accepts a user prompt and initiates an asynchronous job to generate lecture content. Returns a unique prompt ID to track the job."""
    if not BaseCoreApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseCoreApi.subclasses[0]().create_lecture_from_prompt(prompt_request)
