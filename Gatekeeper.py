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

###

import bpy
import json

#Properties Classes

class GatekeeperLayerProps(bpy.types.PropertyGroup):
    name = bpy.props.StringProperty (name = "Layer Name", default = "")
    store = bpy.props.StringProperty(name = "Gatekeeper Renderlayer Store", default = "")
    settings_fails = bpy.props.StringProperty(name = "Render Layer Settings Fails", default = "")
    

class GatekeeperProps (bpy.types.PropertyGroup):
    template_global = {
        #Dimensions:
        "X Resolution" : "render.resolution_x",
        "Y Resolution" : "render.resolution_y",
        "Render Size %" : "render.resolution_percentage",
        "Start Frame" : "frame_start",
        "End Frame" : "frame_end",
        "Frame Step" : "frame_step",
        "Frame Rate" : "render.fps",
        "Frame Map Old" : "render.frame_map_old",
        "Frame Map New" : "render.frame_map_new",
        "Aspect Ratio X" : "render.pixel_aspect_x",
        "Aspect Ratio Y" : "render.pixel_aspect_y",
        "Border" : "render.use_border",
        "Crop" : "render.use_crop_to_border",

        #Border Dimensions:
        "Border X Min" : "render.border_min_x",
        "Border Y Min" : "render.border_min_y",
        "Border X Max" : "render.border_max_x",
        "border Y Max" : "render.border_max_y",
        
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
        
    template_cycles = {
        # Sampling:
        "Integrator" : "cycles.progressive",
        # No check for seed. Might do check for animation later.
        "Square Samples" : "cycles.use_square_samples",
        "Render Samples" : "cycles.samples",
        "Clamp Direct" : "cycles.sample_clamp_direct",
        "Clamp Indirect" : "cycles.sample_clamp_indirect",
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

    template_bi = {
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

    template_renderlayers = {
        #This template goes from scene.render.layers instead of from scene
        "Samples":"samples",
        #"Material Override":"material_override",
        #"Light Override" : "light_override",
        #"Render Layers" : "layers",
        #"Mask Layers" : "layers_zmask",
        #"Exclude Layers" : "layers_exclude"
        #I could go into what passes are included here as well...
        }

    store = bpy.props.StringProperty(name = "Gatekeeper Store", default = "")
    settings_fails = bpy.props.StringProperty(name = "Render Settings Fails", default = "")
    renderlayer_ignoredisabled = bpy.props.BoolProperty(name = "Ignore Disabled Render Layers", default = False)
    renderlayer_ignoreinclusive = bpy.props.BoolProperty(name = "Ignore Render Layers that use EVERY scene layer.", default = False)
    fileoutput_fails = bpy.props.StringProperty(name = "File Output Fails", default = "")
    required_render_layers = bpy.props.BoolVectorProperty(name = "Required Render Layers", default = (False,False,False,False,False,False,False,False,False,False,False,False,False,False,False,False,False,False,False,False), size = 20)
    renderlayer_fails = bpy.props.StringProperty(name = "Render Layer Fails", default = "")
    renderlayerstores = bpy.props.CollectionProperty(type = GatekeeperLayerProps)
    extra_fails = bpy.props.StringProperty(name = "Other Potential Errors", default = "")

    ui_settings = bpy.props.BoolProperty(name = "Render Settings", default = False)
    ui_layers = bpy.props.BoolProperty(name = "Render Layers", default = False)
    ui_outputnodes = bpy.props.BoolProperty(name = "File Output Nodes", default = False)
    ui_extrachecks = bpy.props.BoolProperty(name = "Extras", default = False)
    ui_io = bpy.props.BoolProperty(name = "Import/Export", default = False)


### Function Definitions ###

def dict_from_templates(scene):
    #print("Generating template dict for scene: " + scene.name)
    a = scene.gatekeeper.template_global
    if scene.render.engine == 'CYCLES':
        b = scene.gatekeeper.template_cycles
    else:
        b = scene.gatekeeper.template_bi   
    merged = a.copy()
    merged.update(b)
    return merged #This can be fixed to include some BI settings later.

def dict_from_templates_layers(scene):
    template = scene.gatekeeper.template_renderlayers
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
    # Returns the current value of a property given a key in template.
    prop = name_to_prop(data, key)
    current = getattr(prop[0], prop[1])
    return current

def dump_store(data):
    # Returns the json dump of all the properties for the given scene or render layer, to be stored in store or checked against it.
    if data.rna_type.name == 'Scene':
        template = dict_from_templates(data)
    elif data.rna_type.name == 'Scene Render Layer':
        scene = data.id_data
        template = dict_from_templates_layers(scene)
    dict = {}
    for key in template.keys():
        try:
            dict[key] = current_from_key(data, key)
        except AttributeError:
            print("No such attribute: " + key)
    dump = json.dumps(dict)
    return dump

def stored_from_key(data, key):
    #Returns the value of a key in store
    if data.rna_type.name == 'Scene':
        dict = json.loads(data.gatekeeper.store)
    elif data.rna_type.name == 'Scene Render Layer':
        scene = data.id_data
        dict = json.loads(scene.gatekeeper.renderlayerstores[data.name].store)
    value = dict[key]
    return value

###  Operator Classes ###

class SaveGatekeeperStore(bpy.types.Operator):
    bl_idname = 'scene.save_gatekeeper_store'
    bl_label = "Update the stored settings for render gatekeeper"
    to_save = bpy.props.StringProperty(name = "to_save", default = "")
    all_scenes = bpy.props.BoolProperty(name = "All Scenes", default = False)
    #Saves the json dump to store
    
    def execute(self, context):
        if self.all_scenes:
            scenes = bpy.data.scenes
        else:
            scenes = [bpy.context.scene] 
        if self.to_save == "":
            print("Saving Gatekeeper Store...")
            for scene in scenes:
                #print(dump_store(scene))
                scene.gatekeeper.store = dump_store(scene)
                print("Now doing stores for render layers")
                for layer in scene.render.layers:
                    #Update layer store or create new if missing.
                    stores  = scene.gatekeeper.renderlayerstores
                    if layer.name in stores.keys():
                        layer_store = stores[layer.name]
                        layer_store.store = dump_store(layer)
                    else:
                        layer_store = stores.add()
                        layer_store.name = layer.name
                        layer_store.store = dump_store(layer)
            bpy.ops.scene.check_gatekeeper_store()
            return {'FINISHED'} 
        else:
            try:
                split = self.to_save.split(",")
                data_type = split[0]
                if data_type == 'Scene':
                    data = bpy.data.scenes[split[1]]
                    store = json.loads(data.gatekeeper.store)
                elif data_type == 'Scene Render Layer':
                    scene = bpy.data.scenes[split[1]]
                    data = scene.render.layers[split[2]]
                    store = json.loads(scene.gatekeeper.renderlayerstores[data.name].store)
                key = split[3]
                current = current_from_key(data, key)                
                store[key] = current
                if data_type == 'Scene':
                    data.gatekeeper.store = json.dumps(store)
                elif data_type == 'Scene Render Layer':
                    scene = data.id_data
                    scene.gatekeeper.renderlayerstores[data.name].store = json.dumps(store)    
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
    #Checks the render settings and returns a list of failures to scene.gatekeeper.fails
    
    def execute(self, context):
        for scene in bpy.data.scenes:
            # Render Settings Fails
            fails = {} 
            template = dict_from_templates(scene)
            try:
                stored_dict = json.loads(scene.gatekeeper.store)
            except ValueError:
                print("No stored data detected for store.")
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
                scene.gatekeeper.settings_fails = json.dumps(fails)
            # Layer Settings Fails
            for layer in scene.render.layers:
                fails_layer = {}
                template = dict_from_templates_layers(scene)
                stores = scene.gatekeeper.renderlayerstores
                try:
                    layer_store = json.loads(stores[layer.name].store)
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
                    stores[layer.name].settings_fails = json.dumps(fails_layer)

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
                #Try to Do render layer settings (if saved):
                for layer in scene.render.layers:
                    try:
                        template = dict_from_templates_layers(scene)
                        for key in template.keys():
                            prop = name_to_prop(layer, key)
                            stored = stored_from_key(layer, key)
                    except KeyError:
                        print("No saved settings for render layer:" + layer.name)
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
        bpy.context.scene.gatekeeper.required_render_layers = bpy.context.scene.layers
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
                ignoredisabled = bpy.context.scene.gatekeeper.renderlayer_ignoredisabled
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
                    ignore_inclusive = bpy.context.scene.gatekeeper.renderlayer_ignoreinclusive
                    if len(missing) > 0:
                        if len(required) < 19 or not ignore_inclusive:
                            fails[render_layer.name] = sorted(missing)
            #Also Check Required Render Layers for scene:
            required = [i for i in range(20) if scene.gatekeeper.required_render_layers[i]]
            missing = [i for i in required if not scene.layers[i]]
            if len(missing) > 0:
                fails["Saved Required Layers"] = sorted(missing)
            print(fails)

            scene.gatekeeper.renderlayer_fails = json.dumps(fails)
        return {'FINISHED'}

class RectifyRenderLayers(bpy.types.Operator):
    bl_idname = 'scene.gatekeeper_fix_renderlayers'
    bl_label = 'Enables the required scene layers for the render layers you have.'
    to_fix = bpy.props.StringProperty(name = "to_fix", default = "") #Should be a comma delimited list of render layers to renable, leave empty to re-enable all required.
    
    def execute(self, context):
        if self.to_fix == "":
            #Re-enable all required.
            for scene in bpy.data.scenes:
                fails =  json.loads(scene.gatekeeper.renderlayer_fails)
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
        bpy.context.scene.gatekeeper.fileoutput_fails = json.dumps(fails)
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

    def check_border(self,scene):
        border = scene.render.use_border
        if border:
            a = scene.render.border_min_x  == 0.0 and scene.render.border_min_y == 0.0
            b = scene.render.border_max_x == 1.0 and scene.render.border_max_y == 1.0
            return not a and b
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
        if self.check_border(scene):
            extra_fails["Border Fail"] = "Border is on and the whole frame is not being rendered."  
        # All scenes checks:
        for scene in bpy.data.scenes:
            if self.check_layer_samples(scene) != []:
                layers = self.check_layer_samples(scene)
                extra_fails["Samples Fail, " + scene.name] = "Scene samples < Layer Samlples for Scene: " + scene.name + ", Layers: " + str(layers).strip("[]")

        #Write:
        bpy.context.scene.gatekeeper.extra_fails = json.dumps(extra_fails)
        return {'FINISHED'}


class ExportSettings(bpy.types.Operator):
    bl_idname = 'scene.gatekeeper_export'
    bl_label = "Export Scene's Render Settings"
    bl_info = 'Exports a list of render settings to a file.'
    filepath = bpy.props.StringProperty(name = "filepath", subtype = 'FILE_PATH')

    def execute(self, context):
        #Get settings:
        scene = bpy.context.scene
        settings = json.loads(dump_store(scene))
        with open(self.filepath, "w") as f:
            json.dump(settings, f)
        print("Exported render settings as: " + self.filepath)
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

class ImportSettings(bpy.types.Operator):
    bl_idname = 'scene.gatekeeper_import'
    bl_label = "Import Scene Render Settings"
    bl_info = 'Imports a list of render settings from a file.'
    filepath = bpy.props.StringProperty(name = "filepath", subtype = 'FILE_PATH')

    def execute(self, context):
        with open(self.filepath, "r") as f:
            settings = json.load(f)
            scene = bpy.context.scene
            #Set scenes store as settings:
            scene.gatekeeper.store = json.dumps(settings)
            #Apply settings using restore:
            bpy.ops.scene.restore_gatekeeper_store(to_restore = "")
            print("Imported render settings from: " + self.filepath)
            return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
