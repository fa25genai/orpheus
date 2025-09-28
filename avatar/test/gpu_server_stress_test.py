#!/usr/bin/env python3
"""
stress_av.py — Concurrent stress test for GEN_AUDIO and GEN_VIDEO with optional sample saving.

- Audio endpoint expects multipart:
    files: {"voice_file": <mp3>}
    data : {"voiceTrack": "...", "debug": "true|false", "promptId": "<uuid>"}

- Video endpoint expects multipart:
    files: {"audio": <wav>, "source": <png>}
    data : {"debug": "true|false"}

Defaults (override via env or CLI):
  GEN_AUDIO = https://gpu.aet.cit.tum.de/avatar/audio/v1/audio/generate
  GEN_VIDEO = https://gpu.aet.cit.tum.de/avatar/video/infer

Examples:
  python stress_av.py --audio-requests 200 --video-requests 200 --concurrency 40 \
    --voice-sample /app/database/voice_sample/krusche_voice.mp3 \
    --video-image /app/database/avatar_sample/image_michal.png \
    --save-audio-samples 1 --save-video-samples 1
"""

import argparse
import asyncio
import base64
import io
import math
import os
import random
import struct
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional

import aiohttp

# ---------- Defaults from your config / env ----------
DEFAULT_AUDIO_URL = os.getenv(
    "GEN_AUDIO",
    "https://gpu.aet.cit.tum.de/avatar/audio/v1/audio/generate",
)
DEFAULT_VIDEO_URL = os.getenv(
    "GEN_VIDEO",
    "https://gpu.aet.cit.tum.de/avatar/video/infer",
)

# ---------- Embedded 1x1 PNG (black) for fallback ----------
_ONE_BY_ONE_PNG = base64.b64decode(
    b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMB/kaKpGkAAAAASUVORK5CYII="
)

# ---------- Utilities ----------
def gen_wav_bytes(duration_s: float = 1.0, sample_rate: int = 16000, freq: float = 440.0) -> bytes:
    """Generate mono 16-bit PCM WAV sine tone with stdlib only."""
    n_samples = int(duration_s * sample_rate)
    buf = io.BytesIO()

    def _write(fmt: str, *vals):
        buf.write(struct.pack(fmt, *vals))

    # RIFF header
    buf.write(b"RIFF")
    buf.write(b"\x00\x00\x00\x00")  # file size placeholder
    buf.write(b"WAVE")

    # fmt chunk
    buf.write(b"fmt ")
    _write("<I", 16)            # Subchunk1Size (PCM)
    _write("<H", 1)             # AudioFormat (PCM)
    _write("<H", 1)             # NumChannels
    _write("<I", sample_rate)   # SampleRate
    _write("<I", sample_rate * 2)  # ByteRate (mono, 16-bit)
    _write("<H", 2)             # BlockAlign
    _write("<H", 16)            # BitsPerSample

    # data chunk
    buf.write(b"data")
    data_size_pos = buf.tell()
    buf.write(b"\x00\x00\x00\x00")  # data size placeholder

    max_amp = 32767
    for n in range(n_samples):
        val = int(max_amp * math.sin(2 * math.pi * freq * (n / sample_rate)))
        _write("<h", val)

    # Patch sizes
    data_size = n_samples * 2
    end_pos = buf.tell()
    buf.seek(data_size_pos)
    _write("<I", data_size)

    file_size = end_pos - 8
    buf.seek(4)
    _write("<I", file_size)

    buf.seek(0)
    return buf.read()

def random_text() -> str:
    phrases = [
        "Hello students! I want you to drink coffee.",
        "Welcome to Algorithms 101; today we’ll discuss Dijkstra’s algorithm.",
        "Concurrency test message; please ignore.",
        "This is a synthetic TTS load test prompt.",
        "The quick brown fox jumps over the lazy dog!",
    ]
    return random.choice(phrases)

def jittered_uuid() -> str:
    return str(uuid.uuid4())

class Stats:
    def __init__(self, label: str):
        self.label = label
        self.lock = asyncio.Lock()
        self.count = 0
        self.ok = 0
        self.errors: Dict[str, int] = {}
        self.latencies: List[float] = []

    async def record(self, ok: bool, status_or_err: str, latency: float):
        async with self.lock:
            self.count += 1
            if ok:
                self.ok += 1
            else:
                self.errors[status_or_err] = self.errors.get(status_or_err, 0) + 1
            self.latencies.append(latency)

    def summary(self) -> str:
        if self.latencies:
            p50 = percentile(self.latencies, 50)
            p90 = percentile(self.latencies, 90)
            p99 = percentile(self.latencies, 99)
            avg = sum(self.latencies) / len(self.latencies)
        else:
            p50 = p90 = p99 = avg = 0.0
        lines = [
            f"== {self.label} ==",
            f"Total: {self.count} | OK: {self.ok} | Fail: {self.count - self.ok}",
        ]
        if self.errors:
            errs = ", ".join(f"{k}:{v}" for k, v in sorted(self.errors.items()))
            lines.append(f"Errors: {errs}")
        lines.append(f"Latency (s): avg={avg:.3f}, p50={p50:.3f}, p90={p90:.3f}, p99={p99:.3f}")
        return "\n".join(lines)

def percentile(data: List[float], p: float) -> float:
    if not data:
        return 0.0
    s = sorted(data)
    k = (len(s) - 1) * (p / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return s[int(k)]
    return s[f] * (c - k) + s[c] * (k - f)

async def backoff_sleep(attempt: int):
    base = min(2 ** attempt, 32)
    await asyncio.sleep(base * (0.5 + random.random() * 0.5))

# ---------- Sample file manager (thread-safe counters) ----------
class SampleSaver:
    def __init__(self, out_dir: Path, audio_limit: int, video_limit: int):
        self.out_dir = out_dir
        self.audio_limit = int(max(0, audio_limit))
        self.video_limit = int(max(0, video_limit))
        self._a_count = 0
        self._v_count = 0
        self._lock = asyncio.Lock()
        self.out_dir.mkdir(parents=True, exist_ok=True)

    async def reserve_audio_path(self) -> Optional[Path]:
        async with self._lock:
            if self._a_count >= self.audio_limit:
                return None
            self._a_count += 1
            return self.out_dir / f"sample-audio-{self._a_count:03d}.wav"

    async def reserve_video_path(self) -> Optional[Path]:
        async with self._lock:
            if self._v_count >= self.video_limit:
                return None
            self._v_count += 1
            return self.out_dir / f"sample-video-{self._v_count:03d}.mp4"

# ---------- Workers ----------
async def hit_audio(
    session: aiohttp.ClientSession,
    url: str,
    voice_sample_path: str,
    stats: Stats,
    semaphore: asyncio.Semaphore,
    debug_flag: bool,
    timeout_s: int,
    attempt_retries: int,
    saver: Optional[SampleSaver] = None,
):
    if not os.path.isfile(voice_sample_path):
        await stats.record(False, "no-voice-sample", 0.0)
        return

    async with semaphore:
        attempt = 0
        while True:
            prompt_id = jittered_uuid()
            voice_text = random_text()
            started = time.perf_counter()
            try:
                with open(voice_sample_path, "rb") as vf:
                    form = aiohttp.FormData()
                    form.add_field("voice_file", vf, filename=os.path.basename(voice_sample_path), content_type="audio/mpeg")
                    form.add_field("voiceTrack", voice_text)
                    form.add_field("debug", str(debug_flag).lower())
                    form.add_field("promptId", prompt_id)

                    async with session.post(url, data=form, timeout=timeout_s) as resp:
                        if resp.status >= 400:
                            _ = await resp.text()
                            await stats.record(False, f"HTTP{resp.status}", time.perf_counter() - started)
                            return

                        # Decide if we save this one
                        out_path: Optional[Path] = None
                        out_f = None
                        if saver:
                            out_path = await saver.reserve_audio_path()
                            if out_path is not None:
                                out_f = open(out_path, "wb")

                        try:
                            async for chunk in resp.content.iter_chunked(1024 * 256):
                                if out_f and chunk:
                                    out_f.write(chunk)
                        finally:
                            if out_f:
                                out_f.flush()
                                os.fsync(out_f.fileno())
                                out_f.close()

                await stats.record(True, "OK", time.perf_counter() - started)
                return

            except asyncio.TimeoutError:
                await stats.record(False, "timeout", time.perf_counter() - started)
            except aiohttp.ClientError as e:
                await stats.record(False, f"client:{type(e).__name__}", time.perf_counter() - started)
            except Exception as e:
                await stats.record(False, f"other:{type(e).__name__}", time.perf_counter() - started)

            attempt += 1
            if attempt > attempt_retries:
                return
            await backoff_sleep(attempt)

async def hit_video(
    session: aiohttp.ClientSession,
    url: str,
    stats: Stats,
    semaphore: asyncio.Semaphore,
    debug_flag: bool,
    timeout_s: int,
    attempt_retries: int,
    wav_duration_s: float = 1.0,
    video_image_path: Optional[str] = None,
    saver: Optional[SampleSaver] = None,
):
    # Choose PNG: user-provided or built-in fallback
    if video_image_path and os.path.isfile(video_image_path):
        with open(video_image_path, "rb") as f:
            png_bytes = f.read()
    else:
        png_bytes = _ONE_BY_ONE_PNG

    wav_bytes = gen_wav_bytes(duration_s=wav_duration_s)

    async with semaphore:
        attempt = 0
        while True:
            started = time.perf_counter()
            try:
                form = aiohttp.FormData()
                form.add_field("audio", wav_bytes, filename="audio.wav", content_type="audio/wav")
                form.add_field("source", png_bytes, filename="image.png", content_type="image/png")
                form.add_field("debug", str(debug_flag).lower())

                async with session.post(url, data=form, timeout=timeout_s) as resp:
                    if resp.status >= 400:
                        _ = await resp.text()
                        await stats.record(False, f"HTTP{resp.status}", time.perf_counter() - started)
                        return

                    # Decide if we save this one
                    out_path: Optional[Path] = None
                    out_f = None
                    if saver:
                        out_path = await saver.reserve_video_path()
                        if out_path is not None:
                            out_f = open(out_path, "wb")

                    try:
                        async for chunk in resp.content.iter_chunked(1024 * 256):
                            if out_f and chunk:
                                out_f.write(chunk)
                    finally:
                        if out_f:
                            out_f.flush()
                            os.fsync(out_f.fileno())
                            out_f.close()

                await stats.record(True, "OK", time.perf_counter() - started)
                return

            except asyncio.TimeoutError:
                await stats.record(False, "timeout", time.perf_counter() - started)
            except aiohttp.ClientError as e:
                await stats.record(False, f"client:{type(e).__name__}", time.perf_counter() - started)
            except Exception as e:
                await stats.record(False, f"other:{type(e).__name__}", time.perf_counter() - started)

            attempt += 1
            if attempt > attempt_retries:
                return
            await backoff_sleep(attempt)

# ---------- Orchestration ----------
async def run_load(
    audio_url: str,
    video_url: str,
    n_audio: int,
    n_video: int,
    concurrency: int,
    voice_sample_path: Optional[str],
    timeout_s: int,
    retries: int,
    debug_flag: bool,
    video_image_path: Optional[str],
    samples_dir: Path,
    save_audio_samples: int,
    save_video_samples: int,
):
    sem = asyncio.Semaphore(concurrency)
    audio_stats = Stats("AUDIO")
    video_stats = Stats("VIDEO")

    saver = SampleSaver(samples_dir, save_audio_samples, save_video_samples) if (save_audio_samples or save_video_samples) else None

    connector = aiohttp.TCPConnector(limit=0, ttl_dns_cache=300)
    timeout = aiohttp.ClientTimeout(total=None)

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        tasks: List[asyncio.Task] = []

        # Audio tasks
        if voice_sample_path and os.path.isfile(voice_sample_path):
            for _ in range(n_audio):
                tasks.append(asyncio.create_task(
                    hit_audio(session, audio_url, voice_sample_path, audio_stats, sem, debug_flag, timeout_s, retries, saver=saver)
                ))
        else:
            if n_audio > 0:
                print("[WARN] Voice sample not found or not provided; skipping AUDIO tests.")

        # Video tasks
        for _ in range(n_video):
            tasks.append(asyncio.create_task(
                hit_video(session, video_url, video_stats, sem, debug_flag, timeout_s, retries,
                          video_image_path=video_image_path, saver=saver)
            ))

        random.shuffle(tasks)

        started = time.perf_counter()

        async def progress():
            total = len(tasks)
            last_pct = -1
            while True:
                done = sum(t.done() for t in tasks)
                pct = int(100 * done / total) if total else 100
                if pct != last_pct:
                    print(f"[progress] {done}/{total} ({pct}%)", flush=True)
                    last_pct = pct
                if done >= total:
                    break
                await asyncio.sleep(1)

        await asyncio.gather(progress(), *tasks)
        elapsed = time.perf_counter() - started

    print("\n========= SUMMARY =========")
    print(audio_stats.summary())
    print()
    print(video_stats.summary())
    print(f"\nElapsed: {elapsed:.2f}s")
    if saver and (save_audio_samples or save_video_samples):
        print(f"Saved samples in: {samples_dir.resolve()}")

# ---------- CLI ----------
def parse_args():
    p = argparse.ArgumentParser(description="Stress test GEN_AUDIO and GEN_VIDEO services (with optional sample saving).")
    p.add_argument("--audio-url", default=DEFAULT_AUDIO_URL, help="Audio service URL")
    p.add_argument("--video-url", default=DEFAULT_VIDEO_URL, help="Video service URL")
    p.add_argument("--audio-requests", type=int, default=100, help="Number of audio requests")
    p.add_argument("--video-requests", type=int, default=100, help="Number of video requests")
    p.add_argument("--concurrency", type=int, default=20, help="Max concurrent requests (combined)")
    p.add_argument("--timeout", type=int, default=600, help="Per-request timeout seconds")
    p.add_argument("--retries", type=int, default=1, help="Retries per request on failure")
    p.add_argument("--voice-sample", default="/app/database/voice_sample/krusche_voice.mp3",
                   help="Path to voice sample MP3 for audio tests")
    p.add_argument("--video-image", default=None,
                   help="Optional path to a PNG image for video requests. Defaults to an embedded 1x1 PNG.")
    p.add_argument("--save-audio-samples", type=int, default=0,
                   help="Save up to N audio responses to disk (WAV). Default 0 (disabled).")
    p.add_argument("--save-video-samples", type=int, default=0,
                   help="Save up to N video responses to disk (MP4). Default 0 (disabled).")
    p.add_argument("--samples-dir", default="./samples",
                   help="Directory to write sample files into when saving is enabled.")
    p.add_argument("--debug", action="store_true", help="Send debug=true to services")
    return p.parse_args()

def main():
    args = parse_args()
    print("Config:")
    print(f"  AUDIO: {args.audio_url}")
    print(f"  VIDEO: {args.video_url}")
    print(f"  audio_requests={args.audio_requests}, video_requests={args.video_requests}, concurrency={args.concurrency}")
    print(f"  timeout={args.timeout}s, retries={args.retries}, debug={args.debug}")
    print(f"  voice_sample={args.voice_sample}")
    print(f"  video_image={args.video_image or '[embedded 1x1 PNG]'}")
    print(f"  save_audio_samples={args.save_audio_samples}, save_video_samples={args.save_video_samples}, samples_dir={args.samples_dir}")

    try:
        asyncio.run(
            run_load(
                audio_url=args.audio_url,
                video_url=args.video_url,
                n_audio=args.audio_requests,
                n_video=args.video_requests,
                concurrency=args.concurrency,
                voice_sample_path=args.voice_sample,
                timeout_s=args.timeout,
                retries=args.retries,
                debug_flag=args.debug,
                video_image_path=args.video_image,
                samples_dir=Path(args.samples_dir),
                save_audio_samples=args.save_audio_samples,
                save_video_samples=args.save_video_samples,
            )
        )
    except KeyboardInterrupt:
        print("\nInterrupted.")

if __name__ == "__main__":
    main()
