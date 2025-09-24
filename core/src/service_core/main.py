# coding: utf-8

from fastapi import FastAPI
from contextlib import asynccontextmanager
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

app = FastAPI(
    title="Orpheus CoreAI-Service API",
    description="Customized API for Orpheus core orchestration.",
    version="0.1.0",
    # lifespan=lifespan
)

app.include_router(CoreApiRouter)

