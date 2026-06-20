"""Perception layer: turn a frame into game observations.

The bot talks to this layer through a stable interface (`perceive(bgr) ->
Perception`) so the backend is swappable: color filters today, a trained
YOLO model later, without touching the policy/control code.
"""

from .types import Pellet, Perception, Snake
from .color_filter_perceiver import ColorFilterPerceiver

__all__ = ["Pellet", "Snake", "Perception", "ColorFilterPerceiver"]
