import bpy # type: ignore
import os

# --------- Panel ---------
class AUTORIG_PT_DeformRig(bpy.types.Panel):
    bl_label = "Deform Armature Selector"
    bl_idname = "AUTORIG_PT_Deform_Rig"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Auto Rig'

    def draw(self, context):
        layout = self.layout
        props = context.scene.autorig_props
        layout.prop(props, "deform_armature_name")
        layout.prop(props, "deform_limb_name")




