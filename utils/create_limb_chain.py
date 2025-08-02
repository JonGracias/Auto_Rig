import json
import os
from typing import Dict, List, Tuple
from mathutils import Vector, Quaternion, Euler  # type: ignore
import bpy # type: ignore
import json
from pathlib import Path

SCALE = 0.01  # Or whatever you need

#-------------------------------------Translation Functions-------------------------------------#

def vector_sub(a, b):
    return [a[i] - b[i] for i in range(3)]
def vector_add(a, b):
    return [a[i] + b[i] for i in range(3)]
def vector_cross(a, b):
    return [
        a[1]*b[2] - a[2]*b[1],
        a[2]*b[0] - a[0]*b[2],
        a[0]*b[1] - a[1]*b[0]
    ]
def rotate_vector_90(v, direction='left'):
    if direction == 'left':
        return [-v[1], v[0], v[2]]
    else:
        return [v[1], -v[0], v[2]]
def determine_turn(x_prev, x_curr, y_curr):
    a = vector_sub(x_curr, x_prev)
    b = vector_sub(y_curr, x_curr)
    cross_z = vector_cross(a, b)[2]
    return 'left' if cross_z > 0 else 'right'
def scale_vector(vec, scale):
    return [x * scale for x in vec]

#-----------------------------------------------------------------------------------------------#

def create_bone_in_edit_mode(armature, bone_name, head, tail):
    bpy.ops.object.mode_set(mode='EDIT')
    ebones = armature.data.edit_bones

    if bone_name in ebones:
        bone = ebones[bone_name]
    else:
        bone = ebones.new(bone_name)

    bone.head = head
    bone.tail = tail

    return bone

def build_bones_from_json_file(meta, bone_dict, armature):
    """
    Builds an armature from a JSON bone dictionary.

    This function creates bones inside the provided `armature` based on data from `bone_dict`.
    The process happens in two passes:

    Pass 1: Creation
    - Iterates over each bone entry in `bone_dict`.
    - Scales the head and tail coordinates using the global `SCALE` factor.
    - Calls a helper function `create_bone_in_edit_mode()` to generate bones in EDIT mode.

    Pass 2: Parenting
    - Loops through the bones again to assign parents, if specified.
    - Verifies both the child and parent bones exist before assigning parenting.
    - Logs skipped assignments if the parent is missing (helpful for debugging).

    Args:
        meta (dict): Optional metadata (not used directly here).
        bone_dict (dict): Dictionary where each key is a bone name and the value is a dict
                          containing at minimum 'head', 'tail', and optionally 'parent'.
        armature (Object): The Blender Armature object to modify.
    
    Raises:
        ValueError: If `armature` is missing or not of type 'ARMATURE'.

    Note:
        This function assumes that `SCALE` and `scale_vector()` are defined in the current scope.
    """
    if not armature or armature.type != 'ARMATURE':
        raise ValueError("Armature not found or invalid")
    
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='EDIT')

    # First pass: create bones
    for bone_name, bone_data in bone_dict.items():
        head = scale_vector(bone_data["head"], SCALE)
        tail = scale_vector(bone_data["tail"], SCALE)
        create_bone_in_edit_mode(armature, bone_name, head, tail)
        
    # Pass 2: Assign all parents
    for bone_name, bone_data in bone_dict.items():
        
        parent = bone_data["parent"]
        if parent and parent in armature.data.edit_bones and bone_name in armature.data.edit_bones:
            armature.data.edit_bones[bone_name].parent = armature.data.edit_bones[parent]
        elif parent:
            print(f"[INFO] Skipping parent assignment for '{bone_name}' - parent '{parent}' not found.")

    bpy.ops.object.mode_set(mode='OBJECT')

def get_source_file_path(armature_name="driver", limb_chain_name="arm_l"):
    scripts_dir = bpy.utils.user_resource('SCRIPTS')
    return Path(scripts_dir) / "addons" / "Auto_Rig" / "Hierarchy" / armature_name / f"{limb_chain_name}.json"

def get_data_from_file(filepath):
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"[ERROR] File not found: {filepath}")

    with open(filepath, 'r') as f:
        data = json.load(f)

    return data

def is_controller_bone(name):
    lowered = name.lower()
    return any(prefix in lowered for prefix in ["ik_", "fk_", "mch_", "ctrl_", "helper", "pole", "target", "twist"])

def getChild(bone):
    print(f"[DEBUG] bone keys: {list(bone.keys())}")
    children = bone.get("children")
    print(f"[DEBUG] bone.get('children') for bone: {bone.get('name', '<no name>')} => {children}")
    child_name = None

    if isinstance(children, list):
        for c in children:
            if not is_controller_bone(c):
                child_name = c
                break
    elif isinstance(children, str):
        if not is_controller_bone(children):
            child_name = children
            
    return child_name
    
def apply_global_transform(armature, meta_data):
    transform = meta_data.get("transform", {})
    print(f"[apply_global_transform] transform: {transform}")

    # Apply location
    location = Vector(transform.get("location", [0.0, 0.0, 0.0]))
    print(f"[apply_global_transform] setting location: {location}")
    armature.location = location

    # Apply scale
    scale = Vector(transform.get("scale", [1.0, 1.0, 1.0]))
    print(f"[apply_global_transform] setting scale: {scale}")
    armature.scale = scale

    print(f"[apply_global_transform] armature location now: {armature.location}")
    print(f"[apply_global_transform] armature scale now: {armature.scale}")
    
def get_or_create_armature():
    new_armature_name = bpy.context.scene.autorig_props.new_arm_name
    
    if not new_armature_name:
        new_armature_name = "auto_rig"
        
    # Try to get the armature object by name
    arm = bpy.data.objects.get(new_armature_name)

    if arm is None:
        print(f"[AutoRig] Armature '{new_armature_name}' not found. Creating new one.")

        # Create a new Armature data block
        arm_data = bpy.data.armatures.new(new_armature_name)

        # Create an object that uses the armature data
        arm = bpy.data.objects.new(new_armature_name, arm_data)

        # Link it to the current scene collection
        bpy.context.collection.objects.link(arm)

        # Set it to Edit Mode (optional, depends on your use case)
        bpy.context.view_layer.objects.active = arm
        bpy.ops.object.select_all(action='DESELECT')
        arm.select_set(True)
        bpy.ops.object.mode_set(mode='EDIT')

    return arm

def is_deform_armature(armature_name):
    scripts_dir = bpy.utils.user_resource('SCRIPTS')
    registry_file = os.path.join(scripts_dir, "addons", "Auto_Rig", "Hierarchy", "armature_registry.json")
    registry_data = get_data_from_file(registry_file)
    for entry in registry_data:
        if entry.get("name") == armature_name:
            return entry.get("is_deform", False)
    return False

def retarget_ue_bones(original, target):
    for bone_name in original:
        if bone_name in target:
            original[bone_name]["head"] = target[bone_name].get("head")
            child_name = getChild(target[bone_name])
            print(f"CHILDNAME: {child_name}")
            if child_name and child_name in target:
                original[bone_name]["tail"] = target[child_name].get("head")
                print(f"CHILD HEAD LOCATION: {target[child_name].get('head')}")
                print(f"CHILD HEAD LOCATION: {original[bone_name]['tail']}")
    return original

def main(source_armature_name, limb_chain_name, retarget_armature_name=None):
    """
    Main entry point for building an armature from saved JSON data.

    This function:
    - Determines whether the source armature is a deform or control rig.
    - Loads bone data (UE bones and controllers) from a JSON file.
    - Optionally retargets the source bones using another armature’s bone data.
    - Applies global transform metadata to the active armature.
    - Builds the armature by creating both UE bones and controller/helper bones.

    Args:
        source_armature_name (str): Name of the source armature (usually already in the scene).
        limb_chain_name (str): Name of the bone group or chain being processed (used in file lookup).
        retarget_armature_name (str, optional): If provided, bone positions will be retargeted
                                                from this armature instead.
    """
    # Check if the source armature is a deform rig
    is_deform = is_deform_armature(source_armature_name)

    # Locate file paths for the source and (optionally) retarget data
    source_file = get_source_file_path(source_armature_name, limb_chain_name)
    retarget_file = None
    if retarget_armature_name:
        retarget_file = get_source_file_path(retarget_armature_name, limb_chain_name)

    # Load JSON bone data from files
    source_data = get_data_from_file(source_file)
    retarget_data = get_data_from_file(retarget_file) if retarget_file else {}

    # Extract UE bone data (main bones) and optional retarget bones
    ue_bones_data = source_data.get("ue_bones", {})
    retargeting_bones_data = retarget_data.get("ue_bones", {})

    # If retarget data is available, use it to overwrite positions in source UE bones
    if retargeting_bones_data:
        if is_deform:
            print("RETARGETING A DEFORM ARMATURE")
        else:
            print("RETARGETING A CONTROL ARMATURE")
        retarget_ue_bones(source_data, retargeting_bones_data)

    # Get controller/helper bone data and armature metadata
    controller_bones_data = source_data.get("controllers", {})
    meta_data = source_data.get("_meta", {})

    # Create or retrieve the working armature, and apply its global transform
    armature = get_or_create_armature()
    apply_global_transform(armature, meta_data)

    # Basic error handling for missing data
    if not ue_bones_data:
        print("No source bone data.")
    elif not retargeting_bones_data:
        print("No target bone data.")
    else:
        # Apply retargeting override (note: this might be a duplicate retarget, consider revising)
        ue_bones_data = retarget_ue_bones(ue_bones_data, retargeting_bones_data)

    # Build the UE bones and controller/helper bones into the armature
    build_bones_from_json_file(meta_data, ue_bones_data, armature)
    build_bones_from_json_file(meta_data, controller_bones_data, armature)
    
if __name__ == "__main__":
    main("driver.01", "arm_l")