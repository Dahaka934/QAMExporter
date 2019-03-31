bl_info = {
    "name" : "QAM Exporter",
    "author" : "Dahaka934",
    "description" : "Export scene to QAM format",
    "blender" : (2, 80, 0),
    "location" : "File > Import-Export",
    "warning" : "",
    "category" : "Import-Export"
}

from . import auto_load

auto_load.init()

def register():
    auto_load.register()

def unregister():
    auto_load.unregister()
