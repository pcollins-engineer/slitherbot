"""HSV color thresholding for isolating Slither.io entities."""

from typing import Tuple

import cv2
import numpy as np


class ColorFilter:
    def __init__(self):
        # Default wide-open HSV range.
        self.h_min = 0
        self.h_max = 179
        self.s_min = 0
        self.s_max = 255
        self.v_min = 0
        self.v_max = 255

    def set_range(self, h_min, h_max, s_min, s_max, v_min, v_max):
        self.h_min = int(h_min)
        self.h_max = int(h_max)
        self.s_min = int(s_min)
        self.s_max = int(s_max)
        self.v_min = int(v_min)
        self.v_max = int(v_max)

    def apply(self, bgr_image: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Return (mask, filtered_bgr).

        mask: single-channel 0/255
        filtered_bgr: original image with mask applied
        """
        hsv = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2HSV)
        lower = np.array([self.h_min, self.s_min, self.v_min], dtype=np.uint8)
        upper = np.array([self.h_max, self.s_max, self.v_max], dtype=np.uint8)
        mask = cv2.inRange(hsv, lower, upper)
        filtered = cv2.bitwise_and(bgr_image, bgr_image, mask=mask)
        return mask, filtered
