"""Shared config: class map, tunable settings, and filter loading."""

import glob
import json
import os
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from core import ColorFilter

# YOLO class order. Index == class id written to label files.
CLASS_NAMES: List[str] = [
    "snake_head",
    "snake_tail",
    "body_segment",
    "pellet",
    "boost_orb",
]
NAME_TO_ID = {name: i for i, name in enumerate(CLASS_NAMES)}


@dataclass
class Settings:
    """Tunable thresholds for the auto-labeler."""

    # Drop connected components smaller than this (px²) as noise.
    min_pellet_area: int = 8
    min_head_area: int = 30
    min_body_area: int = 200

    # Body centerline sampling.
    spacing_factor: float = 1.0   # min gap between samples = factor * local radius
    min_spacing_px: float = 6.0   # absolute floor on that gap
    max_skeleton_points: int = 2500  # subsample cap for the O(n²) path walk

    # Grid detection.
    detect_grid: bool = True


@dataclass
class FilterSpec:
    """A loaded filter + the kind of entity it isolates."""

    name: str
    color_filter: ColorFilter
    kind: str  # "pellet" | "head" | "body" | "boost_orb"


@dataclass
class Detection:
    """One proposed YOLO box, in pixel coordinates (center + size)."""

    cls: int
    cx: float
    cy: float
    w: float
    h: float
    radius: float = 0.0  # for body/pellet circles; used by the overlay


def _kind_from_name(name: str) -> Optional[str]:
    low = name.lower()
    if "pellet" in low or "food" in low:
        return "pellet"
    if "head" in low:
        return "head"
    if "body" in low:
        return "body"
    if "boost" in low or "orb" in low:
        return "boost_orb"
    return None


def load_filters(folder: str) -> List[FilterSpec]:
    """Load every ``*.json`` filter, inferring its entity kind from the name."""
    specs: List[FilterSpec] = []
    for path in sorted(glob.glob(os.path.join(folder, "*.json"))):
        name = os.path.splitext(os.path.basename(path))[0]
        kind = _kind_from_name(name)
        if kind is None:
            print(f"  ! skipping {path}: can't infer entity kind from name "
                  f"(expected 'head', 'body', 'pellet', or 'boost' in the name)")
            continue
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        cf = ColorFilter()
        cf.set_range(
            data["h_min"], data["h_max"],
            data["s_min"], data["s_max"],
            data["v_min"], data["v_max"],
        )
        specs.append(FilterSpec(name=name, color_filter=cf, kind=kind))
    return specs
