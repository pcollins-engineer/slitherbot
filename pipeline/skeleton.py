"""Skeletonization + centerline path helpers (pure NumPy/OpenCV).

Implemented without scikit-image or opencv-contrib so the base
``opencv-python`` dependency is enough.
"""

from typing import Optional

import numpy as np


def thin(binary: np.ndarray) -> np.ndarray:
    """Zhang-Suen thinning. Returns a 1-pixel-wide uint8 skeleton (0/1).

    Vectorized over the whole image per iteration; operate on a cropped
    blob for speed.
    """
    img = (binary > 0).astype(np.uint8)
    changed = True
    while changed:
        changed = False
        for step in (0, 1):
            P = np.pad(img, 1, mode="constant")
            P2 = P[:-2, 1:-1]; P3 = P[:-2, 2:]; P4 = P[1:-1, 2:]
            P5 = P[2:, 2:];    P6 = P[2:, 1:-1]; P7 = P[2:, :-2]
            P8 = P[1:-1, :-2]; P9 = P[:-2, :-2]

            B = P2 + P3 + P4 + P5 + P6 + P7 + P8 + P9
            seq = [P2, P3, P4, P5, P6, P7, P8, P9, P2]
            A = np.zeros_like(img)
            for i in range(8):
                A += ((seq[i] == 0) & (seq[i + 1] == 1)).astype(np.uint8)

            cond = (img == 1) & (B >= 2) & (B <= 6) & (A == 1)
            if step == 0:
                cond &= (P2 * P4 * P6 == 0) & (P4 * P6 * P8 == 0)
            else:
                cond &= (P2 * P4 * P8 == 0) & (P2 * P6 * P8 == 0)

            if cond.any():
                img[cond] = 0
                changed = True
    return img


def skeleton_points(skel: np.ndarray, max_points: int) -> np.ndarray:
    """Return skeleton pixel coords as an (N, 2) array of (y, x).

    Randomly subsampled to ``max_points`` to bound the path-walk cost.
    """
    pts = np.argwhere(skel > 0)
    if len(pts) > max_points:
        idx = np.linspace(0, len(pts) - 1, max_points).astype(int)
        pts = pts[idx]
    return pts


def farthest_endpoints(points: np.ndarray) -> np.ndarray:
    """Approximate the two ends of an elongated point set (double sweep)."""
    centroid = points.mean(axis=0)
    a = points[np.argmax(((points - centroid) ** 2).sum(axis=1))]
    b = points[np.argmax(((points - a) ** 2).sum(axis=1))]
    c = points[np.argmax(((points - b) ** 2).sum(axis=1))]
    return np.array([b, c])


def order_path(points: np.ndarray, start: np.ndarray) -> np.ndarray:
    """Greedy nearest-neighbor ordering of ``points`` starting near ``start``.

    Good enough for a smooth, mostly-linear skeleton; branches may cause
    small jumps (acceptable for v0 proposals).
    """
    n = len(points)
    used = np.zeros(n, dtype=bool)
    order = []
    cur = int(np.argmin(((points - start) ** 2).sum(axis=1)))
    for _ in range(n):
        used[cur] = True
        order.append(cur)
        dist = ((points - points[cur]) ** 2).sum(axis=1).astype(float)
        dist[used] = np.inf
        nxt = int(np.argmin(dist))
        if not np.isfinite(dist[nxt]):
            break
        cur = nxt
    return points[order]
