import numpy as np
import py3mf_slicer.get_items

from obplanner.model.pattern import PatternData
from obplanner.pattern.functions import (
    apply_edge_compensation,
    apply_overhang_compensation_distance_weighted,
    apply_combined_compensation
)

from obplanner.model.pattern import PatternData

def compensate_pattern(pattern: PatternData, settings: dict, sliced_model, layer: int):
    #Expandable to perform geometrical energy compensation
    if  settings.get("edge_compensation") and settings.get("overhang_compensation"):
        compensation = "combined"
    elif settings.get("edge_compensation"):
        pattern = compensate_side_dist("edge", pattern, settings, sliced_model, layer)
        return pattern
    elif settings.get("overhang_compensation"):
        pattern = compensate_side_dist("overhang", pattern, settings, sliced_model, layer)
        return pattern
    else:
        return pattern
    return None

def compensate_side_dist(compensation: str, pattern: PatternData, settings: dict, sliced_model, layer: int):
    if compensation == "edge":
        grid = pattern.grid                
        flat = grid.ravel()                      
        mask = flat["energy"] > 0                   # shape (70*61,)
        spots = flat[mask]                          # 1D structured array
        points = np.column_stack((spots["x"], spots["y"]))
        contour = py3mf_slicer.get_items.get_shapely_slice(sliced_model, layer)
        edge_energy = settings.get("edge_energy", 0.5)
        edge_compensation_width = settings.get("edge_compensation_width", 2)
        energies = apply_edge_compensation(points, contour, edge_energy, edge_compensation_width)
        flat["energy"][mask] = energies.astype(flat["energy"].dtype)
        pattern.grid = flat.reshape(grid.shape)
    
    elif compensation == "combined":
        grid = pattern.grid                
        flat = grid.ravel()                      
        mask = flat["energy"] > 0                   # shape (70*61,)
        spots = flat[mask]                          # 1D structured array
        points = np.column_stack((spots["x"], spots["y"]))
        contour = py3mf_slicer.get_items.get_shapely_slice(sliced_model, layer)
        
        overhang_edge_energy = settings.get("overhang_edge_energy", 0.5)
        overhang_compensation_width = settings.get("overhang_compensation_width", 2)
        max_compensation = settings.get("max_compensation", 2)
        overhang_area_threshold = settings.get("overhang_area_threshold", 0.0)

        energies = apply_combined_compensation(points, contour, lower_layers=[],
                                edge_energy=overhang_edge_energy, compensation_width=overhang_compensation_width,
                                max_compensation=max_compensation, area_threshold=overhang_area_threshold)
        
        flat["energy"][mask] = energies.astype(flat["energy"].dtype)
        pattern.grid = flat.reshape(grid.shape)
    elif compensation == "overhang":
        grid = pattern.grid                
        flat = grid.ravel()                      
        mask = flat["energy"] > 0                   # shape (70*61,)
        spots = flat[mask]                          # 1D structured array
        points = np.column_stack((spots["x"], spots["y"]))
        
        overhang_compensation_layers = settings.get("overhang_compensation_layers", 10)

        lower_layers = []
        for i in range(layer, max(layer-overhang_compensation_layers,0), -1):
            lower_layers.append(py3mf_slicer.get_items.get_shapely_slice(sliced_model, i))

        max_compensation = settings.get("max_compensation", 0.5)
        overhang_distance = settings.get("overhang_distance", 0.001)
        #print(lower_layers)
        energies = apply_overhang_compensation_distance_weighted(
                        points,
                        lower_layers,
                        max_compensation=max_compensation,
                        distance_scale=overhang_distance,   # D0 in our notation
                        alpha=0.5
        )
        
        flat["energy"][mask] = energies.astype(flat["energy"].dtype)
        pattern.grid = flat.reshape(grid.shape)
    return pattern
