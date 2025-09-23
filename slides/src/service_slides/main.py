import os
from concurrent.futures.thread import ThreadPoolExecutor
from os import cpu_count

from fastapi import FastAPI
from langchain.chat_models import init_chat_model

from service_slides.apis.slides_api import router as SlidesApiRouter
from service_slides.impl.manager.job_manager import JobManager
from service_slides.impl.manager.layout_manager import LayoutManager


async def lifespan(app: FastAPI):
    model = None
    if "GOOGLE_API_KEY" in os.environ:
        model = init_chat_model("gemini-2.5-flash", model_provider="google_genai")

    if model is not None:
        app.state.model = model
    else:
        raise RuntimeError("No supported LLM API key supplied")

    app.state.executor = ThreadPoolExecutor(max_workers=cpu_count())
    app.state.job_manager = JobManager()
    app.state.layout_manager = LayoutManager()

    yield

    # Teardown code goes here
    app.state.executor.shutdown()


app = FastAPI(title="orpheus-service-slides", lifespan=lifespan)

app.include_router(SlidesApiRouter)
