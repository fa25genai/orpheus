from __future__ import annotations

import logging
import os
import tempfile
import urllib.request
from dataclasses import dataclass
from typing import Any

import numpy as np

from .utils import Box, clip_box

log = logging.getLogger(__name__)


@dataclass
class Detection:
    box: Box
    score: float
    label: str = "Figure"


@dataclass
class DetectionResult:
    detections: list[Detection]


class FigureDetector:
    def detect(self, image: np.ndarray) -> DetectionResult:  # image in RGB
        raise NotImplementedError


class LayoutParserDetector(FigureDetector):
    def __init__(self, score_thresh: float = 0.8, figure_thresh: float = 0.9) -> None:
        self.score_thresh = score_thresh
        self.figure_thresh = figure_thresh
        self._model: Any | None = None
        self._init_error: str | None = None

    def _ensure_model(self) -> None:
        if self._model is not None or self._init_error is not None:
            return
        try:
            import layoutparser as lp
            from PIL import Image

            # Compatibility shim for Pillow >= 10, used by detectron2
            if not hasattr(Image, "LINEAR"):
                linear = getattr(Image, "BILINEAR", None)
                if linear is None:
                    resampling = getattr(Image, "Resampling", None)
                    if resampling is not None:
                        linear = getattr(resampling, "BILINEAR", None)
                if linear is not None:
                    Image.LINEAR = linear

            self._lp = lp
            weights_path = self._ensure_publaynet_weights()
            self._model = lp.Detectron2LayoutModel(
                config_path="lp://PubLayNet/faster_rcnn_R_50_FPN_3x/config",
                model_path=weights_path,
                extra_config=[
                    "MODEL.ROI_HEADS.SCORE_THRESH_TEST",
                    self.score_thresh,
                ],
                label_map={0: "Text", 1: "Title", 2: "List", 3: "Table", 4: "Figure"},
            )
            log.info("Initialized LayoutParser Detectron2 model (PubLayNet)")
        except Exception as e:  # pragma: no cover - import-time issues
            self._init_error = str(e)
            log.warning("Failed to initialize LayoutParser model: %s", e)

    def detect(self, image: np.ndarray) -> DetectionResult:
        self._ensure_model()
        if self._model is None:
            # No fallback. We require detectron in Docker.
            from fastapi import HTTPException
            log.error("LayoutParser model unavailable: %s", self._init_error)
            err = self._init_error
            msg = f"LayoutParser/Detectron2 unavailable: {err}"
            raise HTTPException(status_code=500, detail=msg)

        h, w = image.shape[:2]
        layout = self._model.detect(image)
        detections: list[Detection] = []
        for block in layout:
            t = getattr(block, "type", None)
            score = getattr(block, "score", 0.0) or 0.0
            if t == "Figure" and score >= self.figure_thresh:
                x1, y1, x2, y2 = map(int, block.coordinates)
                b = clip_box(Box(x1, y1, x2, y2), w, h)
                detections.append(Detection(box=b, score=float(score), label="Figure"))
        return DetectionResult(detections)

    def _ensure_publaynet_weights(self) -> str:
        # Download PubLayNet Faster R-CNN R50-FPN 3x weights once to a stable path.
        # Using explicit download avoids iopath cache filenames that include querystrings.
        url = os.getenv(
            "PUBLAYNET_MODEL_URL",
            "https://www.dropbox.com/s/dgy9c10wykk4lq4/model_final.pth?dl=1",
        )
        weights_dir = os.getenv("WEIGHTS_DIR", "/weights")
        os.makedirs(weights_dir, exist_ok=True)
        target = os.path.join(
            weights_dir, "publaynet_frcnn_R50_FPN_3x_model_final.pth"
        )
        if os.path.exists(target):
            return target
        # Download atomically
        fd, tmp = tempfile.mkstemp(dir=weights_dir, prefix="publaynet_dl_", suffix=".tmp")
        os.close(fd)
        try:
            logging.info("Downloading PubLayNet weights to %s", target)
            urllib.request.urlretrieve(url, tmp)
            os.replace(tmp, target)
        finally:
            try:
                if os.path.exists(tmp):
                    os.remove(tmp)
            except OSError:
                pass
        return target


def get_detector(preferred: str | None = None) -> FigureDetector:
    # Always use LayoutParser/Detectron2. No OpenCV-only mode.
    det = LayoutParserDetector()
    det._ensure_model()
    if det._model is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail="LayoutParser/Detectron2 not available")
    return det

    
