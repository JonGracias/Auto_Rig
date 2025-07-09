import bpy # type: ignore
import os
import json
from datetime import datetime

def get_registry_path():
    scripts_dir = bpy.utils.user_resource('SCRIPTS')
    return os.path.join(scripts_dir, "addons", "Auto_Rig", "Hierarchy", "armature_registry.json")

# ------------------------
# Core JSON I/O
# ------------------------

def load_registry():
    path = get_registry_path()
    if not os.path.isfile(path):
        return []
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"[AutoRig] Failed to load registry: {e}")
        return []

def save_registry(data):
    try:
        with open(get_registry_path(), "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"[AutoRig] Failed to save registry: {e}")

# ------------------------
# Armature Management
# ------------------------

def get_items_by_type(is_deform=True):
    data = load_registry()
    items = []
    for a in data:
        if a.get("is_deform") == is_deform:
            path = a.get("path", "")
            if os.path.isdir(path):
                items.append((a["name"], a["name"], ""))
            else:
                print(f"[AutoRig] Skipping '{a['name']}' – missing folder: {path}")
    return sorted(items)

def get_limb_items_from(armature_name):
    print(f"[AutoRig Debug] Fetching limbs for armature: {armature_name}")
    items = []

    if not armature_name:
        return [("", "<no armature>", "")]

    scripts_dir = bpy.utils.user_resource('SCRIPTS')
    driver_path = os.path.join(scripts_dir, "addons", "Auto_Rig", "Hierarchy", armature_name)
    print(f"[AutoRig Debug] Looking in: {driver_path}")

    if os.path.isdir(driver_path):
        for file in os.listdir(driver_path):
            if file.endswith(".json") and not file.startswith(".meta"):
                name = os.path.splitext(file)[0]
                items.append((name, name, ""))

    if not items:
        items.append(("none", "No limbs found", ""))

    return sorted(items)


def update_is_deform(armature_name, is_deform):
    data = load_registry()
    for a in data:
        if a["name"] == armature_name:
            a["is_deform"] = is_deform
            break
    else:
        print(f"[AutoRig] Armature '{armature_name}' not found in registry.")
    save_registry(data)

def create_or_update_entry(name, path=None, is_deform=False, notes=""):
    data = load_registry()
    for a in data:
        if a["name"] == name:
            a.update({
                "is_deform": is_deform,
                "notes": notes,
                "path": path or a.get("path"),
            })
            break
    else:
        data.append({
            "name": name,
            "created": datetime.now().strftime("%Y-%m-%d"),
            "is_deform": is_deform,
            "notes": notes,
            "path": path or "",
        })
    save_registry(data)
