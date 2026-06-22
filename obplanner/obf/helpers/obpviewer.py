# SPDX-FileCopyrightText: 2022 Freemelt AB
# SPDX-License-Identifier: Apache-2.0

"""OBP data viewer."""

# Built-in
import argparse
import dataclasses
import pathlib
import gzip
import sys
import tkinter
import re
from tkinter import ttk

# Freemelt
from obplib import OBP_pb2 as obp

# PyPI
try:
    import matplotlib
except ModuleNotFoundError:
    sys.exit(
        "Error: matplotlib is not installed. Try:\n"
        "  $ sudo apt install python3-matplotlib\n"
        "or\n"
        "  $ python3 -m pip install matplotlib"
    )

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from matplotlib.ticker import EngFormatter
from matplotlib.path import Path
import matplotlib.collections as mcoll
import numpy as np
from google.protobuf.internal.decoder import _DecodeVarint32
from matplotlib.patches import Circle

plt.style.use("dark_background")

def natural_sort_key(text):
    """Sort strings with numbers naturally (layer9 before layer100)"""
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', str(text))]

@dataclasses.dataclass
class Data:
    paths: list
    speeds: np.ndarray
    dwell_times: np.ndarray
    is_spot: np.ndarray
    spotsizes: np.ndarray
    beampowers: np.ndarray
    syncpoints: dict
    restores: np.ndarray

class TimedPoint:
    pass

def load_obp_objects(filepath):
    with open(filepath, "rb") as fh:
        data = fh.read()
    if filepath.suffix == ".gz":
        data = gzip.decompress(data)
    consumed = new_pos = 0
    while consumed < len(data):
        msg_len, new_pos = _DecodeVarint32(data, consumed)
        msg_buf = data[new_pos : new_pos + msg_len]
        consumed = new_pos + msg_len
        packet = obp.Packet()
        packet.ParseFromString(msg_buf)
        attr = packet.WhichOneof("payload")
        yield getattr(packet, attr)


def load_obp_objects_from_files(filepaths):
    for filepath in filepaths:
        yield from load_obp_objects(filepath)

def _unpack_tp(obp_objects):
    for obj in obp_objects:
        if isinstance(obj, obp.TimedPoints):
            t = 0
            for point in obj.points:
                tp = TimedPoint()
                tp.x = point.x
                tp.y = point.y
                if point.t == 0:
                    point.t = t
                tp.t = t = point.t
                tp.params = obj.params
                yield tp
        else:
            yield obj

def load_artist_data(obp_objects) -> Data:
    paths, speeds, dwell_times = [], [], []
    is_spot = []
    spotsizes, beampowers, restores = [], [], []
    syncpoints, _lastseen = {}, {}
    _restore = 0

    for obj in _unpack_tp(obp_objects):
        if isinstance(obj, (obp.Line, obp.AcceleratingLine)):
            paths.append(Path(np.array([[obj.x0, obj.y0], [obj.x1, obj.y1]]) / 1e6, (Path.MOVETO, Path.LINETO)))
            speeds.append(obj.speed / 1e6 if isinstance(obj, obp.Line) else obj.sf)
            dwell_times.append(getattr(obj.params, "dwell_time", 0))
            is_spot.append(False)
        elif isinstance(obj, (obp.Curve, obp.AcceleratingCurve)):
            paths.append(Path(np.array([[obj.p0.x, obj.p0.y], [obj.p1.x, obj.p1.y], [obj.p2.x, obj.p2.y], [obj.p3.x, obj.p3.y]]) / 1e6, [Path.MOVETO, Path.CURVE4, Path.CURVE4, Path.CURVE4]))
            speeds.append(obj.speed / 1e6 if isinstance(obj, obp.Curve) else obj.sf)
            dwell_times.append(getattr(obj.params, "dwell_time", 0))
            is_spot.append(False)
        elif isinstance(obj, TimedPoint):
            paths.append(Path(np.array([[obj.x - 100, obj.y], [obj.x, obj.y + 100], [obj.x + 100, obj.y], [obj.x, obj.y - 100], [obj.x - 100, obj.y], [obj.x, obj.y]]) / 1e6, (Path.MOVETO, Path.LINETO, Path.LINETO, Path.LINETO, Path.LINETO, Path.MOVETO)))
            speeds.append(0)
            dwell_times.append(obj.t / 1e6)
            is_spot.append(True)
        elif isinstance(obj, obp.SyncPoint):
            if obj.endpoint not in syncpoints:
                syncpoints[obj.endpoint] = [0] * len(paths)
            _lastseen[obj.endpoint] = int(obj.value)
            continue
        elif isinstance(obj, obp.Restore):
            _restore = 1
            continue
        else:
            continue

        spotsizes.append(obj.params.spot_size)
        beampowers.append(obj.params.beam_power)
        for k, v in _lastseen.items():
            syncpoints[k].append(v)
        restores.append(_restore)
        _restore = 0

    for key in syncpoints:
        syncpoints[key] = np.array(syncpoints[key])

    if len(paths) == 0:
        raise Exception("no drawable objects in obp data")

    return Data(
        paths,
        np.array(speeds),
        np.array(dwell_times),
        np.array(is_spot, dtype=bool),
        np.array(spotsizes),
        np.array(beampowers),
        syncpoints,
        np.array(restores),
    )


def _build_norm(values, fallback_min=0.0, fallback_max=1.0):
    if len(values) == 0:
        return matplotlib.colors.Normalize(vmin=fallback_min, vmax=fallback_max)
    vmin = float(np.min(values))
    vmax = float(np.max(values))
    if vmin == vmax:
        if vmin == 0:
            vmax = 1.0
        else:
            vmin = 0.0
    return matplotlib.colors.Normalize(vmin=vmin, vmax=vmax)


def _compute_plot_limits(paths):
    vertices = np.concatenate([path.vertices for path in paths if len(path.vertices) > 0], axis=0)
    x_min, y_min = np.min(vertices, axis=0)
    x_max, y_max = np.max(vertices, axis=0)

    span = max(x_max - x_min, y_max - y_min, 1e-6)
    pad = max(span * 0.08, 5e-4)
    half = span / 2 + pad
    center_x = (x_min + x_max) / 2
    center_y = (y_min + y_max) / 2

    return (center_x - half, center_x + half), (center_y - half, center_y + half)

class ObpFrame(ttk.Frame):
    def __init__(self, master, data, slice_size, index=None, **kwargs):
        super().__init__(master, **kwargs)
        self.data = data
        index = index if index is not None else slice_size
        self.cap = lambda i: max(0, min(len(self.data.paths) - 1, int(i)))

        index = self.cap(index)
        slice_ = slice(self.cap(index + 1 - slice_size), self.cap(index) + 1)

        fig = Figure(figsize=(9, 8), constrained_layout=True)
        ax = fig.add_subplot(111)
        ax.axhline(0, linewidth=1, zorder=0)
        ax.axvline(0, linewidth=1, zorder=0)
        ax.add_patch(Circle((0, 0), 0.04, edgecolor='white', facecolor='none'))
        ax.add_patch(Circle((0, 0), 0.05, edgecolor='grey', facecolor='none', linestyle='--'))
        x_limits, y_limits = _compute_plot_limits(self.data.paths)
        ax.set_xlim(x_limits)
        ax.set_ylim(y_limits)
        ax.set_aspect("equal", adjustable="box")
        si_meter = EngFormatter(unit="m")
        ax.xaxis.set_major_formatter(si_meter)
        ax.yaxis.set_major_formatter(si_meter)
        ax.tick_params(axis="x", labelsize=8)
        ax.tick_params(axis="y", labelsize=8)

        line_mask = ~self.data.is_spot
        spot_mask = self.data.is_spot
        self.line_collection = mcoll.PathCollection(
            [self.data.paths[i] for i in np.flatnonzero(line_mask)],
            facecolors="none",
            transform=ax.transData,
            cmap=plt.cm.rainbow,
            norm=_build_norm(self.data.speeds[line_mask]),
        )
        self.line_collection.set_array(self.data.speeds[line_mask])
        ax.add_collection(self.line_collection)

        self.speed_cbar = fig.colorbar(self.line_collection, ax=ax, pad=0.01, aspect=50, format=EngFormatter(unit="m/s"))
        self.speed_cbar.set_label("Speed")
        self.speed_cbar.ax.tick_params(axis="y", labelsize=8)

        self.spot_collection = None
        self.dwell_cbar = None
        if np.any(spot_mask):
            self.spot_collection = mcoll.PathCollection(
                [self.data.paths[i] for i in np.flatnonzero(spot_mask)],
                transform=ax.transData,
                cmap=plt.cm.plasma,
                norm=_build_norm(self.data.dwell_times[spot_mask]),
                edgecolors="white",
                linewidths=0.5,
            )
            self.spot_collection.set_array(self.data.dwell_times[spot_mask])
            ax.add_collection(self.spot_collection)
            self.dwell_cbar = fig.colorbar(self.spot_collection, ax=ax, pad=0.05, aspect=50)
            self.dwell_cbar.set_label("Dwell Time (ms)")
            self.dwell_cbar.ax.tick_params(axis="y", labelsize=8)

        seg = self.data.paths[index]
        self.marker = ax.scatter(*seg.vertices[-1], c="white", marker="*", zorder=2)

        self.canvas = FigureCanvasTkAgg(fig, master=self)
        self.canvas.draw()
        self.canvas.mpl_connect("key_press_event", self.keypress)

        self._slice_size = tkinter.IntVar(value=slice_size)
        self._index = tkinter.IntVar(value=index)

        self._slice_size_spinbox = ttk.Spinbox(self, from_=0, to=len(self.data.paths) - 1, textvariable=self._slice_size, command=self.update_index, width=6)
        self._slice_size_spinbox.bind("<KeyRelease>", self.update_index)

        self._index_scale = tkinter.Scale(self, from_=0, to=len(self.data.paths) - 1, orient=tkinter.HORIZONTAL, variable=self._index, command=self.update_index)
        self._index_spinbox = ttk.Spinbox(self, from_=0, to=len(self.data.paths) - 1, textvariable=self._index, command=self.update_index, width=6)
        self._index_spinbox.bind("<KeyRelease>", self.update_index)

        self.info_value = tkinter.StringVar(value=",  ".join(self.get_info(index)))
        self.info_label = ttk.Label(self, textvariable=self.info_value)
        self.button_quit = ttk.Button(self, text="Quit", command=self.master.quit)
        self.toolbar_frame = ttk.Frame(master=self)
        NavigationToolbar2Tk(self.canvas, self.toolbar_frame).update()

        self._update_collections(slice_)

    def get_info(self, index):
        info = [f"{k}={v[index]}" for k, v in self.data.syncpoints.items()]
        info.append(f"Restore={int(self.data.restores[index])}")
        info.append(f"BeamPower(W)={int(self.data.beampowers[index])}")
        info.append(f"SpotSize(μm)={int(self.data.spotsizes[index])}")
        info.append(f"Speed(m/s)={self.data.speeds[index]:.3f}")
        info.append(f"DwellTime(ms)={self.data.dwell_times[index]:.5f}")
        return info

    def update_index(self, _=None):
        index = self.cap(self._index.get())
        ss = self._slice_size.get() or 1
        slice_ = slice(self.cap(index + 1 - ss), self.cap(index) + 1)
        segs = self.data.paths[slice_]

        if segs:
            self._update_collections(slice_)
            self.marker.set_offsets(segs[-1].vertices[-1])
            self.canvas.draw_idle()

        self.info_value.set(",  ".join(self.get_info(index)))

    def _update_collections(self, slice_):
        indices = np.arange(slice_.start, slice_.stop)
        line_indices = indices[~self.data.is_spot[indices]]
        spot_indices = indices[self.data.is_spot[indices]]

        self.line_collection.set_paths([self.data.paths[i] for i in line_indices])
        self.line_collection.set_array(self.data.speeds[line_indices])

        if self.spot_collection is not None:
            self.spot_collection.set_paths([self.data.paths[i] for i in spot_indices])
            self.spot_collection.set_array(self.data.dwell_times[spot_indices])

    def keypress(self, event):
        key = event.key.lower()
        stepsize = {"": 1, "shift": 10, "ctrl": 100, "alt": 1000}.get(event.key.split("+")[0], 1)
        if key in {"right", "p"}:
            self._index.set(self.cap(self._index.get() + stepsize))
        elif key in {"left", "n"}:
            self._index.set(self.cap(self._index.get() - stepsize))
        elif key == "a":
            self._index.set(0)
        elif key == "e":
            self._index.set(len(self.data.paths) - 1)
        elif key in "0123456789":
            n = int(key)
            for i, k in enumerate(self.data.syncpoints):
                if i + 1 == n:
                    self.nextdifferent(self.data.syncpoints[k])
        elif key == "r":
            self.nextdifferent(self.data.restores)
        elif key == "b":
            self.nextdifferent(self.data.beampowers)
        elif key == "s":
            self.nextdifferent(self.data.spotsizes)
        self.update_index()

    def nextdifferent(self, array):
        start = self.cap(self._index.get())
        diff = array[start:] != array[start]
        if diff.any():
            self._index.set(start + np.argmax(diff))

    def setup_grid(self):
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.canvas.get_tk_widget().grid(row=0, columnspan=4, sticky="NSWE")
        self._index_scale.grid(row=1, columnspan=4, sticky="NSWE")
        self.info_label.grid(row=2, column=0, sticky="SW")
        self._slice_size_spinbox.grid(row=2, column=1, sticky="SE")
        self._index_spinbox.grid(row=2, column=2, sticky="SE")
        self.button_quit.grid(row=2, column=3, sticky="SE")
        self.toolbar_frame.grid(row=3, columnspan=4, sticky="NSWE")

class FileSelector(ttk.Frame):
    """Frame with checkbox list for selecting one or more .obp files."""
    def __init__(self, master, folder_path, on_file_selected, **kwargs):
        super().__init__(master, **kwargs)
        self.folder_path = pathlib.Path(folder_path).resolve()
        self.on_file_selected = on_file_selected
        
        if not self.folder_path.exists():
            raise Exception(f"Folder not found: {self.folder_path}")
        
        # Look for .obp files in folder or obp/ subfolder
        self.obp_files = sorted(self.folder_path.glob("*.obp"), key=lambda path: natural_sort_key(path.name))
        if not self.obp_files:
            obp_subfolder = self.folder_path / "obp"
            if obp_subfolder.exists():
                self.folder_path = obp_subfolder
                self.obp_files = sorted(self.folder_path.glob("*.obp"), key=lambda path: natural_sort_key(path.name))
        
        if not self.obp_files:
            raise Exception(f"No .obp files found in {self.folder_path}")

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        ttk.Label(self, text="Files").grid(row=0, column=0, sticky="W", padx=5, pady=(5, 0))

        self.canvas = tkinter.Canvas(self, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient=tkinter.VERTICAL, command=self.canvas.yview)
        self.checkbox_frame = ttk.Frame(self.canvas)
        self.checkbox_frame.bind(
            "<Configure>",
            lambda _event: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas.create_window((0, 0), window=self.checkbox_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.grid(row=1, column=0, sticky="NSWE", padx=(5, 0), pady=5)
        self.scrollbar.grid(row=1, column=1, sticky="NS", pady=5)

        self.file_vars = []
        for idx, path in enumerate(self.obp_files):
            var = tkinter.BooleanVar(value=(idx == 0))
            ttk.Checkbutton(self.checkbox_frame, text=path.name, variable=var).pack(anchor="w", padx=5, pady=1)
            self.file_vars.append((path, var))

        self.status_value = tkinter.StringVar(value="")
        self.status_label = ttk.Label(self, textvariable=self.status_value, foreground="#ffb347")
        self.status_label.grid(row=2, column=0, columnspan=2, sticky="W", padx=5)

        self.ok_button = ttk.Button(self, text="OK", command=self._on_confirm)
        self.ok_button.grid(row=3, column=0, columnspan=2, sticky="EW", padx=5, pady=(5, 5))

        self._on_confirm()

    def _on_confirm(self):
        selected_files = [path for path, var in self.file_vars if var.get()]
        if not selected_files:
            self.status_value.set("Select at least one file.")
            return
        self.status_value.set("")
        self.on_file_selected(selected_files)

def main():
    parser = argparse.ArgumentParser(description="OBP data viewer")
    parser.add_argument(
        "folder",
        type=pathlib.Path,
        nargs="?",                    # makes it optional
        default=pathlib.Path.cwd(),   # fallback to current folder
        help="Path to build folder with .obp files (default: current directory)"
    )
    args = parser.parse_args()
    args.folder = args.folder.resolve()
    parser.add_argument("--slice-size", type=int, default=9999, help="Initial slice size")
    parser.add_argument("--index", type=int, default=100, help="Initial index")
    args = parser.parse_args()

    root = tkinter.Tk()
    root.title(f"OBP Viewer - {args.folder.name}")
    root.geometry("1000x900")
    root.columnconfigure(0, weight=1)
    root.columnconfigure(1, weight=0)
    root.rowconfigure(0, weight=1)
    
    current_frame = [None]
    
    def load_obp_files(filepaths):
        if current_frame[0] is not None:
            current_frame[0].destroy()
        
        try:
            obp_objects = load_obp_objects_from_files(filepaths)
            data = load_artist_data(obp_objects)
            
            frame = ObpFrame(root, data, args.slice_size, args.index)
            frame.grid(row=0, column=0, sticky="NSWE", padx=5, pady=5)
            frame.setup_grid()
            current_frame[0] = frame
            if len(filepaths) == 1:
                root.title(f"OBP Viewer - {filepaths[0].name}")
            else:
                root.title(f"OBP Viewer - {len(filepaths)} files")
        except Exception as e:
            print(f"Error loading selected files: {e}")
    
    selector = FileSelector(root, args.folder, load_obp_files)
    selector.grid(row=0, column=1, sticky="NS", padx=5, pady=5)
    
    root.mainloop()

if __name__ == "__main__":
    main()
