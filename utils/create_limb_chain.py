import json
import os
from typing import Dict, List, Tuple
from mathutils import Vector, Quaternion, Euler  # type: ignore
import bpy # type: ignore
import json
from pathlib import Path

SCALE = 1 # Or whatever you need

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

    # Apply Armature scale
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

def retarget_control_bones(original, target):
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

def retarget_deform_bones(original, target):
    # Later: Simply copy bone layout — already control-driven.
    print("Performing deform → control retargeting")
    return retarget_control_bones(original, target)

def apply_constraints_from_json(armature, bone_data):
    for bone_name, data in bone_data.items():
        print(f"Applying constraints for {bone_name}")
        if bone_name not in armature.pose.bones:
            print(f"Bone '{bone_name}' not found in armature.")
            continue
        pose_bone = armature.pose.bones[bone_name]
        for constraint_data in data.get("constraints", []):
            constraint = pose_bone.constraints.new(constraint_data["type"])
            for key, value in constraint_data.items():
                if key == "type":
                    continue  # Already handled by .new()
                # Robust target assignment for object fields
                if key in {"target", "pole_target", "space_object"} and value:
                    obj = armature
                    if obj:
                        setattr(constraint, key, obj)
                    else:
                        print(f"Warning: Object '{value}' not found for {key} on bone '{bone_name}'.")
                    continue
                # Subtargets are string names (for bone-in-object)
                if key in {"subtarget", "space_subtarget"}:
                    setattr(constraint, key, value)
                    continue
                # Everything else—set if possible
                try:
                    setattr(constraint, key, value)
                except Exception as e:
                    print(f"Warning: Could not set {key} to {value} on constraint '{constraint.name}' of bone '{bone_name}': {e}")
                    
def apply_drivers_from_json(armature, bone_data):
    for bone_name, data in bone_data.items():
        print(f"Applying drivers for {bone_name}")
        for driver_data in data.get("drivers", []):
            try:
                fcurve = armature.driver_add(driver_data["data_path"])
                driver = fcurve.driver
                driver.type = 'SCRIPTED'
                driver.expression = driver_data["expression"]
                for var_data in driver_data["variables"]:
                    var = driver.variables.new()
                    var.name = var_data["name"]
                    var.type = var_data["type"]
                    target = var.targets[0]
                    if var_data["target_id"]:
                        obj = bpy.data.objects.get(var_data["target_id"])
                        if obj:
                            target.id = obj
                        else:
                            print(f"Warning: Driver target object '{var_data['target_id']}' not found for bone '{bone_name}'")
                    target.data_path = var_data["data_path"]
            except Exception as e:
                print(f"Failed to create driver on '{bone_name}': {e}")
                
def apply_custom_properties(armature, bone_data):
    """
    Apply custom properties to pose bones from the provided bone data.

    Args:
        armature (bpy.types.Object): The armature object.
        bone_data (dict): Dictionary with bone names as keys and custom_properties as nested dicts.
    """
    for bone_name, data in bone_data.items():
        if bone_name not in armature.pose.bones:
            print(f"Bone '{bone_name}' not found.")
            continue

        pose_bone = armature.pose.bones[bone_name]
        custom_props = data.get("custom_properties", {})

        for prop, value in custom_props.items():
            try:
                pose_bone[prop] = value
                print(f"Set custom property '{prop}' = {value} on bone '{bone_name}'")
            except Exception as e:
                print(f"Failed to set custom property '{prop}' on bone '{bone_name}': {e}")


def main(source_armature_name, limb_chain_name, retarget_armature_name=None):
    """
    Build an armature using stored JSON data, optionally retargeting from another armature.

    Args:
        source_armature_name (str): Name of the base armature.
        limb_chain_name (str): Name of the limb or bone group.
        retarget_armature_name (str, optional): Armature to retarget positions from.
    """
    is_deform = is_deform_armature(source_armature_name)

    # Load source data
    source_file = get_source_file_path(source_armature_name, limb_chain_name)
    source_data = get_data_from_file(source_file)
    ue_bones = source_data.get("ue_bones", {})
    controllers = source_data.get("controllers", {})
    meta = source_data.get("_meta", {})

    # Load retarget data if requested
    if retarget_armature_name:
        retarget_file = get_source_file_path(retarget_armature_name, limb_chain_name)
        retarget_data = get_data_from_file(retarget_file)
        retarget_bones = retarget_data.get("ue_bones", {}) if retarget_data else {}

        if retarget_bones:
            print(f"RETARGETING A {'DEFORM' if is_deform else 'CONTROL'} ARMATURE")
            if is_deform:
                retarget_deform_bones(ue_bones, retarget_bones)
            else:
                retarget_control_bones(ue_bones, retarget_bones)
        else:
            print("No target bone data found.")
            print("Checking Print Statements")

    if not ue_bones:
        print("No source bone data found.")
        return

    # Create and transform the armature
    armature = get_or_create_armature()
    apply_global_transform(armature, meta)

    # Build bones into armature
    print("Building Bones")
    build_bones_from_json_file(meta, ue_bones, armature)
    build_bones_from_json_file(meta, controllers, armature)
    
    # Add Constraints
    apply_constraints_from_json(armature, ue_bones)
    apply_constraints_from_json(armature, controllers)

    # Add Drivers
    apply_drivers_from_json(armature, ue_bones)
    apply_drivers_from_json(armature, controllers)

    
    # Add Properties 
    print("Adding Properties")

if __name__ == "__main__":
    main("driver.01", "arm_l")