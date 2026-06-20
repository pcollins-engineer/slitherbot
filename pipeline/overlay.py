"""Debug overlay: draw proposed detections back onto the frame for QA."""

from typing import List

import cv2
import numpy as np

from pipeline.config import CLASS_NAMES, Detection

# BGR colors per class.
_COLORS = {
    "snake_head": (0, 0, 255),     # red
    "snake_tail": (0, 165, 255),   # orange
    "body_segment": (0, 255, 255), # yellow
    "pellet": (0, 255, 0),         # green
    "boost_orb": (255, 0, 255),    # magenta
}


def draw(bgr: np.ndarray, detections: List[Detection]) -> np.ndarray:
    out = bgr.copy()
    for d in detections:
        name = CLASS_NAMES[d.cls]
        color = _COLORS.get(name, (255, 255, 255))
        if name in ("body_segment", "pellet") and d.radius > 0:
            cv2.circle(out, (int(d.cx), int(d.cy)), max(1, int(d.radius)), color, 1)
        else:
            x1 = int(d.cx - d.w / 2); y1 = int(d.cy - d.h / 2)
            x2 = int(d.cx + d.w / 2); y2 = int(d.cy + d.h / 2)
            cv2.rectangle(out, (x1, y1), (x2, y2), color, 1)
    return out
