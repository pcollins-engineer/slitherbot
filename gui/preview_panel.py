"""Helpers for converting OpenCV images into Tk-displayable images."""

from typing import Tuple

import cv2
import numpy as np
from PIL import Image, ImageTk


def bgr_to_tk(bgr: np.ndarray, max_size: Tuple[int, int] = (400, 400)) -> ImageTk.PhotoImage:
    """Convert a BGR image to a thumbnail PhotoImage for a Tk canvas."""
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(rgb)
    pil_img.thumbnail(max_size, Image.LANCZOS)
    return ImageTk.PhotoImage(pil_img)


def gray_to_tk(gray: np.ndarray, max_size: Tuple[int, int] = (400, 400)) -> ImageTk.PhotoImage:
    """Convert a single-channel (0-255) mask to a thumbnail PhotoImage."""
    pil_img = Image.fromarray(gray).convert("L")
    pil_img.thumbnail(max_size, Image.LANCZOS)
    return ImageTk.PhotoImage(pil_img)
