"""Color-filter perception backend.

Reuses the exported HSV filters + the pipeline's blob logic to produce
lightweight per-frame observations fast enough for a live loop. Deliberately
skips the skeleton circle-chain (that's for offline YOLO labeling) — for live
seek/avoid we only need pellet positions and whole-snake boxes.

Own-snake heuristic: slither keeps your head near screen center, so the snake
whose body is nearest the center is "you", and your head is the body pixel
closest to the center.
"""

from typing import List, Optional

import cv2
import numpy as np

from pipeline.config import Settings, load_filters

from .types import Pellet, Perception, Snake


class ColorFilterPerceiver:
    def __init__(self, filters_dir: str = "filters",
                 settings: Optional[Settings] = None,
                 min_snake_area: int = 800):
        self.specs = load_filters(filters_dir)
        self.settings = settings or Settings()
        self.min_snake_area = min_snake_area
        self.body_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))

    def perceive(self, bgr: np.ndarray) -> Perception:
        h, w = bgr.shape[:2]
        cx, cy = w / 2.0, h / 2.0
        per = Perception()

        body_mask = None
        for spec in self.specs:
            mask, _ = spec.color_filter.apply(bgr)
            if spec.kind in ("pellet", "boost_orb"):
                per.pellets += self._pellets(mask)
            elif spec.kind == "body":
                body_mask = mask if body_mask is None else cv2.bitwise_or(body_mask, mask)

        if body_mask is not None:
            per.snakes = self._snakes(body_mask, cx, cy)
        return per

    def _pellets(self, mask: np.ndarray) -> List[Pellet]:
        out: List[Pellet] = []
        n, _l, stats, cent = cv2.connectedComponentsWithStats(mask, connectivity=8)
        for i in range(1, n):
            a = int(stats[i, cv2.CC_STAT_AREA])
            if a < self.settings.min_pellet_area:
                continue
            w = int(stats[i, cv2.CC_STAT_WIDTH]); h = int(stats[i, cv2.CC_STAT_HEIGHT])
            if w == 0 or h == 0:
                continue
            extent = a / float(w * h)
            aspect = max(w, h) / float(min(w, h))
            if extent < 0.45 or aspect > 2.5:  # drop thin UI text / lines
                continue
            out.append(Pellet(float(cent[i][0]), float(cent[i][1]), 0.5 * (w + h) / 2.0))
        return out

    def _snakes(self, body_mask: np.ndarray, cx: float, cy: float) -> List[Snake]:
        body_mask = cv2.morphologyEx(body_mask, cv2.MORPH_CLOSE, self.body_kernel)
        n, labels, stats, cent = cv2.connectedComponentsWithStats(body_mask, connectivity=8)
        idxs = [i for i in range(1, n) if int(stats[i, cv2.CC_STAT_AREA]) >= self.min_snake_area]
        if not idxs:
            return []

        self_i = min(idxs, key=lambda i: (cent[i][0] - cx) ** 2 + (cent[i][1] - cy) ** 2)
        snakes: List[Snake] = []
        for i in idxs:
            s = Snake(
                x=int(stats[i, cv2.CC_STAT_LEFT]), y=int(stats[i, cv2.CC_STAT_TOP]),
                w=int(stats[i, cv2.CC_STAT_WIDTH]), h=int(stats[i, cv2.CC_STAT_HEIGHT]),
                cx=float(cent[i][0]), cy=float(cent[i][1]),
                is_self=(i == self_i),
            )
            if s.is_self:
                ys, xs = np.where(labels == i)
                k = int(np.argmin((xs - cx) ** 2 + (ys - cy) ** 2))
                s.head = (int(xs[k]), int(ys[k]))
            snakes.append(s)
        return snakes
