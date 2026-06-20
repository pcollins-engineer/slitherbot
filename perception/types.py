"""Observation types returned by a Perceiver — backend-agnostic."""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class Pellet:
    cx: float
    cy: float
    r: float


@dataclass
class Snake:
    x: int
    y: int
    w: int
    h: int
    cx: float
    cy: float
    is_self: bool = False
    head: Optional[Tuple[int, int]] = None  # estimated head pixel (self only, for now)


@dataclass
class Perception:
    pellets: List[Pellet] = field(default_factory=list)
    snakes: List[Snake] = field(default_factory=list)

    @property
    def own(self) -> Optional[Snake]:
        return next((s for s in self.snakes if s.is_self), None)

    @property
    def enemies(self) -> List[Snake]:
        return [s for s in self.snakes if not s.is_self]
