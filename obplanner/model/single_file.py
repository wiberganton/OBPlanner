from dataclasses import dataclass, field
from typing import Tuple, Literal, List

from obplanner.model.strategies import Strategy

@dataclass 
class SingleShape:
    strategies: List[Strategy] = field(default_factory=list)
    shape: Literal["square", "circle"] = "circle"  # shape
    size: float = 50.0 # if circle radius if square side (in mm)