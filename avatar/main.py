from __future__ import annotations

import logging
import os
from threading import Event, Thread

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.avatars import router as avatars_router
from app.api.video import router as video_router
from app.workers import audio as audio_worker
from app.workers import cleanup as cleanup_worker
from app.workers import video as video_worker

logging.basicConfig(
    level=logging.DEBUG if os.getenv("ORPHEUS_VERBOSE") else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%m/%d/%Y %I:%M:%S %p",
)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)
logging.getLogger("botocore").setLevel(logging.WARNING)

app = FastAPI(title="Service Video-Generation APIs", version="0.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(avatars_router)
app.include_router(video_router)

_audio_started = Event()
_video_started = Event()
_cleanup_started = Event()


@app.on_event("startup")
def _start_workers() -> None:
    if not _audio_started.is_set():
        Thread(target=audio_worker.loop, name="audio-worker", daemon=True).start()
        _audio_started.set()
    if not _video_started.is_set():
        Thread(target=video_worker.loop, name="video-worker", daemon=True).start()
        _video_started.set()
    if not _cleanup_started.is_set():
        Thread(target=cleanup_worker.loop, name="job-cleanup", daemon=True).start()
        _cleanup_started.set()

# Run: uvicorn main:app --host 0.0.0.0 --port 8080 --reload
