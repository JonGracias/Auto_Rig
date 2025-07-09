import bpy # type: ignore
import os
import json
from bpy.types import Panel, Operator, PropertyGroup # type: ignore
from bpy.props import StringProperty, PointerProperty # type: ignore


# ---- File path helper ----
def get_limb_chains_path():
    scripts_dir = bpy.utils.user_resource('SCRIPTS')
    return os.path.join(scripts_dir, "addons", "Auto_Rig", "Hierarchy", "limb_chains.json")


# ---- JSON Load/Save ----
def load_limb_chains():
    path = get_limb_chains_path()
    if not os.path.isfile(path):
        return []
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"[AutoRig] Failed to load limb chains: {e}")
        return []

def save_limb_chains(data):
    try:
        with open(get_limb_chains_path(), "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"[AutoRig] Failed to save limb chains: {e}")


# ---- Operator ----
class AUTORIG_OT_SaveLimbChain(Operator):
    bl_idname = "autorig.save_limb_chain"
    bl_label = "Save Limb Chain"
    bl_description = "Add or update a limb chain definition"

    def execute(self, context):
        props = context.scene.limb_editor
        name = props.limb_name.strip()
        if not name:
            self.report({'ERROR'}, "Limb name is required.")
            return {'CANCELLED'}

        roots = [b.strip() for b in props.limb_roots_csv.split(",") if b.strip()]
        stops = [b.strip() for b in props.limb_stops_csv.split(",") if b.strip()]
        note = props.limb_note.strip()

        data = load_limb_chains()

        # Replace or add
        for item in data:
            if item["name"] == name:
                item.update({"roots": roots, "stops": stops, "note": note})
                break
        else:
            data.append({"name": name, "roots": roots, "stops": stops, "note": note})

        save_limb_chains(data)
        self.report({'INFO'}, f"Saved limb chain: {name}")
        return {'FINISHED'}


# ---- Property Group ----
class AutoRigLimbEditorProperties(PropertyGroup):
    limb_name: StringProperty(name="Limb Name") # type: ignore
    limb_roots_csv: StringProperty(name="Start Bones (CSV)", default="") # type: ignore
    limb_stops_csv: StringProperty(name="End Bones (CSV)", default="") # type: ignore
    limb_note: StringProperty(name="Note", default="") # type: ignore


# ---- Panel ----
class AUTORIG_PT_LimbChainEditor(Panel):
    bl_label = "Limb Chain Editor"
    bl_idname = "AUTORIG_PT_limb_chain_editor"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Auto Rig"

    def draw(self, context):
        layout = self.layout
        props = context.scene.limb_editor

        layout.prop(props, "limb_name")
        layout.prop(props, "limb_roots_csv")
        layout.prop(props, "limb_stops_csv")
        layout.prop(props, "limb_note")
        layout.operator("autorig.save_limb_chain")
        

    
