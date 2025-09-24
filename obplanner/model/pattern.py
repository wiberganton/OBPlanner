from __future__ import annotations
from dataclasses import dataclass
from typing import Literal, Optional, Tuple
import numpy as np

# 2D point dtype: x, y, energy (NO z)
point_dtype = np.dtype([
    ("x", np.float32),
    ("y", np.float32),
    ("energy", np.float32),
])

@dataclass
class PatternSettings:
    point_distance: float                              # unified spacing control
    type: Literal["square", "triangular", "contour"] = "square"
    offset: float = 0.0
    start_rotation: float = 0.0
    layer_rotation: float = 0.0
    lattice_3d: Optional[Literal["bcc", "fcc", "hcp"]] = None  # optional 3D stacking style

@dataclass
class PatternData:
    grid: np.ndarray                    # shape = (layers, rows, cols) of (x,y,energy)
    shape: Tuple[int, int, int]         # (layers, rows, cols)
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
        *,
        lattice_3d: Optional[Literal["bcc", "fcc", "hcp"]] = None,
        layers: int = 1,
        layer_rotation: float = 0.0,
    ) -> "PatternData":
        """
        Create a layered pattern over a 2D bounding box.
        - No z is stored. Layer index (0..layers-1) implies z order.
        - If lattice_3d is None => plain 2D (layers defaults to 1).
        - If lattice_3d in {bcc,fcc,hcp} => per-layer XY offsets mimic atomic stacking.
        """
        # --- center & rotation helpers ---
        cx = (xmin + xmax) / 2.0
        cy = (ymin + ymax) / 2.0

        def rotmat(deg: float) -> np.ndarray:
            th = np.deg2rad(deg)
            c, s = np.cos(th), np.sin(th)
            return np.array([[c, -s], [s,  c]], dtype=np.float64)

        base_R = rotmat(rotation_deg)

        # rotate bbox to compute extents in rotated frame
        corners = np.array([[xmin, ymin],
                            [xmin, ymax],
                            [xmax, ymin],
                            [xmax, ymax]], dtype=np.float64).T
        centered = corners - np.array([[cx], [cy]])
        rot_corners = base_R @ centered + np.array([[cx], [cy]])
        rxmin, rxmax = rot_corners[0].min(), rot_corners[0].max()
        rymin, rymax = rot_corners[1].min(), rot_corners[1].max()
        width, height = rxmax - rxmin, rymax - rymin

        # --- base 2D lattice (single layer) built in rotated frame ---
        def make_square_layer(pitch: float):
            cols = int(np.floor(width  / pitch)) + 1
            rows = int(np.floor(height / pitch)) + 1
            xs = rxmin + np.arange(cols) * pitch
            ys = rymin + np.arange(rows) * pitch
            X, Y = np.meshgrid(xs, ys)
            return X.astype(np.float64), Y.astype(np.float64)

        def make_triangular_layer(pitch: float):
            cols = int(np.floor(width / pitch)) + 1
            row_h = pitch * np.sqrt(3.0) / 2.0
            rows = int(np.floor(height / row_h)) + 1
            X = np.zeros((rows, cols), dtype=np.float64)
            Y = np.zeros((rows, cols), dtype=np.float64)
            for r in range(rows):
                off = (pitch / 2.0) if (r % 2 == 1) else 0.0
                X[r, :] = rxmin + off + np.arange(cols) * pitch
                Y[r, :] = rymin + r * row_h
            return X, Y

        # choose in-plane lattice based on 3D choice (close-packed uses triangular)
        if (lattice_3d in {"fcc", "hcp"}) or (lattice_3d is None and pattern_type == "triangular"):
            X0, Y0 = make_triangular_layer(point_distance)
        else:
            X0, Y0 = make_square_layer(point_distance)

        rows, cols = X0.shape

        # --- per-layer XY offsets to mimic 3D stacking (still 2D storage) ---
        a = point_distance
        a1 = np.array([a, 0.0])
        a2 = np.array([a/2.0, a*np.sqrt(3.0)/2.0])

        def tri_offset(u: float, v: float) -> np.ndarray:
            return u * a1 + v * a2  # linear comb in triangular basis (rotated frame)

        if lattice_3d == "hcp":  # ABAB...
            seq = [np.array([0.0, 0.0]), tri_offset(1/3, 2/3)]
        elif lattice_3d == "fcc":  # ABCABC...
            seq = [np.array([0.0, 0.0]),
                   tri_offset(1/3, 2/3),
                   tri_offset(2/3, 1/3)]
        elif lattice_3d == "bcc":  # square with half-cell shift every other layer
            seq = [np.array([0.0, 0.0]), np.array([a/2.0, a/2.0])]
        else:  # plain 2D (no stacking offsets)
            seq = [np.array([0.0, 0.0])]

        period = len(seq)
        L = max(1, int(layers))

        # allocate: (layers, rows, cols) with 2D dtype
        grid = np.zeros((L, rows, cols), dtype=point_dtype)

        # fill each layer
        for li in range(L):
            R_layer = rotmat(rotation_deg + li * layer_rotation)

            X, Y = X0.copy(), Y0.copy()
            dxy = seq[li % period]
            X += dxy[0]
            Y += dxy[1]

            pts = np.vstack((X.ravel(), Y.ravel()))
            centered_pts = pts - np.array([[cx], [cy]])
            # inverse transform back to global frame
            XY = R_layer.T @ centered_pts + np.array([[cx], [cy]])
            Xg = XY[0].reshape(rows, cols)
            Yg = XY[1].reshape(rows, cols)

            grid[li, :, :]["x"] = Xg.astype(np.float32)
            grid[li, :, :]["y"] = Yg.astype(np.float32)
            grid[li, :, :]["energy"] = 0.0

        return cls(grid=grid, shape=(L, rows, cols), spacing=point_distance)
