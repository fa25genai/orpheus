import os

from service_slides.clients.postprocessing import Configuration as PostprocessingConfiguration
from service_slides.clients.status import Configuration as StatusConfiguration


def get_postprocessing_api_config() -> PostprocessingConfiguration:
    return PostprocessingConfiguration(
        host=os.environ.get("POSTPROCESSING_SERVICE_HOST")
        if "POSTPROCESSING_SERVICE_HOST" in os.environ
        else "http://slides-postprocessing:30607",
    )


def get_status_api_config() -> StatusConfiguration:
    return PostprocessingConfiguration(
        host=os.environ.get("STATUS_SERVICE_HOST")
        if "STATUS_SERVICE_HOST" in os.environ
        else "http://status-service:19910",
    )
