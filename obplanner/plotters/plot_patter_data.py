import numpy as np
import matplotlib.pyplot as plt
from typing import Optional, Tuple

from obplanner.model.pattern import PatternData

def visualize_pattern(
    pattern: PatternData,
    *,
    ax: Optional[plt.Axes] = None,
    show_grid_lines: bool = True,
    annotate_indices: bool = False,
    point_size: Optional[float] = None,
    vmin: Optional[float] = None,
    vmax: Optional[float] = None,
    title: Optional[str] = None,
):
    """
    Visualize a PatternData object as a scatter plot colored by energy.

    Parameters
    ----------
    pattern : PatternData
        The pattern to visualize.
    ax : matplotlib.axes.Axes, optional
        If provided, draw on this axes; otherwise a new figure/axes is created.
    show_grid_lines : bool, default True
        Draw faint lines connecting neighbors in the grid (row/col topology).
    annotate_indices : bool, default False
        Annotate each point with its (row, col) index.
    point_size : float, optional
        Marker size. If None, an automatic size is chosen based on point density.
    vmin, vmax : float, optional
        Color limits for the energy colormap. Defaults to data min/max.
    title : str, optional
        Plot title.

    """
    grid = pattern.grid  # structured array with fields: x, y, energy
    rows, cols = pattern.shape

    # Flattened coordinate + energy arrays
    X = grid["x"].reshape(rows, cols)
    Y = grid["y"].reshape(rows, cols)
    E = grid["energy"].reshape(rows, cols)

    # Create axes if needed
    created_fig = False
    if ax is None:
        fig, ax = plt.subplots(figsize=(7, 7))
        created_fig = True
    else:
        fig = ax.figure

    # Choose a reasonable default marker size from scale/point density
    if point_size is None:
        # Heuristic: denser grids get smaller markers
        npts = rows * cols
        # Estimate plot area for scale
        xmin, xmax = np.nanmin(X), np.nanmax(X)
        ymin, ymax = np.nanmin(Y), np.nanmax(Y)
        area = max((xmax - xmin) * (ymax - ymin), 1e-9)
        density = npts / area if area > 0 else npts
        # Clamp to a practical range
        point_size = float(np.clip(50.0 / (1.0 + 0.01 * density), 2.0, 20.0))

    # Color limits
    finite_E = E[np.isfinite(E)]
    if finite_E.size == 0:
        vmin = vmin if vmin is not None else 0.0
        vmax = vmax if vmax is not None else 1.0
    else:
        if vmin is None: vmin = float(np.nanmin(finite_E))
        if vmax is None: vmax = float(np.nanmax(finite_E))
        if vmin == vmax:
            # Avoid zero-range colorbar
            vmin -= 0.5
            vmax += 0.5

    # Optional faint grid lines to show topology (row and column neighbors)
    if show_grid_lines and rows > 1 and cols > 1:
        # Row connections
        for r in range(rows):
            ax.plot(X[r, :], Y[r, :], linewidth=0.6, alpha=0.3)
        # Column connections
        for c in range(cols):
            ax.plot(X[:, c], Y[:, c], linewidth=0.6, alpha=0.3)

    # Scatter points colored by energy
    sc = ax.scatter(X.ravel(), Y.ravel(), c=E.ravel(), s=point_size, cmap="viridis",
                    vmin=vmin, vmax=vmax)

    # Annotations if requested
    if annotate_indices:
        for r in range(rows):
            for c in range(cols):
                ax.text(X[r, c], Y[r, c], f"{r},{c}", fontsize=6,
                        ha="center", va="center", alpha=0.7)

    # Axes formatting
    ax.set_aspect("equal", adjustable="datalim")
    pad = 0.05
    xmin, xmax = np.nanmin(X), np.nanmax(X)
    ymin, ymax = np.nanmin(Y), np.nanmax(Y)
    xr = xmax - xmin
    yr = ymax - ymin
    ax.set_xlim(xmin - pad * xr, xmax + pad * xr)
    ax.set_ylim(ymin - pad * yr, ymax + pad * yr)

    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_title(title or f"Pattern ({rows}×{cols}), spacing={pattern.spacing:g}")

    # Colorbar for energy
    cbar = fig.colorbar(sc, ax=ax)
    cbar.set_label("energy")

    # Light grid
    ax.grid(True, which="both", linestyle="--", alpha=0.25)

    if created_fig:
        fig.tight_layout()

    plt.show()
