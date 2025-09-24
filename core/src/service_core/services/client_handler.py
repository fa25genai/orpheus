import httpx
from service_core.models.data_response import DataResponse

client = httpx.AsyncClient()

DI_API_URL = "https://slides:8050"
SLIDES_API_URL = "https://videos:8050"


async def process_prompt(prompt_id: str, prompt: str) -> DataResponse:
    """
    Asynchronously calls the appropriate external API to get the final result.
    """
    pass