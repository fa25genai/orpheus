from __future__ import annotations

import os
from pathlib import Path

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

IMAGES_OUTPUT_DIR = Path(os.getenv("IMAGES_OUTPUT_DIR", "data/avatars")).resolve()
IMAGES_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

VIDEO_ROOT = Path(os.getenv("VIDEO_ROOT", "/data/jobs")).resolve()
PUBLIC_VIDEOS_BASE = os.getenv("PUBLIC_VIDEOS_BASE", "/videos/jobs")
VIDEO_ROOT.mkdir(parents=True, exist_ok=True)

STATUS_SERVICE_HOST = os.getenv("STATUS_SERVICE_HOST", "http://host.docker.internal:19910")
STATUS_SERVICE_TIMEOUT = (3, 15)