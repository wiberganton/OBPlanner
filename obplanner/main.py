from py3mf_slicer.get_items import get_number_layers, get_py3mf_from_pyvista
import py3mf_slicer.slice as slice
import obplib as obp
import json
import pyvista as pv


from obplanner.obf.generate_obf import generate_obf_directories, generate_other_files
from obplanner.model.build import Build
from obplanner.model.strategies import Strategy
from obplanner.model.single_file import SingleShape
import obplanner.pattern.generator as pattern_generator
import obplanner.pattern.compensator as pattern_compensator
import obplanner.strategy.generate_strategy as generate_strategy


def prepare_build(build_input: Build, sliced_model, path):
    build_info = {}
    # Create build path
    obf_path = generate_obf_directories(path)
    # Create start_heat
    if build_input.start_heat is not None:
        path = prepare_single_obp(build_input.start_heat.shape, obf_path, "start_heat")
        build_info["startHeat"] = {
            "file": path[0]["file"],
            "temperatureSensor": build_input.start_heat.temp_sensor,
            "targetTemperature": build_input.start_heat.target_temp,
            "timeout": build_input.start_heat.timeout
        }

    # Create layer_defaults
    build_info["layerDefaults"] = build_input.layer_default.layer_feed.to_camel_dict()
    if build_input.layer_default.jump_safe is not None:
        path = prepare_single_obp(build_input.layer_default.jump_safe, obf_path, "jump")
        build_info["layerDefaults"]["jumpSafe"] = path
    if build_input.layer_default.spatter_safe is not None:
        path = prepare_single_obp(build_input.layer_default.spatter_safe, obf_path, "spatter")
        build_info["layerDefaults"]["spatterSafe"] = path
    if build_input.layer_default.melt is not None:
        path = prepare_single_obp(build_input.layer_default.melt, obf_path, "melt")
        build_info["layerDefaults"]["melt"] = path
    if build_input.layer_default.heat_balance is not None:
        path = prepare_single_obp(build_input.layer_default.heat_balance, obf_path, "balance")
        build_info["layerDefaults"]["heatBalance"] = path
    # Create layer_strategies
    obp_directory = obf_path + r"/obp"
    num_layers = get_number_layers(sliced_model)
    layers = []
    for i in range(max(num_layers)):
        layer = {}
        # jump safe
        for ii, strategy in enumerate(build_input.layer_strategies.jump_safe):
            path = prepare_layer_obp(strategy, sliced_model, obp_directory, i, ii, "jump")
            layer.setdefault("jumpSafe", []).append({"file": path, "repetitions": strategy.repetitions})
        # spatter safe
        for ii, strategy in enumerate(build_input.layer_strategies.spatter_safe):
            path = prepare_layer_obp(strategy, sliced_model, obp_directory, i, ii, "spatter")
            layer.setdefault("spatterSafe", []).append({"file": path, "repetitions": strategy.repetitions})
        # melt
        for ii, strategy in enumerate(build_input.layer_strategies.melt):
            path = prepare_layer_obp(strategy, sliced_model, obp_directory, i, ii, "melt")
            layer.setdefault("melt", []).append({"file": path, "repetitions": strategy.repetitions})
        # heat_balance
        for ii, strategy in enumerate(build_input.layer_strategies.heat_balance):
            path = prepare_layer_obp(strategy, sliced_model, obp_directory, i, ii, "melt")
            layer.setdefault("heatBalance", []).append({"file": path, "repetitions": strategy.repetitions})
        layers.append(layer)
    build_info["layers"] = layers
    with open(f"{obf_path}/buildInfo.json", "w") as f:
        json.dump(build_info, f, indent=2)
    # Create other obf file
    generate_other_files(obf_path)



def prepare_layer_obp(strategy: Strategy, sliced_model, obp_directory, layer, strat_numb, type):
    # create pattern
    pattern = pattern_generator.generate_pattern(sliced_model, layer, strategy.geometry, strategy.pattern)
    # compensate pattern
    compensated_patter = pattern_compensator.compensate_pattern(pattern, {}, sliced_model, layer)
    # create obp elements
    obp_elements = generate_strategy.create_obp_elements(compensated_patter, strategy)
    #print("obp_elements", obp_elements)
    # export obp file
    obp_path = f"{obp_directory}/layer{layer}{type}{strat_numb}.obp"
    obp.write_obp(obp_elements, obp_path)
    # return path
    return f"obp/layer{layer}{type}{strat_numb}.obp"

def prepare_single_obp(single_shape: SingleShape, obp_directory: str, type: str):
    # create pattern
    if single_shape.shape == "circle":
        mesh = pv.Cylinder(
            center=(0, 0, 1),      # Center of the cylinder
            direction=(0, 0, 1),   # Axis direction (here along Z)
            radius=single_shape.size,            # Radius of the cylinder
            height=2.0,            # Height of the cylinder
            resolution=100         # Number of points on the circular face
        )
    else:
        mesh = pv.Cube(
            center=(0, 0, 1),      # Center of the cube
            x_length=single_shape.size,          # Length along the X-axis
            y_length=single_shape.size,          # Length along the Y-axis
            z_length=2.0           # Length along the Z-axis
        )
    model = get_py3mf_from_pyvista([mesh])
    sliced_model = slice.slice_model(model, 1)
    my_list = []
    for i, strategy in enumerate(single_shape.strategies):
        pattern = pattern_generator.generate_pattern(sliced_model, 0, [0], strategy.pattern)
        # create obp elements
        obp_elements = generate_strategy.create_obp_elements(pattern, strategy)
        obp_path = f"{obp_directory}/obp/{type}{i}.obp"
        obp.write_obp(obp_elements, obp_path)
        my_list.append({"file": f"obp/{type}{i}.obp", "repetitions": strategy.repetitions})
    return my_list
