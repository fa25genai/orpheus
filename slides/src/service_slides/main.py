import logging
import os
from concurrent.futures.thread import ThreadPoolExecutor
from os import cpu_count, getenv
from typing import Any
from logging import getLogger

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from service_slides.apis.slides_api import router as SlidesApiRouter
from service_slides.impl.manager.job_manager import JobManager
from service_slides.impl.manager.layout_manager import LayoutManager
from service_slides.impl.llm_chain.shared_llm import create_base_model

_log = getLogger("app")


async def lifespan(app: FastAPI) -> Any:
    _log.info("Setting up **Slide Generation Service**")
    splitting_model_name = getenv("SPLITTING_MODEL")
    if splitting_model_name is None:
        raise ValueError("SPLITTING_MODEL environment variable is not set")

    slidesgen_model_name = getenv("SLIDESGEN_MODEL")
    if slidesgen_model_name is None:
        raise ValueError("SLIDESGEN_MODEL environment variable is not set")

    _log.debug(f"Initializing splitting model: {splitting_model_name}")
    splitting_model = create_base_model(splitting_model_name, temperature=0.0)
    if splitting_model is not None:
        app.state.splitting_model = splitting_model

    _log.debug(f"Initializing slides model: {slidesgen_model_name}")
    slidesgen_model = create_base_model(slidesgen_model_name, temperature=0.0)
    if slidesgen_model is not None:
        app.state.slidesgen_model = slidesgen_model

    app.state.executor = ThreadPoolExecutor(max_workers=cpu_count())
    app.state.job_manager = JobManager()
    app.state.layout_manager = LayoutManager()

    yield

    # Teardown code goes here
    app.state.executor.shutdown()
    _log.info("Exiting **Slide Generation Service**")


logging.basicConfig(
    level=logging.DEBUG if os.getenv("DEBUG") else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%m/%d/%Y %I:%M:%S %p",
)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)


app = FastAPI(title="orpheus-service-slides", lifespan=lifespan)

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(SlidesApiRouter)
