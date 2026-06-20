"""Core (non-GUI) logic for the Slither.io color tool."""

from .screenshot_loader import ScreenshotLoader
from .color_filter import ColorFilter
from .export_json import FilterExporter

__all__ = ["ScreenshotLoader", "ColorFilter", "FilterExporter"]
