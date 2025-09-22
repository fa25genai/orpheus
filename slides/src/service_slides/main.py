from concurrent.futures.thread import ThreadPoolExecutor
from os import cpu_count, getenv
import os
import typing
from concurrent.futures.thread import ThreadPoolExecutor
from os import cpu_count

from fastapi import FastAPI

from service_slides.apis.slides_api import router as SlidesApiRouter
from service_slides.impl.manager.job_manager import JobManager
from service_slides.impl.manager.layout_manager import LayoutManager
from service_slides.llm_chain.shared_llm import create_base_model



async def lifespan(app: FastAPI):
    splitting_model_name = getenv("SPLITTING_MODEL")
    if splitting_model_name is None:
        raise ValueError("SPLITTING_MODEL environment variable is not set")

    slidesgen_model_name = getenv("SLIDESGEN_MODEL")
    if slidesgen_model_name is None:
        raise ValueError("SLIDESGEN_MODEL environment variable is not set")

    splitting_model = create_base_model(splitting_model_name, temperature=0.0)
    if splitting_model is not None:
        app.state.splitting_model = splitting_model

    slidesgen_model = create_base_model(slidesgen_model_name, temperature=0.0)
    if slidesgen_model is not None:
        app.state.slidesgen_model = slidesgen_model

    app.state.executor = ThreadPoolExecutor(max_workers=cpu_count())
    app.state.job_manager = JobManager()
    app.state.layout_manager = LayoutManager()

    yield

    # Teardown code goes here
    app.state.executor.shutdown()


app = FastAPI(title="orpheus-service-slides", lifespan=lifespan)

app.include_router(SlidesApiRouter)


@app.get("/test")
async def test_endpoint():
    from service_slides.llm_chain.slide_splitting import test

    try:
        # Get the splitting model from app state
        splitting_model = app.state.splitting_model

        # Call the test function with the model
        response = test(splitting_model)

        return {
            "message": "Test successful",
            "model_response": response,
            "status": "ok"
        }
    except Exception as e:
        return {
            "message": "Test failed",
            "error": str(e),
            "status": "error"
        }
