import bpy

# Finger definitions
FINGERS = ["thumb", "index", "middle", "ring", "pinky"]

# Each finger has segments (bone suffixes)
SEGMENTS = {
    "thumb": ["02", "03"],  # Thumb typically has fewer segments
    "index": ["01", "02", "03"],
    "middle": ["01", "02", "03"],
    "ring": ["01", "02", "03"],
    "pinky": ["01", "02", "03"]
}

def rig_single_finger(armature, finger, segments, side):
    """
    Rigs a single finger by:
    - Adding a driver to the first segment
    - Applying a limit rotation to the root segment
    - Adding copy rotation constraints to the remaining segments
    """
    first_seg = segments[0]  # The base segment of the finger

    for i, seg in enumerate(segments):
        bone_name = f"{finger}_{seg}_{side}"

        if seg == first_seg:
            # Add driver and limit rotation to the root bone of the finger
            add_driver_to_finger_root(armature, bone_name, finger, side)
            try:
                pbone = armature.pose.bones[bone_name]
                add_limit_rotation(pbone)
            except KeyError:
                print(f"[WARN] Could not apply limit rotation: {bone_name} not found.")
        else:
            # For other segments, copy rotation from the previous bone in the chain
            prev_seg = segments[i - 1]
            source_bone = f"{finger}_{prev_seg}_{side}"
            add_copy_rotation_constraint(armature, bone_name, source_bone)


def add_driver_to_finger_root(armature, bone_name, finger, side):
    """
    Adds a driver to the quaternion rotation X (index 1) of the base finger bone.
    The driver uses two custom properties:
    - 'Hand' (general hand control)
    - Finger-specific (e.g., 'Thumb', 'Index', etc.)
    Both are stored on the controller bone 'ik_hand_{side}'
    """
    try:
        # Add driver to the X component of the quaternion rotation
        fcurve = armature.driver_add(f'pose.bones["{bone_name}"].rotation_quaternion', 1)
        driver = fcurve.driver
        driver.type = 'SCRIPTED'
        driver.expression = 'Hand + Finger'  # Combine two controls

        # Define 'Hand' driver variable
        var1 = driver.variables.new()
        var1.name = "Hand"
        var1.type = 'SINGLE_PROP'
        var1.targets[0].id = armature
        var1.targets[0].data_path = f'pose.bones["ik_hand_{side}"]["Hand"]'

        # Define 'Finger' driver variable (e.g., "Index", "Thumb")
        var2 = driver.variables.new()
        var2.name = "Finger"
        var2.type = 'SINGLE_PROP'
        var2.targets[0].id = armature
        var2.targets[0].data_path = f'pose.bones["ik_hand_{side}"]["{finger.capitalize()}"]'

        print(f"[OK] Driver added to {bone_name}")

    except KeyError:
        print(f"[WARN] Bone not found: {bone_name}")
    except Exception as e:
        print(f"[ERROR] Failed to add driver to {bone_name}: {e}")


def add_copy_rotation_constraint(armature, target_bone_name, source_bone_name):
    """
    Adds a 'Copy Rotation' constraint to make the target bone rotate like the source bone.
    - Only copies the X rotation (local space)
    - Used for finger segments to follow the segment before them
    """
    try:
        bone = armature.pose.bones[target_bone_name]
        con = bone.constraints.new('COPY_ROTATION')
        con.name = "AutoCopyRot"
        con.target = armature
        con.subtarget = source_bone_name
        con.owner_space = 'LOCAL'
        con.target_space = 'LOCAL'
        con.use_x = True     # Only X-axis
        con.use_y = False
        con.use_z = False
        con.mix_mode = 'REPLACE'

        print(f"[OK] Copy Rotation added to {target_bone_name} from {source_bone_name}")
    except KeyError:
        print(f"[WARN] Bone not found: {target_bone_name}")
    except Exception as e:
        print(f"[ERROR] Failed to add constraint to {target_bone_name}: {e}")


def add_limit_rotation(pbone, axis='X', min_val=-1.5708, max_val=0.174533):
    """
    Adds a 'Limit Rotation' constraint to restrict bone movement.
    - By default, limits rotation on the X axis from -90° to 10° (in radians)
    - Prevents fingers from rotating in unnatural ways
    """
    # Remove any existing limit rotation constraints
    for c in pbone.constraints:
        if c.type == 'LIMIT_ROTATION':
            pbone.constraints.remove(c)

    constraint = pbone.constraints.new(type='LIMIT_ROTATION')
    constraint.name = "AutoLimitRot"
    constraint.owner_space = 'LOCAL'

    # Set the axis limits
    if axis == 'X':
        constraint.use_limit_x = True
        constraint.min_x = min_val
        constraint.max_x = max_val
    elif axis == 'Y':
        constraint.use_limit_y = True
        constraint.min_y = min_val
        constraint.max_y = max_val
    elif axis == 'Z':
        constraint.use_limit_z = True
        constraint.min_z = min_val
        constraint.max_z = max_val

    print(f"[OK] Limit Rotation added to {pbone.name} on axis {axis}")


def rig_fingers(armature, side="l"):
    """
    Rigs all fingers on the specified side of the hand.
    - 'side' is usually 'l' (left) or 'r' (right)
    """
    print(f"[INFO] Rigging fingers on side: {side.upper()}")

    for finger in FINGERS:
        rig_single_finger(armature, finger, SEGMENTS[finger], side)


def main(side='l', armature_name='driver'):
    """
    Finds the armature by name and rigs the fingers on the given side.
    This is the entry point if the script is called programmatically.
    """
    arm = bpy.data.objects.get(armature_name)
    if not arm:
        print(f"[ERROR] Armature '{armature_name}' not found.")
        return
    rig_fingers(arm, side)


# Only run this block if the script is executed directly (not imported)
if __name__ == "__main__":
    main('l')  # Rig the left hand by default
