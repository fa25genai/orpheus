#!/usr/bin/env python3
"""Fire 24 consecutive requests against /v1/video/generate for manual smoke testing."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Iterable

import requests

DEFAULT_BASE_URL = "http://localhost:9000"
COURSE_ID = "3fa85f64-5717-4562-b3fc-2c963f66a999"


PROMPT_IDS: tuple[str, ...] = (
    "3fa85f64-5717-4562-b3fc-2c963f661000",
    "3fa85f64-5717-4562-b3fc-2c963f661001",
    "3fa85f64-5717-4562-b3fc-2c963f661002",
    "3fa85f64-5717-4562-b3fc-2c963f661003",
)


BASE_VOICE_TRACK = (
    "The Sarntal Valley in South Tyrol is known for its untouched nature and traditional alpine culture. "
    "Surrounded by the Sarntal Alps, it offers countless hiking trails with breathtaking mountain views. "
    "Visitors can also enjoy authentic South Tyrolean cuisine and explore charming villages rich in history."
)


USER_PROFILE = {
    "id": "test-student",
    "role": "student",
    "language": "english",
    "preferences": {
        "answerLength": "short",
        "languageLevel": "basic",
        "expertiseLevel": "beginner",
        "includePictures": "none",
    },
    "enrolled_courses": ["demo-course"],
}


@dataclass(frozen=True)
class RequestSpec:
    prompt_id: str
    slide_number: int


def iter_specs() -> Iterable[RequestSpec]:
    # Interleave prompts by slide number to exercise queue ordering.
    for slide_no in range(6):  # 0..5 inclusive -> 6 requests per prompt
        for prompt_id in PROMPT_IDS:
            yield RequestSpec(prompt_id=prompt_id, slide_number=slide_no)


def main() -> int:
    base_url = os.getenv("VIDEO_GENERATION_URL", DEFAULT_BASE_URL).rstrip("/")
    endpoint = f"{base_url}/v1/video/generate"

    print(f"POST {endpoint} (24 requests in total)")
    session = requests.Session()

    success = 0
    for spec in iter_specs():
        suffix = spec.prompt_id[-3:]
        voice_track = f"Slide {spec.slide_number}, ID {suffix}. {BASE_VOICE_TRACK}"

        payload = {
            "voiceTrack": voice_track,
            "slideNumber": spec.slide_number,
            "promptId": spec.prompt_id,
            "courseId": COURSE_ID,
            "userProfile": USER_PROFILE,
            "slot": "default",
        }

        try:
            resp = session.post(endpoint, json=payload, timeout=30)
        except requests.RequestException as exc:
            print(f"[ERROR] prompt={spec.prompt_id} slide={spec.slide_number}: {exc}")
            continue

        if resp.status_code != 202:
            print(
                "[FAIL] prompt=%s slide=%s -> %s %s" % (spec.prompt_id, spec.slide_number, resp.status_code, resp.text[:160]),
            )
        else:
            print(
                "[OK] prompt=%s slide=%s -> Location=%s" % (spec.prompt_id, spec.slide_number, resp.headers.get("Location", "-")),
            )
            success += 1

    print(f"Done: {success}/24 accepted (202).")
    return 0 if success == 24 else 1


if __name__ == "__main__":
    sys.exit(main())
