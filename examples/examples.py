import obplanner.model.pattern as pattern
import obplanner.pattern.generator as generator
from obplanner.model.strategies import Strategy
from obplanner.model.layer_default import LayerDefault, LayerStrategies
from obplanner.model.build import Build
from os.path import normpath as normalized_path


my_pattern_settings = pattern.PatternSettings(
    point_distance = 1,
    type = "square",
    offset = 0.0, # Offset distance compared against 3mf file contour
    start_rotation = 90.0, # Rotation angle in degrees for first layer
    layer_rotation = 0.0)  # Rotation angle in degrees between layers)
    

# Paths to the files used in the test
geometry1 = normalized_path("tests/geometries/test_geometry1.stl")
geometry2 = normalized_path("tests/geometries/test_geometry2.stl")
geometry3 = normalized_path("tests/geometries/test_geometry3.stl")

geometry_list = [geometry1, geometry2, geometry3]
components = list(range(len(geometry_list))) #passes in a list in the form [0,1,2,3...n]

import py3mf_slicer.load
import py3mf_slicer.slice
model = py3mf_slicer.load.load_files(geometry_list)
sliced_model = py3mf_slicer.slice.slice_model(model, 1)

pattern = generator.generate_pattern(sliced_model, 0, components, my_pattern_settings)

strategy = Strategy(
    geometry = components,
    pattern = my_pattern_settings, # Which pattern that should be used
    strategy = "LineSort", # defining which strategy that is used (the different strategies are defined in docs/scanning_strategies.md)
    power = 660, # Watt
    spot_size = 50, # in um 
    speed = 100000, # in um/s
    dwell_time = 10000 # in ns
)

strategy2 = Strategy(
    geometry = components,
    pattern = my_pattern_settings, 
    strategy = "SpotRandom", 
    power = 660,
    spot_size = 50, 
    speed = 100000,
    dwell_time = 10000 
)
layer_strat = LayerStrategies(
    melt = [strategy, strategy2] 
)

from obplanner.model.single_file import SingleShape

shape = SingleShape(
    strategies = [strategy,strategy2],
    shape = my_pattern_settings.type,
    size = 500
)

from obplanner.model.layer_default import LayerDefault, StartHeat

layer_def = LayerDefault(
    jump_safe=shape
)

start_heat = StartHeat(
    shape = shape
)
build = Build(
    layer_strategies = layer_strat,
    layer_default = layer_def,
    start_heat = start_heat
)
    
build.write_to_json(normalized_path("tests/input/build1.json"))

from obplanner.main import prepare_build

prepare_build(build, sliced_model, normalized_path("tests/output"))

