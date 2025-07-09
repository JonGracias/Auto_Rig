import bpy, os, json, math # type: ignore
from mathutils import Vector, Matrix # type: ignore

# — Helpers: JSON loader & rotation —
def load_limb_json(path):
    with open(path, 'r') as f:
        return json.load(f)

def rotate_z(vec, deg):
    return Matrix.Rotation(math.radians(deg), 3, 'Z') @ vec

# — Build function —
def build_limb(arm, limb_data, mode, source_arm=None):
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='EDIT')
    bones = limb_data['bones']
    prev_vec = None

    for bone in bones:
        parent = bone['parent']
        head = Vector(bone['head'])
        tail = Vector(bone['tail'])

        if mode == 'ctrl_from_def' and source_arm:
            def_b = source_arm.data.bones
            head = def_b[parent].head_local.copy()
            child = next((b['name'] for b in bones if b['parent'] == bone['name']), None)
            if child and child in def_b:
                tail = def_b[child].head_local.copy()
            elif prev_vec:
                tail = head + rotate_z(prev_vec, 90).normalized() * (tail - head).length

        elif mode == 'def_from_ctrl' and source_arm:
            ctrl_b = source_arm.data.bones
            head = ctrl_b[parent].head_local.copy()
            vec = (ctrl_b[bone['name']].tail_local - ctrl_b[bone['name']].head_local)
            tail = head + rotate_z(vec, 90).normalized() * 1.8

        eb = arm.data.edit_bones.new(bone['name'])
        eb.head, eb.tail = head, tail
        eb.parent = arm.data.edit_bones.get(parent, None)
        prev_vec = eb.tail - eb.head

    bpy.ops.object.mode_set(mode='OBJECT')
    
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
        props = context.scene.autorig_props 
        
        if props.mode   == 'ctrl_from_def':
            target_name     = props.control_armature_name
            limb_chain_name = props.control_limb_name
            source_name     = props.deform_armature_name
        elif props.mode == 'def_from_ctrl':
            target_name     = props.deform_armature_name
            limb_chain_name = props.deform_limb_name
            source_name     = props.control_armature_name
        elif props.mode == 'json':
            target_name     = None
            limb_chain_name = None
            source_name     = props.filepath
        elif props.mode == 'deform':
            target_name     = None
            limb_chain_name = props.deform_limb_name
            source_name     = props.deform_armature_name
        elif props.mode == 'control':
            target_name     = None
            limb_chain_name = props.control_limb_name
            source_name     = props.control_armature_name
        else:
            return self.report({'ERROR'}, "Invalid mode.")

        if not source_name:
            return self.report({'ERROR'}, "Source Armature must be set.")

        scripts_dir = bpy.utils.user_resource('SCRIPTS')
        base_path = os.path.join(scripts_dir, "addons", "Auto_Rig", "Hierarchy")
        target_path = os.path.join(base_path, target_name) if target_name else None
        source_path = os.path.join(base_path, source_name) 
        
        if not limb_chain_name:
            limb_chain_name = get_limb_chain_name_from_json(source_path)

        # Build it!
        build_limb(target_path, limb_chain_name, props.mode, source_path)

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
