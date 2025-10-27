import pyvista as pv

# Create sliced 3mf model
import py3mf_slicer.get_items
import py3mf_slicer.slice

mesh1 = pv.Cube(center=(10, 10, 5), x_length=10, y_length=10, z_length=10) # Creating cubes as example geometries
mesh2 = pv.Cube(center=(10, -10, 5), x_length=10, y_length=10, z_length=10)
mesh3 = pv.Cube(center=(-10, 10, 5), x_length=10, y_length=10, z_length=10)
mesh4 = pv.Cube(center=(-10, -10, 5), x_length=10, y_length=10, z_length=10)
mesh5 = pv.Cube(center=(10, 10, 15), x_length=10, y_length=10, z_length=10)
# mesh1 = pv.read("your_path.stl") # you can also read a stl file directly

model = py3mf_slicer.get_items.get_py3mf_from_pyvista([mesh1, mesh2, mesh3, mesh4, mesh5]) # create a 3mf model
sliced_model = py3mf_slicer.slice.slice_model(model, 0.1) #slice the model with a layer height of 0.1mm

# Create a build from json file
from obplanner.model.build import Build
from obplanner.main import prepare_build

build = Build.from_json(r"examples\example2.json") # Loading build settings from a json file
prepare_build(build, sliced_model, r"examples\output") # Prepare the build and create obf files in the output folder