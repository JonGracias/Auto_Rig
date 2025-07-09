import os
import bpy # type: ignore

def get_script_root():
    blend_dir = os.path.dirname(bpy.data.filepath)
    return os.path.join(blend_dir, "scripts", "Auto_Rig")

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
