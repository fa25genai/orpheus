import httpx
from ..models.data_response import DataResponse

SLIDE_API = "https://slides:8050"
VIDEO_API = "https://videos:8050"



def get_slides(lecture_id: str) -> DataResponse:
    """Calls the external API to get the final slide result."""
    response = httpx.get(
        f"{SLIDE_API}/slides/{lecture_id}/result",
        timeout=10.0
    )
    response.raise_for_status()
    data = response.json()
    return DataResponse(url=data.get("url"))

def get_video(lecture_id: str) -> DataResponse:
    """Calls the external API to get the final video result."""
    response = httpx.get(
        f"{VIDEO_API}/videos/{lecture_id}/result",
        timeout=10.0
    )
    response.raise_for_status()
    data = response.json()
    return DataResponse(url=data.get("url"))