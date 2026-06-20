"""Background-grid pitch estimation for screen-space localization.

Slither.io draws a faint fixed-pitch lattice. Recovering the pitch gives
the pixels-per-world-unit scale, which anchors the parametric screen model
and lets detections be tracked in world coordinates across frames.

v0 implementation: find the dominant spatial period of the row/column mean
intensity via FFT. Good enough to estimate pitch; a Hough-line or
phase-correlation refinement is a TODO.
"""

from typing import Optional

import cv2
import numpy as np


def _dominant_period(profile: np.ndarray, min_period: int = 8, max_period: int = 200) -> Optional[float]:
    profile = profile - profile.mean()
    if np.allclose(profile, 0):
        return None
    spectrum = np.abs(np.fft.rfft(profile * np.hanning(len(profile))))
    freqs = np.fft.rfftfreq(len(profile))

    best_period = None
    best_power = 0.0
    for f, power in zip(freqs[1:], spectrum[1:]):
        if f == 0:
            continue
        period = 1.0 / f
        if min_period <= period <= max_period and power > best_power:
            best_power = power
            best_period = period
    return best_period


def estimate_grid_pitch(bgr: np.ndarray) -> Optional[float]:
    """Estimate grid pitch in pixels, or None if no clear lattice is found."""
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
    col_period = _dominant_period(gray.mean(axis=0))  # vertical lines
    row_period = _dominant_period(gray.mean(axis=1))  # horizontal lines

    periods = [p for p in (col_period, row_period) if p is not None]
    if not periods:
        return None
    return float(np.mean(periods))
