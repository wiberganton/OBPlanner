from dataclasses import dataclass, field
from typing import Tuple, Literal, Optional
import numpy as np


@dataclass
class PatternSettings:
    point_distance: float  # Distance between points in the grid
    type: Literal["square", "triangular", "contour"] = "square"  # e.g., "square", "triangular", "hex", "contour_offset", etc.
    offset: float = 0.0 # Offset distance compared against 3mf file contour
    start_rotation: float = 0.0 # Rotation angle in degrees for first layer
    layer_rotation: float = 0.0  # Rotation angle in degrees between layers
    pattern_3D: Optional[Literal["HCP"]] = None # Applies a 3D pattern if specified

point_dtype = np.dtype([
    ("x", np.float32),
    ("y", np.float32),
    ("energy", np.float32)
])

@dataclass
class PatternData:
    grid: np.ndarray  # 2D structured array
    shape: Tuple[int, int]
    spacing: float

    @classmethod
    def create_empty(
        cls,
        xmin: float,
        ymin: float,
        xmax: float,
        ymax: float,
        point_distance: float,
        pattern_type: Literal["square", "triangular"] = "square",
        rotation_deg: float = 0.0,
    ) -> "PatternData":

        # Center of bounding box
        cx = (xmin + xmax) / 2
        cy = (ymin + ymax) / 2

        # Rotation matrix components
        theta = np.deg2rad(rotation_deg)
        cos_theta = np.cos(theta)
        sin_theta = np.sin(theta)
        rot_matrix = np.array([[cos_theta, -sin_theta], [sin_theta, cos_theta]])

        # Rotate bounding box corners to get new bounding box after rotation
        corners = np.array([
            [xmin, ymin],
            [xmin, ymax],
            [xmax, ymin],
            [xmax, ymax]
        ]).T

        centered_corners = corners - np.array([[cx], [cy]])
        rotated_corners = rot_matrix @ centered_corners
        rotated_corners += np.array([[cx], [cy]])

        rot_xmin = rotated_corners[0].min()
        rot_xmax = rotated_corners[0].max()
        rot_ymin = rotated_corners[1].min()
        rot_ymax = rotated_corners[1].max()

        width = rot_xmax - rot_xmin
        height = rot_ymax - rot_ymin

        if pattern_type == "square":
            cols = int(np.floor(width / point_distance)) + 1
            rows = int(np.floor(height / point_distance)) + 1

            xs = rot_xmin + np.arange(cols) * point_distance
            ys = rot_ymin + np.arange(rows) * point_distance

            X, Y = np.meshgrid(xs, ys)

        elif pattern_type == "triangular":
            cols = int(np.floor(width / point_distance)) + 1
            row_height = point_distance * np.sqrt(3) / 2
            rows = int(np.floor(height / row_height)) + 1

            X = np.zeros((rows, cols), dtype=np.float32)
            Y = np.zeros((rows, cols), dtype=np.float32)

            for r in range(rows):
                offset = (point_distance / 2) if (r % 2 == 1) else 0
                for c in range(cols):
                    x = rot_xmin + c * point_distance + offset
                    y = rot_ymin + r * row_height
                    X[r, c] = x
                    Y[r, c] = y

        else:
            raise ValueError(f"Unsupported pattern type: {pattern_type}")

        # Rotate points back by inverse rotation
        points = np.vstack((X.ravel(), Y.ravel()))
        centered_points = points - np.array([[cx], [cy]])
        inv_rot_matrix = np.array([[cos_theta, sin_theta], [-sin_theta, cos_theta]])
        rotated_points = inv_rot_matrix @ centered_points
        rotated_points += np.array([[cx], [cy]])

        X_rot = rotated_points[0].reshape(rows, cols)
        Y_rot = rotated_points[1].reshape(rows, cols)

        grid = np.zeros((rows, cols), dtype=point_dtype)

        for r in range(rows):
            for c in range(cols):
                grid[r, c]["x"] = X_rot[r, c]
                grid[r, c]["y"] = Y_rot[r, c]
                grid[r, c]["energy"] = 0.0  # all zero regardless of position

        return cls(grid=grid, shape=(rows, cols), spacing=point_distance)
    
    @classmethod
    def create_empty_3D(
        cls,
        xmin: float,
        ymin: float,
        xmax: float,
        ymax: float,
        point_distance: float,
        pattern_3D: Literal["hcp", "fcc"],
        layer: int,
        start_rotation: float = 0.0,
        layer_rotation: float = 0.0,
    ) -> "PatternData":
        """
        Create a single 2D layer for a 3D close-packed pattern (HCP or FCC).
        The layer orientation is rotated by (start_rotation + layer * layer_rotation).
        """

        # --- Helpers for layer offset ---
        def layer_offset_cp(stacking: str, k: int, d: float):
            """Return (dx, dy) offset for layer index k."""
            s = stacking.lower()
            h = d * np.sqrt(3) / 2.0
            if s == "hcp":
                # ABAB...
                return (0.0, 0.0) if k % 2 == 0 else (0.5 * d, (1.0 / 3.0) * h)
            elif s == "fcc":
                # ABCABC...
                m = k % 3
                if m == 0:
                    return (0.0, 0.0)
                elif m == 1:
                    return (0.5 * d, (1.0 / 3.0) * h)
                else:
                    return (0.5 * d, -(1.0 / 3.0) * h)
            else:
                raise ValueError(f"Unsupported pattern_3D: {stacking}")

        # --- Center of bounding box ---
        cx = (xmin + xmax) / 2.0
        cy = (ymin + ymax) / 2.0

        # --- Rotation for this layer ---
        rotation_deg = start_rotation + layer * layer_rotation
        theta = np.deg2rad(rotation_deg)
        cos_theta = np.cos(theta)
        sin_theta = np.sin(theta)
        rot_matrix = np.array([[cos_theta, -sin_theta],
                               [sin_theta,  cos_theta]])

        # --- Rotate bounding box to find rotated extents ---
        corners = np.array([[xmin, ymin],
                            [xmin, ymax],
                            [xmax, ymin],
                            [xmax, ymax]], dtype=np.float64).T
        centered_corners = corners - np.array([[cx], [cy]])
        rotated_corners = rot_matrix @ centered_corners
        rotated_corners += np.array([[cx], [cy]])

        rot_xmin = rotated_corners[0].min()
        rot_xmax = rotated_corners[0].max()
        rot_ymin = rotated_corners[1].min()
        rot_ymax = rotated_corners[1].max()

        width  = rot_xmax - rot_xmin
        height = rot_ymax - rot_ymin

        # --- Generate close-packed (triangular) grid ---
        d = point_distance
        h = d * np.sqrt(3) / 2.0
        dxL, dyL = layer_offset_cp(pattern_3D, layer, d)

        cols = int(np.floor(width / d)) + 4
        rows = int(np.floor(height / h)) + 4

        X = np.zeros((rows, cols), dtype=np.float32)
        Y = np.zeros((rows, cols), dtype=np.float32)

        for r in range(rows):
            row_offset = (d / 2.0) if (r % 2 == 1) else 0.0
            y = rot_ymin + r * h + dyL
            x0 = rot_xmin - d + row_offset + dxL
            for c in range(cols):
                x = x0 + c * d
                X[r, c] = x
                Y[r, c] = y

        # --- Rotate back to original coordinate frame ---
        points = np.vstack((X.ravel(), Y.ravel()))
        centered_points = points - np.array([[cx], [cy]])
        inv_rot_matrix = np.array([[cos_theta, sin_theta],
                                   [-sin_theta, cos_theta]])
        rotated_points = inv_rot_matrix @ centered_points
        rotated_points += np.array([[cx], [cy]])

        X_rot = rotated_points[0].reshape(rows, cols)
        Y_rot = rotated_points[1].reshape(rows, cols)

        # --- Populate grid ---
        grid = np.zeros((rows, cols), dtype=point_dtype)
        grid["x"] = X_rot
        grid["y"] = Y_rot
        grid["energy"].fill(0.0)

        return cls(grid=grid, shape=(rows, cols), spacing=point_distance)