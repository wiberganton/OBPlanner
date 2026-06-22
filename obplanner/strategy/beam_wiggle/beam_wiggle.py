import obplib as obp
from typing import List


from obplanner.strategy.beam_wiggle.wiggle_functions import (
    generate_concentric_rings,
    overlay_pattern_on_timedpoints,
    generate_zigzag_pattern)

""" 
Beam Wiggle Strategy Implementation 
Expects that the follwoing settings exists in the settings dict:
- wiggle_pattern: "concentric_rings" or "zigzag"    
- wiggle_spot_size_um: Spot size for the wiggle pattern in µm
- wiggle_dwell_time_ns: Dwell time for the wiggle pattern in ns
- num_rings: Number of rings in the wiggle pattern
- ring_spacing_um: Spacing between rings in the wiggle pattern in µm
- direction: "ccw", "cw", or "alternate"


"""

def beam_wiggle(obp_elements, settings, bp):
    points = []
    dwell_times = []
    for element in obp_elements:
        if isinstance(element, obp.TimedPoints):
            points.extend(element.points)
            dwell_times.extend(element.dwellTimes)
    timed_points = obp.TimedPoints(points, dwell_times, bp)
    if settings["wiggle_pattern"] == "concentric_rings":
        wiggle_points = concentring_rings(timed_points, settings, bp)
    elif settings["wiggle_pattern"] == "zigzag":
        wiggle_points = zigzag_pattern(timed_points, settings, bp)
    else:
        print(f"Unknown wiggle pattern: {settings['wiggle_pattern']}")
        return None
    keep_center = bool(settings.get("wiggle_keep_center", False))
    if keep_center:
        wiggle_points = interleave_timedpoints(timed_points, wiggle_points[0])

    return wiggle_points

def concentring_rings(timed_points, settings, bp):

    num_points = settings.get("num_points", 4)
    wiggle_dwell_time_ns = settings["wiggle_dwell_time_ns"]
    concentric_kwargs = {
        "num_rings": settings["num_rings"],
        "ring_spacing_um": settings["ring_spacing_um"],
        "num_points": num_points,
        "direction": settings["direction"]
    }
    pts_c, dts_c = overlay_pattern_on_timedpoints(
        [timed_points], generate_concentric_rings, concentric_kwargs, wiggle_dwell_time_ns
    )
    tp_c = obp.TimedPoints(pts_c, dts_c, bp)
    return [tp_c]

def zigzag_pattern(timed_points, settings, bp):
    spot_size_um = settings["wiggle_spot_size_um"]
    wiggle_dwell_time_ns = settings["wiggle_dwell_time_ns"]
    zigzag_kwargs = {
        "num_rings": settings["num_rings"],
        "ring_spacing_um": settings["ring_spacing_um"],
        "arc_spacing_um": spot_size_um / 2,
        "direction": settings["direction"]
    }
    pts_z, dts_z = overlay_pattern_on_timedpoints(
        [timed_points], generate_zigzag_pattern, zigzag_kwargs, wiggle_dwell_time_ns
    )
    tp_z = obp.TimedPoints(pts_z, dts_z, bp)
    return [tp_z]


 
def interleave_timedpoints(a: obp.TimedPoints, b: obp.TimedPoints) -> List[obp.TimedPoints]:
    """
    Returns: [a0, b0..b(k-1), a1, b(k)..b(2k-1), ...] as a list of TimedPoints.
    Each returned TimedPoints keeps a consistent bp (either a.bp or b.bp).
    """
    na = len(a.points)
    nb = len(b.points)
 
    if na == 0 and nb == 0:
        return []
    if na == 0:
        raise ValueError("Cannot interleave: 'a' has zero points but 'b' does not.")
    if nb % na != 0:
        raise ValueError(f"Expected len(b.points) to be divisible by len(a.points). Got {nb} % {na} != 0.")
    if len(a.dwellTimes) != na or len(b.dwellTimes) != nb:
        raise ValueError("Invariant violated: points and dwellTimes lengths must match.")
 
    chunk = nb // na  # e.g. 5
 
    out: List[obp.TimedPoints] = []
    for i in range(na):
        # 1) one point from a
        out.append(obp.TimedPoints(
            points=[a.points[i]],
            dwellTimes=[a.dwellTimes[i]],
            bp=a.bp
        ))
 
        # 2) chunk points from b
        start = i * chunk
        end = start + chunk
        out.append(obp.TimedPoints(
            points=b.points[start:end],
            dwellTimes=b.dwellTimes[start:end],
            bp=b.bp
        ))
 
    return out