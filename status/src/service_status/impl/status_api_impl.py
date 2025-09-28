from pydantic import StrictStr, Field
from typing_extensions import Annotated

from service_status.apis.status_api_base import BaseStatusApi
from service_status.impl.manager.status_manager import StatusManager
from service_status.models.status import Status
from service_status.models.status_patch import StatusPatch


class ImplStatusApi(BaseStatusApi):
    async def get_status(
        self,
        status_manager: StatusManager,
        promptId: Annotated[StrictStr, Field(description="The promptId of the generation job")],
    ) -> Status:
        return await status_manager.get_status(promptId)

    async def update_status(
        self,
        status_manager: StatusManager,
        promptId: Annotated[StrictStr, Field(description="The promptId of the generation job")],
        status_patch: Annotated[
            StatusPatch, Field(description="The changes to apply to the status.")
        ],
    ) -> None:
        await status_manager.update_status(promptId, status_patch)
