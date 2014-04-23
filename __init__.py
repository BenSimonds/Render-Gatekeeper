#Add-On Metadata:

bl_info = {
    "name": "Render Gatekeeper",
    "author": "Ben Simonds",
    "version": (0, 1),
    "blender": (2, 69, 0),
    "location": "Properties > Render > Gatekeeper",
    "description": "Allows you to save your scenes final render settings and check/restore them for doing final renders. Also does some other error checks.",
    "wiki_url": "",
    "tracker_url": "",
    "category": "Render",
    }

import bpy
from .Gatekeeper import *

#UI:

class GatekeeperPanel(bpy.types.Panel):
    """ UI Panel for Gatekeeper"""
    bl_label = "Gatekeeper"
    bl_idname = "OBJECT_PT__Gatekeeper"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'render'
    
    def draw(self, context):
        layout = self.layout
        gatekeeper = bpy.context.scene.gatekeeper

        #Settings Checks:
        row = layout.row()
        box = row.box()
        row = box.row()
        icon = 'TRIA_RIGHT'
        if gatekeeper.ui_settings:
            icon = 'TRIA_DOWN'
        row.prop(gatekeeper, "ui_settings", text = "Settings Checks:", icon = icon)
        if gatekeeper.ui_settings:
            row = box.row(align = True)
            row.operator('scene.save_gatekeeper_store', text = "Save Render Settings", icon = 'SAVE_PREFS').to_save = ""
            row.operator('scene.check_gatekeeper_store', text = "Check Settings", icon = 'VIEWZOOM')
            row.operator('scene.restore_gatekeeper_store', text = "Restore Settings", icon = 'RECOVER_AUTO').to_restore = ""
            
            #List current issues:
            is_fails = False
            row = box.row()
            row.label(text = "Current Settings Issues:")

            for scene in bpy.data.scenes:          
                try: #Load the list of saved settings fails (requires that the user checks settings first).:
                    fails = json.loads(scene.gatekeeper.settings_fails)
                except ValueError:
                    #print("No stored data detected!")
                    box.label(text = "No stored settings detected.", icon = 'ERROR')
                    fails = {}
                    
                if len(fails) > 0:
                    is_fails = True
                    row = box.row()
                    row.label(text = scene.name, icon = 'SCENE_DATA')
                    
                    row = box.row()
                    col = row.column()
                    col.label(text = "Property:")
                    for fail in fails.keys():
                        col.label(text = fail)
                    col = row.column()
                    col.label(text = "Current:")
                    for fail in fails.keys():
                        col.label(text = str(fails[fail][0]))
                    col = row.column()
                    col.label(text = "Stored:")
                    for fail in fails.keys():
                        col.label(text = str(fails[fail][1]))
                    col = row.column()
                    col.label(text = "Restore:")
                    for fail in fails.keys():
                        col.operator('scene.restore_gatekeeper_store', text = "Restore").to_restore = "Scene," + scene.name + "," + scene.name + "," + fail
                    col = row.column()
                    col.label(text = "Overwrite:")
                    for fail in fails.keys():
                        col.operator('scene.save_gatekeeper_store', text = "Overwrite").to_save = "Scene," + scene.name + "," + scene.name + "," + fail


                # Render layer settings fails:
                
                for layer in scene.render.layers:
                    try:
                        fails_layer =  json.loads(scene.gatekeeper.renderlayerstores[layer.name].settings_fails)
                        #print(fails_layer)
                    except (KeyError, ValueError):
                        box.label("No stored settings detected for render layer: " + layer.name)
                        fails_layer = {}

                    if len(fails_layer) > 0:
                        row = box.row()
                        box.label(text = "Render Layer Settings:")
                        is_fails = True
                        row = box.row()
                        row.label(text = layer.name, icon = 'RENDERLAYERS')

                        row = box.row()
                        col = row.column()
                        col.label(text = "Property:")
                        for fail in fails_layer.keys():
                            col.label(text = fail)
                        col = row.column()
                        col.label(text = "Current:")
                        for fail in fails_layer.keys():
                            col.label(text = str(fails_layer[fail][0]))
                        col = row.column()
                        col.label(text = "Stored:")
                        for fail in fails_layer.keys():
                            col.label(text = str(fails_layer[fail][1]))
                        col = row.column()
                        col.label(text = "Restore:")
                        for fail in fails_layer.keys():
                            col.operator('scene.restore_gatekeeper_store', text = "Restore").to_restore = "Scene Render Layer," + scene.name + "," + layer.name + "," + fail
                        col = row.column()
                        col.label(text = "Overwrite:")
                        for fail in fails_layer.keys():
                            col.operator('scene.save_gatekeeper_store', text = "Overwrite").to_save =  "Scene Render Layer," + scene.name + "," + layer.name + "," + fail


            if not is_fails:
                row.label(text = "No Settings Errors", icon = 'FILE_TICK')   



        #Enabled layer checks:
        row  = layout.row()
        box  = row.box()
        icon = 'TRIA_RIGHT'
        if gatekeeper.ui_layers:
            icon = 'TRIA_DOWN'
        row = box.row()
        row.prop(gatekeeper, "ui_layers", text = "Render Layer Checks:", icon = icon)

        if gatekeeper.ui_layers:
            #Layer checks Operators:
            row = box.row(align = True)
            row.operator('scene.gatekeeper_mark_render_layers', text = "Save Required Layers", icon = 'SAVE_PREFS')
            row.operator('scene.gatekeeper_check_renderlayers', text = "Check Layers", icon = 'VIEWZOOM')
            row.operator('scene.gatekeeper_fix_renderlayers', text = "Enable Missing Layers",  icon = 'RECOVER_AUTO').to_fix = ""

            col = box.column()
            col.prop(bpy.context.scene.gatekeeper, 'renderlayer_ignoredisabled', text = "Ignore Disabled Render Layers")
            col.prop(bpy.context.scene.gatekeeper, 'renderlayer_ignoreinclusive', text  = "Ignore Inclusive Render Layers")


            #List current issues:
            row = box.row()
            row.label(text = "Render Layer Issues:")
            is_fails = False
            for scene in bpy.data.scenes:
                try:
                    fails = json.loads(scene.gatekeeper.renderlayer_fails)
                except ValueError:
                    #print("No stored data detected for renderlayer_fails.")
                    fails = {}
                
                if len(fails) > 0:
                    is_fails = True
                    row = box.row()
                    #row.label(text = scene.name, icon = 'SCENE_DATA')
                    
                    col = row.column()
                    col.label(text = scene.name, icon = 'SCENE_DATA')
                    col.alignment = 'RIGHT'
                    for fail in sorted(fails.keys()):
                        col.label(text = fail)
                        
                    col = row.column()
                    col.label(text = "Missing:")
                    for fail in fails.keys():
                        def i_to_layer(i):
                            if 0 <= i <= 9:
                                return str(i +1)
                            elif 9 < i <= 19:
                                return "Alt-" + str(i-9)
                        missing = [i_to_layer(n) for n in fails[fail]]
                        string = str(missing).strip("[]").replace("'","")
                        col.label(text = string)
                        
                    col = row.column()
                    col.label(text = "Enable")
                    for fail in fails.keys():
                        col.operator('scene.gatekeeper_fix_renderlayers', text = "Enable Missing").to_fix = scene.name + "," + str(fails[fail]).strip("[]")
            if not is_fails:
                row.label(text = "No Render Layer Errors", icon = 'FILE_TICK')        


        #File Output Node Checks:
        row  = layout.row()
        box  = row.box()
        icon = 'TRIA_RIGHT'
        if gatekeeper.ui_outputnodes:
            icon = 'TRIA_DOWN'
        row = box.row()
        row.prop(gatekeeper, 'ui_outputnodes', text = "File Output Node Checks:", icon = icon)

        if gatekeeper.ui_outputnodes:
            #File Output Node Operators
            row = box.row()
            row.operator('scene.gatekeeper_check_fileoutputs', text = "Check File Output Nodes", icon = 'VIEWZOOM')

            row = box.row()
            row.label(text = "File Ouput Issues:")

            try:
                fails = json.loads(bpy.context.scene.gatekeeper.fileoutput_fails)
            except ValueError:
                #print("No stored data detected for fileoutput_fails.")
                fails = {}
            if len(fails) > 0:
                col  = row.column()
                
                row = col.row()

                col = row.column()
                col.label(text = "Node", icon = 'NODETREE')
                for fail in fails.keys():
                    col.label(text = fail)

                col = row.column()
                col.label(text = "Inputs", icon = 'NODETREE')
                for fail in fails.keys():
                    col.label(text = fails[fail])

                row = box.row()
                col = row.column()
                col.label(text = "No auto-fix for file output nodes.", icon = 'ERROR')
                col.label(text = "Check the node editor and fix manually.")
            else:
                row.label(text = "No File Output Errors", icon = 'FILE_TICK')


        #Other Checks:
        row = layout.row()
        box = row.box()
        icon = 'TRIA_RIGHT'
        if gatekeeper.ui_extrachecks:
            icon = 'TRIA_DOWN'
        row = box.row()
        row.prop(gatekeeper, "ui_extrachecks", text = "Extra Checks:", icon = icon)
        if gatekeeper.ui_extrachecks:
            row = box.row()
            row.operator('scene.gatekeeper_extra_checks', text = "Run Extra Checks", icon = 'VIEWZOOM')
            row = box.row()
            row.label(text = "Potential Issues:", icon = 'ERROR')

            try:
                fails = json.loads(bpy.context.scene.gatekeeper.extra_fails)
            except ValueError:
                fails = {}

            if len(fails) > 0:
                col = box.column()
                for fail in fails.keys():
                    col.label(text = fails[fail], icon = 'RIGHTARROW')

        #IO:
        row = layout.row()
        box = row.box()
        icon = 'TRIA_RIGHT'
        if gatekeeper.ui_io:
            icon = 'TRIA_DOWN'
        row = box.row()
        row.prop(gatekeeper, "ui_io", text = "Import/Export:", icon = icon)
        if gatekeeper.ui_io:
            col = box.column()
            col.operator('scene.gatekeeper_export', icon  = 'EXPORT')
            col.operator('scene.gatekeeper_import', icon = 'IMPORT')


# Registration:
def register():
    #Properties
    bpy.utils.register_class(GatekeeperLayerProps)
    bpy.utils.register_class(GatekeeperProps)
    bpy.types.Scene.gatekeeper = bpy.props.PointerProperty(type = GatekeeperProps)
    #Operators
    bpy.utils.register_class(SaveGatekeeperStore)
    bpy.utils.register_class(CheckGatekeeperStore)
    bpy.utils.register_class(RestoreGatekeeperStore)
    bpy.utils.register_class(MarkRenderLayers)
    bpy.utils.register_class(CheckRenderLayers)
    bpy.utils.register_class(RectifyRenderLayers)
    bpy.utils.register_class(CheckFileOutputs)
    bpy.utils.register_class(CheckExtras)
    bpy.utils.register_class(ExportSettings)
    bpy.utils.register_class(ImportSettings)
    #UI
    bpy.utils.register_class(GatekeeperPanel)


def unregister():
#Properties
    bpy.utils.unregister_class(GatekeeperLayerProps)
    bpy.utils.unregister_class(GatekeeperProps)
    #Operators
    bpy.utils.unregister_class(SaveGatekeeperStore)
    bpy.utils.unregister_class(CheckGatekeeperStore)
    bpy.utils.unregister_class(RestoreGatekeeperStore)
    bpy.utils.unregister_class(MarkRenderLayers)
    bpy.utils.unregister_class(CheckRenderLayers)
    bpy.utils.unregister_class(RectifyRenderLayers)
    bpy.utils.unregister_class(CheckFileOutputs)
    bpy.utils.unregister_class(CheckExtras)
    bpy.utils.unregister_class(ExportSettings)
    bpy.utils.unregister_class(ImportSettings)
    #UI
    bpy.utils.unregister_class(GatekeeperPanel)