import json
import tempfile
from pathlib import Path
from typing import List

import plotly.graph_objects as go
import pyvista as pv
import streamlit as st
from py3mf_slicer.get_items import get_py3mf_from_pyvista
import py3mf_slicer.slice as slicer

from obplanner.main import get_numb_layers, prepare_build
from obplanner.model.build import Build


ROOT = Path(__file__).resolve().parent
DEFAULT_JSON = ROOT / "examples" / "wiggle" / "example_wiggle.json"
DEFAULT_OUTPUT = ROOT / "examples" / "output"
STRATEGY_GROUPS = ["melt", "jump_safe", "spatter_safe", "heat_balance"]
PATTERN_TYPES = ["square", "triangular", "contour"]
COLORS = ["#2563eb", "#dc2626", "#16a34a", "#ca8a04", "#9333ea", "#0891b2", "#ea580c"]
BASE_PLATE_RADIUS = 50
BASE_PLATE_THICKNESS = 10


def load_default_json() -> str:
    return DEFAULT_JSON.read_text()


def parse_json_text(json_text: str) -> dict:
    return json.loads(json_text)


def make_geometry(kind: str, name: str, size: float, height: float, x: float, y: float, z: float):
    if kind == "Cube":
        mesh = pv.Cube(center=(x, y, z + height / 2), x_length=size, y_length=size, z_length=height)
    elif kind == "Cylinder":
        mesh = pv.Cylinder(
            center=(x, y, z + height / 2),
            direction=(0, 0, 1),
            radius=size / 2,
            height=height,
            resolution=80,
        )
    else:
        mesh = pv.Sphere(center=(x, y, z + size / 2), radius=size / 2, theta_resolution=48, phi_resolution=48)
    mesh["source_name"] = [name] * mesh.n_points
    return mesh


def read_uploaded_stls(uploaded_files):
    records = []
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        for index, uploaded_file in enumerate(uploaded_files):
            stl_path = tmp_path / uploaded_file.name
            stl_path.write_bytes(uploaded_file.getbuffer())
            mesh = pv.read(stl_path)
            mesh["source_name"] = [uploaded_file.name] * mesh.n_points
            records.append(
                {
                    "id": f"uploaded_{index}_{uploaded_file.name}",
                    "name": uploaded_file.name,
                    "source": "STL",
                    "mesh": mesh,
                }
            )
    return records


def save_build_json(json_text: str, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    settings_path = output_dir / "streamlit_build_settings.json"
    parsed = json.loads(json_text)
    settings_path.write_text(json.dumps(parsed, indent=2))
    return settings_path


def default_transform():
    return {"scale": 1.0, "x": 0.0, "y": 0.0, "z": 0.0}


def ensure_transform(geometry_id: str):
    key = f"transform_{geometry_id}"
    if key not in st.session_state:
        st.session_state[key] = default_transform()
    return st.session_state[key]


def transformed_mesh(mesh, transform: dict):
    moved = mesh.copy(deep=True)
    moved.scale([transform["scale"]] * 3, inplace=True)
    moved.translate([transform["x"], transform["y"], transform["z"]], inplace=True)
    return moved


def center_and_ground_transform(mesh, geometry_id: str):
    transform = ensure_transform(geometry_id)
    scaled = mesh.copy(deep=True)
    scaled.scale([transform["scale"]] * 3, inplace=True)
    bounds = scaled.bounds
    transform["x"] = -((bounds[0] + bounds[1]) / 2)
    transform["y"] = -((bounds[2] + bounds[3]) / 2)
    transform["z"] = -bounds[4]
    st.session_state[f"transform_{geometry_id}"] = transform


def center_and_ground_clicked(geometry_id: str, mesh):
    center_and_ground_transform(mesh, geometry_id)
    transform = st.session_state[f"transform_{geometry_id}"]
    st.session_state[f"scale_{geometry_id}"] = transform["scale"]
    st.session_state[f"x_move_{geometry_id}"] = transform["x"]
    st.session_state[f"y_move_{geometry_id}"] = transform["y"]
    st.session_state[f"z_move_{geometry_id}"] = transform["z"]


def make_geometry_records(uploaded_records, generated_meshes):
    records = list(uploaded_records)
    for index, mesh in enumerate(generated_meshes):
        records.append(
            {
                "id": f"generated_{index}",
                "name": f"Generated geometry {index}",
                "source": "Generated",
                "mesh": mesh,
            }
        )

    transformed_records = []
    for index, record in enumerate(records):
        transform = ensure_transform(record["id"])
        transformed_records.append(
            {
                **record,
                "geometry_index": index,
                "transform": transform,
                "raw_mesh": record["mesh"],
                "mesh": transformed_mesh(record["mesh"], transform),
            }
        )
    return transformed_records


def mesh_summary(records):
    rows = []
    for record in records:
        mesh = record["mesh"]
        bounds = mesh.bounds
        transform = record["transform"]
        rows.append(
            {
                "geometry_index": record["geometry_index"],
                "name": record["name"],
                "source": record["source"],
                "scale": round(transform["scale"], 4),
                "x": round(transform["x"], 3),
                "y": round(transform["y"], 3),
                "z": round(transform["z"], 3),
                "points": mesh.n_points,
                "cells": mesh.n_cells,
                "x_min": round(bounds[0], 3),
                "x_max": round(bounds[1], 3),
                "y_min": round(bounds[2], 3),
                "y_max": round(bounds[3], 3),
                "z_min": round(bounds[4], 3),
                "z_max": round(bounds[5], 3),
            }
        )
    return rows


def base_plate_mesh():
    return pv.Cylinder(
        center=(0, 0, -BASE_PLATE_THICKNESS / 2),
        direction=(0, 0, 1),
        radius=BASE_PLATE_RADIUS,
        height=BASE_PLATE_THICKNESS,
        resolution=120,
    )


def add_mesh_trace(fig, mesh, name, color, opacity, hovertemplate):
    surface = mesh.extract_surface().triangulate()
    points = surface.points
    faces = surface.faces.reshape((-1, 4))[:, 1:4]
    fig.add_trace(
        go.Mesh3d(
            x=points[:, 0],
            y=points[:, 1],
            z=points[:, 2],
            i=faces[:, 0],
            j=faces[:, 1],
            k=faces[:, 2],
            name=name,
            color=color,
            opacity=opacity,
            flatshading=True,
            hovertemplate=hovertemplate,
        )
    )


def add_bounds_trace(fig, mesh, name):
    xmin, xmax, ymin, ymax, zmin, zmax = mesh.bounds
    corners = [
        (xmin, ymin, zmin),
        (xmax, ymin, zmin),
        (xmax, ymax, zmin),
        (xmin, ymax, zmin),
        (xmin, ymin, zmin),
        (xmin, ymin, zmax),
        (xmax, ymin, zmax),
        (xmax, ymax, zmax),
        (xmin, ymax, zmax),
        (xmin, ymin, zmax),
        (xmax, ymin, zmax),
        (xmax, ymin, zmin),
        (xmax, ymax, zmin),
        (xmax, ymax, zmax),
        (xmin, ymax, zmax),
        (xmin, ymax, zmin),
    ]
    fig.add_trace(
        go.Scatter3d(
            x=[point[0] for point in corners],
            y=[point[1] for point in corners],
            z=[point[2] for point in corners],
            mode="lines",
            name=name,
            line=dict(color="#f59e0b", width=7),
            hoverinfo="skip",
        )
    )


def mesh_to_plotly(records, selected_index=None):
    fig = go.Figure()
    add_mesh_trace(
        fig,
        base_plate_mesh(),
        "Base plate",
        "#737373",
        0.22,
        f"Base plate<br>radius {BASE_PLATE_RADIUS} mm<br>z -{BASE_PLATE_THICKNESS} to 0<extra></extra>",
    )
    for record in records:
        index = record["geometry_index"]
        is_selected = selected_index == index
        has_selection = selected_index is not None
        add_mesh_trace(
            fig,
            record["mesh"],
            f"{index}: {record['name']}",
            "#f59e0b" if is_selected else COLORS[index % len(COLORS)],
            0.95 if is_selected else (0.28 if has_selection else 0.72),
            f"Geometry {index}<br>{record['name']}<extra></extra>",
        )
        if is_selected:
            add_bounds_trace(fig, record["mesh"], f"Selected {index}")
    fig.update_layout(
        margin=dict(l=0, r=0, t=8, b=0),
        height=520,
        scene=dict(
            aspectmode="data",
            xaxis_title="X",
            yaxis_title="Y",
            zaxis_title="Z",
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0),
    )
    return fig


def selected_geometry_index(selection, rows):
    if not selection:
        return None
    selected_rows = getattr(getattr(selection, "selection", None), "rows", [])
    if not selected_rows and isinstance(selection, dict):
        selected_rows = selection.get("selection", {}).get("rows", [])
    if not selected_rows:
        return None
    selected_row = selected_rows[0]
    if selected_row >= len(rows):
        return None
    return rows[selected_row]["geometry_index"]


def strategy_to_row(group: str, strategy: dict, index: int) -> dict:
    pattern = strategy.get("pattern", {})
    return {
        "enabled": True,
        "group": group,
        "index": index,
        "strategy": strategy.get("strategy", "SpotRandom"),
        "geometry": ",".join(str(item) for item in strategy.get("geometry", [])),
        "power": strategy.get("power", 700),
        "spot_size": json.dumps(strategy.get("spot_size", 250)) if isinstance(strategy.get("spot_size"), list) else strategy.get("spot_size", 250),
        "speed": strategy.get("speed"),
        "dwell_time": json.dumps(strategy.get("dwell_time")) if isinstance(strategy.get("dwell_time"), list) else strategy.get("dwell_time"),
        "repetitions": strategy.get("repetitions", 1),
        "point_distance": pattern.get("point_distance", 0.25),
        "pattern_type": pattern.get("type", "square"),
        "start_layer": strategy.get("start_layer", 0),
        "end_layer": strategy.get("end_layer", -1),
        "apply_each": strategy.get("apply_at_each_n_layer", 1),
        "backscatter": strategy.get("backscatter", False),
        "pro_heat": strategy.get("pro_heat", False),
        "settings_json": json.dumps(strategy.get("settings", {}), indent=2),
        "pattern_settings_json": json.dumps(pattern.get("pattern_settings", {}), indent=2),
    }


def strategies_to_rows(build_data: dict) -> List[dict]:
    rows = []
    for group in STRATEGY_GROUPS:
        for index, strategy in enumerate(build_data.get("layer_strategies", {}).get(group, [])):
            rows.append(strategy_to_row(group, strategy, index))
    if not rows:
        rows.append(
            {
                "enabled": True,
                "group": "melt",
                "index": 0,
                "strategy": "SpotRandom",
                "geometry": "0",
                "power": 700,
                "spot_size": 250,
                "speed": None,
                "dwell_time": 500000,
                "repetitions": 1,
                "point_distance": 0.25,
                "pattern_type": "triangular",
                "start_layer": 0,
                "end_layer": -1,
                "apply_each": 1,
                "backscatter": False,
                "pro_heat": False,
                "settings_json": "{}",
                "pattern_settings_json": "{}",
            }
        )
    return rows


def parse_optional_number(value):
    if value is None or value == "":
        return None
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith("["):
            return json.loads(stripped)
        value = stripped
    numeric = float(value)
    return int(numeric) if numeric.is_integer() else numeric


def parse_geometry(value) -> List[int]:
    if value is None or str(value).strip() == "":
        return []
    return [int(item.strip()) for item in str(value).split(",") if item.strip()]


def rows_to_build_data(rows, base_data: dict) -> dict:
    data = json.loads(json.dumps(base_data))
    layer_strategies = {group: [] for group in STRATEGY_GROUPS}
    for row in rows:
        if not row.get("enabled", True):
            continue
        group = row.get("group", "melt")
        pattern = {
            "point_distance": float(row.get("point_distance") or 0.25),
            "type": row.get("pattern_type") or "square",
        }
        pattern_settings = json.loads(row.get("pattern_settings_json") or "{}")
        if pattern_settings:
            pattern["pattern_settings"] = pattern_settings

        strategy = {
            "pattern": pattern,
            "strategy": row.get("strategy") or "SpotRandom",
            "power": int(row.get("power") or 0),
            "spot_size": parse_optional_number(row.get("spot_size")),
            "repetitions": int(row.get("repetitions") or 1),
            "settings": json.loads(row.get("settings_json") or "{}"),
            "backscatter": bool(row.get("backscatter", False)),
            "pro_heat": bool(row.get("pro_heat", False)),
            "apply_at_each_n_layer": int(row.get("apply_each") or 1),
            "start_layer": int(row.get("start_layer") or 0),
            "end_layer": int(row.get("end_layer") if row.get("end_layer") is not None else -1),
            "geometry": parse_geometry(row.get("geometry")),
        }
        speed = parse_optional_number(row.get("speed"))
        dwell_time = parse_optional_number(row.get("dwell_time"))
        if speed is not None:
            strategy["speed"] = speed
        if dwell_time is not None:
            strategy["dwell_time"] = dwell_time
        layer_strategies.setdefault(group, []).append(strategy)

    data["layer_strategies"] = layer_strategies
    return data


def apply_layer_height_to_feed(data: dict, layer_height: float) -> dict:
    updated = json.loads(json.dumps(data))
    layer_default = updated.setdefault("layer_default", {})
    layer_feed = layer_default.setdefault("layer_feed", {})
    layer_feed["build_piston_distance"] = -float(layer_height)
    layer_feed["powder_piston_distance"] = 2 * float(layer_height)
    return updated


def load_json_to_session(data: dict):
    st.session_state.json_text = json.dumps(data, indent=2)


def default_single_shape(shape="circle", size=45):
    return {"shape": shape, "size": size, "strategies": []}


def render_start_and_defaults_editor(build_data: dict, layer_height: float) -> dict:
    data = apply_layer_height_to_feed(build_data, layer_height)

    st.markdown("**Start heat**")
    start_heat = data.get("start_heat") or {}
    start_enabled = st.checkbox("Use start heat", value=bool(data.get("start_heat")), key="start_heat_enabled")
    if start_enabled:
        cols = st.columns(4)
        start_heat["temp_sensor"] = cols[0].text_input("Temp sensor", value=start_heat.get("temp_sensor", "Sensor1"))
        start_heat["target_temp"] = cols[1].number_input("Target temp", value=int(start_heat.get("target_temp", 800)), step=10)
        start_heat["timeout"] = cols[2].number_input("Timeout", value=int(start_heat.get("timeout", 3600)), step=60)
        shape = start_heat.get("shape") or default_single_shape()
        shape["shape"] = cols[3].selectbox("Heat shape", ["circle", "square"], index=["circle", "square"].index(shape.get("shape", "circle")))
        shape["size"] = st.number_input("Heat shape size", min_value=0.1, value=float(shape.get("size", 45.0)), step=1.0)
        shape["strategies"] = json.loads(
            st.text_area(
                "Start heat strategies JSON",
                value=json.dumps(shape.get("strategies", []), indent=2),
                height=150,
            )
            or "[]"
        )
        start_heat["shape"] = shape
        data["start_heat"] = start_heat
    else:
        data["start_heat"] = None

    st.markdown("**Layer feed**")
    layer_default = data.setdefault("layer_default", {})
    layer_feed = layer_default.setdefault("layer_feed", {})
    layer_feed["build_piston_distance"] = -float(layer_height)
    layer_feed["powder_piston_distance"] = 2 * float(layer_height)
    feed_cols = st.columns(4)
    feed_cols[0].number_input("Build piston", value=float(layer_feed["build_piston_distance"]), disabled=True)
    feed_cols[1].number_input("Powder piston", value=float(layer_feed["powder_piston_distance"]), disabled=True)
    layer_feed["recoater_advance_speed"] = feed_cols[2].number_input(
        "Recoater advance speed",
        value=float(layer_feed.get("recoater_advance_speed", 100.0)),
    )
    layer_feed["recoater_retract_speed"] = feed_cols[3].number_input(
        "Recoater retract speed",
        value=float(layer_feed.get("recoater_retract_speed", 100.0)),
    )
    feed_cols = st.columns(4)
    layer_feed["recoater_dwell_time"] = feed_cols[0].number_input(
        "Recoater dwell time",
        value=float(layer_feed.get("recoater_dwell_time", 0)),
    )
    layer_feed["recoater_full_repeats"] = int(
        feed_cols[1].number_input("Full repeats", value=int(layer_feed.get("recoater_full_repeats", 0)), step=1)
    )
    layer_feed["recoater_build_repeats"] = int(
        feed_cols[2].number_input("Build repeats", value=int(layer_feed.get("recoater_build_repeats", 0)), step=1)
    )
    layer_feed["triggered_start"] = feed_cols[3].checkbox(
        "Triggered start",
        value=bool(layer_feed.get("triggered_start", True)),
    )

    st.markdown("**Layer defaults**")
    for key, label in [
        ("jump_safe", "Jump safe"),
        ("spatter_safe", "Spatter safe"),
        ("melt", "Melt"),
        ("heat_balance", "Heat balance"),
    ]:
        current = layer_default.get(key)
        with st.expander(label, expanded=bool(current)):
            enabled = st.checkbox(f"Use {label.lower()}", value=bool(current), key=f"default_{key}_enabled")
            if enabled:
                shape = current or default_single_shape()
                cols = st.columns(2)
                shape["shape"] = cols[0].selectbox(
                    "Shape",
                    ["circle", "square"],
                    index=["circle", "square"].index(shape.get("shape", "circle")),
                    key=f"default_{key}_shape",
                )
                shape["size"] = cols[1].number_input(
                    "Size",
                    min_value=0.1,
                    value=float(shape.get("size", 45.0)),
                    step=1.0,
                    key=f"default_{key}_size",
                )
                shape["strategies"] = json.loads(
                    st.text_area(
                        "Strategies JSON",
                        value=json.dumps(shape.get("strategies", []), indent=2),
                        height=150,
                        key=f"default_{key}_strategies",
                    )
                    or "[]"
                )
                layer_default[key] = shape
            else:
                layer_default[key] = None

    return data


st.set_page_config(page_title="OBPlanner Build Editor", layout="wide")
st.title("OBPlanner Build Editor")

if "json_text" not in st.session_state:
    st.session_state.json_text = load_default_json()

meshes = []
layer_height = 0.07
output_dir = DEFAULT_OUTPUT
run = False

with st.expander("1. Geometry import", expanded=True):
    import_left, import_right = st.columns([2, 1])
    with import_left:
        uploaded_files = st.file_uploader("Add STL files", type=["stl"], accept_multiple_files=True)
        uploaded_records = read_uploaded_stls(uploaded_files) if uploaded_files else []
        if uploaded_records:
            st.dataframe(
                [{"name": record["name"], "source": record["source"]} for record in uploaded_records],
                width="stretch",
                hide_index=True,
            )
    with import_right:
        geometry_count = st.number_input("Number of generated geometries", min_value=0, max_value=20, value=1, step=1)

    generated_meshes = []
    for i in range(int(geometry_count)):
        with st.expander(f"Generated geometry {i}", expanded=i == 0):
            cols = st.columns(6)
            kind = cols[0].selectbox("Type", ["Cube", "Cylinder", "Sphere"], key=f"kind_{i}")
            size = cols[1].number_input("Size", min_value=0.1, value=10.0, step=1.0, key=f"size_{i}")
            height = cols[2].number_input("Height", min_value=0.1, value=10.0, step=1.0, key=f"height_{i}")
            x = cols[3].number_input("X", value=0.0, step=1.0, key=f"x_{i}")
            y = cols[4].number_input("Y", value=0.0, step=1.0, key=f"y_{i}")
            z = cols[5].number_input("Z base", value=0.0, step=1.0, key=f"z_{i}")
            generated_meshes.append(make_geometry(kind, f"{kind} {i}", size, height, x, y, z))

with st.expander("2. Geometry modifiers and 3D view", expanded=True):
    geometry_records = make_geometry_records(uploaded_records, generated_meshes)
    meshes = [record["mesh"] for record in geometry_records]
    selected_index = None

    if geometry_records:
        view_col, table_col = st.columns([3, 2])
        with table_col:
            st.markdown("**Build geometries**")
            summary_rows = mesh_summary(geometry_records)
            geometry_table = st.dataframe(
                summary_rows,
                width="stretch",
                hide_index=True,
                selection_mode="single-row",
                on_select="rerun",
                key="geometry_table",
            )
            selected_index = selected_geometry_index(geometry_table, summary_rows)
            st.caption("Use these geometry_index values in the JSON strategy `geometry` fields.")
        with view_col:
            st.plotly_chart(mesh_to_plotly(geometry_records, selected_index), width="stretch")

        st.subheader("Move and scale")
        for record in geometry_records:
            transform = ensure_transform(record["id"])
            expanded = selected_index == record["geometry_index"]
            with st.expander(f"{record['geometry_index']}: {record['name']}", expanded=expanded):
                cols = st.columns([1, 1, 1, 1, 1])
                transform["scale"] = cols[0].number_input(
                    "Scale",
                    min_value=0.001,
                    value=float(transform["scale"]),
                    step=0.1,
                    format="%.4f",
                    key=f"scale_{record['id']}",
                )
                transform["x"] = cols[1].number_input(
                    "Move X",
                    value=float(transform["x"]),
                    step=1.0,
                    format="%.3f",
                    key=f"x_move_{record['id']}",
                )
                transform["y"] = cols[2].number_input(
                    "Move Y",
                    value=float(transform["y"]),
                    step=1.0,
                    format="%.3f",
                    key=f"y_move_{record['id']}",
                )
                transform["z"] = cols[3].number_input(
                    "Move Z",
                    value=float(transform["z"]),
                    step=1.0,
                    format="%.3f",
                    key=f"z_move_{record['id']}",
                )
                cols[4].button(
                    "Center and ground",
                    key=f"center_ground_{record['id']}",
                    on_click=center_and_ground_clicked,
                    args=(record["id"], record["raw_mesh"]),
                )
                st.session_state[f"transform_{record['id']}"] = transform
    else:
        st.plotly_chart(mesh_to_plotly([], None), width="stretch")
        st.info("Upload at least one STL file or create a simple geometry.")

with st.expander("3. Build preparation", expanded=True):
    build_top_left, build_top_right = st.columns([2, 1])
    with build_top_left:
        json_upload = st.file_uploader("Load settings JSON", type=["json"])
        if json_upload is not None:
            st.session_state.json_text = json_upload.getvalue().decode("utf-8")
    with build_top_right:
        layer_height = st.number_input("Layer height", min_value=0.001, value=0.07, step=0.01, format="%.3f")
        output_dir = Path(st.text_input("Output folder", value=str(DEFAULT_OUTPUT))).expanduser()

    try:
        build_data = parse_json_text(st.session_state.json_text)
        build_data = apply_layer_height_to_feed(build_data, layer_height)
        json_is_valid = True
    except json.JSONDecodeError as exc:
        build_data = {}
        json_is_valid = False
        st.error(f"JSON error: {exc}")

    start_tab, editor_tab, raw_tab = st.tabs(["Start/defaults", "Strategy table", "Raw JSON"])

    with start_tab:
        if json_is_valid:
            try:
                guided_data = render_start_and_defaults_editor(build_data, layer_height)
                if st.button("Apply start/defaults to JSON"):
                    load_json_to_session(guided_data)
                    st.success("Start settings and layer defaults updated.")
                    st.rerun()
            except Exception as exc:
                st.exception(exc)
        else:
            st.info("Fix the raw JSON before using the guided settings.")

    with editor_tab:
        if json_is_valid:
            strategy_rows = st.data_editor(
                strategies_to_rows(build_data),
                width="stretch",
                hide_index=True,
                num_rows="dynamic",
                column_config={
                    "enabled": st.column_config.CheckboxColumn("Use"),
                    "group": st.column_config.SelectboxColumn("Group", options=STRATEGY_GROUPS),
                    "pattern_type": st.column_config.SelectboxColumn("Pattern", options=PATTERN_TYPES),
                    "settings_json": st.column_config.TextColumn("Strategy settings JSON", width="large"),
                    "pattern_settings_json": st.column_config.TextColumn("Pattern settings JSON", width="large"),
                },
                key="strategy_editor",
            )
            if st.button("Apply table to JSON"):
                try:
                    updated_data = rows_to_build_data(strategy_rows, build_data)
                    updated_data = apply_layer_height_to_feed(updated_data, layer_height)
                    st.session_state.json_text = json.dumps(updated_data, indent=2)
                    st.success("JSON updated from the strategy table.")
                    st.rerun()
                except Exception as exc:
                    st.exception(exc)
        else:
            st.info("Fix the raw JSON before using the strategy table.")

    with raw_tab:
        raw_json_text = st.text_area(
            "Settings",
            value=json.dumps(build_data, indent=2) if json_is_valid else st.session_state.json_text,
            height=520,
            label_visibility="collapsed",
        )
        st.session_state.json_text = raw_json_text

    run = st.button("Slice and prepare build", type="primary", disabled=not meshes or not json_is_valid)

if run:
    try:
        build_json = apply_layer_height_to_feed(parse_json_text(st.session_state.json_text), layer_height)
        st.session_state.json_text = json.dumps(build_json, indent=2)
        settings_path = save_build_json(st.session_state.json_text, output_dir)
        build = Build.from_json(settings_path)

        with st.status("Preparing build...", expanded=True) as status:
            st.write("Creating py3mf model")
            model = get_py3mf_from_pyvista(meshes)
            st.write(f"Slicing at {layer_height} mm")
            sliced_model = slicer.slice_model(model, layer_height)
            st.write(f"Detected {get_numb_layers(sliced_model)} layers")
            st.write("Writing OBP/OBF output")
            prepare_build(build, sliced_model, str(output_dir))
            status.update(label="Build complete", state="complete")

        st.success(f"Build files written under: {output_dir}")
        st.info(f"Settings used: {settings_path}")
    except Exception as exc:
        st.exception(exc)
