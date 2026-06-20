"""Body "sausage" → centerline circle-chain + head/tail proposals.

Each snake body blob becomes:
  - a chain of ``body_segment`` boxes sampled along its skeleton, each sized
    to the local body thickness (distance transform), and
  - a ``snake_head`` / ``snake_tail`` box at the two ends (oriented toward a
    detected head centroid when one is available).

This is the detection-mode fallback for the sausage shape; if you switch to
YOLOv8-seg the body becomes a single mask instead (see README).
"""

from typing import List, Optional, Tuple

import cv2
import numpy as np

from pipeline import skeleton
from pipeline.config import Detection, NAME_TO_ID, Settings


def _nearest_dist(point_xy: Tuple[float, float], centers: List[Tuple[float, float]]) -> float:
    if not centers:
        return float("inf")
    px, py = point_xy
    return min((px - cx) ** 2 + (py - cy) ** 2 for cx, cy in centers) ** 0.5


def body_detections(
    mask: np.ndarray,
    settings: Settings,
    head_centers: Optional[List[Tuple[float, float]]] = None,
) -> List[Detection]:
    head_centers = head_centers or []
    out: List[Detection] = []

    # Close small anti-aliased/shaded gaps so a single snake stays one component.
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    num, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    for i in range(1, num):
        if int(stats[i, cv2.CC_STAT_AREA]) < settings.min_body_area:
            continue

        x = int(stats[i, cv2.CC_STAT_LEFT]); y = int(stats[i, cv2.CC_STAT_TOP])
        w = int(stats[i, cv2.CC_STAT_WIDTH]); h = int(stats[i, cv2.CC_STAT_HEIGHT])

        blob = (labels[y:y + h, x:x + w] == i).astype(np.uint8)
        dt = cv2.distanceTransform(blob, cv2.DIST_L2, 5)
        skel = skeleton.thin(blob)
        pts = skeleton.skeleton_points(skel, settings.max_skeleton_points)
        if len(pts) < 2:
            continue

        ends = skeleton.farthest_endpoints(pts)
        ordered = skeleton.order_path(pts, ends[0])

        # Sample the centerline with a minimum spacing tied to local thickness.
        samples: List[Tuple[float, float, float]] = []  # (x_global, y_global, radius)
        last_yx = None
        for (py, px) in ordered:
            r = float(dt[py, px])
            spacing = max(settings.min_spacing_px, settings.spacing_factor * r)
            if last_yx is None or np.hypot(py - last_yx[0], px - last_yx[1]) >= spacing:
                samples.append((float(px + x), float(py + y), r))
                last_yx = (py, px)
        if len(samples) < 2:
            continue

        # Orient so samples[0] is the head end (nearest a detected head, if any).
        if _nearest_dist((samples[0][0], samples[0][1]), head_centers) > \
           _nearest_dist((samples[-1][0], samples[-1][1]), head_centers):
            samples.reverse()

        for j, (cx, cy, r) in enumerate(samples):
            side = max(2.0 * r, 4.0)
            if j == 0:
                cls = NAME_TO_ID["snake_head"]
            elif j == len(samples) - 1:
                cls = NAME_TO_ID["snake_tail"]
            else:
                cls = NAME_TO_ID["body_segment"]
            out.append(Detection(cls=cls, cx=cx, cy=cy, w=side, h=side, radius=r))

    return out
