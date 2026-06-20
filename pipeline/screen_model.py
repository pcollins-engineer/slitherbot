"""Parametric per-frame "screen model" (OpenSCAD-style scene summary).

A compact, geometric description of one frame: image size, recovered scale
(from the grid), and entity counts/poses. Easy to sanity-check and to feed
downstream agents. Extend ``extra`` with zoom/minimap/self-snake params as
those solvers come online.
"""

from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional

from pipeline.config import CLASS_NAMES, Detection


@dataclass
class ScreenModel:
    image: str
    width: int
    height: int
    grid_pitch_px: Optional[float] = None
    px_per_world_unit: Optional[float] = None  # filled once world grid size is known
    counts: Dict[str, int] = field(default_factory=dict)
    entities: List[Dict] = field(default_factory=list)
    extra: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return asdict(self)


def build(image_name: str, width: int, height: int,
          detections: List[Detection], grid_pitch_px: Optional[float]) -> ScreenModel:
    counts = {name: 0 for name in CLASS_NAMES}
    entities: List[Dict] = []
    for d in detections:
        name = CLASS_NAMES[d.cls]
        counts[name] += 1
        entities.append({
            "class": name,
            "cx": round(d.cx, 1),
            "cy": round(d.cy, 1),
            "w": round(d.w, 1),
            "h": round(d.h, 1),
            "radius": round(d.radius, 1),
        })
    return ScreenModel(
        image=image_name,
        width=width,
        height=height,
        grid_pitch_px=None if grid_pitch_px is None else round(grid_pitch_px, 2),
        counts=counts,
        entities=entities,
    )
