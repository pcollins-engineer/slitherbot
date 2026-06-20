"""Pixel-sampling logic for the eyedropper tool."""

from typing import Dict, Optional, Tuple

import cv2
import numpy as np


def canvas_to_image_coords(
    x_click: int,
    y_click: int,
    img_width: int,
    img_height: int,
    max_size: int = 400,
) -> Optional[Tuple[int, int]]:
    """Map a click on the (thumbnail-scaled) canvas back to image coordinates.

    Returns None if the click falls outside the displayed image area.
    """
    scale = min(max_size / img_width, max_size / img_height)
    disp_w = int(img_width * scale)
    disp_h = int(img_height * scale)

    if x_click >= disp_w or y_click >= disp_h:
        return None

    x_img = int(x_click / scale)
    y_img = int(y_click / scale)

    if x_img < 0 or x_img >= img_width or y_img < 0 or y_img >= img_height:
        return None

    return x_img, y_img


def sample_pixel(bgr_image: np.ndarray, x_img: int, y_img: int) -> Dict:
    """Sample a pixel and return its RGB, HSV, hex, and coordinate."""
    b, g, r = bgr_image[y_img, x_img]
    rgb = (int(r), int(g), int(b))

    hsv_img = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2HSV)
    h, s, v = hsv_img[y_img, x_img]
    hsv = (int(h), int(s), int(v))

    hex_color = "#{:02X}{:02X}{:02X}".format(rgb[0], rgb[1], rgb[2])

    return {"rgb": rgb, "hsv": hsv, "hex": hex_color, "coord": (x_img, y_img)}
