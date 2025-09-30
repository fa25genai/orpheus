# coding: utf-8


from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import os

from .apis.core_api import router as CoreApiRouter

# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     print("Starting up and creating CoreThreadPoolExecutor...")
#     app_state.executor = ThreadPoolExecutor()
#     print(app_state.executor)
#     yield
#     # On shutdown, shut down the executor.
#     print("Shutting down the CoreThreadPoolExecutor...")
#     if app_state.executor:
#         app_state.executor.shutdown(wait=True)

logging.basicConfig(
    level=logging.DEBUG if os.getenv("ORPHEUS_VERBOSE") else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%m/%d/%Y %I:%M:%S %p",
)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)
logging.getLogger("botocore").setLevel(logging.WARNING)

app = FastAPI(
    title="Orpheus CoreAI-Service API",
    description="Customized API for Orpheus core orchestration.",
    version="0.1.0",
    # lifespan=lifespan
)

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(CoreApiRouter)
