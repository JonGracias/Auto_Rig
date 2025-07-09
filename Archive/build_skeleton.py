from mathutils import Vector, Euler, Quaternion # type: ignore
import bpy # type: ignore
import json
import os

def apply_global_transform(armature, meta_data):
    transform = meta_data.get("transform", {})
    
    # Apply location
    location = Vector(transform.get("location", [0.0, 0.0, 0.0]))
    armature.location = location

    # Apply scale
    scale = Vector(transform.get("scale", [1.0, 1.0, 1.0]))
    armature.scale = scale


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

def create_bone_in_edit_mode(armature, bone_name, head, tail, parent_name=None):
    bpy.ops.object.mode_set(mode='EDIT')
    ebones = armature.data.edit_bones

    if bone_name in ebones:
        bone = ebones[bone_name]
    else:
        bone = ebones.new(bone_name)

    bone.head = head
    bone.tail = tail

    if parent_name and parent_name in ebones:
        bone.parent = ebones[parent_name]

    return bone

def rebuild_bones_from_json_file(filepath, armature):
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"[ERROR] File not found: {filepath}")

    with open(filepath, 'r') as f:
        data = json.load(f)

    if not armature or armature.type != 'ARMATURE':
        raise ValueError("Armature not found or invalid")

    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='EDIT')

    bone_data = {k: v for k, v in data.items() if not k.startswith('_')}
    meta = data.get("_meta", {})
    apply_global_transform(armature, meta)

    # First pass: create all bones using scaled coordinates
    for bone_name, attrs in bone_data.items():
        head = Vector(attrs.get('head', [0, 0, 0]))
        tail = Vector(attrs.get('tail', [0, 1, 0]))
        create_bone_in_edit_mode(armature, bone_name, head, tail)

    # Second pass: assign parenting
    for bone_name, attrs in bone_data.items():
        parent = attrs.get('parent')
        if parent and parent in armature.data.edit_bones:
            armature.data.edit_bones[bone_name].parent = armature.data.edit_bones[parent]
        else:
            if parent:
                print(f"[INFO] Skipping parent assignment for '{bone_name}' - parent '{parent}' not found.")

    # Third pass: pose mode settings
    bpy.ops.object.mode_set(mode='POSE')
    for bone_name, attrs in bone_data.items():
        pose_bone = armature.pose.bones.get(bone_name)
        if not pose_bone:
            continue
        
        # Add bone to bone collections
        bone_collections = attrs.get("bone_collections", [])
        for col_name in bone_collections:
            if col_name not in armature.data.collections:
                new_col = armature.data.collections.new(name=col_name)
            else:
                new_col = armature.data.collections[col_name]

            bone_ref = armature.data.bones.get(bone_name)
            if bone_ref:
                new_col.assign(bone_ref)

         # Custom shape
        shape_name = attrs.get("custom_shape")
        if shape_name and shape_name in bpy.data.objects:
            pose_bone.custom_shape = bpy.data.objects[shape_name]

        # Custom shape transform
        shape_transform = attrs.get("custom_shape_transform")
        if shape_transform and shape_transform in bpy.data.objects:
            pose_bone.custom_shape_transform = bpy.data.objects[shape_transform]

        # Simple vector settings
        pose_bone.custom_shape_scale_xyz = Vector(attrs.get("custom_shape_scale_xyz", [1.0, 1.0, 1.0]))
        pose_bone.custom_shape_translation = Vector(attrs.get("custom_shape_translation", [0.0, 0.0, 0.0]))
        pose_bone.custom_shape_wire_width = attrs.get("custom_shape_wire_width", 0.5)
        pose_bone.use_custom_shape_bone_size = attrs.get("use_custom_shape_bone_size", False)

        # Lock settings
        pose_bone.lock_location = attrs.get("lock_location", [False, False, False])
        pose_bone.lock_rotation = attrs.get("lock_rotation", [False, False, False])
        pose_bone.lock_rotation_w = attrs.get("lock_rotation_w", False)
        pose_bone.lock_scale = attrs.get("lock_scale", [False, False, False])

        # Rotation mode
        pose_bone.rotation_mode = attrs.get("rotation_mode", "QUATERNION")
        
    bpy.ops.object.mode_set(mode='OBJECT')



def main(armature, limb):
    if not armature:
        print("[INFO] User input pending... run main() again after selection.")
        return

    rebuild_bones_from_json_file(limb, armature)


if __name__ == "__main__":
    armature = get_or_create_armature('driver')
    rebuild_bones_from_json_file('C:\\Users\\jon\\AppData\\Roaming\\Blender Foundation\\Blender\\4.4\\scripts\\addons\\Auto_Rig\\Hierarchy\\root.003\\arm_l.json', armature)






