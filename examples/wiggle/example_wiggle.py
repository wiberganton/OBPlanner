import pyvista as pv

# Create sliced 3mf model
import py3mf_slicer.get_items
import py3mf_slicer.slice

paths = [
    r"C:\Users\antwi87\Downloads\Part Studio 1\Part Studio 1 - Part 1.stl",
    r"C:\Users\antwi87\Downloads\Part Studio 1\Part Studio 1 - Part 2.stl",
    r"C:\Users\antwi87\Downloads\Part Studio 1\Part Studio 1 - Part 3.stl",
    r"C:\Users\antwi87\Downloads\Part Studio 1\Part Studio 1 - Part 4.stl",
    r"C:\Users\antwi87\Downloads\Part Studio 1\Part Studio 1 - Part 5.stl",
    r"C:\Users\antwi87\Downloads\Part Studio 1\Part Studio 1 - Part 6.stl",
    r"C:\Users\antwi87\Downloads\Part Studio 1\Part Studio 1 - Part 7.stl",
    r"C:\Users\antwi87\Downloads\Part Studio 1\Part Studio 1 - Part 8.stl",
    r"C:\Users\antwi87\Downloads\Part Studio 1\Part Studio 1 - Part 9.stl",
    r"C:\Users\antwi87\Downloads\Part Studio 1\Part Studio 1 - Part 10.stl",
    r"C:\Users\antwi87\Downloads\Part Studio 1\Part Studio 1 - Part 11.stl",
    r"C:\Users\antwi87\Downloads\Part Studio 1\Part Studio 1 - Part 12.stl",
    r"C:\Users\antwi87\Downloads\Part Studio 1\Part Studio 1 - Part 13.stl",
    ]
meshes = [pv.read(path) for path in paths]

# mesh1 = pv.read("your_path.stl") # you can also read a stl file directly

model = py3mf_slicer.get_items.get_py3mf_from_pyvista(meshes) # create a 3mf model
sliced_model = py3mf_slicer.slice.slice_model(model, 0.07) #slice the model with a layer height of 0.1mm

# Create a build from json file
from obplanner.model.build import Build
from obplanner.main import prepare_build

build = Build.from_json(r"examples\wiggle\example_wiggle.json") # Loading build settings from a json file
prepare_build(build, sliced_model, r"examples\output") # Prepare the build and create obf files in the output folder