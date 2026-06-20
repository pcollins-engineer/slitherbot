"""Draw a Perception onto a frame for the read-only live view."""

import cv2
import numpy as np

from .types import Perception

GREEN = (0, 255, 0)
RED = (0, 0, 255)
YELLOW = (0, 255, 255)
MAGENTA = (255, 0, 255)
WHITE = (255, 255, 255)


def draw(frame: np.ndarray, per: Perception) -> np.ndarray:
    vis = frame.copy()
    h, w = vis.shape[:2]

    # screen center crosshair (= roughly where your head is)
    cx, cy = w // 2, h // 2
    cv2.drawMarker(vis, (cx, cy), WHITE, cv2.MARKER_CROSS, 18, 1)

    for p in per.pellets:
        cv2.circle(vis, (int(p.cx), int(p.cy)), max(2, int(p.r)), GREEN, 1)

    for s in per.snakes:
        color = YELLOW if s.is_self else RED
        cv2.rectangle(vis, (s.x, s.y), (s.x + s.w, s.y + s.h), color, 2)
        label = "YOU" if s.is_self else "enemy"
        cv2.putText(vis, label, (s.x, max(12, s.y - 4)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)
        if s.is_self and s.head is not None:
            cv2.circle(vis, s.head, 6, MAGENTA, -1)
            cv2.putText(vis, "head", (s.head[0] + 8, s.head[1]),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, MAGENTA, 1, cv2.LINE_AA)

    return vis


def hud(vis: np.ndarray, text: str) -> None:
    cv2.rectangle(vis, (0, 0), (vis.shape[1], 24), (0, 0, 0), -1)
    cv2.putText(vis, text, (6, 17), cv2.FONT_HERSHEY_SIMPLEX, 0.55, WHITE, 1, cv2.LINE_AA)
