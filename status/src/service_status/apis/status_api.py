# coding: utf-8

from typing import Dict, List  # noqa: F401
import importlib
import pkgutil
import uuid

from starlette.websockets import WebSocket, WebSocketDisconnect

from service_status.apis.status_api_base import BaseStatusApi
import service_status.impl

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
    Request,
    Response,
    Security,
    status,
)

from service_status.models.extra_models import TokenModel  # noqa: F401
from pydantic import Field, StrictStr
from typing import Any
from typing_extensions import Annotated
from service_status.models.error import Error
from service_status.models.status import Status
from service_status.models.status_patch import StatusPatch

router = APIRouter()

ns_pkg = service_status.impl
for _, name, _ in pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + "."):
    importlib.import_module(name)


@router.get(
    "/status/{promptId}",
    responses={
        200: {"model": Status, "description": "The current status of the request."},
    },
    tags=["status"],
    summary="Get the current status for a generation job",
    response_model_by_alias=True,
)
async def get_status(
    request: Request,
    promptId: Annotated[StrictStr, Field(description="The promptId of the generation job")] = Path(
        ..., description="The promptId of the generation job"
    ),
) -> Status:
    """Returns the current status of a generation job. If a job is unknown, then the initial status is returned. The current value is also subscribable by opening a websocket to &#x60;/status/{promptId}/live&#x60;. There the status object is pushed as it is described by this endpoint whenever it is updated."""
    if not BaseStatusApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseStatusApi.subclasses[0]().get_status(
        request.app.state.status_manager, promptId
    )


@router.patch(
    "/status/{promptId}/update",
    responses={
        203: {"description": "The status update has been applied."},
        400: {"model": Error, "description": "Bad Request. The request body is invalid."},
    },
    tags=["status"],
    summary="Updates the status for a generation job",
    response_model_by_alias=True,
)
async def update_status(
    request: Request,
    promptId: Annotated[StrictStr, Field(description="The promptId of the generation job")] = Path(
        ..., description="The promptId of the generation job"
    ),
    status_patch: Annotated[
        StatusPatch, Field(description="The changes to apply to the status.")
    ] = Body(None, description="The changes to apply to the status."),
) -> None:
    """Takes a status update and applies it to the current status. If a status is unknown, it creates a new object for it."""
    if not BaseStatusApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseStatusApi.subclasses[0]().update_status(
        request.app.state.status_manager, promptId, status_patch
    )


@router.websocket("/status/{promptId}/live")
async def websocket_status(
    websocket: WebSocket,
    promptId: Annotated[
        StrictStr,
        Field(description="The promptId of the generation job"),
    ] = Path(..., description="The promptId of the generation job"),
) -> None:
    await websocket.accept()
    id = uuid.uuid4()
    status_manager = websocket.app.state.status_manager

    async def send_status_update(status: Status):
        try:
            await websocket.send_text(status.model_dump_json())
        except WebSocketDisconnect:
            status_manager.remove_listener(promptId, id)

    await status_manager.add_listener(promptId, id, send_status_update)

    try:
        while True:
            await websocket.receive()
    except WebSocketDisconnect:
        status_manager.remove_listener(promptId, id)
