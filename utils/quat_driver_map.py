import bpy # type: ignore

"""
dominus_servus_quat_link — Build a quaternion component/sign MAP from an example bone,
then add quaternion rotation drivers from the DOMINUS armature to the SERVUS armature.

Model
-----
DOM (dominus): the driving/controlling armature (source of motion)
SERV (servus): the deform armature that is driven (destination that deforms the mesh)

What this does
--------------
- Pick a START bone on SERV (active pose bone by default), include it and all descendants.
- Build a MAP from an EXAMPLE bone (default = START) by comparing REST-pose local axes
  (DOM vs SERV). The MAP captures both axis *permutation* and *sign*.
- For each SERV bone and each quaternion channel (W,X,Y,Z in that order), add a driver
  that reads the DOM’s same-named bone’s quaternion component in LOCAL space.
- Force driver variable Mode = QUATERNION (and set DOM pose bone rotation_mode too).

Driver Variable UI (per channel)
--------------------------------
Object: DOM armature
Bone:   <same bone name on DOM>   (or mapped name if you adapt it)
Type:   ROT_W / ROT_X / ROT_Y / ROT_Z  (from MAP)
Mode:   QUATERNION (forced)
Space:  LOCAL_SPACE
Expr:   'var' or '-var' (from MAP sign)

Notes
-----
- Assumes bone names match between DOM and SERV for the driven set.
- Avoid circular deps: drivers only read from DOM and write on SERV.
- If an axis aligns weakly (|dot| < threshold), consider a full 3×3 mix approach.
"""

# ------------------- MAP builder (handles permutation + sign) -------------------
def build_map_from_example(dom_arm, serv_arm, bone_name, warn_threshold=0.5):
    """Return MAP tuple:
       (('ROT_W', +1), (comp_for_X, ±1), (comp_for_Y, ±1), (comp_for_Z, ±1))
       where comp_for_* ∈ {'ROT_X','ROT_Y','ROT_Z'} chosen via |dot|, sign via dot sign.
    """
    dpb = dom_arm.pose.bones.get(bone_name)
    spb = serv_arm.pose.bones.get(bone_name)
    if not dpb or not spb:
        raise RuntimeError(
            f"Example bone '{bone_name}' must exist on BOTH armatures "
            f"(dom='{dom_arm.name}', serv='{serv_arm.name}')."
        )

    # Rest-pose local bases (armature space)
    Md = dpb.bone.matrix_local.to_3x3().normalized()  # DOM basis
    Ms = spb.bone.matrix_local.to_3x3().normalized()  # SERV basis

    dom_axes  = [Md.col[0], Md.col[1], Md.col[2]]     # DOM X,Y,Z
    serv_axes = [Ms.col[0], Ms.col[1], Ms.col[2]]     # SERV X,Y,Z
    dom_lbls  = ['ROT_X', 'ROT_Y', 'ROT_Z']

    # Dot table D[row=SERV axis, col=DOM axis]
    D = [[serv_axes[j].dot(dom_axes[i]) for i in range(3)] for j in range(3)]

    picks = []
    for j in range(3):                                 # for each SERV axis (X,Y,Z)
        i = max(range(3), key=lambda k: abs(D[j][k]))  # choose DOM axis with max |dot|
        s = +1 if D[j][i] >= 0 else -1                # sign from dot
        picks.append((dom_lbls[i], s, D[j][i], i))

    # Diagnostics
    print(f"[MAP] example bone '{bone_name}'  dom='{dom_arm.name}'  serv='{serv_arm.name}'")
    print("      dot table (rows=SERV X,Y,Z ; cols=DOM X,Y,Z):")
    for row in D:
        print("        " + "  ".join(f"{v:+.3f}" for v in row))
    print("      chosen: " + ", ".join(
        f"SERV{axis}->DOM {dom_lbls[i]}{'+' if s>0 else '-'}(dot={d:+.3f})"
        for axis, (_, s, d, i) in zip('XYZ', picks)
    ))
    for axis, (_, _, d, _) in zip('XYZ', picks):
        if abs(d) < warn_threshold:
            print(f"WARNING: SERV {axis} weak alignment (|dot|={abs(d):.3f}). "
                  "Sign/permutation map may be insufficient; consider a full 3×3 mix.")

    MAP = (('ROT_W', +1),
           (picks[0][0], picks[0][1]),  # SERV X reads DOM comp ±
           (picks[1][0], picks[1][1]),  # SERV Y reads DOM comp ±
           (picks[2][0], picks[2][1]))  # SERV Z reads DOM comp ±

    print(f"      MAP = {MAP}")
    return MAP


# ------------------------- Driver creation helpers -------------------------
def force_quat_mode_on_dom(dom_arm, bone_name):
    """Ensure the DOM pose bone is set to quaternion rotation mode."""
    pb = dom_arm.pose.bones.get(bone_name)
    if pb:
        pb.rotation_mode = 'QUATERNION'

def set_q_driver(serv_arm, dom_arm, serv_bone, idx, comp, sign):
    """
    Add/replace a driver on:
        serv_arm.pose.bones[serv_bone].rotation_quaternion[idx]
    where idx: 0=W, 1=X, 2=Y, 3=Z  (Blender's order)

    Variable reads DOM's same-named bone quaternion component in LOCAL space.
    """
    path = f'pose.bones["{serv_bone}"].rotation_quaternion'
    try:
        serv_arm.driver_remove(path, idx)
    except Exception:
        pass

    fcu = serv_arm.driver_add(path, idx)
    drv = fcu.driver
    drv.type = 'SCRIPTED'
    drv.expression = 'var' if sign > 0 else '-var'

    var = drv.variables.new()
    var.name = 'var'
    var.type = 'TRANSFORMS'
    tgt = var.targets[0]

    tgt.id = dom_arm                 # DOM object (driver reads from here)
    tgt.bone_target = serv_bone      # same-named bone on DOM (or swap in a name-map)
    tgt.transform_type = comp        # ROT_W / ROT_X / ROT_Y / ROT_Z
    tgt.transform_space = 'LOCAL_SPACE'

    # Force variable Mode = QUATERNION (some Blender builds default to Auto-Euler)
    if hasattr(tgt, "rotation_mode"):
        tgt.rotation_mode = 'QUATERNION'

    # Also ensure DOM bone itself is in quaternion mode (helps authoring)
    force_quat_mode_on_dom(dom_arm, serv_bone)

def iter_edges_from(start_name, arm_obj):
    """Yield (parent_name, child_name) pairs for all descendants (depth-first)."""
    pb = arm_obj.pose.bones
    start = pb.get(start_name)
    if not start:
        raise RuntimeError(f"Bone '{start_name}' not found in {arm_obj.name}")
    stack = [start]
    while stack:
        parent = stack.pop()
        for child in parent.children:
            yield parent.name, child.name
            stack.append(child)


# ------------------------------- Orchestration -------------------------------
def run(dom_name="dominus"):
    ctx = bpy.context
    serv_arm = ctx.object                           # SERV is the active/selected armature
    dom_arm  = bpy.data.objects.get(dom_name)       # DOM by name

    if not serv_arm or serv_arm.type != 'ARMATURE':
        raise RuntimeError("Select the SERV armature (drivers will be added here).")
    if not dom_arm or dom_arm.type != 'ARMATURE':
        raise RuntimeError(f"No armature named '{dom_name}' found.")

    # Start/Example bones (default to active pose bone on SERV)
    apb = bpy.context.active_pose_bone
    start_bone   = apb.name if (apb and bpy.context.object is serv_arm) else "spine_01"
    example_bone = start_bone

    # Build MAP from example bone
    MAP = build_map_from_example(dom_arm, serv_arm, example_bone)

    # Ensure anim data exists on SERV
    if not serv_arm.animation_data:
        serv_arm.animation_data_create()

    # Include the start bone itself (SERV[start] driven by DOM[same name])
    for idx, (comp, sign) in enumerate(MAP):  # W,X,Y,Z in order
        set_q_driver(serv_arm, dom_arm, start_bone, idx, comp, sign)

    # Then every descendant (still samples DOM's same-named bones)
    for _, child_name in iter_edges_from(start_bone, serv_arm):
        for idx, (comp, sign) in enumerate(MAP):
            set_q_driver(serv_arm, dom_arm, child_name, idx, comp, sign)

    print(f"Quaternion drivers set from '{start_bone}' down through all descendants (DOM='{dom_arm.name}', SERV='{serv_arm.name}').")


# Run immediately when executed as a Text block
if __name__ == "__main__":
    run(dom_name="dominus")
