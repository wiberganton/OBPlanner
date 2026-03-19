import pyvista as pv

# Create sliced 3mf model
import py3mf_slicer.get_items
import py3mf_slicer.slice

mesh = pv.read(r"examples\overhang\overhang_45.stl")
# create translated copies
x_move = 10
y_move = 15
mesh1 = mesh.copy().translate([-x_move, -y_move, 0])
mesh2 = mesh.copy().translate([  0, -y_move, 0])
mesh3 = mesh.copy().translate([ x_move, -y_move, 0])

mesh4 = mesh.copy().translate([-x_move,   0, 0])
mesh5 = mesh.copy().translate([  0,   0, 0])
mesh6 = mesh.copy().translate([ x_move,   0, 0])

mesh7 = mesh.copy().translate([-x_move,  y_move, 0])
mesh8 = mesh.copy().translate([  0,  y_move, 0])
mesh9 = mesh.copy().translate([ x_move,  y_move, 0])

p = pv.Plotter()

p.add_mesh(mesh1, color="red")
p.add_mesh(mesh2, color="green")
p.add_mesh(mesh3, color="blue")

p.add_mesh(mesh4, color="cyan")
p.add_mesh(mesh5, color="yellow")
p.add_mesh(mesh6, color="magenta")

p.add_mesh(mesh7, color="orange")
p.add_mesh(mesh8, color="purple")
p.add_mesh(mesh9, color="white")

p.show()
"""
# mesh1 = pv.read("your_path.stl") # you can also read a stl file directly

model = py3mf_slicer.get_items.get_py3mf_from_pyvista([mesh1, mesh2, mesh3, mesh4, mesh5, mesh6, mesh7, mesh8, mesh9]) # create a 3mf model
sliced_model = py3mf_slicer.slice.slice_model(model, 0.07) #slice the model with a layer height of 0.1mm

# Create a build from json file
from obplanner.model.build import Build
from obplanner.main import prepare_build

build = Build.from_json(r"examples\overhang\example_geo_comp.json") # Loading build settings from a json file
prepare_build(build, sliced_model, r"examples\output") # Prepare the build and create obf files in the output folder

"""