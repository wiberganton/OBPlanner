import numpy as np
from scipy.ndimage import binary_erosion
from skimage import measure

from obplanner.model.pattern import PatternData

def offset_all(pattern: PatternData, offset_mm: float, energy_threshold: float = 0.0):
    contours = []
    all_same = False
    offset = 0
    while not all_same:
        offset_contour = extract_offset_contour_by_distance(pattern, offset, energy_threshold)
        if contours and contours[-1] and len(contours[-1][0]) > 0:
            all_same = np.all(contours[-1][0] == contours[-1][0][0, 0])
        if not all_same:
            contours.append(offset_contour)
        offset += offset_mm
    return contours



def extract_offset_contour_by_distance(pattern: PatternData, offset_mm: float, energy_threshold: float = 0.0):
    """
    Extracts a single inward offset contour by X mm from a structured grid.

    Args:
        pattern : PatternData
        offset_mm (float): Physical offset distance in mm
        energy_threshold (float): Threshold to binarize the energy grid

    Returns:
        List[np.ndarray]: A list of contours (each a Nx2 array of [x, y] points)
    """
    grid = pattern.grid
    # Extract fields
    energy = grid['energy']
    x_coords = grid['x']
    y_coords = grid['y']

    # Estimate physical spacing from grid
    dx = np.mean(np.abs(np.diff(x_coords, axis=1)))
    dy = np.mean(np.abs(np.diff(y_coords, axis=0)))
    pixel_size = np.mean([dx, dy])

    # Convert offset distance to erosion steps
    erosion_steps = int(round(offset_mm / pixel_size))
    if erosion_steps <= 0:
        erosion_steps = 1

    # Create initial mask
    mask = energy > energy_threshold

    # Apply erosion
    for _ in range(erosion_steps):
        if not mask.any():
            return []  # no contour possible
        mask = binary_erosion(mask)

    # Extract contours from eroded mask
    contours = measure.find_contours(mask.astype(float), level=0.5)
    real_contours = []

    for c in contours:
        pts = []
        for y, x in c:
            yi, xi = int(round(y)), int(round(x))
            if 0 <= yi < grid.shape[0] and 0 <= xi < grid.shape[1]:
                pts.append([x_coords[yi, xi], y_coords[yi, xi]])
        if pts:
            real_contours.append(np.array(pts))

    return real_contours
