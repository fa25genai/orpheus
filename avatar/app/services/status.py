from __future__ import annotations

from typing import Any, Dict, Mapping, Optional
from uuid import UUID

import requests

from app import config


def _status_service_url(prompt_id: UUID) -> str:
    base = config.STATUS_SERVICE_HOST.rstrip("/")
    return f"{base}/status/{prompt_id}/update"


def patch_status(prompt_id: UUID, payload: Mapping[str, Any]) -> None:
    if not payload:
        return
    url = _status_service_url(prompt_id)
    try:
        resp = requests.patch(url, json=payload, timeout=config.STATUS_SERVICE_TIMEOUT)
        if resp.status_code >= 400:
            snippet = resp.text[:200] if resp.text else ""
            print(f"[status] PATCH {url} -> {resp.status_code} {snippet}")
    except requests.RequestException as exc:
        print(f"[status] PATCH {url} failed: {exc}")


def update_avatar_generation_step_status(prompt_id: UUID, slide_index: int, *, audio: Optional[str] = None, video: Optional[str] = None) -> None:
    step_payload: Dict[str, str] = {}
    if audio is not None:
        step_payload["audio"] = audio
    if video is not None:
        step_payload["video"] = video
    if not step_payload:
        return
    payload = {"stepsAvatarGeneration": {str(slide_index): step_payload}}
    patch_status(prompt_id, payload)
