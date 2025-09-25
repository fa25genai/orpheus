"""
FastAPI wrapper to expose your Ditto model's `run` function as a simple API.

- POST /infer  with JSON { audio_path, source_path, output_path, optional setup_kwargs/run_kwargs }
- GET  /health for a quick health check.

Notes
-----
* The StreamSDK is initialized **once** at startup and reused for all requests.
* A global lock prevents concurrent GPU access. If you want parallelism, shard GPUs and run multiple workers.
* Start with: `uvicorn app:app --host 0.0.0.0 --port 8000 --workers 1`
"""

import os
import math
import pickle
import random
import threading
import json
import numpy as np
import torch
import librosa
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

# -----------------------------
# Your SDK import
# -----------------------------
from stream_pipeline_offline import StreamSDK


def seed_everything(seed: int) -> None:
    os.environ["PYTHONHASHSEED"] = str(seed)
    os.environ["PL_GLOBAL_SEED"] = str(seed)
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def load_pkl(pkl_path: str):
    with open(pkl_path, "rb") as f:
        return pickle.load(f)


def run_inference(
        SDK: StreamSDK,
        audio_path: str,
        source_path: str,
        output_path: str,
        more_kwargs: Dict[str, Any] | str | None = None,
) -> str:
    """Wraps original `run` with minor safety checks and returns the output path."""
    if more_kwargs is None:
        more_kwargs = {}

    if isinstance(more_kwargs, str):
        more_kwargs = load_pkl(more_kwargs)

    setup_kwargs = more_kwargs.get("setup_kwargs", {})
    run_kwargs = more_kwargs.get("run_kwargs", {})

    # Basic existence checks
    if not os.path.isfile(audio_path):
        raise FileNotFoundError(f"audio_path not found: {audio_path}")
    if not os.path.isfile(source_path):
        raise FileNotFoundError(f"source_path not found: {source_path}")

    # Ensure output directory exists
    os.makedirs(os.path.dirname(os.path.abspath(output_path)) or ".", exist_ok=True)

    # ---- Original logic ----
    SDK.setup(source_path, output_path, **setup_kwargs)

    audio, sr = librosa.core.load(audio_path, sr=16000)
    num_f = math.ceil(len(audio) / 16000 * 25)

    fade_in = run_kwargs.get("fade_in", -1)
    fade_out = run_kwargs.get("fade_out", -1)
    ctrl_info = run_kwargs.get("ctrl_info", {})
    SDK.setup_Nd(N_d=num_f, fade_in=fade_in, fade_out=fade_out, ctrl_info=ctrl_info)

    online_mode = SDK.online_mode
    if online_mode:
        chunksize = run_kwargs.get("chunksize", (3, 5, 2))
        audio = np.concatenate([np.zeros((chunksize[0] * 640,), dtype=np.float32), audio], 0)
        split_len = int(sum(chunksize) * 0.04 * 16000) + 80  # 6480
        for i in range(0, len(audio), chunksize[1] * 640):
            audio_chunk = audio[i: i + split_len]
            if len(audio_chunk) < split_len:
                audio_chunk = np.pad(audio_chunk, (0, split_len - len(audio_chunk)), mode="constant")
            SDK.run_chunk(audio_chunk, chunksize)
    else:
        aud_feat = SDK.wav2feat.wav2feat(audio)
        SDK.audio2motion_queue.put(aud_feat)

    SDK.close()

    # Mux video and audio with ffmpeg
    cmd = (
        f'ffmpeg -loglevel error -y -i "{SDK.tmp_output_path}" '
        f'-i "{audio_path}" -map 0:v -map 1:a -c:v copy -c:a aac "{output_path}"'
    )
    ret = os.system(cmd)
    if ret != 0:
        raise RuntimeError("ffmpeg muxing failed. Ensure ffmpeg is installed and inputs are valid.")

    if not os.path.isfile(output_path):
        raise RuntimeError("Output file missing after ffmpeg step.")

    return output_path


# -----------------------------
# API layer
# -----------------------------
class InferenceRequest(BaseModel):
    audio_path: str = Field(..., description="Path to input .wav file")
    source_path: str = Field(..., description="Path to input image or video")
    output_path: str = Field(..., description="Path to desired output .mp4 file")

    # Optional knobs
    setup_kwargs: Optional[Dict[str, Any]] = Field(default=None, description="Args forwarded to SDK.setup")
    run_kwargs: Optional[Dict[str, Any]] = Field(default=None, description="Args used inside run, e.g., fade_in, chunksize")

    # Optional: per-request seeding for reproducibility
    seed: Optional[int] = Field(default=None)


class InferenceResponse(BaseModel):
    status: str
    output_path: str
    details: Optional[Dict[str, Any]] = None


app = FastAPI(title="Ditto Inference API", version="1.0.0")

# Global SDK instance + lock for single-GPU safety
_SDK: Optional[StreamSDK] = None
_sdk_lock = threading.Lock()


@app.on_event("startup")
def _init_sdk():
    """Initialize StreamSDK once at startup.

    Configure via environment variables:
    - DITTO_DATA_ROOT: path to model directory (default: ./checkpoints/ditto_trt_Ampere_Plus)
    - DITTO_CFG_PKL: path to cfg pkl (default: ./checkpoints/ditto_cfg/v0.4_hubert_cfg_trt.pkl)
    """
    global _SDK
    data_root = os.getenv("DITTO_DATA_ROOT", "./checkpoints/ditto_pytorch")
    cfg_pkl = os.getenv("DITTO_CFG_PKL", "./checkpoints/ditto_cfg/v0.4_hubert_cfg_pytorch.pkl")

    if not os.path.exists(data_root):
        raise RuntimeError(f"Model data_root does not exist: {data_root}")
    if not os.path.isfile(cfg_pkl):
        raise RuntimeError(f"Config pkl not found: {cfg_pkl}")

    _SDK = StreamSDK(cfg_pkl, data_root)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/infer")
async def infer(
        audio: UploadFile = File(..., description="WAV audio file"),
        source: UploadFile = File(..., description="Source image or video"),
        output_path: str = Form(..., description="Desired output .mp4 path"),
        setup_kwargs: Optional[str] = Form(None, description="JSON string for SDK.setup kwargs"),
        run_kwargs: Optional[str] = Form(None, description="JSON string for run kwargs (fade_in, chunksize, etc.)"),
        seed: Optional[int] = Form(None),
        return_file: Optional[bool] = Form(True, description="If true, return MP4 file; otherwise JSON with output_path"),
):
    """
    Multipart variant:
    - Files: `audio` (wav), `source` (image/video)
    - Form fields: `output_path` (string), optional `setup_kwargs`, `run_kwargs` (JSON strings), `seed`, `return_file`
    Returns:
      - MP4 file (default), or
      - JSON {status, output_path}
    """
    global _SDK
    if _SDK is None:
        raise HTTPException(status_code=500, detail="SDK not initialized")

    # Optional per-request seeding
    if seed is not None:
        seed_everything(seed)

    # Parse kwargs if provided as JSON strings
    try:
        setup_kw = json.loads(setup_kwargs) if setup_kwargs else {}
        run_kw = json.loads(run_kwargs) if run_kwargs else {}
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON in setup_kwargs/run_kwargs: {e}")

    more_kwargs: Dict[str, Any] = {
        "setup_kwargs": setup_kw,
        "run_kwargs": run_kw,
    }

    # Ensure output directory exists
    os.makedirs(os.path.dirname(os.path.abspath(output_path)) or ".", exist_ok=True)

    # Persist uploaded files to disk (so the existing run_inference can use paths)
    tmp_dir = os.getenv("DITTO_UPLOAD_TMP", "/tmp/ditto_uploads")
    os.makedirs(tmp_dir, exist_ok=True)

    # Build deterministic temp names under tmp_dir
    audio_tmp = os.path.join(tmp_dir, f"audio_{random.getrandbits(32)}.wav")
    source_ext = os.path.splitext(source.filename or "source.png")[1] or ".png"
    source_tmp = os.path.join(tmp_dir, f"source_{random.getrandbits(32)}{source_ext}")

    try:
        # Save audio
        with open(audio_tmp, "wb") as f:
            while True:
                chunk = await audio.read(1024 * 1024)
                if not chunk:
                    break
                f.write(chunk)

        # Save source
        with open(source_tmp, "wb") as f:
            while True:
                chunk = await source.read(1024 * 1024)
                if not chunk:
                    break
                f.write(chunk)

        # Run inference with lock (single-GPU safety)
        with _sdk_lock:
            try:
                final_path = run_inference(
                    _SDK,
                    audio_path=audio_tmp,
                    source_path=source_tmp,
                    output_path=output_path,
                    more_kwargs=more_kwargs,
                )
            except FileNotFoundError as e:
                raise HTTPException(status_code=400, detail=str(e))
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Inference failed: {e}")

        # Return the full video file (default) or JSON summary
        if return_file:
            filename = os.path.basename(final_path)
            # FastAPI will stream the file efficiently
            return FileResponse(
                path=final_path,
                media_type="video/mp4",
                filename=filename,
                headers={"Cache-Control": "no-store"},
            )
        else:
            return InferenceResponse(status="success", output_path=final_path)

    finally:
        # Best-effort cleanup of temp uploads
        for p in (audio_tmp, source_tmp):
            try:
                if os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass


# For local testing: `python app.py`
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False, workers=1)
