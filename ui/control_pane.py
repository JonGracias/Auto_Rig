import bpy # type: ignore
import os

# --------- Panel ---------
class AUTORIG_PT_ControlRig(bpy.types.Panel):
    bl_label = "Control Armature Selector"
    bl_idname = "AUTORIG_PT_Control_Rig"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Auto Rig'

    def draw(self, context):
        layout = self.layout
        props = context.scene.autorig_props
        layout.prop(props, "control_armature_name")
        layout.prop(props, "control_limb_name")



