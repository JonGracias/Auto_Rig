import bpy # type: ignore
import os
import json
from bpy.types import Panel, Operator, PropertyGroup # type: ignore
from bpy.props import EnumProperty, PointerProperty # type: ignore

from ..utils import export_clean_data


# ---- Limb Chain JSON Access ----
def get_limb_chains_path():
    scripts_dir = bpy.utils.user_resource('SCRIPTS')
    return os.path.join(scripts_dir, "addons", "Auto_Rig", "Hierarchy", "limb_chains.json")

def load_limb_chains():
    try:
        with open(get_limb_chains_path(), "r") as f:
            return json.load(f)
    except:
        return {}


# ---- Enum Items Generator ----
def get_limb_names_for_selected_armature(self, context):
    chains_data = load_limb_chains()

    # Support both formats
    if isinstance(chains_data, list):
        chains = chains_data  # flat list (like your image)
    elif isinstance(chains_data, dict):
        arm = context.object
        if not arm or arm.type != 'ARMATURE':
            return [("none", "<No Armature Selected>", "")]
        chains = chains_data.get(arm.name, [])
    else:
        chains = []

    if not chains:
        return [("none", "<No Chains Found>", "")]

    return [(c["name"], c["name"], c.get("note", "")) for c in chains if "name" in c]


# ---- Property Group ----
class AutoRigLimbExportProperties(PropertyGroup):
    export_limb_name: EnumProperty(
        name="Limb",
        description="Choose a limb chain to export",
        items=get_limb_names_for_selected_armature
    ) # type: ignore


class AUTORIG_OT_ExportSelectedLimb(Operator):
    bl_idname = "autorig.export_selected_limb"
    bl_label = "Export Selected Limb"
    bl_description = "Export selected limb chain to a .json file"

    def execute(self, context):
        armature = bpy.context.object
        if not armature or armature.type != 'ARMATURE':
            self.report({'ERROR'}, "Select an armature first.")
            return {'CANCELLED'}

        props = context.scene.limb_export
        limb_name = props.export_limb_name

        all_chains = load_limb_chains()

        # Support both list and dict formats
        if isinstance(all_chains, list):
            chains = all_chains
        elif isinstance(all_chains, dict):
            chains = all_chains.get(armature.name, [])
        else:
            chains = []

        limb = next((c for c in chains if c["name"] == limb_name), None)
        if not limb:
            self.report({'ERROR'}, f"Limb '{limb_name}' not found.")
            return {'CANCELLED'}

        current_dir = os.path.dirname(__file__)
        base_path = os.path.normpath(os.path.join(current_dir, '..', 'Hierarchy', armature.name))
        output_path = os.path.join(base_path, f"{limb_name}.json")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        chain = (limb["roots"], limb["stops"])
        export_clean_data.export_limb_file(limb_name, chain, armature, output_path)

        self.report({'INFO'}, f"Exported: {output_path}")
        return {'FINISHED'}


# ---- Panel ----
class AUTORIG_PT_LimbExportPanel(Panel):
    bl_label = "Limb Chain Exporter"
    bl_idname = "AUTORIG_PT_limb_export"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Auto Rig"

    def draw(self, context):
        layout = self.layout
        props = context.scene.limb_export

        arm = bpy.context.object
        layout.label(text=f"Armature: {arm.name if arm else 'None'}")
        layout.prop(props, "export_limb_name")
        layout.operator("autorig.export_selected_limb", text="Copy Limb")


