"""Saves HSV filter ranges to JSON for later YOLO preprocessing."""

import json
import os

from .color_filter import ColorFilter


class FilterExporter:
    def __init__(self, folder: str = "filters"):
        self.folder = folder
        os.makedirs(self.folder, exist_ok=True)

    def save(self, name: str, color_filter: ColorFilter) -> str:
        data = {
            "h_min": color_filter.h_min,
            "h_max": color_filter.h_max,
            "s_min": color_filter.s_min,
            "s_max": color_filter.s_max,
            "v_min": color_filter.v_min,
            "v_max": color_filter.v_max,
        }
        path = os.path.join(self.folder, f"{name}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return path
