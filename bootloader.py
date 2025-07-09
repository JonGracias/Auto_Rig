import importlib
import traceback
import bpy

modules = {}
module_names = [
    "Auto_Rig.utils.props",   # For AutoRigProperties
    "Auto_Rig.ui",            # For all UI panels
]

def safe_import(name):
    try:
        mod = importlib.import_module(name)
        importlib.reload(mod)
        modules[name] = mod
        print(f"[Auto Rig] Loaded {name}")
        return mod
    except Exception:
        print(f"[Auto Rig] Failed to load {name}")
        traceback.print_exc()

def safe_register():
    print("[Auto Rig] Registering modules...")

    for name in module_names:
        mod = safe_import(name)
        if not mod:
            continue

        # Save module
        modules[name] = mod

        # Special case: PropertyGroup
        if hasattr(mod, "AutoRigProperties"):
            cls = mod.AutoRigProperties
            bpy.utils.register_class(cls)
            print(">>> Setting bpy.types.Scene.autorig_props")
            bpy.types.Scene.autorig_props = bpy.props.PointerProperty(type=cls)
            print(">>> Is it in scene?", hasattr(bpy.types.Scene, "autorig_props"))
            modules["AutoRigProperties"] = cls

        # Generic register() support
        if hasattr(mod, "register"):
            mod.register()


def safe_unregister():
    print("[Auto Rig] Unregistering modules...")

    # Unregister PropertyGroup first (if it exists)
    if hasattr(bpy.types.Scene, "autorig_props"):
        del bpy.types.Scene.autorig_props
    pg = modules.get("AutoRigProperties")
    if pg:
        bpy.utils.unregister_class(pg)

    # Unregister modules in reverse
    for name in reversed(module_names):
        mod = modules.get(name)
        if mod and hasattr(mod, "unregister"):
            try:
                mod.unregister()
            except Exception:
                traceback.print_exc()

