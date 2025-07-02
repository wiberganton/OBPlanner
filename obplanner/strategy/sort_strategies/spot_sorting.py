import numpy as np
import obplib as obp

from obplanner.model.pattern import PatternData
from obplanner.model.strategies import Strategy

def SpotRandom(pattern: PatternData, strategy: Strategy):
    spots = pattern.grid.ravel()
    spots = spots[spots["energy"] > 0]
    seed = strategy.settings.get("seed", None)
    if seed != None:
        np.random.seed(seed)
    np.random.shuffle(spots)
    points = []
    dwell_time = []
    for spot in spots:
        points.append(obp.Point(spot["x"]*1000, spot["y"]*1000))
        dwell_time.append(int(strategy.dwell_time*spot["energy"]))
    bp = obp.Beamparameters(strategy.spot_size, strategy.power)
    return [obp.TimedPoints(points, dwell_time, bp)]
    
def SpotOrdered(pattern: PatternData, strategy: Strategy):
    x_jump = strategy.settings.get("x_jump", 1)
    y_jump = strategy.settings.get("y_jump", 1)
    points = []
    dwell_time = []
    for xi in range(x_jump):
        for yi in range(y_jump):
            subgrid = pattern.grid[xi::x_jump, yi::y_jump]
            # Now process all elements in subgrid at once or with a simple loop
            for element in subgrid.ravel():  # Flatten if needed
                if element["energy"] > 0:
                    points.append(obp.Point(element["x"]*1000, element["y"]*1000))
                    dwell_time.append(int(strategy.dwell_time*element["energy"]))
    bp = obp.Beamparameters(strategy.spot_size, strategy.power)
    return [obp.TimedPoints(points, dwell_time, bp)]