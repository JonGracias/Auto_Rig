import bpy

class AUTORIG_PT_GoodbyeWorldPanel(bpy.types.Panel):
    bl_label = "Goodbye World Panel"
    bl_idname = "AUTORIG_PT_goodbye_world"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Auto Rig'

    def draw(self, context):
        layout = self.layout
        layout.label(text="Praise the Son!")