# ditto_server.py — FastAPI wrapper for Ditto Talking Head
import os, tempfile, json, asyncio
from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, ORJSONResponse
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

# Ditto imports (assumes you run from the repo root)
from stream_pipeline_offline import StreamSDK
from inference import run as run_inference

# --- Config via environment (edit paths if needed) ---
DITTO_DATA_ROOT = Path(os.getenv("DITTO_DATA_ROOT", "./checkpoints/ditto_pytorch")).resolve()
DITTO_CFG_PKL   = Path(os.getenv("DITTO_CFG_PKL",
                                 "./checkpoints/ditto_cfg/v0.4_hubert_cfg_pytorch.pkl")).resolve()
MAX_CONCURRENT = int(os.getenv("MAX_CONCURRENT", "1"))

if not DITTO_DATA_ROOT.exists():
    raise RuntimeError(f"DITTO_DATA_ROOT not found: {DITTO_DATA_ROOT}")
if not DITTO_CFG_PKL.exists():
    raise RuntimeError(f"DITTO_CFG_PKL not found: {DITTO_CFG_PKL}")

# Instantiate SDK once (heavy)
SDK = StreamSDK(str(DITTO_CFG_PKL), str(DITTO_DATA_ROOT))

app = FastAPI(title="Ditto Talking Head", default_response_class=ORJSONResponse)
_sem = asyncio.Semaphore(MAX_CONCURRENT)

class InferParams(BaseModel):
    max_size: int = 1920
    sampling_timesteps: int = 50
    extra: Dict[str, Any] = {}

@app.get("/health")
async def health():
    import torch, platform, sys
    #import onnxruntime as ort
    return {
        "python": sys.version.split()[0],
        "device": "cuda" if torch.cuda.is_available() else ("mps" if torch.backends.mps.is_available() else "cpu"),
        "torch_mps": torch.backends.mps.is_available(),
        "torch_cuda": torch.cuda.is_available(),
        #"ort_providers": ort.get_available_providers(),
        "platform": platform.platform(),
        "data_root": str(DITTO_DATA_ROOT),
        "cfg_pkl": str(DITTO_CFG_PKL),
        "max_concurrent": MAX_CONCURRENT
    }

@app.post("/infer")
async def infer(
    image: UploadFile = File(..., description="Source image (PNG/JPG)"),
    audio: UploadFile = File(..., description="Driving audio (WAV)"),
    params_json: str = Form("{}", description="JSON of optional params"),
):
    try:
        params = InferParams(**json.loads(params_json))
    except Exception as e:
        raise HTTPException(400, f"Invalid params_json: {e}")

    workdir = Path(tempfile.mkdtemp(prefix="ditto_srv_"))
    img_path = workdir / "image.png"
    aud_path = workdir / "audio.wav"
    out_path = workdir / "result.mp4"

    # Save uploads
    img_bytes = await image.read()
    aud_bytes = await audio.read()
    if not img_bytes: raise HTTPException(400, "Empty image")
    if not aud_bytes: raise HTTPException(400, "Empty audio")
    img_path.write_bytes(img_bytes)
    aud_path.write_bytes(aud_bytes)

    # Prepare setup kwargs (keep small to start)
    setup_kwargs = {"max_size": int(params.max_size)}
    setup_kwargs.update(params.extra or {})

    async with _sem:
        try:
            def _do_run():
                # inference.run calls SDK.setup internally
                run_inference(SDK, str(aud_path), str(img_path), str(out_path))
            await run_in_threadpool(_do_run)
        except Exception as e:
            raise HTTPException(500, f"Inference failed: {e}")

    if not out_path.exists():
        raise HTTPException(500, "result.mp4 not produced")

    return FileResponse(str(out_path), media_type="video/mp4", filename="result.mp4")