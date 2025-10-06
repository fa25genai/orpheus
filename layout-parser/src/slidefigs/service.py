"""FastAPI application for extracting figure crops from slide images."""

from __future__ import annotations

import base64
import io
import logging
import os
from typing import Any

import numpy as np
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from PIL import Image

from .detectors import get_detector

log = logging.getLogger(__name__)


async def _read_image_file(file: UploadFile) -> np.ndarray:
    """Return the uploaded image as an RGB NumPy array.

    Invalid payloads raise an :class:`HTTPException` with a 400 status code.
    The temporary upload is always closed before returning.
    """

    try:
        data = await file.read()
        if not data:
            raise ValueError("empty file")
        img = Image.open(io.BytesIO(data)).convert("RGB")
        return np.array(img)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image: {e}") from e
    finally:
        # Ensure temporary files/buffers are closed
        try:
            await file.close()
        except Exception:
            pass


def create_app() -> FastAPI:
    """Instantiate and configure the FastAPI service."""

    app = FastAPI(title="Slides Figure Extraction Service", version="0.1.0")

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        """Expose a basic readiness probe for orchestration."""

        return {"status": "ok"}

    @app.post("/extract")
    async def extract(
        file: UploadFile = File(..., description="Slide image file (PNG/JPEG)"),
    ) -> JSONResponse:
        """Detect figure regions and return cropped images as base64 PNG blobs."""

        image = await _read_image_file(file)
        detector = get_detector()
        result = detector.detect(image)

        items: list[dict[str, Any]] = []
        for det in result.detections:
            b = det.box
            x1, y1, x2, y2 = b.x1, b.y1, b.x2, b.y2
            if x2 <= x1 or y2 <= y1:
                continue
            crop = image[y1:y2, x1:x2]
            im = Image.fromarray(crop)
            im_buf = io.BytesIO()
            im.save(im_buf, format="PNG")
            b64 = base64.b64encode(im_buf.getvalue()).decode("ascii")
            items.append({
                "score": float(det.score),
                "box": {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
                "image": {
                    "format": "png",
                    "width": im.width,
                    "height": im.height,
                    "data": b64,
                },
            })

        return JSONResponse({"count": len(items), "items": items})

    return app


app = create_app()


def main() -> None:  # pragma: no cover
    """Run the service with uvicorn using environment configuration."""

    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8156"))
    uvicorn.run("slidefigs.service:app", host=host, port=port, reload=False)
