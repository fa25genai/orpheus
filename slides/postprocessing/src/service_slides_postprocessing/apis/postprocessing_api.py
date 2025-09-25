# coding: utf-8

from typing import Dict, List  # noqa: F401
import importlib
import pkgutil

from service_slides_postprocessing.apis.postprocessing_api_base import BasePostprocessingApi
import service_slides_postprocessing.impl

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

from service_slides_postprocessing.models.extra_models import TokenModel  # noqa: F401
from pydantic import Field, StrictStr
from typing_extensions import Annotated
from service_slides_postprocessing.models.error import Error
from service_slides_postprocessing.models.list_slidesets200_response_inner import (
    ListSlidesets200ResponseInner,
)
from service_slides_postprocessing.models.get_slideset200_response import (
    GetSlideset200Response,
)
from service_slides_postprocessing.models.store_slideset_request import StoreSlidesetRequest
from service_slides_postprocessing.models.slideset_with_id import SlidesetWithId
from service_slides_postprocessing.models.upload_accepted_response import UploadAcceptedResponse


router = APIRouter()

ns_pkg = service_slides_postprocessing.impl
for _, name, _ in pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + "."):
    importlib.import_module(name)


@router.get(
    "/v1/postprocessing/{promptId}",
    responses={
        200: {"model": SlidesetWithId, "description": "Slideset available and known."},
        404: {"model": Error, "description": "Request not found"},
    },
    tags=["postprocessing"],
    summary="Get the markdown content of a previously stored slideset",
    response_model_by_alias=True,
)
async def get_slideset(
    promptId: Annotated[
        StrictStr, Field(description="The promptId for the requested slideset")
    ] = Path(..., description="The promptId for the requested slideset"),
) -> GetSlideset200Response:
    """Returns a slideset in markdown format"""
    if not BasePostprocessingApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BasePostprocessingApi.subclasses[0]().get_slideset(promptId)


@router.get(
    "/v1/postprocessing",
    responses={
        200: {
            "model": List[ListSlidesets200ResponseInner],
            "description": "List of available slidesets",
        },
    },
    tags=["postprocessing"],
    summary="Get the list of all previously stored slideset IDs",
    response_model_by_alias=True,
)
async def list_slidesets() -> List[ListSlidesets200ResponseInner]:
    if not BasePostprocessingApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BasePostprocessingApi.subclasses[0]().list_slidesets()


@router.put(
    "/v1/postprocessing",
    responses={
        200: {
            "model": UploadAcceptedResponse,
            "description": "Slideset accepted and postprocessing complete.",
        },
        400: {"model": Error, "description": "Malformed request"},
        500: {"description": "Server error"},
    },
    tags=["postprocessing"],
    summary="Store a slideset and perform postprocessing on the file",
    response_model_by_alias=True,
)
async def store_slideset(
    store_slideset_request: StoreSlidesetRequest = Body(None, description=""),
) -> UploadAcceptedResponse:
    """Accepts a slideset in markdown format"""
    if not BasePostprocessingApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BasePostprocessingApi.subclasses[0]().store_slideset(store_slideset_request)
