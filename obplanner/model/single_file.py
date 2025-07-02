from dataclasses import dataclass, field
from typing import Tuple, Literal, List

from obplanner.model.strategies import Strategy

@dataclass 
class SingleShape:
    strategies: List[Strategy] = field(default_factory=list)
    shape: Literal["square", "circle"] = "circle"  # shape
    size: float = 50.0 # if circle radius if square side (in mm)

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            strategies=[Strategy.from_dict(s) for s in data.get("strategies", [])],
            shape=data.get("shape", "circle"),  # default from class definition
            size=data.get("size", 50.0)         # default from class definition
        )