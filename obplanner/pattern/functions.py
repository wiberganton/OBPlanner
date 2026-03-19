"""
Compensation Functions

This module provides all compensation functions for laser scanning patterns:
- Edge distance compensation: Energy reduction near contour boundaries
- Overhang compensation: Energy reduction in unsupported regions
- Combined compensation: Both edge and overhang applied together

All functions work with point arrays and return energy values.
"""

import numpy as np
import math
from shapely.geometry import Point
from shapely.ops import unary_union



# =============================================================================
# EDGE DISTANCE COMPENSATION
# =============================================================================

def apply_edge_compensation(points, contours, edge_energy, compensation_width):
    """
    Apply edge distance compensation to scanning points.

    `contours` can be:
      - a single Shapely Polygon or MultiPolygon
      - a list/tuple of Polygons / MultiPolygons
    """

    from obplanner.pattern.config import PatternConfig
    spot_radius = PatternConfig.SPOT_RADIUS

    # Normalize contours to a list
    if not isinstance(contours, (list, tuple)):
        contours = [contours]

    # Precompute boundaries for speed
    boundaries = [geom.boundary for geom in contours]

    energies = np.ones(len(points), dtype=float)

    for i, (x, y) in enumerate(points):
        pt = Point(x, y)

        # Which contours contain this point?
        inside_flags = [geom.contains(pt) for geom in contours]

        # If it's not inside any contour -> energy = 0
        if not any(inside_flags):
            energies[i] = 0.0
            continue

        # Compute distance to boundaries of contours that contain the point
        dists_inside = [
            boundaries[j].distance(pt)
            for j, inside in enumerate(inside_flags)
            if inside
        ]

        # Fallback: if for some reason no containing geom gave a distance,
        # use all boundaries (very edge-casey, but safe)
        if dists_inside:
            distance = min(dists_inside)
        else:
            distance = min(b.distance(pt) for b in boundaries)

        # Check for spot interference with boundary
        if distance < spot_radius:
            energies[i] = 0.0  # Spot interferes with boundary
            continue

        # Apply linear compensation
        if distance < compensation_width:
            # Linear interpolation from edge_energy (at distance=spot_radius)
            # to 1.0 (at distance=compensation_width)
            t = (distance - spot_radius) / (compensation_width - spot_radius)
            t = max(0.0, min(1.0, t))  # Clamp to [0, 1]
            energies[i] = edge_energy + (1.0 - edge_energy) * t
        else:
            energies[i] = 1.0

    return energies

# =============================================================================
# OVERHANG COMPENSATION
# =============================================================================
def apply_overhang_compensation_distance_weighted(
    points,
    lower_layers,
    max_compensation=0.3,
    distance_scale=0.5,   # D0 in our notation
    alpha=0.5,            # layer weighting, 0<alpha<=1
):
    """
    Distance-based overhang compensation with depth weighting.

    For each point and each lower layer k:
        d_k = distance to union of that layer's polygons (0 if inside)

    Weighted unsupported severity:
        D = sum_k (alpha^(k-1) * d_k)

    severity(D) = 1 - exp(-D / distance_scale)
    energy = 1 - max_compensation * severity
    """

    n_points = len(points)
    energies = np.ones(n_points, dtype=float)

    if not lower_layers:
        # No support at all -> everybody gets maximum punishment
        return np.full(n_points, 1.0 - max_compensation, dtype=float)

    # Precompute union per lower layer
    layer_unions = []
    for geoms in lower_layers:
        if geoms:
            layer_unions.append(unary_union(geoms))
        else:
            layer_unions.append(None)

    n_layers = len(layer_unions)

    # Precompute weights w_k = alpha^(k-1)
    weights = np.array([alpha ** k for k in range(n_layers)], dtype=float)

    for i, (x, y) in enumerate(points):
        pt = Point(x, y)

        D = 0.0
        for k, union in enumerate(layer_unions):
            if union is None:
                # no support polygons on this layer: we can either
                # skip or treat as "infinite distance".
                # Skipping is usually safer: no XY support, but no fake geometry either.
                continue

            d_k = union.distance(pt)   # 0 if inside, >0 if outside
            D += weights[k] * d_k

        if D <= 0.0:
            # fully supported everywhere (inside all relevant unions)
            energies[i] = 1.0
        else:
            severity = 1.0 - math.exp(-D / (distance_scale + 1e-12))
            energies[i] = max(1.0 - max_compensation * severity, 0.0)

    return energies


# =============================================================================
# COMBINED COMPENSATION
# =============================================================================

def apply_combined_compensation(points, contour, lower_layers=[],
                                edge_energy=0.5, compensation_width=2.0,
                                max_compensation=0.3, area_threshold=1.0):
    """
    Apply both edge distance and overhang compensation.
    
    The final energy is the product of both compensations:
    energy_final = energy_edge * energy_overhang
    
    This means that points in both overhang regions AND near edges
    will have the most energy reduction.
    
    Args:
        points: np.array of shape (N, 2) containing (x, y) coordinates
        contour: Shapely Polygon representing the contour
        lower_layers: List of Shapely Polygons for layers below (optional)
        
        Edge parameters:
        edge_energy: Minimum energy at boundary (default: 0.5)
        compensation_width: Distance for edge compensation in mm (default: 2.0)
        
        Overhang parameters:
        n_layers: Number of layers below to examine (default: 3)
        max_compensation: Maximum overhang energy reduction (default: 0.3)
        area_threshold: Minimum overhang area in mm² (default: 1.0)
    
    Returns:
        np.array of shape (N,) containing combined energy values
    
    Example:
        >>> points = np.array([[1.0, 1.0], [5.0, 5.0]])
        >>> contour = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
        >>> energies = apply_combined_compensation(points, contour)
    """
    # Apply edge compensation
    edge_energies = apply_edge_compensation(
        points, contour, edge_energy, compensation_width
    )
    
    # Apply overhang compensation
    overhang_energies = apply_overhang_compensation(
        points, contour, lower_layers, max_compensation, area_threshold
    )
    
    # Combine by multiplication
    combined_energies = edge_energies * overhang_energies
    
    return combined_energies


def validate_edge_parameters(edge_energy, compensation_width):
    """
    Validate edge compensation parameters.
    
    Args:
        edge_energy: Should be between 0.0 and 1.0
        compensation_width: Should be positive
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if not 0.0 <= edge_energy <= 1.0:
        return False, "edge_energy must be between 0.0 and 1.0"
    
    if compensation_width <= 0:
        return False, "compensation_width must be positive"
    
    return True, "Parameters valid"


def validate_overhang_parameters(n_layers, max_compensation, area_threshold):
    """
    Validate overhang compensation parameters.
    
    Args:
        n_layers: Should be positive integer
        max_compensation: Should be between 0.0 and 1.0
        area_threshold: Should be non-negative
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if n_layers < 1:
        return False, "n_layers must be at least 1"
    
    if not 0.0 <= max_compensation <= 1.0:
        return False, "max_compensation must be between 0.0 and 1.0"
    
    if area_threshold < 0:
        return False, "area_threshold must be non-negative"
    
    return True, "Parameters valid"


