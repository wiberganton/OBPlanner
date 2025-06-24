from dataclasses import dataclass, field
from typing import Tuple, Literal, List
import numpy as np

from obplanner.model.pattern import PatternSettings

@dataclass
class Strategy:
    pattern: PatternSettings # Which pattern that should be used
    strategy: str # defining which strategy that is used (the different strategies are defined in docs/scanning_strategies.md)
    power: int # Watt
    spot_size: int # in um 
    dwell_time: int = None # in ns 
    speed: int = None # in um/s
    repetitions: int = 1
    settings: dict = field(default_factory=dict) #Dictionary with custom settings depent on which strategy that is used defined in docs/scanning_strategies.md
    backscatter: bool = False
    geometry: List[int] = field(default_factory=list)  # Which slicestacks in the 3mf files which should be used