import bpy # type: ignore
from mathutils import Vector # type: ignore
# from utils.build_skeleton import main as check_bones

def add_hand_control_bone(arm_obj, side):
    """
    Creates a control bone for IK hand (ik_hand_<side>).
    Parents it to 'ik_hand_root' and positions it at the hand bone's head.
    Adds custom properties for finger controls.
    """
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='EDIT')
    eb = arm_obj.data.edit_bones

    bone_name = f"ik_hand_{side}"
    parent_name = "ik_hand_root"
    head_ref_name = f"hand_{side}"  # Bone to use as position reference

    if bone_name in eb:
        print(f"{bone_name} already exists.")
        return

    if parent_name not in eb or head_ref_name not in eb:
        print(f"[ERROR] Missing parent or reference bone: {parent_name} or {head_ref_name}")
        return

    parent = eb[parent_name]
    head_ref = eb[head_ref_name]

    # Create the control bone
    bone = eb.new(bone_name)
    bone.head = head_ref.head.copy()
    bone.tail = bone.head + Vector((0, 16.0, 0))  # Upward pointing bone
    bone.parent = parent

    # Settings for control behavior
    bone.use_inherit_rotation = True
    bone.use_local_location = True
    bone.use_connect = False

    # Switch to pose mode and add custom properties
    bpy.ops.object.mode_set(mode='POSE')
    pose_bone = arm_obj.pose.bones[bone_name]

    ## I should make a controll bone props function that only adds the properties. Here is a list of all the properties
    for prop in ["Hand", "Thumb", "Index", "Middle", "Ring", "Pinky"]:
        add_custom_prop(pose_bone, prop)

    print(f"{bone_name} created with custom properties.")


def add_custom_prop(pbone, name, default=0.0):
    """
    Adds a float custom property to a pose bone.
    'Hand' has slightly different limits than fingers.
    """
    if name == "Hand":
        min_val = -1.0
        max_val = 0.1
    else:
        min_val = -1.0
        max_val = 1.1

    if name not in pbone:
        pbone[name] = default  # Assign default value
        ui = pbone.id_properties_ui(name)
        ui.update(min=min_val, max=max_val, description=f"{name} control")


def create_arm_pole_target_bone(armature, side="r"):
    """
    Creates a pole target bone named arm_pole_target_<side>.
    It’s placed above the lowerarm_<side> bone's head.
    """
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='EDIT')
    eb = armature.data.edit_bones

    pole_name = f"arm_pole_target_{side}"
    parent_name = "ik_hand_root"
    ref_bone_name = f"lowerarm_{side}"

    if pole_name in eb:
        print(f"{pole_name} already exists.")
        return

    if ref_bone_name not in eb:
        print(f"[ERROR] Reference bone '{ref_bone_name}' not found.")
        return

    parent = eb[parent_name]
    ref_bone = eb[ref_bone_name]

    # Create the pole target bone slightly forward (Y axis) of the elbow
    bone = eb.new(pole_name)
    bone.head = ref_bone.head + Vector((0, 40, 0))  # Offset from elbow
    bone.tail = bone.head + Vector((0, 16.0, 0))    # Make it visible
    bone.parent = parent

    # IK pole target should not inherit unwanted motion
    bone.use_connect = False
    bone.use_inherit_rotation = False
    bone.use_local_location = True

    bpy.ops.object.mode_set(mode='OBJECT')
    print(f"[OK] Created pole target: {pole_name}")


def add_arm_ik_constraint(armature, side="r"):
    """
    Adds IK constraint to lowerarm_<side> to follow:
    - ik_hand_<side> as the IK goal
    - arm_pole_target_<side> as the pole target
    """
    bone_name = f"lowerarm_{side}"
    target_bone = f"ik_hand_{side}"
    pole_bone = f"arm_pole_target_{side}"

    try:
        pbone = armature.pose.bones[bone_name]

        con = pbone.constraints.new('IK')
        con.name = "IK"
        con.target = armature
        con.subtarget = target_bone

        con.pole_target = armature
        con.pole_subtarget = pole_bone
        con.pole_angle = 3.14159  # 180 degrees, often needed to align pole

        # IK behavior settings
        con.iterations = 500
        con.chain_count = 2         # Shoulder to hand chain
        con.use_tail = True
        con.use_stretch = True
        con.use_location = True
        con.use_rotation = False
        con.influence = 1.0

        print(f"[OK] IK constraint added to {bone_name}")

    except KeyError:
        print(f"[ERROR] Bone not found: {bone_name} or targets missing.")
    except Exception as e:
        print(f"[ERROR] Failed to add IK to {bone_name}: {e}")


def setup_ik_hand_constraints(armature, side='L'):
    """
    Applies constraints to ik_hand_<side>:
    - Copies transform from itself (on a driver armature or alternative rig)
    - Snaps to the tail of lowerarm_<side>
    """
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='POSE')

    ik_hand = f"ik_hand_{side.lower()}"
    lowerarm = f"lowerarm_{side.lower()}"

    pbone = armature.pose.bones[ik_hand]
    pbone.constraints.clear()  # Start fresh

    ## This is for the root armature. Should be saved becuase root armature will only copy transforms 
    # ForeArmZRot: 0 - 1
    # Hand: -1 -.10
    # IKInfluence: 0 - 1 Default Value 1 instead of 0
    # Index: -1 - 1.1 step 1 precision 3 
    # Middle: -1 - 1.1 step 1 precision 3 
    # Pinky: -1 - 1.1 step 1 precision 3 
    # Ring: -1 - 1.1 step 1 precision 3 
    # Thumb: -1 - 1.1 step 1 precision 3 
    # UpperArmXRot
    # UpperArmZRot
    # WristXRot
    # WristZRot
    # ##
    # Copy transforms from self (could be retargeted to another armature later)
    ct = pbone.constraints.new(type='COPY_TRANSFORMS')
    ct.name = "Copy Transforms from driver"
    ct.target = armature
    ct.subtarget = ik_hand
    ct.target_space = 'LOCAL'
    ct.owner_space = 'LOCAL'
    ct.mix_mode = 'REPLACE'
    ct.use_target_local = True

    ## not doing this anymore ##
    # Copy location from the tail of the lowerarm
    cl = pbone.constraints.new(type='COPY_LOCATION')
    cl.name = "Copy Location from driver lowerarm tail"
    cl.target = armature
    cl.subtarget = lowerarm
    cl.head_tail = 1.0  # 1.0 = tail
    cl.target_space = 'WORLD'
    cl.owner_space = 'WORLD'
    cl.use_x = cl.use_y = cl.use_z = True

    print(f"{ik_hand} constraints applied successfully.")


def rig_arm(armature, side):
    """
    Master function to rig one side of the arm.
    Steps:
    1. Create control bone
    2. Create pole target
    3. Add IK constraint to forearm
    4. Setup constraints on control bone
    """
    print(f"\n--- Rigging {side.upper()} side ---")
    try:
        # Change this to check for all bones and 
        # add any that need to be added
        add_hand_control_bone(armature, side)
        # Done in the previous function remove this one
        create_arm_pole_target_bone(armature, side)
        
        add_arm_ik_constraint(armature, side)
        setup_ik_hand_constraints(armature, side)
    except Exception as e:
        print(f"[ERROR] Rigging {side} failed: {e}")


def main(side='l', armature_name='driver'):
    """
    Entry point for running this module.
    Finds the armature and rigs the arm on the given side.
    """
    arm = bpy.data.objects.get(armature_name)
    if not arm:
        print(f"[ERROR] Armature '{armature_name}' not found.")
        return
    rig_arm(arm, side)

# Only runs if script is executed directly
if __name__ == "__main__":
    main('l')  # Default: rig the left arm
