import pyvista as pv

# Create sliced 3mf model
import py3mf_slicer.get_items
import py3mf_slicer.slice

mesh1 = pv.Cube(center=(15, 0, 10), x_length=15, y_length=15, z_length=20) # Creating cubes as example geometries
mesh2 = pv.Cube(center=(-15, -15, 10), x_length=15, y_length=15, z_length=20) # Creating cubes as example geometries
mesh3 = pv.Cube(center=(-15, 15, 10), x_length=15, y_length=15, z_length=20) # Creating cubes as example geometries
# mesh1 = pv.read("your_path.stl") # you can also read a stl file directly

model = py3mf_slicer.get_items.get_py3mf_from_pyvista([mesh1, mesh2, mesh3]) # create a 3mf model
sliced_model = py3mf_slicer.slice.slice_model(model, 0.07) #slice the model with a layer height of 0.1mm

# Create a build from json file
from obplanner.model.build import Build
from obplanner.main import prepare_build

build = Build.from_json(r"examples\example3Dpattern.json") # Loading build settings from a json file
prepare_build(build, sliced_model, r"examples\output") # Prepare the build and create obf files in the output folder