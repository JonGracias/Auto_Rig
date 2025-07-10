import bpy # type: ignore
import json
import os


def clean_value(value):
    if isinstance(value, (int, float, str, bool, type(None))):
        return value
    elif hasattr(value, "__iter__") and not isinstance(value, str):
        return [clean_value(v) for v in value]
    elif hasattr(value, "to_tuple"):
        return list(value)
    elif hasattr(value, "name"):
        return value.name
    elif isinstance(value, dict):
        return {k: clean_value(v) for k, v in value.items()}
    return str(value)

def serialize_object_metadata(obj_name, obj):
    data = {
        "name": obj_name,
        "transform": {},
        "custom_properties": {},
        "rna_ui": {}
    }
    for attr in ("location", "scale", "dimensions"):
        try:
            data["transform"][attr] = clean_value(getattr(obj, attr))
        except Exception as e:
            data["transform"][attr] = f"[ERROR] {e}"

    for key in obj.keys():
        if key == "_RNA_UI":
            data["rna_ui"] = {k: clean_value(v) for k, v in obj["_RNA_UI"].items()}
        elif not key.startswith("_"):
            data["custom_properties"][key] = clean_value(obj[key])

    return data

def serialize_driver(driver):
    return {
        "data_path": driver.data_path,
        "expression": driver.driver.expression,
        "variables": [
            {
                "name": var.name,
                "type": var.type,
                "target_id": var.targets[0].id.name if var.targets else None,
                "data_path": var.targets[0].data_path if var.targets else None
            }
            for var in driver.driver.variables
        ]
    }

def serialize_constraint(constraint):
    d = {"name": constraint.name, "type": constraint.type}
    for attr in dir(constraint):
        if not attr.startswith("_") and not callable(getattr(constraint, attr)):
            try:
                d[attr] = clean_value(getattr(constraint, attr))
            except:
                continue
    return d

def is_controller_bone(name):
    lowered = name.lower()
    return any(prefix in lowered for prefix in ["ik_", "fk_", "mch_", "ctrl_", "helper", "pole", "target", "twist"])

def serialize_bone_data(chain, armature):
    """Serialize bone and controller data from an armature limb chain."""

    # Unpack chain definition
    root_bones, stop_bones = chain
    ue_bones = {}
    controllers = {}

    # Ensure correct mode and gather edit bone data
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='EDIT')
    ebones = armature.data.edit_bones
    edit_bone_data = {
        eb.name: {"head": list(eb.head), "tail": list(eb.tail)} for eb in ebones
    }

    # Switch to pose mode for extracting pose transforms
    bpy.ops.object.mode_set(mode='POSE')
    visited = set()

    def serialize_pose_bone(pose_bone, shape_obj, transform_obj):
        """Serialize a single pose bone's data into a dictionary."""
        # Bone color data
        bone_color = (
            {
                "palette": pose_bone.bone_color.palette,
                "custom_colors": {
                    "normal": list(pose_bone.bone_color.custom.normal),
                    "select": list(pose_bone.bone_color.custom.select),
                    "active": list(pose_bone.bone_color.custom.active)
                } if pose_bone.bone_color.palette == 'CUSTOM' else None
            }
            if hasattr(pose_bone, "bone_color")
            else None
        )

        # Constraints data
        constraints = [serialize_constraint(c) for c in pose_bone.constraints]

        # Drivers data
        drivers = []
        if armature.animation_data:
            for d in armature.animation_data.drivers:
                if d.data_path.startswith(f'pose.bones["{pose_bone.name}"]'):
                    drivers.append(serialize_driver(d))

        # Custom properties
        custom_properties = {
            k: clean_value(pose_bone[k])
            for k in pose_bone.keys()
            if not k.startswith("_")
        }

        # RNA UI
        rna_ui = {
            k: clean_value(pose_bone["_RNA_UI"][k])
            for k in pose_bone.get("_RNA_UI", {})
            if k in pose_bone
        }

        # Compose the main bone dictionary
        bone_dict = {
            "bone_collections": [
                col.name for col in getattr(pose_bone.bone, "collections", [])
            ],
            "parent": pose_bone.parent.name if pose_bone.parent else None,
            "children": [
                child.name
                for child in pose_bone.children
                if "twist" not in child.name.lower()
            ],
            "bone_color": bone_color,
            "custom_shape": {
                "object": shape_obj.name if shape_obj else None,
                "transform": transform_obj.name if transform_obj else None,
                "scale_xyz": list(pose_bone.custom_shape_scale_xyz),
                "translation": list(pose_bone.custom_shape_translation),
                "wire_width": pose_bone.custom_shape_wire_width,
                "rotation": list(shape_obj.rotation_euler) if shape_obj else None,
                "use_bone_size": pose_bone.use_custom_shape_bone_size
            },
            "lock": {
                "location": list(pose_bone.lock_location),
                "rotation": list(pose_bone.lock_rotation),
                "rotation_w": pose_bone.lock_rotation_w,
                "scale": list(pose_bone.lock_scale)
            },
            "rotation_mode": pose_bone.rotation_mode,
            "constraints": constraints,
            "drivers": drivers,
            "custom_properties": custom_properties,
            "rna_ui": rna_ui
        }

        return bone_dict

    def traverse(pose_bone):
        """Recursively serialize pose bones and children, skipping stop bones."""
        if pose_bone.name in visited or pose_bone.name in stop_bones:
            return
        visited.add(pose_bone.name)

        shape_obj = pose_bone.custom_shape
        transform_obj = pose_bone.custom_shape_transform

        bone_dict = serialize_pose_bone(pose_bone, shape_obj, transform_obj)

        # Merge edit bone info
        if pose_bone.name in edit_bone_data:
            bone_dict.update(edit_bone_data[pose_bone.name])

        # Sort bones into ue_bones/controllers
        if is_controller_bone(pose_bone.name):
            controllers[pose_bone.name] = bone_dict
        else:
            ue_bones[pose_bone.name] = bone_dict

        for child in pose_bone.children:
            traverse(child)

    # Traverse from all root bones
    for root in root_bones:
        if root in armature.pose.bones:
            traverse(armature.pose.bones[root])

    return {"ue_bones": ue_bones, "controllers": controllers}


def export_limb_file(limb_name, chain, armature, output_path):
    from . import armature_registry
    
    obj_name = f'{limb_name}_{armature.name}'
    bone_data = serialize_bone_data(chain, armature)
    data = {
        "_meta": serialize_object_metadata(obj_name, armature),
        "ue_bones": bone_data["ue_bones"],
        "controllers": bone_data["controllers"]
    }

    with open(output_path, "w") as f:
        json.dump(data, f, indent=4)

    # Add to registry
    full_path = os.path.abspath(os.path.dirname(output_path))
    is_deform = "deform" in armature.name.lower()
    armature_registry.create_or_update_entry(
        name=armature.name,
        path=full_path,
        is_deform=is_deform,
        notes="Auto-added from export_clean_data"
    )

    print(f"Exported: {output_path}")
    return output_path


def main(limb_index):
    limbs = ["base", "spine", "arm_l_target", "arm_r", "leg_l", "leg_r"]
    chains = [
        (["interaction", "center_of_mass"], []),
        (["pelvis"], ["thigh_r", "thigh_l", "clavicle_r", "clavicle_l"]),
        (["clavicle_l", "ik_hand_root"], ["ik_hand_r", "arm_pole_target_r"]),
        (["clavicle_r", "ik_hand_root"], ["ik_hand_l", "arm_pole_target_l"]),
        (["thigh_l", "ik_foot_root"], ["leg_ik_r", "leg_pole_target_r"]),
        (["thigh_r", "ik_foot_root"], ["leg_ik_l", "leg_pole_target_l"]),
    ]

    if limb_index < 0 or limb_index >= len(limbs):
        print("Invalid limb index")
        return

    armature = bpy.context.object
    if not armature or armature.type != 'ARMATURE':
        print("No armature selected")
        return

    limb = limbs[limb_index]
    chain = chains[limb_index]
    data = {
        "_meta": serialize_object_metadata(armature),
        **serialize_bone_data(chain, armature)
    }
    # Output file path
    # Get the directory of the current file
    current_dir = os.path.dirname(__file__)
    print(f"Current Directory: {current_dir}")

    # Move up to Hero/, then into Hierarchy/, then into armature folder
    base_path = os.path.normpath(
        os.path.join(current_dir, '..', 'Hierarchy', armature.name)
    )

    output_path = os.path.join(base_path, f"{limb}.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    export_limb_file(limb, chain, armature, output_path)

if __name__ == "__main__":
    main(2)  # change index for other limbs
