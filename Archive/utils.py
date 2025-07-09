import bpy
import json
import os
from mathutils import Vector

def print_armature():
    """
    Print every bone in armature (from EditBones so .roll is accessible).
    """
    armature = bpy.context.active_object  # This is the Object
    armature_data = armature.data         # This is the Armature data block

    # Make sure we're in Edit Mode
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='EDIT')

    bone_data = []

    for bone in armature.data.edit_bones:
        bone_data.append({
            "name": bone.name,
            "head": bone.head.copy(),
            "tail": bone.tail.copy(),
            "roll": bone.roll,
            "parent": bone.parent.name if bone.parent else None,
        })
        
    for bone in bone_data:
        print(f"\nArmature Object Name: {armature.name}")
        print(f"Armature Data Name: {armature_data.name}")
        print(f"Bone: {bone['name']}")
        print(f"  Head: {bone['head']}")
        print(f"  Tail: {bone['tail']}")
        print(f"  Roll: {bone['roll']}")
        print(f"  Parent: {bone['parent']}")
        print()

    # Return to Pose Mode
    bpy.ops.object.mode_set(mode='POSE')
    
def serialize_vector(vec):
    return [vec.x, vec.y, vec.z]

def serialize_constraint(con):
    con_data = {"type": con.type}
    for attr in dir(con):
        if attr.startswith("__") or attr in {"bl_rna", "rna_type", "type"}:
            continue
        try:
            value = getattr(con, attr)
            # Avoid serializing Blender types directly
            if isinstance(value, (str, int, float, bool)) or value is None:
                con_data[attr] = value
        except Exception:
            pass
    return con_data

def serialize_custom_props(bone):
    props = {}
    for key in bone.keys():
        if key.startswith("_"):
            continue
        props[key] = bone[key]
    return props

def serialize_bone_data(armature, root_bone_name, stop_at=[]):
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='EDIT')
    ebones = armature.data.edit_bones

    data = {}
    stop_at = set(stop_at)

    def traverse(bone):
        if bone.name in data:
            return
        if bone.name in stop_at:
            print(f"[STOP] Reached stop bone: {bone.name}")
            return

        data[bone.name] = {
            "name": bone.name,
            "head": serialize_vector(bone.head),
            "tail": serialize_vector(bone.tail),
            "roll": bone.roll,
            "parent": bone.parent.name if bone.parent else None,
            "use_connect": bone.use_connect,
            "custom_properties": serialize_custom_props(bone),
        }

        for child in bone.children:
            traverse(child)

    if root_bone_name not in ebones:
        print(f"[ERROR] Bone {root_bone_name} not found.")
        return {}

    traverse(ebones[root_bone_name])

    # Switch to pose mode to access constraints and drivers
    bpy.ops.object.mode_set(mode='POSE')
    for bone_name, bone_dict in data.items():
        pose_bone = armature.pose.bones.get(bone_name)
        if not pose_bone:
            continue

        # Constraints
        bone_dict["constraints"] = [serialize_constraint(c) for c in pose_bone.constraints]

        # Custom Properties on Pose Bone
        bone_dict["pose_custom_properties"] = serialize_custom_props(pose_bone)

    return data

def export_bone_chain_to_json(armature, root_bone_name, filepath, stop_at=[]):
    data = serialize_bone_data(armature, root_bone_name, stop_at)

    if not data:
        return

    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w") as f:
        json.dump(data, f, indent=4)

    print(f"[OK] Exported to {filepath}")

def export_bone_chains(base_subdir='root', chain_limit=None):
    # Format: (label, root_bone, output_filename, stop_list)
    chains = [
        ("head",          "head",           "head.json",             []),
        ("spine",         "pelvis",         "pelvis.json",           [
                                                                        'head', 
                                                                        'thigh_r', 
                                                                        'thigh_l', 
                                                                        'clavicle_r', 
                                                                        'clavicle_l'
                                                                     ]),
        ("arm_l",         "clavicle_l",     "arm_l.json",            []),
        ("arm_r",         "clavicle_r",     "arm_r.json",            []),
        ("leg_l",         "thigh_l",        "leg_l.json",            []),
        ("leg_r",         "thigh_r",        "leg_r.json",            []),
        ("ik_hand",       "ik_hand_root",   "ik_hand.json",          []),
        ("ik_leg",        "ik_leg_root",    "ik_leg.json",           []),
        ("center_of_mass","center_of_mass", "center_of_mass.json",   []),
        ("interaction",   "interaction",    "interaction.json",      []),
    ]

    # Truncate list if chain_limit is passed
    if chain_limit is not None:
        chains = chains[:chain_limit]

    armature = bpy.data.objects[base_subdir]
    current_collection = bpy.context.collection.name
    base_path = f'U:/Hero/Auto_Rig/Hierarchy/{current_collection}/{base_subdir}/'

    for label, root, filename, stop in chains:
        print(f"\n[EXPORT] {label} chain → {filename}")
        try:
            export_bone_chain_to_json(
                armature,
                root,
                base_path + filename,
                stop_at=stop
            )
        except Exception as e:
            print(f"[ERROR] Failed to export {label}: {e}")   
            
            
def clean_driver_metadata(driver_name="driver", keys_to_remove=None):
    obj = bpy.data.objects.get(driver_name)
    if not obj:
        print(f"[ERROR] Object '{driver_name}' not found.")
        return

    if keys_to_remove is None:
        keys_to_remove = ["jointTRSData", "lockInfluenceWeights"]

    for key in keys_to_remove:
        if key in obj:
            del obj[key]
        if "_RNA_UI" in obj and key in obj["_RNA_UI"]:
            del obj["_RNA_UI"][key]

    if "_RNA_UI" in obj and not obj["_RNA_UI"]:
        del obj["_RNA_UI"]

    print(f"[OK] Cleaned metadata from {driver_name}")

def remove_custom_property(keys_to_remove=None):
    # Make sure an armature is selected
    obj = bpy.context.object
    
    if keys_to_remove is None:
        print("No keys to remove.")
        return 

    if not obj or obj.type != 'ARMATURE':
        print("Please select an armature object.")
        return
    
    pbones = obj.pose.bones
    removed_count = 0

    for key in keys_to_remove:
        for bone in pbones:
            if key in bone:
                del bone[key]
                removed_count += 1

        print(f"Removed key from {removed_count} bones.")
    else:
        print("Please select an armature object.")

    
remove_custom_property("driver", ["lockInfluenceWeights"])
#export_bone_chains('driver', 8)
#export_bone_chains()
 
            

            
#--------------------------------------------------------------------------------------------------------#

def get_or_create_armature_in_collection(armature_name='root'):
    context_collection = bpy.context.collection

    # Check if the armature exists in the current collection
    for obj in context_collection.objects:
        if obj.name == armature_name and obj.type == 'ARMATURE':
            print(f"[INFO] Found armature '{armature_name}' in active collection.")
            return obj

    # It wasn't found — make a new one and link it
    print(f"[INFO] Creating new armature '{armature_name}' in active collection.")
    arm_data = bpy.data.armatures.new(name=armature_name + "_data")
    arm_object = bpy.data.objects.new(armature_name, arm_data)
    context_collection.objects.link(arm_object)
    return arm_object

    
def deserialize_vector(data):
    return Vector(data)

def build_skeleton_from_chain(label, armature_name='root'):
    chain_map = {
        "head":           "U:/Hero/Auto_Rig/Hierarchy/driver/head.json",
        "spine":          "U:/Hero/Auto_Rig/Hierarchy/driver/pelvis.json",
        "arm_l":          "U:/Hero/Auto_Rig/Hierarchy/driver/arm_l.json",
        "arm_r":          "U:/Hero/Auto_Rig/Hierarchy/driver/arm_r.json",
        "leg_l":          "U:/Hero/Auto_Rig/Hierarchy/driver/leg_l.json",
        "leg_r":          "U:/Hero/Auto_Rig/Hierarchy/driver/leg_r.json",
        "ik_hand":        "U:/Hero/Auto_Rig/Hierarchy/driver/ik_hand.json",
        "ik_leg":         "U:/Hero/Auto_Rig/Hierarchy/driver/ik_leg.json",
        "center_of_mass": "U:/Hero/Auto_Rig/Hierarchy/driver/center_of_mass.json",
        "interaction":    "U:/Hero/Auto_Rig/Hierarchy/driver/interaction.json",
    }
    
    if label not in chain_map:
        print(f"[ERROR] Unknown label: {label}")
        return

    filepath = chain_map[label]

    if not os.path.exists(filepath):
        print(f"[ERROR] JSON file not found: {filepath}")
        return

    with open(filepath, 'r') as f:
        bone_data = json.load(f)

    arm = get_or_create_armature_in_collection('root')
    if not arm:
        print(f"[ERROR] Armature '{armature_name}' not found.")
        return

    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='EDIT')
    eb = arm.data.edit_bones

    # Step 1: Track created bones
    created_bones = set()

    for name, data in bone_data.items():
        if name in eb:
            print(f"[STOP] Bone already exists: {name}")
            break

        bone = eb.new(name)
        bone.head = deserialize_vector(data["head"])
        bone.tail = deserialize_vector(data["tail"])
        bone.roll = data["roll"]
        created_bones.add(name)
        print(f"[OK] Created bone: {name}")

    # Step 2: Parent only bones from this chain
    for name in created_bones:
        data = bone_data[name]
        parent_name = data.get("parent")

        if parent_name and parent_name in created_bones:
            bone = eb[name]
            bone.parent = eb[parent_name]
            bone.use_connect = data.get("use_connect", True)

    bpy.ops.object.mode_set(mode='POSE')
    print(f"[DONE] Chain '{label}' imported into '{armature_name}'")


