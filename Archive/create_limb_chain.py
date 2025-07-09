import json
import os
from typing import Dict, List, Tuple
from mathutils import Vector  # type: ignore
import bpy # type: ignore
import json
from pathlib import Path

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

def build_segment_dict_from_json(json_path: str) -> Dict[str, Tuple[List[float], List[float]]]:
    with open(json_path, 'r') as f:
        data = json.load(f)

    # Filter to just bones, ignore metadata or other entries
    bones = {k: v for k, v in data.items() if not k.startswith('_') and 'head' in v}

    # Make a list of (bone_name, head) in original JSON order
    chain = [(name, attrs["head"]) for name, attrs in bones.items()]

    segment_dict = {}
    for i in range(len(chain) - 1):
        name1, head1 = chain[i]
        _, head2 = chain[i + 1]
        segment_dict[name1] = (head1, head2)

    # Optional: handle final bone using its tail
    last_name, last_head = chain[-1]
    last_tail = bones[last_name].get("tail")
    if last_tail:
        segment_dict[last_name] = (last_head, last_tail)

    return segment_dict


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
    
    """
    if not armature or armature.type != 'ARMATURE':
        raise ValueError("Armature not found or invalid")
    
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='EDIT')

    # First pass: create bones
    for bone_name, bone_data in bone_dict.items():
        head = bone_data["head"]
        tail = bone_data["tail"]
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


def retarget_ue_bones(source, target):
    for bone_name in source:
        if bone_name in target:
            source[bone_name]["head"] = target[bone_name].get("head")
            child_name = target[bone_name].get("child")
            if child_name and child_name in target:
                source[bone_name]["tail"] = target[child_name].get("head")
            else:
                source[bone_name]["tail"] = [0,0,0]
    return source

def scale_and_apply(armature):
    bpy.ops.object.mode_set(mode='OBJECT')
        
    # Scale the armature
    armature.scale = (0.01, 0.01, 0.01)
    bpy.context.view_layer.update()

    # Apply the scale
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    
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
    
def get_or_create_armature(armature_name):
    # Try to get the armature object by name
    arm = bpy.data.objects.get(armature_name)

    if arm is None:
        print(f"[AutoRig] Armature '{armature_name}' not found. Creating new one.")

        # Create a new Armature data block
        arm_data = bpy.data.armatures.new(armature_name)

        # Create an object that uses the armature data
        arm = bpy.data.objects.new(armature_name, arm_data)

        # Link it to the current scene collection
        bpy.context.collection.objects.link(arm)

        # Set it to Edit Mode (optional, depends on your use case)
        bpy.context.view_layer.objects.active = arm
        bpy.ops.object.select_all(action='DESELECT')
        arm.select_set(True)
        bpy.ops.object.mode_set(mode='EDIT')

    return arm

def main(source_armature_name, limb_chain_name, target_armature_name=None):
    source_file = get_source_file_path(source_armature_name, limb_chain_name)
    target_file = None
    if target_armature_name:
        target_file = get_source_file_path(target_armature_name, limb_chain_name)
    
    source_data = get_data_from_file(source_file)
    target_data = get_data_from_file(target_file) if target_file else {}

    ue_bones_data = source_data.get("ue_bones", {})
    retargeting_bones_data = target_data.get("ue_bones", {})
    controller_bones_data = source_data.get("controllers", {})
    meta_data = source_data.get("_meta", {})        
    armature = get_or_create_armature(source_armature_name)
    apply_global_transform(armature, meta_data)

    if not ue_bones_data:
        print("No source bone data.")
    elif not retargeting_bones_data:
        print("No target bone data.")
        build_bones_from_json_file(meta_data, ue_bones_data, armature)
        build_bones_from_json_file(meta_data, controller_bones_data, armature)
        scale_and_apply(armature)
    else:
        ue_bones_data = retarget_ue_bones(ue_bones_data, retargeting_bones_data)
        print(json.dumps(ue_bones_data, indent=4))
        build_bones_from_json_file(meta_data, ue_bones_data, armature)
        build_bones_from_json_file(meta_data, controller_bones_data, armature)
        scale_and_apply(armature)


if __name__ == "__main__":
    
    main("driver", "arm_l")