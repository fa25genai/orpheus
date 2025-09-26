import logging
import os
from logging import getLogger
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from service_status.apis.status_api import router as StatusApiRouter
from service_status.impl.manager.status_manager import StatusManager

_log = getLogger("app")


async def lifespan(app: FastAPI) -> Any:
    _log.info("Setting up **Generation Status Service**")
    app.state.status_manager = StatusManager()

    yield

    _log.info("Exiting **Generation Status Service**")


logging.basicConfig(
    level=logging.DEBUG if os.getenv("ORPHEUS_VERBOSE") else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%m/%d/%Y %I:%M:%S %p",
)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)


app = FastAPI(title="orpheus-service-status", lifespan=lifespan)

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(StatusApiRouter)
