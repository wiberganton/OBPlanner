#!/usr/bin/env python3
"""
Script: overlay_pattern_obp.py

This script reads an input OBP file with timed points and overlays a defined pattern
(e.g., concentric rings or zigzag jumps) around each point from the input. The dwell time
of each input point is treated as the "melt dwell time." The dwell time for the overlay
pattern ("wiggle dwell time") is now user-definable.

USE CASES:
 1. Overlay concentric rings around each input point
 2. Overlay zigzag (opposite-ordered) jump pattern around each input point

All parameters and file paths are user-configurable below.
"""

import obplib as obp
import math
import random
from collections import defaultdict

# === USER CONFIGURABLE PARAMETERS ===
# Pattern parameters (applied around each input point)
#spot_size_um = 200                  # Pattern spot size in µm
#beam_power = 1500                   # Beam power in W
#num_rings = 1                       # Number of concentric rings per pattern
#ring_spacing_um = spot_size_um     # Distance between rings in µm
#direction = "ccw"                  # Pattern direction: "ccw", "cw", or "alternate"

# Dwell times
# Melt dwell time is read from each input point's dwell_times
#wiggle_dwell_time_ns = 100_000      # User-definable dwell time for overlay pattern in ns

# Input/Output file names
#input_obp_file = "input.obp"         # Path to the input OBP file
#output_concentric_file = "overlay_concentric.obp"
#output_zigzag_file     = "overlay_zigzag.obp"

# === Beam Parameter Object ===
#bp = obp.Beamparameters(spot_size_um, beam_power)

# ----------------------------------------------------------
# FUNCTION: Generate CCW Ring Points
# ----------------------------------------------------------
def generate_ring_points_ccw(radius_um, num_points, dwell_time_ns):
    """
    Generate CCW points on a single ring of given radius.
    Returns lists of Points and dwell times (all equal to dwell_time_ns).
    """
    circumference = 2 * math.pi * radius_um
    #num_points = 4 # max(6, int(circumference / arc_spacing_um))
    points = []
    dwell_times = []
    for i in range(num_points):
        angle = 2 * math.pi * i / num_points
        x = int(radius_um * math.cos(angle))
        y = int(radius_um * math.sin(angle))
        points.append(obp.Point(x, y))
        dwell_times.append(dwell_time_ns)
    return points, dwell_times

# ----------------------------------------------------------
# FUNCTION: Generate CW Ring Points
# ----------------------------------------------------------
def generate_ring_points_cw(radius_um, num_points, dwell_time_ns):
    """
    Generate CW points on a single ring of given radius.
    Returns lists of Points and dwell times.
    """
    circumference = 2 * math.pi * radius_um
    #num_points = 4 # max(6, int(circumference / arc_spacing_um))
    points = []
    dwell_times = []
    for i in range(num_points):
        angle = 2 * math.pi * (1 - i / num_points)
        x = int(radius_um * math.cos(angle))
        y = int(radius_um * math.sin(angle))
        points.append(obp.Point(x, y))
        dwell_times.append(dwell_time_ns)
    return points, dwell_times

# ----------------------------------------------------------
# FUNCTION: Random Angular Offset
# ----------------------------------------------------------
def randomize_angular_offset(points):
    """
    Randomly rotates the ordering of the points list to break regularity.
    """
    if not points:
        return []
    offset = random.randint(0, len(points) - 1)
    return points[offset:] + points[:offset]

# ----------------------------------------------------------
# FUNCTION: Generate Concentric Rings
# ----------------------------------------------------------
def _resolve_ring_num_points(radius_um, num_points=None, arc_spacing_um=None):
    """
    Resolve how many points to place on a ring.
    Prefer an explicit num_points value; otherwise estimate from arc spacing.
    """
    if num_points is not None:
        return max(1, int(num_points))

    if arc_spacing_um is None or arc_spacing_um <= 0:
        raise ValueError("Either num_points or a positive arc_spacing_um must be provided.")

    circumference = 2 * math.pi * radius_um
    return max(1, int(circumference / arc_spacing_um))


def generate_concentric_rings(
    num_rings,
    ring_spacing_um,
    arc_spacing_um=None,
    dwell_time_ns=None,
    direction="ccw",
    num_points=None,
):
    """
    Generate multiple concentric rings. Returns combined lists of Points and dwell times.
      - num_rings: number of rings
      - ring_spacing_um: radial spacing between rings
      - arc_spacing_um: spacing along circumference
      - dwell_time_ns: dwell time per pattern point (wiggle dwell time)
      - direction: "ccw", "cw", or "alternate"
      - num_points: explicit number of points per ring
    """
    all_pts = []
    all_dts = []
    for i in range(num_rings):
        radius = (i + 1) * ring_spacing_um
        ring_num_points = _resolve_ring_num_points(
            radius, num_points=num_points, arc_spacing_um=arc_spacing_um
        )
        if direction == "ccw":
            pts, dts = generate_ring_points_ccw(radius, ring_num_points, dwell_time_ns)
        elif direction == "cw":
            pts, dts = generate_ring_points_cw(radius, ring_num_points, dwell_time_ns)
        elif direction == "alternate":
            if i % 2 == 0:
                pts, dts = generate_ring_points_ccw(radius, ring_num_points, dwell_time_ns)
            else:
                pts, dts = generate_ring_points_cw(radius, ring_num_points, dwell_time_ns)
        else:
            raise ValueError("Direction must be 'ccw', 'cw', or 'alternate'.")
        pts = randomize_angular_offset(pts)
        all_pts.extend(pts)
        all_dts.extend(dts)
    return all_pts, all_dts

# ----------------------------------------------------------
# FUNCTION: Generate Zigzag (Opposite-Ordered) Jump Pattern
# ----------------------------------------------------------
def generate_zigzag_pattern(num_rings, ring_spacing_um, arc_spacing_um, dwell_time_ns, direction):
    """
    Generate concentric rings then reorder points to jump across diametrically opposite points.
    """
    ring_pts, _ = generate_concentric_rings(
        num_rings=num_rings,
        ring_spacing_um=ring_spacing_um,
        arc_spacing_um=arc_spacing_um,
        dwell_time_ns=dwell_time_ns,
        direction=direction,
    )
    return generate_opposite_ordered_points(ring_pts, dwell_time_ns)

# ----------------------------------------------------------
# FUNCTION: Overlay Pattern on Input TimedPoints
# ----------------------------------------------------------
def overlay_pattern_on_timedpoints(input_tps, pattern_fn, pattern_kwargs, wiggle_dwell_ns):
    """
    Overlay a given pattern around each point in input_tps.
    - input_tps: list of obp.TimedPoints from input file
    - pattern_fn: function that generates pattern (e.g., generate_concentric_rings)
    - pattern_kwargs: dict of parameters for pattern_fn (excluding dwell_time_ns)
    - wiggle_dwell_ns: user-defined dwell time for overlay pattern

    The input points' dwell_times are treated as "melt dwell time" (not modified).
    Returns combined lists of overlay Points and dwell times.
    """
    overlay_pts = []
    overlay_dts = []
    for tp in input_tps:
        melt_dwell_times = tp.dwellTimes
        for center_pt, melt_dwell in zip(tp.points, melt_dwell_times):
            # generate overlay pattern centered at origin
            pts, dts = pattern_fn(
                **pattern_kwargs,
                dwell_time_ns=wiggle_dwell_ns
            )
            # offset each pattern point by center coordinates
            for p, dt in zip(pts, dts):
                new_pt = obp.Point(center_pt.x + p.x, center_pt.y + p.y)
                overlay_pts.append(new_pt)
                overlay_dts.append(dt)
    return overlay_pts, overlay_dts
# ----------------------------------------------------------
# FUNCTION: Reorder Points to Jump Across Rings (No center point)
# ----------------------------------------------------------
def generate_opposite_ordered_points(points, dwell_time_ns):
    ring_map = defaultdict(list)

    # Group by radius
    for pt in points:
        r = int(math.hypot(pt.x, pt.y))
        ring_map[r].append(pt)

    ordered_points = []
    ordered_dwell_times = []

    for r, pts in ring_map.items():
        pts_sorted = sorted(pts, key=lambda p: math.atan2(p.y, p.x))
        n = len(pts_sorted)
        if n < 2:
            continue
        if n % 2 == 0:
            # even number of points: simple opposite pairing
            for i in range(n // 2):
                ordered_points.append(pts_sorted[i])
                ordered_dwell_times.append(dwell_time_ns)
                ordered_points.append(pts_sorted[i + n // 2])
                ordered_dwell_times.append(dwell_time_ns)
        else:
            # odd number of points: skip the middle point in pairing, add it once at the end
            mid = n // 2
            for i in range(mid):
                j = (i + mid + 1) % n
                if j == mid:
                    continue
                ordered_points.append(pts_sorted[i])
                ordered_dwell_times.append(dwell_time_ns)
                ordered_points.append(pts_sorted[j])
                ordered_dwell_times.append(dwell_time_ns)
            # add the middle point once
            ordered_points.append(pts_sorted[mid])
            ordered_dwell_times.append(dwell_time_ns)

    return ordered_points, ordered_dwell_times

