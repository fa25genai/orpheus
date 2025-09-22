import os
import typing
from concurrent.futures.thread import ThreadPoolExecutor
from os import cpu_count

from fastapi import FastAPI
from langchain.chat_models import init_chat_model
from service_slides.apis.slides_api import router as SlidesApiRouter


async def lifespan(app: FastAPI):
    model = None
    if "GOOGLE_API_KEY" in os.environ:
        model = init_chat_model("gemini-2.5-flash", model_provider="google_genai")
    app.state.executor = ThreadPoolExecutor(max_workers=cpu_count())

    if model is not None:
        app.state.model = model
    else:
        raise RuntimeError("No supported LLM API key supplied")

    yield

    # Teardown code goes here
    app.state.executor.shutdown()


app = FastAPI(title="orpheus-service-slides", lifespan=lifespan)

app.include_router(SlidesApiRouter)


@app.get("/")
async def root() -> typing.Any:
    return {"message": "Hello, AI world!"}
