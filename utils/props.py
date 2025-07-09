import bpy # type: ignore
import os
import importlib
from . import armature_registry
importlib.reload(armature_registry)

from .armature_registry import get_items_by_type, get_limb_items_from

# --------- Property update callbacks ---------

def get_control_armature_items(self, context):
    return get_items_by_type(is_deform=False)

def get_deform_armature_items(self, context):
    return get_items_by_type(is_deform=True)

def control_limb_items(self, context):
    return get_limb_items_from(context.scene.autorig_props.control_armature_name)

def deform_limb_items(self, context):
    return get_limb_items_from(context.scene.autorig_props.deform_armature_name)


class AutoRigProperties(bpy.types.PropertyGroup):
    control_armature_name: bpy.props.EnumProperty(
        name="Control Armature",
        items=get_control_armature_items,
    ) # type: ignore
    control_limb_name: bpy.props.EnumProperty(
        name="Control Limb",
        items=control_limb_items,
    ) # type: ignore
    deform_armature_name: bpy.props.EnumProperty(
        name="Deform Armature",
        items=get_deform_armature_items,
    ) # type: ignore
    deform_limb_name: bpy.props.EnumProperty(
        name="Deform Limb",
        items=deform_limb_items,
    ) # type: ignore
    mode: bpy.props.EnumProperty(
        name="Mode",
        items=[
            ('json', "JSON", ""),
            ('ctrl_from_def', "Deform → Control", ""),
            ('def_from_ctrl', "Control → Deform", ""),
        ]
    ) # type: ignore
    filepath: bpy.props.StringProperty(
        name="JSON Path",
        subtype='FILE_PATH'
    ) # type: ignore
    new_arm_name: bpy.props.StringProperty(
        name="Armature",
    ) # type: ignore