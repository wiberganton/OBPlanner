from datetime import datetime
import os
import json
import shutil


def generate_obf_directories(folder_path, name=""):
    if name == "":
        now = datetime.now()
        name = f"build_{now.year}_{now.month:02}_{now.day:02}_{now.hour:02}_{now.minute:02}_{now.second:02}"
    path = f"{folder_path}/{name}"
    # Create the directory if it doesn't exist
    os.makedirs(path, exist_ok=True)
    os.makedirs(f"{path}/buildProcessors")
    os.makedirs(f"{path}/buildProcessors/lua")
    os.makedirs(f"{path}/obp")
    print(f"Directory '{path}' created or already exists.")
    return path

def generate_other_files(base_folder):
    # build processor
    source_path = r"obplanner\obf\helpers\buildProcessors.json"
    destination_path = f"{base_folder}/buildProcessors.json"
    shutil.copy(source_path, destination_path)
    # depenedencies
    source_path = r"obplanner\obf\helpers\dependencies.json"
    destination_path = f"{base_folder}/dependencies.json"
    shutil.copy(source_path, destination_path)
    # manifest
    source_path = r"obplanner\obf\helpers\manifest.json"
    destination_path = f"{base_folder}/manifest.json"
    shutil.copy(source_path, destination_path)
    # lua
    source_path = r"obplanner\obf\helpers\build.lua"
    destination_path = f"{base_folder}/buildProcessors/lua/build.lua"
    shutil.copy(source_path, destination_path)
    # obpviewer
    # lua
    source_path = r"obplanner\obf\helpers\obpviewer.py"
    destination_path = f"{base_folder}/obp/obpviewer.py"
    shutil.copy(source_path, destination_path)
