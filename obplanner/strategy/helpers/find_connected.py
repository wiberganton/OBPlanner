import numpy as np
from obplanner.model.pattern import PatternData

# Define the dtype for the array
point_dtype = np.dtype([("x", np.float32), ("y", np.float32), ("energy", np.float32)])

def find_connections(pattern: PatternData):
    # Instead of appending in each loop, use a list comprehension
    return [find_connected_points(row) for row in pattern.grid]

def find_connected_points(row):
    connected_points = []
    current_group = []
    
    # Iterate through the row and group consecutive points with the same energy
    for i in range(len(row)):
        if not current_group:
            current_group.append(row[i])
        elif row[i]['energy'] == current_group[-1]['energy']:
            current_group.append(row[i])
        else:
            if len(current_group) > 1:  # Only keep groups with more than one connected point
                connected_points.append(current_group)  # Append the list directly
            current_group = [row[i]]
    
    # Append the last group if it's valid
    if len(current_group) > 1:
        connected_points.append(current_group)
    
    return connected_points
