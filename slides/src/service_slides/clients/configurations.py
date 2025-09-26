import os

from service_slides.clients.postprocessing import Configuration as PostprocessingConfiguration


def get_postprocessing_api_config() -> PostprocessingConfiguration:
    return PostprocessingConfiguration(
        host=os.environ.get("POSTPROCESSING_SERVICE_HOST") if "POSTPROCESSING_SERVICE_HOST" in os.environ else "http://slides-postprocessing:30607",
    )
