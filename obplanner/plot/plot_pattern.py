from dataclasses import dataclass
from typing import Tuple, Literal, Optional
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize

from obplanner.model.pattern import PatternData, point_dtype

def plot_pattern(
    pattern: PatternData,
    kind: Literal["imshow", "pcolormesh"] = "imshow",
    cmap: str = "viridis",
    title: Optional[str] = None,
    show_colorbar: bool = True,
    ax: Optional[plt.Axes] = None,
):
    """
    Plot PatternData with energy in [0,1] as color intensity.
    - kind="imshow": fast; assumes regular grid & uniform spacing.
    - kind="pcolormesh": uses actual x/y per-sample; handles slightly warped grids.
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(6, 5))
    else:
        fig = ax.figure

    H, W = pattern.shape
    grid = pattern.grid
    assert grid.shape == (H, W), f"grid shape {grid.shape} != {pattern.shape}"
    assert grid.dtype == point_dtype, "grid dtype must be point_dtype"

    X = grid["x"].astype(float)
    Y = grid["y"].astype(float)
    E = grid["energy"].astype(float)

    # Clean & clamp energy to [0,1] for stable colors; keep NaNs as masked
    E = np.clip(E, 0.0, 1.0)
    Em = np.ma.masked_invalid(E)
    norm = Normalize(vmin=0.0, vmax=1.0)

    if kind == "imshow":
        # imshow expects a regular grid; compute extent from coordinates & spacing
        s = float(pattern.spacing)
        xmin, xmax = np.nanmin(X), np.nanmax(X)
        ymin, ymax = np.nanmin(Y), np.nanmax(Y)
        extent = [xmin - s/2, xmax + s/2, ymin - s/2, ymax + s/2]

        im = ax.imshow(
            Em,
            origin="lower",
            extent=extent,
            interpolation="nearest",
            cmap=cmap,
            norm=norm,
            aspect="equal",
        )
    elif kind == "pcolormesh":
        # Build cell-edge coordinates from sample centers and spacing (robust even if slightly irregular)
        s = float(pattern.spacing)
        # Estimate edges by offsetting centers by ±s/2 in each direction
        x_edges = np.pad(X - s/2, ((0,0),(0,1)), mode="edge")
        x_edges[:, 1:] = 0.5*(x_edges[:, 1:] + (X + s/2))
        y_edges = np.pad(Y - s/2, ((0,1),(0,0)), mode="edge")
        y_edges[1:, :] = 0.5*(y_edges[1:, :] + (Y + s/2))

        # Create 2D edge grids (H+1, W+1)
        Xe = np.pad(X, ((0,1),(0,1)), mode="edge")
        Ye = np.pad(Y, ((0,1),(0,1)), mode="edge")
        Xe[:, :-1] = x_edges
        Xe[:, -1] = Xe[:, -2] + s
        Ye[:-1, :] = y_edges
        Ye[-1, :] = Ye[-2, :] + s

        im = ax.pcolormesh(
            Xe, Ye, Em,
            cmap=cmap, norm=norm, shading="auto"
        )
        ax.set_aspect("equal", adjustable="box")
    else:
        raise ValueError("kind must be 'imshow' or 'pcolormesh'")

    ax.set_xlabel("x")
    ax.set_ylabel("y")
    if title:
        ax.set_title(title)
    if show_colorbar:
        cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        cbar.set_label("energy (0–1)")
    plt.tight_layout()

    plt.show()