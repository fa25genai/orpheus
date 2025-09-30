from __future__ import annotations

import os
from pathlib import Path
from typing import Optional
from uuid import UUID

import requests
from sqlalchemy.orm import Session

from app.schemas import UserProfile
from app.workers.queues import job_dir
from media import avatar_queries  # keep your existing module


def generate_audio(
    voiceTrack: Optional[str],
    course_id: str | UUID,
    prompt_id: UUID | None,
    user_profile: UserProfile,
    audio_counter: int,
    *,
    db: Session,
    slot: str = "default",
) -> str | None:
    if prompt_id is None:
        print("[generate_audio] prompt_id is required")
        return None

    audio_api_url = os.getenv("GEN_AUDIO", "http://localhost:7000/v1/audio/generate")
    job_folder = job_dir(prompt_id)
    wav_path = job_folder / f"{audio_counter}.wav"

    try:
        ref = avatar_queries.get_latest_audio_for_course_slot(db, str(course_id), slot)
        if not ref or not getattr(ref, "file_path", None):
            print("[generate_audio] No DB voice found; using fallback sample.")
            ref_path = Path("/app/database/voice_sample/krusche_voice.mp3")
        else:
            ref_path = Path(ref.file_path)
            if not ref_path.is_file():
                print(f"[generate_audio] DB voice not found on disk: {ref_path}")
                ref_path = Path("/app/database/voice_sample/krusche_voice.mp3")

        suffix = ref_path.suffix.lower()
        mime_type = "audio/wav" if suffix == ".wav" else "audio/mpeg"

        is_debug = os.getenv("DEBUG", "").lower() == "debug"
        data = {"voiceTrack": voiceTrack or "", "debug": "true" if is_debug else "false", "promptId": str(prompt_id)}

        print(f"[generate_audio] Posting to {audio_api_url} with {ref_path}")
        with ref_path.open("rb") as f:
            resp = requests.post(
                audio_api_url,
                data=data,
                files={"voice_file": (ref_path.name, f, mime_type)},
                timeout=(5, 600),
                stream=True,
            )
            resp.raise_for_status()

            if "application/json" in (resp.headers.get("Content-Type") or "").lower():
                try:
                    print(f"[generate_audio] Unexpected JSON response: {resp.json()}")
                except Exception:
                    print("[generate_audio] Unexpected JSON response (could not parse).")
                return None

            tmp_path = wav_path.with_suffix(".wav.part")
            with tmp_path.open("wb") as out:
                for chunk in resp.iter_content(chunk_size=1024 * 256):
                    if chunk:
                        out.write(chunk)
                out.flush()
                os.fsync(out.fileno())

        if not tmp_path.exists() or tmp_path.stat().st_size == 0:
            print("[generate_audio] Empty file received")
            tmp_path.unlink(missing_ok=True)
            return None

        tmp_path.replace(wav_path)
        print(f"[generate_audio] OK -> {wav_path}")
        return str(wav_path)

    except requests.RequestException as e:
        print(f"[generate_audio] Request error: {e}")
        return None
    except Exception as e:
        print(f"[generate_audio] Unexpected error: {e}")
        return None


def generate_video(
    audio_path: Optional[str] = None,
    prompt_id: Optional[UUID] = None,
    course_id: Optional[str] = None,
    user_profile: Optional[UserProfile] = None,
    video_counter: int = 0,
    source_image_path: Optional[str] = None,
) -> Optional[str]:
    if prompt_id is None or video_counter is None:
        print("[generate_video] prompt_id and video_counter are required")
        return None

    video_api_url = os.getenv("GEN_VIDEO", "http://localhost:8000/infer")
    job_folder = job_dir(prompt_id)
    temp_path = job_folder / f".{video_counter}.mp4.part"
    final_path = job_folder / f"{video_counter}.mp4"

    resolved_audio = audio_path or f"{job_folder}/{video_counter}.wav"
    if not Path(resolved_audio).is_file():
        print(f"[generate_video] Audio file not found: {resolved_audio}")
        return None

    source_path = source_image_path
    if not source_path or not Path(source_path).is_file():
        print(f"[generate_video] Source image not found: {source_path}; using fallback sample.")
        source_path = "/app/database/avatar_sample/image_michal.png"
    if not Path(source_path).is_file():
        print(f"[generate_video] Source image not found: {source_path}")
        return None

    is_debug = os.getenv("DEBUG", "").lower() in {"debug"}
    data = {"debug": is_debug}

    try:
        print(f"[generate_video] Posting to {video_api_url}")
        with (
            open(resolved_audio, "rb") as audio_f,
            open(source_path, "rb") as image_f,
            requests.post(
                video_api_url,
                files={
                    "audio": ("audio.wav", audio_f, "audio/wav"),
                    "source": ("image.png", image_f, "image/png"),
                },
                data=data,
                stream=True,
                timeout=(5, 600),
            ) as resp,
        ):
            if resp.status_code >= 400:
                print(f"[generate_video] HTTP {resp.status_code}: {resp.text[:200]}")
                return None

            with temp_path.open("wb") as f:
                for chunk in resp.iter_content(chunk_size=1024 * 256):
                    if chunk:
                        f.write(chunk)
                f.flush()
                os.fsync(f.fileno())

        if temp_path.stat().st_size == 0:
            print("[generate_video] empty file received")
            temp_path.unlink(missing_ok=True)
            return None

        temp_path.replace(final_path)
        print(f"[generate_video] OK -> {final_path}")
        return str(final_path)

    except requests.RequestException as e:
        print(f"[generate_video] Request error: {e}")
        return None
    except Exception as e:
        print(f"[generate_video] Unexpected error: {e}")
        return None