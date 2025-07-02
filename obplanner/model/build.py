from dataclasses import dataclass, field, asdict
from typing import Tuple, Literal, Optional
import json
from obplanner.model.layer_default import LayerDefault, LayerStrategies, StartHeat

@dataclass
class Build:
    layer_strategies: LayerStrategies
    layer_default: LayerDefault = field(default_factory=LayerDefault)
    start_heat: Optional[StartHeat] = None

    def write_to_json(self, path):
        with open(path, "w") as f:
            json.dump(asdict(self), f, indent=2)
    
    @classmethod
    def from_json(cls, path):
        with open(path, "r") as f:
            data = json.load(f)

        return cls(
            layer_strategies=LayerStrategies.from_dict(data["layer_strategies"]),
            layer_default=LayerDefault.from_dict(data.get("layer_default", {})),
            start_heat=StartHeat.from_dict(data["start_heat"]) if data.get("start_heat") else None
        )