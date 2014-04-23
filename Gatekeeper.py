### Render Gatekeeper ###

"""
Render Gatekeeper is an add on that stops you doing stupid things that waste render time. Like forgetting to turn on that one layer, or having images export to the wrong file format. It's there so that you can make smart choices about rendering when you're in a happy, alert, and well adjusted frame of mind and not at midnight on a friday when you just want to go home and sleep.

Core functionality:
    Allows you to define and store all your important render settings. Things like:
        Size
        File Format
        Output Directory
        Sampling/Light Paths Properties
        and many more!
        Active Camera
        
    Sanity Checks Render Layers and comp setups for things like:
        Scene layers not turned on that should be.
        File output nodes without inputs.    
        
    Checks that you have these same settings enabled when it comes to rendering final frames, and notifies you if they are not.
    
    Extras:
        Quick switch for preview render settings.
    
                

"""


bl_info = {
    "name": "Render Gatekeeper",
    "author": "Ben Simonds",
    "version": (0, 1),
    "blender": (2, 69, 0),
    "location": "Properties > Render > Gatekeeper",
    "description": "Allows you to save your scenes final render settings and check/restore them for doing final renders. Also does some other error checks.",
    #"warning": "Requires qt_tools and ffmpeg",
    "wiki_url": "",
    "tracker_url": "",
    "category": "Render",
    }


###

import bpy
import json

#Properties Classes

class GatekeeperLayerProps(bpy.types.PropertyGroup):
    name = bpy.props.StringProperty (name = "Layer Name", default = "")
    gk_store = bpy.props.StringProperty(name = "Gatekeeper Renderlayer Store", default = "")
    gk_settings_fails = bpy.props.StringProperty(name = "Render Layer Settings Fails", default = "")
    

class GatekeeperProps (bpy.types.PropertyGroup):
    gk_template_global = {
        #Dimensions:
        "X Resolution" : "render.resolution_x",
        "Y Resolution" : "render.resolution_y",
        "Render Size %" : "render.resolution_percentage",
        "Start Frame" : "frame_start",
        "End Frame" : "frame_end",
        "Frame Rate" : "render.fps",
        
        #Stamp:
        "Stamp" : "render.use_stamp",
        
        #Output:
        "Output Filepath" : "render.filepath",
        "Overwrite" : "render.use_overwrite",
        "Place Holders" : "render.use_placeholder",
        "File Extensions" : "render.use_file_extension",
        
        # Motion Blur:
        "Use Motion Blur" : "render.use_motion_blur",
        "Motion Blur Shutter" : "render.motion_blur_shutter",

        #Post Processing:

        "Compositing" : "render.use_compositing",
        "Sequencer" : "render.use_sequencer",
        "Dither" : "render.dither_intensity",
        "Edge" : "render.use_edge_enhance",
        "Edge Threshold" : "render.edge_threshold" 
        
        }
        
    gk_template_cycles = {
        # Sampling:
        "Integrator" : "cycles.progressive",
        # No check for seed. Might do check for animation later.
        "Square Samples" : "cycles.use_square_samples",
        "Render Samples" : "cycles.samples",
        "Clamp" : "cycles.sample_clamp",
        "AA Samples" : "cycles.aa_samples",
        "Diffuse Samples" : "cycles.diffuse_samples",
        "Glossy Samples" : "cycles.glossy_samples",
        "Transmission Samples" : "cycles.transmission_samples",
        "AO Samples" : "cycles.ao_samples",
        "Mesh Light Samples" : "cycles.mesh_light_samples",
        "Subsuface Samples" : "cycles.subsurface_samples",
        "Use Layer Samples" : "cycles.use_layer_samples",
        
        # Light paths:
        "Transparent Bounces Max" : "cycles.transparent_max_bounces",
        "Transparent Bounces Min" : "cycles.transparent_min_bounces",
        "Use Transparent Shadows" : "cycles.use_transparent_shadows",
        "No Caustics" : "cycles.no_caustics",
        "Filter Glossy" : "cycles.blur_glossy",
        "Max Bounces" : "cycles.max_bounces",
        "Min Bounces" : "cycles.min_bounces",
        "Diffuse Bounces" : "cycles.diffuse_bounces",
        "Glossy Bounces" : "cycles.glossy_bounces",
        "Transmission Bounces" : "cycles.transmission_bounces",

        #Film:
        "Film Exposure":"cycles.film_exposure",
        "Film Transparent":"cycles.film_transparent",

        
         # I will add more to this soon. Should be enough to check for now.
         }

    gk_template_blenderinternal = {
        #Shading:
        "Use Textures":"render.use_textures",
        "Use Shadows":"render.use_shadows",
        "Use SSS": "render.use_sss",
        "Use Env Maps" : "render.use_envmaps",
        "Use Ray Tracing" : "render.use_raytrace",
        "Alpha Mode" : "render.alpha_mode",

        #Motion Blur:
        "Motion Blur Samples" : "render.motion_blur_samples",

        #Anti Aliasing:
        "Anti Aliasing" : "render.use_antialiasing",
        "AA Samples" : "render.antialiasing_samples",
        "Full Sample" : "render.use_full_sample",
        "Pixel Filter Type:" : "render.pixel_filter_type",
        "Pixel Filter Size" : "render.filter_size",


        }

    gk_template_renderlayers = {
        #This template goes from scene.render.layers instead of from scene
        "Samples":"samples",
        #"Material Override":"material_override",
        #"Light Override" : "light_override",
        #"Render Layers" : "layers",
        #"Mask Layers" : "layers_zmask",
        #"Exclude Layers" : "layers_exclude"
        #I could go into what passes are included here as well...
        }

    gk_store = bpy.props.StringProperty(name = "Gatekeeper Store", default = "")
    gk_settings_fails = bpy.props.StringProperty(name = "Render Settings Fails", default = "")
    gk_renderlayer_ignoredisabled = bpy.props.BoolProperty(name = "Ignore Disabled Render Layers", default = False)
    gk_renderlayer_ignoreinclusive = bpy.props.BoolProperty(name = "Ignore Render Layers that use EVERY scene layer.", default = False)
    gk_fileoutput_fails = bpy.props.StringProperty(name = "File Output Fails", default = "")
    gk_required_render_layers = bpy.props.BoolVectorProperty(name = "Required Render Layers", default = (False,False,False,False,False,False,False,False,False,False,False,False,False,False,False,False,False,False,False,False), size = 20)
    gk_renderlayer_fails = bpy.props.StringProperty(name = "Render Layer Fails", default = "")
    gk_renderlayerstores = bpy.props.CollectionProperty(type = GatekeeperLayerProps)
    gk_extra_fails = bpy.props.StringProperty(name = "Other Potential Errors", default = "")


### Function Definitions ###

def dict_from_templates(scene):
    #print("Generating template dict for scene: " + scene.name)
    a = scene.gatekeeper.gk_template_global
    if scene.render.engine == 'CYCLES':
        b = scene.gatekeeper.gk_template_cycles
    else:
        b = scene.gatekeeper.gk_template_blenderinternal   
    merged = a.copy()
    merged.update(b)
    return merged #This can be fixed to include some BI settings later.

def dict_from_templates_layers(scene):
    template = scene.gatekeeper.gk_template_renderlayers
    return template
    
def name_to_prop(data, key):
    # Returns the data path to a property in the form [bpy.data....  , 'property'] when given the name of a key from the template.
    #This should actually be usable for not just scenes but any thing... e.g. layers
    path_start = data
    if data.rna_type.name == 'Scene':
        path_end = dict_from_templates(data)[key]
    elif data.rna_type.name == 'Scene Render Layer':
        scene = data.id_data
        path_end = dict_from_templates_layers(scene)[key]
    else:
        print("Unrecognised type for first argument, expected scene or render layer")
        print("Type was: " + data.rna_type.name)
        return None
    if "." in path_end:
        path_list = path_end.split(".")
        while len(path_list) > 1:
            path_start = getattr(path_start,  path_list[0])
            path_list = path_list[1:]
        path_end = path_list[0]
    return [path_start, path_end]


def current_from_key(data, key):
    # Returns the current value of a property given a key in gk_template.
    prop = name_to_prop(data, key)
    current = getattr(prop[0], prop[1])
    return current

def dump_store(data):
    # Returns the json dump of all the properties for the given scene or render layer, to be stored in gk_store or checked against it.
    if data.rna_type.name == 'Scene':
        template = dict_from_templates(data)
    elif data.rna_type.name == 'Scene Render Layer':
        scene = data.id_data
        template = dict_from_templates_layers(scene)
    dict = {}
    for key in template.keys():
        dict[key] = current_from_key(data, key)
    dump = json.dumps(dict)
    return dump

def stored_from_key(data, key):
    #Returns the value of a key in gk_store
    if data.rna_type.name == 'Scene':
        dict = json.loads(data.gatekeeper.gk_store)
    elif data.rna_type.name == 'Scene Render Layer':
        scene = data.id_data
        dict = json.loads(scene.gatekeeper.gk_renderlayerstores[data.name].gk_store)
    value = dict[key]
    return value

###  Operator Classes ###

class SaveGatekeeperStore(bpy.types.Operator):
    bl_idname = 'scene.save_gatekeeper_store'
    bl_label = "Update the stored settings for render gatekeeper"
    to_save = bpy.props.StringProperty(name = "to_save", default = "")
    all_scenes = bpy.props.BoolProperty(name = "All Scenes", default = False)
    #Saves the json dump to gk_store
    
    def execute(self, context):
        if self.all_scenes:
            scenes = bpy.data.scenes
        else:
            scenes = [bpy.context.scene] 
        if self.to_save == "":
            print("Saving Gatekeeper Store...")
            for scene in scenes:
                #print(dump_store(scene))
                scene.gatekeeper.gk_store = dump_store(scene)
                print("Now doing stores for render layers")
                for layer in scene.render.layers:
                    #Update layer store or create new if missing.
                    stores  = scene.gatekeeper.gk_renderlayerstores
                    if layer.name in stores.keys():
                        layer_store = stores[layer.name]
                        layer_store.gk_store = dump_store(layer)
                    else:
                        layer_store = stores.add()
                        layer_store.name = layer.name
                        layer_store.gk_store = dump_store(layer)
            return {'FINISHED'} 
        else:
            try:
                split = self.to_save.split(",")
                data_type = split[0]
                if data_type == 'Scene':
                    data = bpy.data.scenes[split[1]]
                    store = json.loads(data.gatekeeper.gk_store)
                elif data_type == 'Scene Render Layer':
                    scene = bpy.data.scenes[split[1]]
                    data = scene.render.layers[split[2]]
                    store = json.loads(scene.gatekeeper.gk_renderlayerstores[data.name].gk_store)
                key = split[3]
                current = current_from_key(data, key)                
                store[key] = current
                if data_type == 'Scene':
                    data.gatekeeper.gk_store = json.dumps(store)
                elif data_type == 'Scene Render Layer':
                    scene = data.id_data
                    scene.gatekeeper.gk_renderlayerstores[data.name].gk_store = json.dumps(store)    
            except (TypeError, KeyError):
                print("to_save was incorrectly formatted, should be in the form 'type, scene.name, scene/layer.name, key' ")
                print("to_save :" + self.to_save)
            bpy.ops.scene.check_gatekeeper_store()
            return {'FINISHED'}

    def invoke(self, context, event): #Add dialogue for choosing between current or all scenes.
        if self.to_save is "":
            wm = bpy.context.window_manager
            return wm.invoke_props_dialog(self)
        else:
            return self.execute(context)

    def draw (self, context):
        layout = self.layout
        col = layout.column()
        col.prop(self, "all_scenes")
            
class CheckGatekeeperStore(bpy.types.Operator):
    bl_idname = 'scene.check_gatekeeper_store'
    bl_label = "Check the current render settings vs the gatekeeper store."
    #Checks the render settings and returns a list of failures to scene.gatekeeper.gk_fails
    
    def execute(self, context):
        for scene in bpy.data.scenes:
            # Render Settings Fails
            fails = {} 
            template = dict_from_templates(scene)
            try:
                stored_dict = json.loads(scene.gatekeeper.gk_store)
            except ValueError:
                print("No stored data detected for gk_store.")
                return{'FINISHED'}
            for key in template.keys():
                current = current_from_key(scene, key)
                try:
                    stored = stored_dict[key]
                except KeyError:
                    stored = None
                    print("No stored value for " + key)
                if stored != None:
                    if stored != current:
                        fails[key] = (current, stored)
                scene.gatekeeper.gk_settings_fails = json.dumps(fails)
            # Layer Settings Fails
            for layer in scene.render.layers:
                fails_layer = {}
                template = dict_from_templates_layers(scene)
                stores = scene.gatekeeper.gk_renderlayerstores
                try:
                    layer_store = json.loads(stores[layer.name].gk_store)
                except (KeyError, ValueError):
                    print("No stored data for the renderlayer: " + layer.name)
                    return {'FINISHED'}
                for key in template.keys():
                    current = current_from_key(layer, key)
                    try:
                        stored = layer_store[key]
                    except KeyError:
                        stored = None
                        print ("No stored value for " + key)
                    if stored is not None:
                        if stored != current:
                            fails_layer[key] = (current, stored)
                    stores[layer.name].gk_settings_fails = json.dumps(fails_layer)

        return {'FINISHED'}

class RestoreGatekeeperStore (bpy.types.Operator):
    bl_idname = 'scene.restore_gatekeeper_store'
    bl_label = 'Restore the value from the gatekeeper store.'
    to_restore = bpy.props.StringProperty(name = "to_restore", default = "") #Now in the form [data_type, scene, data, key] where data_type denotes scene or key
    
    def execute(self, context):
        if self.to_restore == "":
            #Do a full restore of all values.
            for scene in bpy.data.scenes:
                # Do scene render settings:
                template = dict_from_templates(scene)
                for key in template.keys():
                    prop = name_to_prop(scene, key)
                    stored = stored_from_key(scene, key)
                    setattr(prop[0], prop[1], stored)
                # Do render layer settings:
                for layer in scene.render.layers:
                    template = dict_from_templates_layers(scene)
                    for key in template.keys():
                        prop = name_to_prop(layer, key)
                        stored = stored_from_key(layer, key)
            bpy.ops.scene.check_gatekeeper_store()
            return {'FINISHED'}
        else:
            try:
                #to_restore should be in the format "data_type, scene, data_name, key"
                split = self.to_restore.split(",")
                data_type = split[0]
                if data_type == 'Scene':
                    data = bpy.data.scenes[split[1]]
                elif data_type == 'Scene Render Layer':
                    scene = bpy.data.scenes[split[1]]
                    data = scene.render.layers[split[2]]
                key = split[3]
                stored = stored_from_key(data, key)
                prop = name_to_prop(data, key)
                setattr(prop[0], prop[1], stored)
                bpy.ops.scene.check_gatekeeper_store()
            except (TypeError, KeyError):
                print("to_restore was incorrectly formatted, should be in the form 'type, scene.name, scene/layer.name, key'")
                pritn("to_restore: " + self.to_restore)
            return {'FINISHED'}

class MarkRenderLayers (bpy.types.Operator):
    bl_idname = 'scene.gatekeeper_mark_render_layers'
    bl_label = 'Marks current render layers as required for final render.'

    def execute(self, context):
        bpy.context.scene.gatekeeper.gk_required_render_layers = bpy.context.scene.layers
        return {'FINISHED'}

        
class CheckRenderLayers(bpy.types.Operator):
    bl_idname = 'scene.gatekeeper_check_renderlayers'
    bl_label = 'Checks that the required render layers are enabled.'
    
    def execute (self, context):
        #Check for each scene if the required render layers are on:
        for scene in bpy.data.scenes:
            fails = {}
            renderlayers = scene.render.layers
            for render_layer in renderlayers:
                ignoredisabled = bpy.context.scene.gatekeeper.gk_renderlayer_ignoredisabled
                skip = False
                if ignoredisabled and not render_layer.use:
                    skip = True
                if not skip:
                    #This bit might need expanding for mask layers etc...
                    required = []
                    required = list(set(required + [(render_layer.name, i) for i in range(20) if render_layer.layers[i]]))
                    #Check required against actual enabled layers:
                    actual = [i for i in range(20) if scene.layers[i]]
                    missing = [i for name, i in required if i not in actual]
                    ignore_inclusive = bpy.context.scene.gatekeeper.gk_renderlayer_ignoreinclusive
                    if len(missing) > 0:
                        if len(required) < 19 or not ignore_inclusive:
                            fails[render_layer.name] = sorted(missing)
            #Also Check Required Render Layers for scene:
            required = [i for i in range(20) if scene.gatekeeper.gk_required_render_layers[i]]
            missing = [i for i in required if not scene.layers[i]]
            if len(missing) > 0:
                fails["[All Render Layers]"] = sorted(missing)
            print(fails)

            scene.gatekeeper.gk_renderlayer_fails = json.dumps(fails)
        return {'FINISHED'}

class RectifyRenderLayers(bpy.types.Operator):
    bl_idname = 'scene.gatekeeper_fix_renderlayers'
    bl_label = 'Enables the required scene layers for the render layers you have.'
    to_fix = bpy.props.StringProperty(name = "to_fix", default = "") #Should be a comma delimited list of render layers to renable, leave empty to re-enable all required.
    
    def execute(self, context):
        if self.to_fix == "":
            #Re-enable all required.
            for scene in bpy.data.scenes:
                fails =  json.loads(scene.gatekeeper.gk_renderlayer_fails)
                missing = []
                for fail in fails.keys():
                    missing = missing + fails[fail]
                to_enable = set(missing)
                for i in to_enable:
                    scene.layers[i] = True #This only enables required layers, it doesn't disable non-requried ones...
            bpy.ops.scene.gatekeeper_check_renderlayers()
            return {'FINISHED'}
        else:
            try:
                #to_fix should be in the form of a comma delimited list of render layers, with a scene name at the beginning.        
                to_fix_list = self.to_fix.split(",")
                scene = bpy.data.scenes[to_fix_list[0]]
                to_enable = [int(i) for i in to_fix_list[1:]]
                for i in range(20):
                    if i in to_enable:
                        scene.layers[i] = True
            except (KeyError, TypeError):
                print("to_fix was incorrectly formatted.")
                print(self.to_fix)
            bpy.ops.scene.gatekeeper_check_renderlayers()
            return {'FINISHED'}
        

class CheckFileOutputs(bpy.types.Operator):
    bl_idname = 'scene.gatekeeper_check_fileoutputs'
    bl_label = 'Checks file output nodes have inputs.'

    def execute(self, context):
        fails = {}
        try:
            all_nodes = bpy.context.scene.node_tree.nodes #Only checks current scenes file output nodes. After all that's all that will run.
        except AttributeError:
            print("Scene has no node setup, skipping.")
            return {'FINISHED'}
        file_output_nodes = [node for node in all_nodes if node.type == 'OUTPUT_FILE']
        #Check each file output node for unconnected sockets.
        for node in file_output_nodes:
            unconnected = []
            #node.inputs gives inputs, node.layer_slots gives file output names. I think the indices match up...
            inputs = node.inputs
            layers = node.layer_slots
            for i in range(len(inputs)):
                if inputs[i].links == ():
                    unconnected.append(layers[i].name)
            if unconnected != []:
                fails[node.name] = str(unconnected).strip("[]")
        bpy.context.scene.gatekeeper.gk_fileoutput_fails = json.dumps(fails)
        return {'FINISHED'}
                    

class CheckExtras (bpy.types.Operator):
    #Checks some extra stuff.
    bl_idname = 'scene.gatekeeper_extra_checks'
    bl_label = 'Checks some extra stuff.'

    def check_output_for_tmp(self, scene):
        output = scene.render.filepath
        if output.startswith("/tmp/"):
            return True
        else:
            return False

    def check_alpha_1(self, scene):
        #Check if file formats support alpha:
        extension = scene.render.file_extension
        if extension in [".png", ".tga", ".dpx", ".exr", ".hdr", ".tif"]:
            if scene.render.image_settings.color_mode == 'RGB':
                return True
        else:
            return False

    def check_alpha_2(self, scene):
        #Check if bg is set to transparent but alpha not saved:
        if scene.render.engine == 'CYCLES':
            bg_alpha = scene.cycles.film_transparent
        elif scene.render.engine == "BLENDER_RENDER":
            bg_alpha = scene.render.alpha_mode == 'ALPHA'
        if bg_alpha:
            if scene.render.image_settings.color_mode is not 'RGBA':
                return True
        else:
            return False

    def check_alpha_3(self, scene):
        #Check if alpha is being saved but bg not transparent:
        alpha_saved = scene.render.image_settings.color_mode is 'RGBA'
        if alpha_saved:
            if scene.render.engine == 'CYCLES':
                bg_alpha = scene.cycles.film_transparent
            elif scene.render.engine == 'BLENDER_RENDER':
                bg_alpha = scene.render.alpha_mode is 'ALPHA'
            if not bg_alpha:
                return True
        else:
            return False

    def check_no_stamp(self,scene):
        stamp = scene.render.use_stamp
        if stamp:
            return True
        else:
            return False

    def check_layer_samples (self, scene):
        #Only run if cycles:
        if scene.render.engine == 'CYCLES':
            scene_samples = scene.cycles.samples
            fails = []
            for layer in scene.render.layers:
                if layer.samples > scene_samples:
                    fails.append(layer.name)
            return fails
        else:
            return []


    def execute (self, context):
        extra_fails = {}
        # Context checks:
        scene = bpy.context.scene
        if self.check_output_for_tmp(scene):
            extra_fails["Temp Fail"] = "The current scene is rendering to the /tmp/ folder."
        if self.check_alpha_1(scene):
            extra_fails["Alpha 1 Fail"] = "Image format supports alpha, but blender is not saving an alpha channel."
        if self.check_alpha_2(scene):
            extra_fails["Alpha 2 Fail"] = "Scene is rendering with transparent background, but no alpha is being saved."
        if self.check_alpha_3(scene):
            extra_fails["Alpha 3 Fail"] = "Saving alpha channel for render, but not rendering bg with alpha."
        if self.check_no_stamp(scene):
            extra_fails["Stamp Fail"] = "Render has stamp enabled."   
        # All scenes checks:
        for scene in bpy.data.scenes:
            if self.check_layer_samples(scene) != []:
                layers = self.check_layer_samples(scene)
                extra_fails["Samples Fail, " + scene.name] = "Scene samples < Layer Samlples for Scene: " + scene.name + ", Layers: " + str(layers).strip("[]")

        #Write:
        bpy.context.scene.gatekeeper.gk_extra_fails = json.dumps(extra_fails)
        return {'FINISHED'}



# Basic UI:

class GatekeeperPanel(bpy.types.Panel):
    """Test UI Panel for Gatekeeper"""
    bl_label = "Gatekeeper"
    bl_idname = "OBJECT_PT__Gatekeeper"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = 'render'
    
    def draw(self, context):
        layout = self.layout
                
        row  = layout.row()
        box  = row.box()
        ### RENDER SETTINGS: ###
        row = box.row(align = True)
        row.operator('scene.save_gatekeeper_store', text = "Save Render Settings", icon = 'SAVE_PREFS').to_save = ""
        row.operator('scene.check_gatekeeper_store', text = "Check Settings", icon = 'VIEWZOOM')
        row.operator('scene.restore_gatekeeper_store', text = "Restore Settings", icon = 'RECOVER_AUTO').to_restore = ""

        box.label(text = "Current Settings Fails:")
        is_fails = False
        for scene in bpy.data.scenes:            
            try:
                fails = json.loads(scene.gatekeeper.gk_settings_fails)
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
            row = box.row()
            for layer in scene.render.layers:
                try:
                    fails_layer =  json.loads(scene.gatekeeper.gk_renderlayerstores[layer.name].gk_settings_fails)
                    #print(fails_layer)
                except (KeyError, ValueError):
                    box.label("No stored settings detected for render layer: " + layer.name)
                    fails_layer = {}
                if len(fails_layer) > 0:
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
            box.label(text = "No Settings Errors", icon = 'FILE_TICK')   

        
        ### ENABLED LAYER FAILS: ###
        row  = layout.row()
        box  = row.box()

        row = box.row(align = True)
        row.operator('scene.gatekeeper_check_renderlayers', text = "Check Layers", icon = 'VIEWZOOM')
        row.operator('scene.gatekeeper_fix_renderlayers', text = "Rectify Layers",  icon = 'RECOVER_AUTO').to_fix = ""
        row = box.row()
        row.prop(bpy.context.scene.gatekeeper, 'gk_renderlayer_ignoredisabled', text = "Ignore Disabled")
        row.prop(bpy.context.scene.gatekeeper, 'gk_renderlayer_ignoreinclusive', text  = "Ignore Inclusive")

        row = box.row()
        row.operator('scene.gatekeeper_mark_render_layers', text = "Save Required Layers")



        box.label(text = "Current Layer Fails:")
        is_fails = False
        for scene in bpy.data.scenes:
            try:
                fails = json.loads(scene.gatekeeper.gk_renderlayer_fails)
            except ValueError:
                #print("No stored data detected for gk_renderlayer_fails.")
                fails = {}
            
            if len(fails) > 0:
                is_fails = True
                row = box.row()
                row.label(text = scene.name, icon = 'SCENE_DATA')
                
                col = row.column()
                col.label(text = "Render Layer", icon = 'RENDERLAYERS')
                for fail in sorted(fails.keys()):
                    col.label(text = fail)
                    
                col = row.column()
                col.label(text = "Missing")
                for fail in fails.keys():
                    col.label(text = str(fails[fail]))
                    
                col = row.column()
                col.label(text = "Rectify")
                for fail in fails.keys():
                    col.operator('scene.gatekeeper_fix_renderlayers', text = "Enable Missing").to_fix = scene.name + "," + str(fails[fail]).strip("[]")
        if not is_fails:
            box.label(text = "No Render Layer Errors", icon = 'FILE_TICK')        

        ### FILE OUTPUT NODE FAILS ###
        box = layout.box()                    
        row = box.row()
        row.operator('scene.gatekeeper_check_fileoutputs', text = "Check File Output Nodes", icon = 'VIEWZOOM')

        row = box.row()
        try:
            fails = json.loads(scene.gatekeeper.gk_fileoutput_fails)
        except ValueError:
            #print("No stored data detected for gk_fileoutput_fails.")
            fails = {}
        if len(fails) > 0:
            box  = row.column()
            box.label(text = "File Ouput Fails:")
            row = box.row()

            col = row.column()
            col.label(text = "Node", icon = 'NODETREE')
            for fail in fails.keys():
                col.label(text = fail)

            col = row.column()
            col.label(text = "Inputs", icon = 'NODETREE')
            for fail in fails.keys():
                col.label(text = fails[fail])

            row = box.row()
            #box = row.box()
            #box.label(text = "No auto-fix for file output nodes.", icon = 'ERROR')
            #box.label(text = "Check the node editor and fix manually.")
        else:
            box.label(text = "No File Output Errors", icon = 'FILE_TICK')

        #Other Potential Errors:
        row = layout.row()
        box = row.box()
        box.operator('scene.gatekeeper_extra_checks', text = "Run Extra Checks", icon = 'VIEWZOOM')
        box.label(text = "Other Checks", icon = 'ERROR')
        try:
            fails = json.loads(bpy.context.scene.gatekeeper.gk_extra_fails)
        except ValueError:
            fails = {}


        if len(fails) > 0:
            col = box.column()
            for fail in fails.keys():
                col.label(text = fails[fail], icon = 'DOT')






# Registration:
def register():
    #Properties
    bpy.utils.register_class(GatekeeperLayerProps)
    bpy.utils.register_class(GatekeeperProps)
    bpy.types.Scene.gatekeeper = bpy.props.PointerProperty(type = GatekeeperProps)
    #bpy.types.SceneRenderLayer.gatekeeper = bpy.props.PointerProperty(type = GatekeeperLayerProps)
    #Operators
    bpy.utils.register_class(SaveGatekeeperStore)
    bpy.utils.register_class(CheckGatekeeperStore)
    bpy.utils.register_class(RestoreGatekeeperStore)
    bpy.utils.register_class(MarkRenderLayers)
    bpy.utils.register_class(CheckRenderLayers)
    bpy.utils.register_class(RectifyRenderLayers)
    bpy.utils.register_class(CheckFileOutputs)
    bpy.utils.register_class(CheckExtras)
    #UI
    bpy.utils.register_class(GatekeeperPanel)


def unregister():
    #Properties
    bpy.utils.unregister_class(GatekeeperProps)
    bpy.utils.unregister_class(GatekeeperLayerProps)
    #Operators
    bpy.utils.unregister_class(SaveGatekeeperStore)
    bpy.utils.unregister_class(CheckGatekeeperStore)
    bpy.utils.unregister_class(RestoreGatekeeperStore)
    bpy.utils.unregister_class(MarkRenderLayers)
    bpy.utils.unregister_class(CheckRenderLayers)
    bpy.utils.unregister_class(RectifyRenderLayers)
    bpy.utils.unregister_class(CheckFileOutputs)
    bpy.utils.unregister_class(CheckExtras)    
    #UI
    bpy.utils.unregister_class(GatekeeperPanel)


if __name__ == '__main__':
    register()