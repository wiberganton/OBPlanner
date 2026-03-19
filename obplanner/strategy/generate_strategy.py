import obplib as obp

from obplanner.model.pattern import PatternData
from obplanner.model.strategies import Strategy
import obplanner.strategy.strategy_mapping as strategy_mapping
from obplanner.strategy.beam_wiggle.beam_wiggle import beam_wiggle


def create_obp_elements(pattern: PatternData, strategy: Strategy):
    strategy_name = strategy.strategy # Name of strategy
    # sort paths
    function_path = strategy_mapping.sort_function_map.get(strategy_name) # Get the sorting function
    if function_path:
        obp_elements = function_path(pattern, strategy)  # Call the function
        if "wiggle_pattern" in strategy.settings:
            bp = obp.Beamparameters(strategy.spot_size, strategy.power)
            obp_elements = beam_wiggle(obp_elements, strategy.settings, bp)
        return obp_elements
    else:
        print(f"Sorting function '{strategy_name}' not found.")
        return None