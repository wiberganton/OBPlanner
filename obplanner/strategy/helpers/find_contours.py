import numpy as np
import matplotlib.pyplot as plt
from skimage import measure

from obplanner.model.pattern import PatternData
def extract_contours(pattern: PatternData):
    # Assume pattern_data.grid is the input
    grid = pattern.grid  # shape: (H, W, 3)
    energy = grid['energy']    # extract energy
    mask = energy > 0         # binary mask
    # Find contours in the mask
    contours = measure.find_contours(mask.astype(float), level=0.5)
    # Convert contour indices to physical coordinates
    boundary_points = []
    for contour in contours:
        # contour is in (row, col) format
        points = []
        for y, x in contour:
            # Round to nearest integer indices
            yi, xi = int(round(y)), int(round(x))
            if 0 <= yi < grid.shape[0] and 0 <= xi < grid.shape[1]:
                points.append([grid[yi, xi]['x'], grid[yi, xi]['y']])
        boundary_points.append(np.array(points))

    # Optional: visualize
    for contour in boundary_points:
        plt.plot(contour[:, 0], contour[:, 1])
    x_coords = grid['x'].flatten()
    y_coords = grid['y'].flatten()
    plt.scatter(x_coords, y_coords, c=energy.flatten(), cmap='hot', s=5)
    plt.title("Boundary of Energy > 0")
    plt.colorbar(label="Energy")
    plt.show()
    return contours
