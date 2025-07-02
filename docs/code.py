
# Define components
import pyvista as pv
height = 20 #mm
cube1 = pv.Cube(center=(-18, 18, height/2), x_length=12, y_length=12, z_length=height)
cube2 = pv.Cube(center=(0, 18, height/2), x_length=12, y_length=12, z_length=height)
cube3 = pv.Cube(center=(18, 18, height/2), x_length=12, y_length=12, z_length=height)
cube4 = pv.Cube(center=(-18, 0, height/2), x_length=12, y_length=12, z_length=height)
cube5 = pv.Cube(center=(0, 0, height/2), x_length=12, y_length=12, z_length=height)
cube6 = pv.Cube(center=(18, 0, height/2), x_length=12, y_length=12, z_length=height)
cube7 = pv.Cube(center=(-18, -18, height/2), x_length=12, y_length=12, z_length=height)
cube8 = pv.Cube(center=(0, -18, height/2), x_length=12, y_length=12, z_length=height)
cube9 = pv.Cube(center=(18, -18, height/2), x_length=12, y_length=12, z_length=height)

# Create sliced 3mf model
import py3mf_slicer.get_items
import py3mf_slicer.slice

model = py3mf_slicer.get_items.get_py3mf_from_pyvista([cube1, cube2, cube3, cube4, cube5, cube6, cube7, cube8, cube9]) # create a 3mf model
sliced_model = py3mf_slicer.slice.slice_model(model, 0.075) #slice the model with a layer height of 0.075mm

# Create a build from json file
from obplanner.model.build import Build
from obplanner.main import prepare_build

build = Build.from_json(r"examples\example1\build_settings.json")
prepare_build(build, sliced_model, r"examples\example1")

