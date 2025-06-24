from obplanner.model.pattern import PatternData
from obplanner.model.strategies import Strategy
import obplanner.strategy.strategy_mapping as strategy_mapping


def create_obp_elements(pattern: PatternData, strategy: Strategy):
    strategy_name = strategy.strategy # Name of strategy
    # sort paths
    function_path = strategy_mapping.sort_function_map.get(strategy_name) # Get the sorting function
    if function_path:
        return function_path(pattern, strategy)  # Call the function
    else:
        print(f"Sorting function '{strategy_name}' not found.")
        return None