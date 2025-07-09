bl_info = {
    "name": "Auto Rig System",
    "author": "Jonatan Gracias",
    "version": (1, 0, 0),
    "blender": (3, 0, 0),
    "location": "3D View > Sidebar > Auto Rig",
    "description": "Modular auto-rigging panel for Blender",
    "category": "Rigging",
}

def register():
    try:
        from . import bootloader
        bootloader.safe_register()
    except Exception as e:
        print("[Auto Rig] Register Error:", e)

def unregister():
    try:
        from . import bootloader
        bootloader.safe_unregister()
    except Exception as e:
        print("[Auto Rig] Unregister Error:", e)
