import bpy
import importlib

from . import goodbye
importlib.reload(goodbye)

class AUTORIG_PT_HelloWorldPanel(bpy.types.Panel):
    bl_label = "Hello World Panel"
    bl_idname = "AUTORIG_PT_hello_world"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Auto Rig'

    def draw(self, context):
        layout = self.layout
        layout.label(text="Hello, World!")

classes = [
    AUTORIG_PT_HelloWorldPanel,
    goodbye.AUTORIG_PT_GoodbyeWorldPanel,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
