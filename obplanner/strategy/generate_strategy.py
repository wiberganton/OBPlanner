from dataclasses import replace

import obplib as obp

from obplanner.model.pattern import PatternData
from obplanner.model.strategies import Strategy
import obplanner.strategy.strategy_mapping as strategy_mapping
from obplanner.strategy.beam_wiggle.beam_wiggle import beam_wiggle


def _normalize_strategy_value(name, value):
    if isinstance(value, (list, tuple)):
        if len(value) == 0:
            raise ValueError(f"strategy.{name} cannot be empty.")
        return list(value)
    return [value]


def _build_spot_expansion_specs(spot_size, dwell_time):
    spot_sizes = _normalize_strategy_value("spot_size", spot_size)
    dwell_times = _normalize_strategy_value("dwell_time", dwell_time)

    if len(spot_sizes) > 1 and len(dwell_times) > 1 and len(spot_sizes) != len(dwell_times):
        raise ValueError(
            "strategy.spot_size and strategy.dwell_time must have the same length when both are lists."
        )

    spec_count = max(len(spot_sizes), len(dwell_times))

    if len(spot_sizes) == 1:
        spot_sizes = spot_sizes * spec_count
    elif len(spot_sizes) != spec_count:
        raise ValueError("strategy.spot_size must be a scalar or match the number of dwell_time values.")

    if len(dwell_times) == 1:
        dwell_times = dwell_times * spec_count
    elif len(dwell_times) != spec_count:
        raise ValueError("strategy.dwell_time must be a scalar or match the number of spot_size values.")

    return list(zip(spot_sizes, dwell_times))


def _select_reference_expansion_spec(expansion_specs):
    for spot_size, dwell_time in expansion_specs:
        if dwell_time not in (None, 0):
            return spot_size, dwell_time
    return expansion_specs[0]


def _scale_dwell_time(dwell_time, base_dwell_time, target_dwell_time):
    if base_dwell_time == target_dwell_time:
        return int(dwell_time)

    if base_dwell_time in (None, 0):
        if target_dwell_time in (None, 0):
            return 0
        raise ValueError("Cannot expand non-zero dwell times from a zero or missing reference dwell_time.")

    if target_dwell_time is None:
        raise ValueError("strategy.dwell_time cannot be None for spot-based strategies.")

    return int(round(dwell_time * target_dwell_time / base_dwell_time))


def _clone_obp_element_with_bp(element, bp):
    if isinstance(element, obp.TimedPoints):
        return obp.TimedPoints(
            [obp.Point(point.x, point.y) for point in element.points],
            list(element.dwellTimes),
            bp,
        )
    if isinstance(element, obp.Line):
        a = obp.Point(element.P1.x, element.P1.y)
        b = obp.Point(element.P2.x, element.P2.y)
        return obp.Line(a, b, int(element.Speed), bp)
    raise TypeError(f"Unsupported OBP element type for spot-size expansion: {type(element).__name__}")


def _clone_obp_elements_with_bp(obp_elements, bp):
    return [_clone_obp_element_with_bp(element, bp) for element in obp_elements]


def _expand_obp_elements_for_specs(obp_elements, expansion_specs, power, base_dwell_time):
    expanded_elements = []
    for element in obp_elements:
        if isinstance(element, obp.TimedPoints):
            for point, dwell_time in zip(element.points, element.dwellTimes):
                for spot_size, target_dwell_time in expansion_specs:
                    bp = obp.Beamparameters(spot_size, power)
                    expanded_elements.append(
                        obp.TimedPoints(
                            points=[obp.Point(point.x, point.y)],
                            dwellTimes=[_scale_dwell_time(dwell_time, base_dwell_time, target_dwell_time)],
                            bp=bp,
                        )
                    )
        elif isinstance(element, obp.Line):
            for spot_size, _ in expansion_specs:
                bp = obp.Beamparameters(spot_size, power)
                expanded_elements.append(_clone_obp_element_with_bp(element, bp))
        else:
            raise TypeError(f"Unsupported OBP element type for expansion: {type(element).__name__}")
    return expanded_elements


def _expand_obp_elements_for_specs_with_last_wiggle(
    obp_elements, expansion_specs, power, settings, base_dwell_time
):
    expanded_elements = []
    wiggle_settings = dict(settings)
    wiggle_settings["wiggle_keep_center"] = False
    last_spot_size, last_dwell_time = expansion_specs[-1]
    last_bp = obp.Beamparameters(last_spot_size, power)

    for element in obp_elements:
        if isinstance(element, obp.TimedPoints):
            for point, dwell_time in zip(element.points, element.dwellTimes):
                point_copy = obp.Point(point.x, point.y)
                for spot_size, target_dwell_time in expansion_specs:
                    bp = obp.Beamparameters(spot_size, power)
                    expanded_elements.append(
                        obp.TimedPoints(
                            points=[obp.Point(point_copy.x, point_copy.y)],
                            dwellTimes=[_scale_dwell_time(dwell_time, base_dwell_time, target_dwell_time)],
                            bp=bp,
                        )
                    )
                wiggle_source = obp.TimedPoints(
                    points=[obp.Point(point_copy.x, point_copy.y)],
                    dwellTimes=[_scale_dwell_time(dwell_time, base_dwell_time, last_dwell_time)],
                    bp=last_bp,
                )
                expanded_elements.extend(beam_wiggle([wiggle_source], wiggle_settings, last_bp))
        elif isinstance(element, obp.Line):
            for spot_size, _ in expansion_specs:
                bp = obp.Beamparameters(spot_size, power)
                expanded_elements.append(_clone_obp_element_with_bp(element, bp))
        else:
            raise TypeError(f"Unsupported OBP element type for expansion: {type(element).__name__}")

    return expanded_elements


def create_obp_elements(pattern: PatternData, strategy: Strategy):
    strategy_name = strategy.strategy # Name of strategy
    # sort paths
    function_path = strategy_mapping.sort_function_map.get(strategy_name) # Get the sorting function
    if function_path:
        expansion_specs = _build_spot_expansion_specs(strategy.spot_size, strategy.dwell_time)
        reference_spot_size, reference_dwell_time = _select_reference_expansion_spec(expansion_specs)
        base_strategy = replace(
            strategy,
            spot_size=reference_spot_size,
            dwell_time=reference_dwell_time,
        )
        base_elements = function_path(pattern, base_strategy)  # Call the function once so repeated spot sizes keep the same execution order.

        if base_elements is None:
            return None

        if len(expansion_specs) == 1:
            spot_size, _ = expansion_specs[0]
            bp = obp.Beamparameters(spot_size, strategy.power)
            obp_elements = _expand_obp_elements_for_specs(
                base_elements,
                expansion_specs,
                strategy.power,
                reference_dwell_time,
            )
            if "wiggle_pattern" in strategy.settings:
                obp_elements = beam_wiggle(obp_elements, strategy.settings, bp)
            return obp_elements

        if "wiggle_pattern" in strategy.settings:
            return _expand_obp_elements_for_specs_with_last_wiggle(
                base_elements,
                expansion_specs,
                strategy.power,
                strategy.settings,
                reference_dwell_time,
            )

        return _expand_obp_elements_for_specs(
            base_elements,
            expansion_specs,
            strategy.power,
            reference_dwell_time,
        )
    else:
        print(f"Sorting function '{strategy_name}' not found.")
        return None
