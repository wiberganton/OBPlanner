import numpy as np
import obplib as obp

from obplanner.model.pattern import PatternData
from obplanner.model.strategies import Strategy


import obplanner.strategy.helpers.find_contours as find_contours
import obplanner.strategy.helpers.find_connected as find_connected
import obplanner.strategy.helpers.offset_pattern as offset_pattern

def ContourLine(pattern: PatternData, strategy: Strategy):
    objects = []
    bp = obp.Beamparameters(strategy.spot_size, strategy.power)
    for row in range(pattern.grid.shape[0]):
        for col in range(pattern.grid.shape[1]-1):
            if pattern.grid.shape[1] > 1:
                point1 = pattern.grid[row, col]
                point2 = pattern.grid[row, col+1]
                if point1["energy"] > 0 and point2["energy"] > 0:
                    a = obp.Point(point1["x"]*1000, point1["y"]*1000)
                    b = obp.Point(point2["x"]*1000, point2["y"]*1000)
                    speed = strategy.speed * point1["energy"]
                    objects.append(obp.Line(a, b, int(speed), bp))

    return objects