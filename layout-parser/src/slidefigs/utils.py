from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class Box:
    x1: int
    y1: int
    x2: int
    y2: int

    def width(self) -> int:
        return max(0, self.x2 - self.x1)

    def height(self) -> int:
        return max(0, self.y2 - self.y1)

    def area(self) -> int:
        return self.width() * self.height()

    def as_tuple(self) -> tuple[int, int, int, int]:
        return (self.x1, self.y1, self.x2, self.y2)


def clip_box(box: Box, w: int, h: int) -> Box:
    x1 = max(0, min(w, box.x1))
    y1 = max(0, min(h, box.y1))
    x2 = max(0, min(w, box.x2))
    y2 = max(0, min(h, box.y2))
    # Ensure non-negative area
    if x2 < x1:
        x1, x2 = x2, x1
    if y2 < y1:
        y1, y2 = y2, y1
    return Box(x1, y1, x2, y2)


def iou(a: Box, b: Box) -> float:
    ix1 = max(a.x1, b.x1)
    iy1 = max(a.y1, b.y1)
    ix2 = min(a.x2, b.x2)
    iy2 = min(a.y2, b.y2)
    iw = max(0, ix2 - ix1)
    ih = max(0, iy2 - iy1)
    inter = iw * ih
    if inter == 0:
        return 0.0
    union = a.area() + b.area() - inter
    return inter / union if union > 0 else 0.0


def merge_overlaps(boxes: Iterable[Box], iou_threshold: float = 0.3) -> list[Box]:
    # Simple NMS-style merge: keep boxes with max area and drop overlaps
    sorted_boxes = sorted(boxes, key=lambda b: b.area(), reverse=True)
    kept: list[Box] = []
    for b in sorted_boxes:
        if all(iou(b, k) < iou_threshold for k in kept):
            kept.append(b)
    return kept
