# coding: utf-8

from fastapi import FastAPI
from contextlib import asynccontextmanager
from .apis.core_api import router as CoreApiRouter
from fastapi.middleware.cors import CORSMiddleware

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

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(CoreApiRouter)

