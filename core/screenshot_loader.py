"""Loads and navigates screenshot frames from a folder on disk."""

import os
from typing import List, Optional


class ScreenshotLoader:
    SUPPORTED_EXTS = (".png", ".jpg", ".jpeg", ".bmp")

    def __init__(self, folder: str = "screenshots"):
        self.folder = folder
        self.files: List[str] = []
        self.index: int = 0
        self._scan_folder()

    def _scan_folder(self):
        if not os.path.isdir(self.folder):
            os.makedirs(self.folder, exist_ok=True)
        self.files = [
            os.path.join(self.folder, f)
            for f in sorted(os.listdir(self.folder))
            if f.lower().endswith(self.SUPPORTED_EXTS)
        ]
        self.index = 0

    def set_folder(self, folder: str):
        self.folder = folder
        self._scan_folder()

    def has_images(self) -> bool:
        return len(self.files) > 0

    def current_path(self) -> Optional[str]:
        if not self.has_images():
            return None
        return self.files[self.index]

    def next(self) -> Optional[str]:
        if not self.has_images():
            return None
        self.index = (self.index + 1) % len(self.files)
        return self.current_path()

    def prev(self) -> Optional[str]:
        if not self.has_images():
            return None
        self.index = (self.index - 1) % len(self.files)
        return self.current_path()
