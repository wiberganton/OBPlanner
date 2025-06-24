import numpy as np
import obplib as obp

from obplanner.model.pattern import PatternData
from obplanner.model.strategies import Strategy

import obplanner.strategy.helpers.find_connected as find_connected

def LineSort(pattern: PatternData, strategy: Strategy):
    connected = find_connected.find_connections(pattern)
    objects = []
    for row in connected:
        for el in row:
            if len(el) > 1 and el[0]["energy"]>0:
                bp = obp.Beamparameters(strategy.spot_size, strategy.power)
                a = obp.Point(el[0]["x"]*1000, el[0]["y"]*1000)
                b = obp.Point(el[-1]["x"]*1000, el[-1]["y"]*1000)
                speed = strategy.speed*el[0]["energy"]
                objects.append(obp.Line(a,b,int(speed),bp))
    return objects
    
def LineSnake(pattern: PatternData, strategy: Strategy):
    connected = find_connected.find_connections(pattern)
    objects = []
    for i, row in enumerate(connected):
        if i % 2 == 0:
            for el in row:
                if len(el) > 1 and el[0]["energy"]>0:
                    bp = obp.Beamparameters(strategy.spot_size, strategy.power)
                    a = obp.Point(el[0]["x"]*1000, el[0]["y"]*1000)
                    b = obp.Point(el[-1]["x"]*1000, el[-1]["y"]*1000)
                    speed = strategy.speed*el[0]["energy"]
                    objects.append(obp.Line(a,b,int(speed),bp))
        else:
            for el in reversed(row):
                if len(el) > 1 and el[0]["energy"]>0:
                    bp = obp.Beamparameters(strategy.spot_size, strategy.power)
                    a = obp.Point(el[-1]["x"]*1000, el[0]["y"]*1000)
                    b = obp.Point(el[0]["x"]*1000, el[-1]["y"]*1000)
                    speed = strategy.speed*el[0]["energy"]
                    objects.append(obp.Line(a,b,int(speed),bp))
    return objects