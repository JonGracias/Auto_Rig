import bpy
import os

# --------- Panel ---------
class AUTORIG_PT_LimbRig(bpy.types.Panel):
    bl_label = "Limb Armature Selector"
    bl_idname = "AUTORIG_PT_Limb_Rig"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Auto Rig'

    def draw(self, context):
        layout = self.layout
        layout.label(text="Limb Properties")



