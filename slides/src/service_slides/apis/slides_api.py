# coding: utf-8
import importlib
import pkgutil

from fastapi import (  # noqa: F401
    APIRouter,
    Body,
    HTTPException,
    Path,
    Request,
)
from pydantic import Field, StrictStr
from typing_extensions import Annotated

import service_slides.impl
from service_slides.apis.slides_api_base import BaseSlidesApi
from service_slides.models.error import Error
from service_slides.models.generation_accepted_response import GenerationAcceptedResponse
from service_slides.models.generation_status_response import GenerationStatusResponse
from service_slides.models.request_slide_generation_request import RequestSlideGenerationRequest

router = APIRouter()

ns_pkg = service_slides.impl
for _, name, _ in pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + "."):  # type: ignore
    importlib.import_module(name)


@router.get(
    "/v1/slides/{promptId}/status",
    responses={
        200: {"model": GenerationStatusResponse, "description": "Status of the generation job"},
        404: {"model": Error, "description": "Request not found"},
    },
    tags=["slides"],
    summary="Get generation status for a previously-submitted request",
    response_model_by_alias=True,
)
async def get_generation_status(
    http_request: Request,
    promptId: Annotated[StrictStr, Field(description="The promptId returned by /v1/slides/generate")] = Path(..., description="The promptId returned by /v1/slides/generate"),
) -> GenerationStatusResponse:
    if not BaseSlidesApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    result = await BaseSlidesApi.subclasses[0]().get_generation_status(promptId, http_request.app.state.job_manager)
    return result  # type: ignore


@router.post(
    "/v1/slides/generate",
    responses={
        202: {
            "model": GenerationAcceptedResponse,
            "description": "Request accepted — generation started. Returns request metadata and immediate structure summary.",
        },
        400: {
            "model": Error,
            "description": "Malformed request (missing concept, invalid files, etc.)",
        },
        401: {"description": "Unauthorized"},
        500: {"description": "Server error"},
    },
    tags=["slides"],
    summary="Request generation of a slide deck (async — returns early)",
    response_model_by_alias=True,
)
async def request_slide_generation(
    http_request: Request,
    request_slide_generation_request: RequestSlideGenerationRequest = Body(None, description=""),
) -> GenerationAcceptedResponse:
    """Accepts a concept and supporting assets (images, graphs, tables, code listings, equations). The request returns immediately with a request_id and status (typically IN_PROGRESS). Final slide deck (PDF) is produced asynchronously; the client can poll the status endpoint and fetch the resulting deck when complete."""
    if not BaseSlidesApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    result = await BaseSlidesApi.subclasses[0]().request_slide_generation(
        request_slide_generation_request,
        http_request.app.state.executor,
        http_request.app.state.job_manager,
        http_request.app.state.layout_manager,
        http_request.app.state.splitting_model,
        http_request.app.state.slidesgen_model,
    )
    return result  # type: ignore
