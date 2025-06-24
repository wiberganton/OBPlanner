from dataclasses import dataclass, field, asdict
from typing import Tuple, Literal, List, Optional

from obplanner.model.strategies import Strategy
from obplanner.model.single_file import SingleShape

@dataclass
class Layerfeed:
    build_piston_distance: float = -0.1
    powder_piston_distance: float = 0.2
    recoater_advance_speed: float = 100.0
    recoater_retract_speed: float = 100.0
    recoater_dwell_time: float = 0
    recoater_full_repeats: int = 0
    recoater_build_repeats: int = 0
    triggered_start: bool = True
    def to_camel_dict(self):
        def snake_to_camel(snake_str):
            parts = snake_str.split('_')
            return parts[0] + ''.join(word.capitalize() for word in parts[1:])
        camel_dict = {
            snake_to_camel(k): v for k, v in asdict(self).items()
        }
        return {"layerFeed": camel_dict}

@dataclass 
class LayerStrategies:
    jump_safe: List[Strategy] = field(default_factory=list)
    spatter_safe: List[Strategy] = field(default_factory=list)
    melt: List[Strategy] = field(default_factory=list)
    heat_balance: List[Strategy] = field(default_factory=list)
    layer_feed: List[Layerfeed] = field(default_factory=list)

@dataclass 
class LayerDefault:
    jump_safe: Optional[SingleShape] = None
    spatter_safe: Optional[SingleShape] = None
    melt: Optional[SingleShape] = None
    heat_balance: Optional[SingleShape] = None
    layer_feed: Layerfeed = field(default_factory=Layerfeed)

@dataclass 
class StartHeat:
    shape: Optional[SingleShape] = None
    temp_sensor: str = "Sensor1"
    target_temp: int = 800
    timeout: int = 3600