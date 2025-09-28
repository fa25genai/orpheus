# coding: utf-8

from typing import ClassVar, Dict, List, Tuple  # noqa: F401

from pydantic import Field, StrictStr
from typing import Any
from typing_extensions import Annotated

from service_status.impl.manager.status_manager import StatusManager
from service_status.models.error import Error
from service_status.models.status import Status
from service_status.models.status_patch import StatusPatch


class BaseStatusApi:
    subclasses: ClassVar[Tuple] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        BaseStatusApi.subclasses = BaseStatusApi.subclasses + (cls,)

    async def get_status(
        self,
        status_manager: StatusManager,
        promptId: Annotated[StrictStr, Field(description="The promptId of the generation job")],
    ) -> Status:
        """Returns the current status of a generation job. If a job is unknown, then the initial status is returned. The current value is also subscribable by opening a websocket to &#x60;/status/{promptId}/live&#x60;. There the status object is pushed as it is described by this endpoint whenever it is updated."""
        ...

    async def update_status(
        self,
        status_manager: StatusManager,
        promptId: Annotated[StrictStr, Field(description="The promptId of the generation job")],
        status_patch: Annotated[
            StatusPatch, Field(description="The changes to apply to the status.")
        ],
    ) -> None:
        """Takes a status update and applies it to the current status. If a status is unknown, it creates a new object for it."""
        ...
