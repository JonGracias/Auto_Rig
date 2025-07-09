import bpy
import os
import importlib
from bpy.types import Panel, Operator, PropertyGroup # type: ignore
from bpy.props import StringProperty, PointerProperty # type: ignore

from . import control_pane
from . import deform_pane
from . import limb_pane
from . import limb_editor
from . import limb_export
from . import limb_creator
importlib.reload(control_pane)
importlib.reload(deform_pane)
importlib.reload(limb_pane) 
importlib.reload(limb_editor) 
importlib.reload(limb_export) 
importlib.reload(limb_creator) 



# --------- Register/Unregister ---------
classes = [
    control_pane.AUTORIG_PT_ControlRig,
    deform_pane.AUTORIG_PT_DeformRig,
    limb_editor.AutoRigLimbEditorProperties,
    limb_editor.AUTORIG_OT_SaveLimbChain,
    limb_editor.AUTORIG_PT_LimbChainEditor,
    limb_export.AutoRigLimbExportProperties,
    limb_export.AUTORIG_OT_ExportSelectedLimb,
    limb_export.AUTORIG_PT_LimbExportPanel,
    limb_creator.LIMB_OT_Build,
    limb_creator.LIMB_PT_Builder,
    limb_pane.AUTORIG_PT_LimbRig,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.limb_editor = PointerProperty(type=limb_editor.AutoRigLimbEditorProperties)
    bpy.types.Scene.limb_export = PointerProperty(type=limb_export.AutoRigLimbExportProperties)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.limb_editor
    del bpy.types.Scene.limb_export

if __name__ == "__main__":
    register()