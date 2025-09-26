from logging import getLogger

from service_slides.clients.configurations import get_status_api_config
from service_slides.clients.status import ApiClient, ApiException, StatusApi, StatusPatch

_log = getLogger("status_update")

async def update_status(prompt_id: str, patch: StatusPatch) -> None:
    try:
        async with ApiClient(get_status_api_config()) as api_client:
            status_api = StatusApi(api_client)
            await status_api.update_status(prompt_id, patch)
    except ApiException as ex:
        _log.error(
            "Failed to update generation status for %s. Error %d: %s",
            prompt_id,
            ex.status,
            ex.reason,
        )
    except Exception as e:
        _log.error(
            "Error when updateing the generation status for %s",
            prompt_id,
            exc_info=e,
        )
