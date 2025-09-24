from shapely.geometry import Polygon, MultiPolygon, Point
from shapely import contains_xy
import numpy as np
import py3mf_slicer.get_items
from obplanner.model.pattern import PatternSettings, PatternData


def generate_pattern(sliced_model, layer: int, components: list[int], pattern_settings: PatternSettings) -> PatternData:
    component_slices = py3mf_slicer.get_items.get_shapely_slice(sliced_model, layer)
    nmb_slices = len(component_slices)
    selected_shapes = [component_slices[i] for i in components if component_slices[i] is not None]
    union_polygon = selected_shapes[0]
    for shape in selected_shapes[1:]:
        union_polygon = union_polygon.union(shape)

    if pattern_settings.offset != 0.0:
        union_polygon = union_polygon.buffer(pattern_settings.offset)
    
    rotation = pattern_settings.start_rotation + pattern_settings.layer_rotation * layer
    if pattern_settings.type == "contour":
        x = []
        y = []
        if isinstance(union_polygon, MultiPolygon):
            for poly in union_polygon.geoms:
                coords = list(poly.exterior.coords)
                # Extract all x values
                x_values = [point[0] for point in coords]
                # Extract all y values
                y_values = [point[1] for point in coords]
                x.append(x_values) 
                y.append(y_values)
        else:
            coords = list(union_polygon.exterior.coords)
            # Extract all x values
            x_values = [point[0] for point in coords]
            # Extract all y values
            y_values = [point[1] for point in coords]
            x.append(x_values) 
            y.append(y_values)
        
        point_dtype = np.dtype([
            ("x", np.float32),
            ("y", np.float32),
            ("energy", np.float32)
        ])
        rows = len(x)
        cols = max(len(row) for row in x)
        grid = np.zeros((rows, cols), dtype=point_dtype)
        for i, (row_x, row_y) in enumerate(zip(x, y)):
            for j in range(len(row_x)):
                grid[i, j]["x"] = row_x[j]
                grid[i, j]["y"] = row_y[j]
                grid[i, j]["energy"] = 1.0  # default energy
        pattern = PatternData(grid=grid, shape=(rows, cols), spacing=1.0)
        return pattern
    else:
        xmin, ymin, xmax, ymax = union_polygon.bounds
        pattern = PatternData.create_empty(
            xmin, ymin, xmax, ymax,
            point_distance=pattern_settings.point_distance,
            pattern_type=pattern_settings.type,
            rotation_deg=rotation,
            lattice_3d=pattern_settings.lattice_3d,
            layers=nmb_slices,
        )
        
        x = pattern.grid['x'].ravel()
        y = pattern.grid['y'].ravel()

        if isinstance(union_polygon, MultiPolygon):
            inside = np.zeros_like(x, dtype=bool)
            for poly in union_polygon.geoms:
                inside |= contains_xy(poly, x, y)
        else:
            inside = contains_xy(union_polygon, x, y)
        pattern.grid['energy'] = inside.reshape(pattern.grid.shape).astype(float)

        return pattern



