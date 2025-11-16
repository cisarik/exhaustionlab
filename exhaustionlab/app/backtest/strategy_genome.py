"""
Shared StrategyGenome dataclass used across evolution components.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class StrategyGenome:
    """Represents a complete trading strategy genome."""

    name: str
    description: str
    pine_code: str
    pyne_code: str
    parameters: Dict[str, float]
    fitness: float = 0.0
    generation: int = 0
    parent_ids: List[str] = field(default_factory=list)

    def __post_init__(self):
        # Ensure parent_ids is always a list (legacy callers may send None)
        if self.parent_ids is None:
            self.parent_ids = []
