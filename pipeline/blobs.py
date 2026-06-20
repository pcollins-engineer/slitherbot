"""Connected-component extraction for the simple (round) entity classes."""

from typing import List, Tuple

import cv2
import numpy as np

from pipeline.config import Detection, NAME_TO_ID


def _components(mask: np.ndarray, min_area: int):
    """Yield (x, y, w, h, area, cx, cy) for each component above ``min_area``."""
    num, _labels, stats, centroids = cv2.connectedComponentsWithStats(mask, connectivity=8)
    for i in range(1, num):  # skip background (0)
        area = int(stats[i, cv2.CC_STAT_AREA])
        if area < min_area:
            continue
        x = int(stats[i, cv2.CC_STAT_LEFT])
        y = int(stats[i, cv2.CC_STAT_TOP])
        w = int(stats[i, cv2.CC_STAT_WIDTH])
        h = int(stats[i, cv2.CC_STAT_HEIGHT])
        cx, cy = float(centroids[i][0]), float(centroids[i][1])
        yield x, y, w, h, area, cx, cy


def box_detections(mask: np.ndarray, class_name: str, min_area: int) -> List[Detection]:
    """One tight box per blob — used for pellets, heads, and boost orbs."""
    cls = NAME_TO_ID[class_name]
    out: List[Detection] = []
    for x, y, w, h, _area, cx, cy in _components(mask, min_area):
        out.append(Detection(cls=cls, cx=cx, cy=cy, w=float(w), h=float(h),
                             radius=0.5 * (w + h) / 2.0))
    return out


def head_centers(mask: np.ndarray, min_area: int) -> List[Tuple[float, float]]:
    """Centroids of head blobs — used to orient the body head/tail."""
    return [(cx, cy) for *_rest, cx, cy in _components(mask, min_area)]
