"""Write YOLO-format labels and a data.yaml."""

import os
from typing import List

from pipeline.config import CLASS_NAMES, Detection


def write_label(path: str, detections: List[Detection], img_w: int, img_h: int) -> None:
    """Write one YOLO label file: ``cls cx cy w h`` (all normalized 0..1)."""
    lines = []
    for d in detections:
        cx = min(max(d.cx / img_w, 0.0), 1.0)
        cy = min(max(d.cy / img_h, 0.0), 1.0)
        w = min(max(d.w / img_w, 0.0), 1.0)
        h = min(max(d.h / img_h, 0.0), 1.0)
        lines.append(f"{d.cls} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
        if lines:
            f.write("\n")


def write_data_yaml(path: str, dataset_root: str) -> None:
    """Write an Ultralytics ``data.yaml`` pointing at images/ + labels/."""
    names = "\n".join(f"  {i}: {name}" for i, name in enumerate(CLASS_NAMES))
    content = (
        f"path: {os.path.abspath(dataset_root)}\n"
        f"train: images\n"
        f"val: images\n"
        f"names:\n{names}\n"
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
