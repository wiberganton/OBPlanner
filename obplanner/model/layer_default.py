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
    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)

@dataclass 
class LayerStrategies:
    jump_safe: List[Strategy] = field(default_factory=list)
    spatter_safe: List[Strategy] = field(default_factory=list)
    melt: List[Strategy] = field(default_factory=list)
    heat_balance: List[Strategy] = field(default_factory=list)
    layer_feed: List[Layerfeed] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict):
        def load_list(key, klass):
            return [klass.from_dict(item) for item in data.get(key, [])]

        return cls(
            jump_safe=load_list("jump_safe", Strategy),
            spatter_safe=load_list("spatter_safe", Strategy),
            melt=load_list("melt", Strategy),
            heat_balance=load_list("heat_balance", Strategy),
            layer_feed=load_list("layer_feed", Layerfeed)
        )

@dataclass 
class LayerDefault:
    jump_safe: Optional[SingleShape] = None
    spatter_safe: Optional[SingleShape] = None
    melt: Optional[SingleShape] = None
    heat_balance: Optional[SingleShape] = None
    layer_feed: Layerfeed = field(default_factory=Layerfeed)

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            jump_safe=SingleShape.from_dict(data["jump_safe"]) if data.get("jump_safe") else None,
            spatter_safe=SingleShape.from_dict(data["spatter_safe"]) if data.get("spatter_safe") else None,
            melt=SingleShape.from_dict(data["melt"]) if data.get("melt") else None,
            heat_balance=SingleShape.from_dict(data["heat_balance"]) if data.get("heat_balance") else None,
            layer_feed=Layerfeed.from_dict(data["layer_feed"]) if data.get("layer_feed") else Layerfeed()
        )

@dataclass 
class StartHeat:
    shape: Optional[SingleShape] = None
    temp_sensor: str = "Sensor1"
    target_temp: int = 800
    timeout: int = 3600

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            shape=SingleShape.from_dict(data["shape"]) if data.get("shape") else None,
            temp_sensor=data.get("temp_sensor", "Sensor1"),
            target_temp=data.get("target_temp", 800),
            timeout=data.get("timeout", 3600)
        )