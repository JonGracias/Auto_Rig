from mathutils import Vector, Euler, Quaternion # type: ignore
import bpy # type: ignore
import os
import json

AVAILABLE_ARMATURES = []

def get_armature_enum_items(self, context):
    global AVAILABLE_ARMATURES
    return [(name, name, "") for name in AVAILABLE_ARMATURES]

def ensure_armature_exists(name, meta_path=None):
    # Determine final name based on collection presence
    base_name = name
    suffix = 0
    collection_objects = bpy.context.collection.objects

    while True:
        name_to_check = base_name if suffix == 0 else f"{base_name}.{str(suffix).zfill(3)}"
        obj = bpy.data.objects.get(name_to_check)
        
        if obj is None:
            name = name_to_check
            break  # Unique name found
        elif obj.type == 'ARMATURE' and collection_objects.get(name_to_check) is obj:
            return obj  # Reuse armature already in current collection
        else:
            suffix += 1

    # Create new armature object
    arm_data = bpy.data.armatures.new(name)
    arm_obj = bpy.data.objects.new(name, arm_data)

    # Link to current collection and select
    bpy.context.collection.objects.link(arm_obj)
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.select_all(action='DESELECT')
    arm_obj.select_set(True)

    # If meta_path is given, apply transform from metadata
    if meta_path and os.path.exists(meta_path):
        with open(meta_path, 'r') as f:
            data = json.load(f)
            meta = data.get("_meta", {}).get("properties", {})

        arm_obj.location = Vector(meta.get("location", [0.0, 0.0, 0.0]))
        arm_obj.scale = Vector(meta.get("scale", [0.01, 0.01, 0.01]))
        arm_obj.rotation_mode = meta.get("rotation_mode", 'XYZ')

        if arm_obj.rotation_mode == 'QUATERNION':
            arm_obj.rotation_quaternion = Quaternion(meta.get("rotation_quaternion", [1.0, 0.0, 0.0, 0.0]))
        elif arm_obj.rotation_mode == 'AXIS_ANGLE':
            arm_obj.rotation_axis_angle = meta.get("rotation_axis_angle", [0.0, 0.0, 1.0, 0.0])
        else:
            arm_obj.rotation_euler = Euler(meta.get("rotation_euler", [0.0, 0.0, 0.0]))

        print(f"[OK] Applied transform from _meta to armature '{name}'")

    return arm_obj

def get_selected_armature():
    obj = bpy.context.active_object
    return obj if obj and obj.type == 'ARMATURE' else None

def read_available_armatures():
    current_dir = os.path.dirname(__file__)
    list_path = os.path.join(current_dir, '..', 'Hierarchy', 'available_armatures')
    
    if not os.path.isfile(list_path):
        raise FileNotFoundError(f"[ERROR] Missing 'available_armatures' file: {list_path}")
    
    with open(list_path, 'r') as f:
        armature_names = [line.strip() for line in f if line.strip()]
    
    return armature_names

class ARMATURE_OT_select_available(bpy.types.Operator):
    """Select an available armature"""
    bl_idname = "wm.select_available_armature"
    bl_label = "Select Available Armature"
    bl_options = {'REGISTER', 'UNDO'}

    armature_list: bpy.props.EnumProperty(
        name="Available Armatures",
        description="Choose an armature from the list",
        items=get_armature_enum_items  # not []
    ) # type: ignore
    
    def execute(self, context):
        # Store the selected name for later use
        context.window_manager.selected_armature_name = self.armature_list
        print(f"[INFO] User selected armature: {self.armature_list}")
        return {'FINISHED'}

    def invoke(self, context, event):
        global AVAILABLE_ARMATURES
        items = [(name, name, "") for name in AVAILABLE_ARMATURES]
        if not items:
            self.report({'ERROR'}, "No available armatures to select")
            return {'CANCELLED'}
        return context.window_manager.invoke_props_dialog(self)


def resolve_armature_object():
    selected = get_selected_armature()
    if selected:
        print(f"[INFO] Using selected armature: {selected.name}")
        return selected

    wm = bpy.context.window_manager
    chosen = getattr(wm, "selected_armature_name", None)
    if chosen:
        print(f"[INFO] Using previously selected armature: {chosen}")
        return ensure_armature_exists(chosen)

    # Otherwise launch menu
    global AVAILABLE_ARMATURES
    AVAILABLE_ARMATURES = read_available_armatures()
    bpy.ops.wm.select_available_armature('INVOKE_DEFAULT')

    print("[INFO] Awaiting user armature selection...")
    return None



def get_filepath(limb_name, armature_name):
    current_dir = os.path.dirname(__file__)
    base_path = os.path.normpath(os.path.join(current_dir, '..', 'Hierarchy', armature_name))
    os.makedirs(base_path, exist_ok=True)
    filepath = os.path.join(base_path, limb_name)
    return filepath

def update_available_armatures():
    current_dir = os.path.dirname(__file__)
    hierarchy_dir = os.path.join(current_dir, '..', 'Hierarchy')
    armatures_file = os.path.join(hierarchy_dir, 'available_armatures')

    if not os.path.isdir(hierarchy_dir):
        print(f"[ERROR] Hierarchy directory does not exist: {hierarchy_dir}")
        return

    # Get subdirectory names
    subdirs = [
        name for name in os.listdir(hierarchy_dir)
        if os.path.isdir(os.path.join(hierarchy_dir, name))
    ]

    # Optional: only include subdirs that have .json files inside
    valid_armatures = []
    for sub in subdirs:
        sub_path = os.path.join(hierarchy_dir, sub)
        if any(fname.endswith('.json') for fname in os.listdir(sub_path)):
            valid_armatures.append(sub)

    # Write to available_armatures
    with open(armatures_file, 'w') as f:
        for name in sorted(valid_armatures):
            f.write(name + '\n')

    print(f"[OK] Updated available armatures: {armatures_file}")