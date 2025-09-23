import numpy as np
import obplib as obp

from obplanner.model.pattern import PatternData
from obplanner.model.strategies import Strategy


import obplanner.strategy.helpers.find_contours as find_contours
import obplanner.strategy.helpers.find_connected as find_connected
import obplanner.strategy.helpers.offset_pattern as offset_pattern

def LineSort(pattern: PatternData, strategy: Strategy):
    start = strategy.settings.get("start", 1)
    jump = strategy.settings.get("jump", 1)
    connected = find_connected.find_connections(pattern)
    objects = []
    total_rows = len(connected)
    visited_rows = []
    # Generate the reordered row indices
    for offset in range(jump):
        for i in range(start - 1 + offset, total_rows, jump):
            visited_rows.append(i)
    # Append remaining rows not yet included (e.g., row 1 if start=2)
    for i in range(total_rows):
        if i not in visited_rows:
            visited_rows.append(i)
    # Process each row in the new order
    for i in visited_rows:
        row = connected[i]
        for el in row:
            if len(el) > 1 and el[0]["energy"] > 0:
                bp = obp.Beamparameters(strategy.spot_size, strategy.power)
                a = obp.Point(el[0]["x"] * 1000, el[0]["y"] * 1000)
                b = obp.Point(el[-1]["x"] * 1000, el[-1]["y"] * 1000)
                speed = strategy.speed * el[0]["energy"]
                objects.append(obp.Line(a, b, int(speed), bp))
    return objects
    
def LineSnake(pattern: PatternData, strategy: Strategy):
    start = strategy.settings.get("start", 1)
    jump = strategy.settings.get("jump", 1)

    connected = find_connected.find_connections(pattern)
    objects = []
    total_rows = len(connected)

    # Build the row visitation order just like LineSort
    visited_rows = []
    for offset in range(jump):
        for i in range(start - 1 + offset, total_rows, jump):
            visited_rows.append(i)
    # Append any rows not yet included (e.g., row 0 when start=2)
    for i in range(total_rows):
        if i not in visited_rows:
            visited_rows.append(i)

    # Process rows in the computed order; alternate direction per processed row
    for seq_idx, row_idx in enumerate(visited_rows):
        row = connected[row_idx]
        if seq_idx % 2 == 0:
            # forward
            for el in row:
                if len(el) > 1 and el[0]["energy"] > 0:
                    bp = obp.Beamparameters(strategy.spot_size, strategy.power)
                    a = obp.Point(el[0]["x"] * 1000, el[0]["y"] * 1000)
                    b = obp.Point(el[-1]["x"] * 1000, el[-1]["y"] * 1000)
                    speed = strategy.speed * el[0]["energy"]
                    objects.append(obp.Line(a, b, int(speed), bp))
        else:
            # reverse
            for el in reversed(row):
                if len(el) > 1 and el[0]["energy"] > 0:
                    bp = obp.Beamparameters(strategy.spot_size, strategy.power)
                    # Note: reverse the segment endpoints (last -> first)
                    a = obp.Point(el[-1]["x"] * 1000, el[-1]["y"] * 1000)
                    b = obp.Point(el[0]["x"] * 1000, el[0]["y"] * 1000)
                    speed = strategy.speed * el[0]["energy"]
                    objects.append(obp.Line(a, b, int(speed), bp))

    return objects

def LineConcentric(pattern: PatternData, strategy: Strategy):
    direction = strategy.settings.get("direction", "inward")
    bp = obp.Beamparameters(strategy.spot_size, strategy.power)
    objects = []
    offset_contour = offset_pattern.offset_all(pattern, 0.35)
    if direction == "inward":
        for contour in offset_contour:
            for c in contour:
                for i in range(len(c)-1):
                    a = obp.Point(c[i, 0]*1000, c[i, 0]*1000)
                    b = obp.Point(c[i+1, 0]*1000, c[i+1, 0]*1000)
                    speed = strategy.speed
                    objects.append(obp.Line(a,b,int(speed),bp))
    elif direction == "outward":
        for contour in reversed(offset_contour):
            for c in contour:
                for i in range(len(c)-1):
                    a = obp.Point(c[i, 0]*1000, c[i, 0]*1000)
                    b = obp.Point(c[i+1, 0]*1000, c[i+1, 0]*1000)
                    speed = strategy.speed
                    objects.append(obp.Line(a,b,int(speed),bp))
    else:
        print("Wrong in setting for direction of concentric scan")
    return objects