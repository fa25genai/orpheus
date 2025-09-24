import httpx
from service_core.models.data_response import DataResponse

client = httpx.AsyncClient()

SLIDE_API_URL = "https://slides:8050"
VIDEO_API_URL = "https://videos:8050"


async def get_content_result(content_type: str, lecture_id: str) -> DataResponse:
    """
    Asynchronously calls the appropriate external API to get the final result.
    `content_type` should be 'slides' or 'video'.
    """
    if content_type == "slides":
        base_url = SLIDE_API_URL
    elif content_type == "video":
        base_url = VIDEO_API_URL
    else:
        raise ValueError(f"Invalid content type: {content_type}")

    response = await client.get(
        f"{base_url}/{content_type}/{lecture_id}/status",
        timeout=10.0
    )
    response.raise_for_status()
    data = response.json()
    return DataResponse(url=data.get("url"))