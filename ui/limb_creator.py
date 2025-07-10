import bpy, os, json, math # type: ignore
from mathutils import Vector, Matrix # type: ignore
from ..utils import create_limb_chain

# — Helpers: JSON loader & rotation —
def load_limb_json(path):
    with open(path, 'r') as f:
        return json.load(f)

def rotate_z(vec, deg):
    return Matrix.Rotation(math.radians(deg), 3, 'Z') @ vec

def get_limb_chain_name_from_json(path):
    with open(path, "r") as f:
        data = json.load(f)
    for key in data.keys():
        if key != "_meta":
            return key  # Return the first actual limb chain name found
    return None

# — Operator —
class LIMB_OT_Build(bpy.types.Operator):
    bl_idname = "limb.build"
    bl_label = "Build Limb"

    def execute(self, context):
        scripts_dir = bpy.utils.user_resource('SCRIPTS')
        base_path = os.path.join(scripts_dir, "addons", "Auto_Rig", "Hierarchy")
        props = context.scene.autorig_props 
        retarget_name = None
        limb_chain_name = None
        source_name = None
        
        if props.mode   == 'ctrl_from_def':
            retarget_name   = props.deform_armature_name
            limb_chain_name = props.control_limb_name
            source_name     = props.control_armature_name
        elif props.mode == 'def_from_ctrl':
            retarget_name   = props.control_armature_name
            limb_chain_name = props.deform_limb_name
            source_name     = props.deform_armature_name
        elif props.mode == 'json':
            source_name     = props.filepath
            source_path     = os.path.join(base_path, source_name) 
            limb_chain_name = get_limb_chain_name_from_json(source_path)
        elif props.mode == 'deform':
            limb_chain_name = props.deform_limb_name
            source_name     = props.deform_armature_name
        elif props.mode == 'control':
            limb_chain_name = props.control_limb_name
            source_name     = props.control_armature_name
        else:
            return self.report({'ERROR'}, "Invalid mode.")

        if not source_name:
            self.report({'ERROR'}, "Source Armature must be set.")
            return {'CANCELLED'}


        # Build it!
        create_limb_chain.main(source_name, limb_chain_name, retarget_name)

        

        return {'FINISHED'}


# — Panel —
class LIMB_PT_Builder(bpy.types.Panel):
    bl_label = "Limb Builder"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Auto Rig'

    def draw(self, context):
        layout = self.layout
        props = context.scene.autorig_props
        layout.prop(props, "filepath")
        layout.prop(props, "new_arm_name")
        layout.prop(props, "mode") 
        layout.operator("limb.build")

# — Register —
classes = (LIMB_OT_Build, LIMB_PT_Builder)
def register():
    for c in classes: bpy.utils.register_class(c)

def unregister():
    del bpy.types.Scene.limb_builder
    for c in reversed(classes): bpy.utils.unregister_class(c)

if __name__ == "__main__":
    register()
