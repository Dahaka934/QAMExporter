import os
import bpy
import mathutils

from numpy import array

from bpy.props import (
        BoolProperty,
        IntProperty,
        FloatProperty,
        StringProperty,
        EnumProperty
        )
from bpy_extras.io_utils import (
        ExportHelper,
        orientation_helper,
        path_reference,
        axis_conversion
        )
from bpy_extras.node_shader_utils import PrincipledBSDFWrapper

from . import utils
from .profiler import *
from .model import *
from .approximator import Approximator

def menu_func(self, context):
    self.layout.operator(ExportQAM.bl_idname, text="QAM (.qam)")

def register():
    utils.debug("register QAM Exporter")
    bpy.types.TOPBAR_MT_file_export.append(menu_func)

def unregister():
    utils.debug("unregister QAM Exporter")
    bpy.types.TOPBAR_MT_file_export.remove(menu_func)

@orientation_helper(axis_forward='-Z', axis_up='Y')
class ExportQAM(bpy.types.Operator, ExportHelper):

    bl_idname = "export_scene.qam"
    bl_label = "Export QAM"
    bl_options = {'PRESET'}

    ui_tab: EnumProperty(
            items=(('MAIN', "Main", "Main basic settings"),
                   ('ARMATURE', "Armature", "Armature-related settings"),
                   ('ANIMATION', "Animation", "Animation-related settings"),
                   ),
            name="ui_tab",
            description="Export options categories",
            )

    filename_ext = ".qam"
    filter_glob: StringProperty(
            default="*.qam",
            options={'HIDDEN'},
            )

    text_output: BoolProperty(
            name="Text output",
            description="Export model as text file",
            default=False,
            )

    use_selection: BoolProperty(
            name="Selection Only",
            description="Export selected objects only",
            default=False
            )

    use_mesh_modifiers: BoolProperty(
            name="Apply Modifiers",
            description="Apply Modifiers",
            default=False
            )

    include_uvs: BoolProperty(
        name="Include UVs",
        description="Write out the active UV coordinates",
        default=True,
        )

    include_normals: BoolProperty(
            name="Include Normals",
            description="Export normals",
            default=True,
            )

    include_tangent_binormal: BoolProperty(
            name="Include Tangents and Binormals",
            description="Calculate and export tangent and binormal vectors for normal mapping (requires UV mapping the mesh)",
            default=False
            )

    include_bones: BoolProperty(
            name="Include bones",
            description="Export bones (vertex attributes and matrices)",
            default=True
            )

    include_armature: BoolProperty(
            name="Include armatures",
            description="Export armatures (nodes)",
            default=True
            )

    include_animations: BoolProperty(
            name="Include animations",
            description="Export animations",
            default=True
            )

    bones_per_vert_mod: IntProperty(
            name="Mod bones per vert",
            description="Mod count of bones per vertex",
            default=4,
            soft_min=0, soft_max=100
            )

    bones_per_vert_max: IntProperty(
            name="Max bones per vert",
            description="Maximum count of bones per vertex",
            default=8,
            soft_min=0, soft_max=100
            )

    bones_per_mesh_max: IntProperty(
            name="Max bones per mesh",
            description="Maximum count of bones per mesh part",
            default=15,
            soft_min=8, soft_max=100
            )

    approx_animations: BoolProperty(
            name="Approx animations",
            description="Approximate animations",
            default=True
            )

    debug_animations: BoolProperty(
            name="Debug animations",
            description="Debug animations",
            default=False
            )

    approx_err_translations: FloatProperty(
            name="Approx translations",
            description="Approximate translations error",
            default=0.0001,
            soft_min=0, soft_max=1
            )

    approx_err_rotations: FloatProperty(
            name="Approx rotations",
            description="Approximate rotations error",
            default=0.0001,
            soft_min=0, soft_max=1
            )

    approx_err_scales: FloatProperty(
            name="Approx scales",
            description="Approximate scales error",
            default=0.0001,
            soft_min=0, soft_max=1
            )

    def __init__(self):
        self.model = None
        self.bpyObjects = None
        self.cache = ExportQAM.Cache()
        self.vector3AxisMapper = [[0.0, 0.0], [0.0, 0.0], [0.0, 0.0]]
        self.vector4AxisMapper = [[0.0, 0.0], [0.0, 0.0], [0.0, 0.0], [0.0, 0.0]]
        self.global_matrix = None

    def draw(self, context):
        layout = self.layout

        layout.prop(self, "ui_tab", expand=True)
        if self.ui_tab == 'MAIN':
            layout.prop(self, "text_output")
            layout.prop(self, "use_selection")
            layout.prop(self, "use_mesh_modifiers")
            layout.prop(self, "include_uvs")
            layout.prop(self, "include_normals")
            layout.prop(self, "include_tangent_binormal")
        elif self.ui_tab == 'ARMATURE':
            layout.prop(self, "include_bones")
            layout.prop(self, "include_armature")
            layout.prop(self, "bones_per_vert_mod")
            layout.prop(self, "bones_per_vert_max")
            layout.prop(self, "bones_per_mesh_max")
        elif self.ui_tab == 'ANIMATION':
            layout.prop(self, "include_animations")
            layout.prop(self, "approx_animations")
            layout.prop(self, "approx_err_translations")
            layout.prop(self, "approx_err_rotations")
            layout.prop(self, "approx_err_scales")
            layout.prop(self, "debug_animations")

    def execute(self, context):
        try:
            self.cleanData()
            bpy.ops.ed.undo_push("INVOKE_DEFAULT")
            return self.exportModel(context)
        finally:
            bpy.ops.ed.undo()
            self.cleanData()
        return {'FINISHED'}

    @profile_print()
    @profile('totalExportModel', 0)
    def exportModel(self, context):
        """Main method run by Blender to export a QAM file"""
        utils.infoCaps("Start exporting QAM model")

        wm = bpy.context.window_manager
        wm.progress_begin(0, 6)

        # Defines our mapping from Blender Z-Up to whatever the user selected
        self.setupAxisConversion(self.axis_forward, self.axis_up)
        self.global_matrix = (axis_conversion(to_forward=self.axis_forward,
                                              to_up=self.axis_up,
                                              ).to_4x4())

        wm.progress_update(1)
        self.model = QamModel()
        self.bpyObjects = self.filterBlenderObjects(context)

        # Generate the mesh list of the model
        wm.progress_update(2)
        utils.infoCaps("Exporting meshes...")
        meshes = self.generateMeshes(context)
        if meshes is not None:
            self.model.meshes = meshes

        # Generate the materials used in the model
        wm.progress_update(3)
        utils.infoCaps("Exporting materials...")
        materials = self.generateMaterials(context)
        if materials is not None:
            self.model.materials = materials

        # Generate the nodes binding mesh parts, materials and bones
        wm.progress_update(4)
        utils.infoCaps("Exporting nodes...")
        nodes = self.generateNodes(context)
        if nodes is not None:
            self.model.nodes = nodes

        # Convert action curves to animations
        wm.progress_update(5)
        utils.infoCaps("Exporting animations...")
        animations = self.generateAnimations(context)
        if animations is not None:
            self.model.animations = animations

        wm.progress_update(6)
        utils.infoCaps("Writing output file")
        self.writeToFile()

        wm.progress_end()
        utils.info("Finished")

        return {'FINISHED'}

    def cleanData(self):
        self.model = None
        self.bpyObjects = None
        self.cache.clear()

    @profile('writeToFile', 0)
    def writeToFile(self):
        from .nbt import NBTFile
        nbt = NBTFile(value=self.model.packNBT())

        import gzip
        with gzip.open(self.filepath, 'wb') as io:
            nbt.save(io)

        if self.text_output:
            with open(self.filepath + '.txt', 'w') as io:
                io.write(nbt.pretty())

        if self.include_animations == 'DEBUG':
            writeToFileDebugKeyframes(self.filepath, self.model)

    def filterBlenderObjects(self, context):
        objects = []
        setMeshes = set()
        for blNode in bpy.data.objects:
            if (self.use_selection and not blNode.select):
                continue

            if blNode.type == 'MESH':
                if blNode.data.name not in setMeshes:
                    setMeshes.add(blNode.data.name)
                    objects.append(blNode)
            elif blNode.type == 'ARMATURE':
                if self.include_armature:
                    objects.append(blNode)

        return objects

    @profile('generateMeshes', 0)
    def generateMeshes(self, context):
        """Reads all MESH type objects and exported the selected ones (or all if 'only selected' isn't checked"""
        meshes = []

        blNodes = list(filter(lambda x: x.type == 'MESH', self.bpyObjects))
        for idx, blNode in enumerate(blNodes):
            utils.info("[{:>2}/{:>2}]: {:s}", idx, len(blNodes), blNode.name)

            mesh = Mesh()
            mesh.id = blNode.name

            # Clone mesh to a temporary object. Wel'll apply modifiers and triangulate the clone before exporting.
            blNode = self.copyNode(context, blNode)
            blMesh = blNode.data
            self.meshTriangulate(blMesh)

            # We can only export polygons that are associated with a material, so we loop
            # through the list of materials for this mesh

            if blMesh.materials is None:
                utils.warn("Ignored mesh %r, no materials found" % blMesh)
                continue

            gen_tangents = False
            if self.include_tangent_binormal and blMesh.uv_layers is not None and len(blMesh.uv_layers) > 0:
                try:
                    blMesh.calc_tangents(uvmap=blMesh.uv_layers[0].name)
                    gen_tangents = True
                except:
                    pass

            colorMap = blMesh.vertex_colors.active

            wrVertices = self.wrapVertices(blMesh, self.include_bones)

            need_normals = self.include_normals
            need_tangents = gen_tangents
            need_colors = colorMap is not None
            need_uvs = self.include_uvs and blMesh.uv_layers is not None and len(blMesh.uv_layers) > 0

            meshPartIndex = 0
            for blMaterialIndex in range(len(blMesh.materials)):
                utils.info("  [{:>2}/{:>2}]: {:s}", blMaterialIndex, len(blMesh.materials), blMesh.materials[blMaterialIndex].name)

                wrGroups, polyGroups = self.splitVertices(blMesh, blMaterialIndex, wrVertices, self.bones_per_mesh_max)
                self.cache.groups(mesh.id, blMaterialIndex, wrGroups)

                for wrGroupIndex in range(len(wrGroups)):
                    wrGroup = wrGroups[wrGroupIndex]
                    wrGroup.remap()

                    meshPart = MeshPart(id=mesh.id + "_" + str(meshPartIndex))
                    meshPartIndex += 1

                    for poly_i, poly in enumerate(blMesh.polygons):
                        if poly.material_index != blMaterialIndex or polyGroups[poly_i] != wrGroupIndex:
                            continue

                        for loopIndex in poly.loop_indices:
                            blLoop = blMesh.loops[loopIndex]
                            blVertex = blMesh.vertices[blLoop.vertex_index]
                            wrVertex = wrVertices[blLoop.vertex_index]
                            vertex = Vertex()

                            ############
                            # Vertex position is the minimal attribute
                            attribute = VertexAttributes.POSITION.of(wrVertex.pos, blLoop.vertex_index)
                            vertex.add(attribute)
                            ############

                            ############
                            # Exporting tangent and binormals. We calculate those prior to normals because
                            # if we want tangent and binormals then we'll be also using split normals, which
                            # will be exported next section
                            if need_tangents:
                                normal = [None, None, None]
                                normal[0], normal[1], normal[2] = blLoop.normal
                                vertex.add(VertexAttributes.NORMAL.of(normal))

                                tangent = [None, None, None]
                                tangent[0], tangent[1], tangent[2] = blLoop.tangent
                                vertex.add(VertexAttributes.TANGENT.of(tangent, 0))

                                binormal = [None, None, None]
                                binormal[0], binormal[1], binormal[2] = blLoop.bitangent
                                vertex.add(VertexAttributes.BINORMAL.of(binormal, 0))
                            ############

                            ############
                            # Read normals. We also determine if we'll user per-face (flat shading)
                            # or per-vertex normals (gouraud shading) here.
                            elif need_normals:
                                normal = [None, None, None]
                                if poly.use_smooth:
                                    normal[0], normal[1], normal[2] = blVertex.normal
                                else:
                                    normal[0], normal[1], normal[2] = poly.normal
                                vertex.add(VertexAttributes.NORMAL.of(normal))
                            ############

                            ############
                            # Defining vertex color
                            if need_colors:
                                color = [None, None, None, 1.0]
                                color[0], color[1], color[2] = colorMap.data[loopIndex].color

                                attribute = VertexAttributes.COLOR.of(color)
                                vertex.add(attribute)
                            ############

                            ############
                            # Exporting UV coordinates
                            if need_uvs:
                                texCoordCount = 0
                                for uv in blMesh.uv_layers:
                                    # We need to flip UV's because Blender use bottom-left as Y=0 and G3D use top-left
                                    flippedUV = [uv.data[loopIndex].uv[0], 1.0 - uv.data[loopIndex].uv[1]]
                                    vertex.add(VertexAttributeObj(VertexAttributes.TEXCOORD0.id + texCoordCount, flippedUV))
                                    texCoordCount += 1
                            ############

                            ############
                            # Exporting weights
                            if self.include_bones:
                                for g in wrVertex.blendWeights:
                                    vertex.addBlendWeight(wrGroup.map[g[0]], g[1])
                            ############

                            vertex.rehash()
                            meshPart.addIndex(mesh.addVertex(vertex))
                    mesh.addPart(meshPart)

                utils.debug("\nFinished creating mesh part.\nMesh part data:\n###\n{!r}\n###", meshPart)

            if gen_tangents:
                blMesh.free_tangents()

            bpy.data.objects.remove(blNode)
            bpy.data.meshes.remove(blMesh)

            mesh.normalizeAttributes(self.bones_per_vert_mod)
            meshes.append(mesh)

        return meshes

    @profile('generateMaterials', 0)
    def generateMaterials(self, context):
        """Read and returns all materials used by the exported objects"""
        source_dir = os.path.dirname(bpy.data.filepath)
        materials = []

        blMaterials = []
        for blMaterial in bpy.data.materials:
                # If none of the objects in the scene use the material we don't export it
                materialIsUsed = False
                for blNode in self.bpyObjects:
                    if blNode.type != 'MESH':
                        continue

                    blMesh = blNode.data
                    if blMesh is not None and len(blMesh.materials) > 0:
                        for it in blMesh.materials:
                            if it.name == blMaterial.name:
                                blMaterials.append(blMaterial)
                                materialIsUsed = True
                                break

                    if materialIsUsed:
                        break

        for idx, blMaterial in enumerate(blMaterials):
            utils.info("[{:>2}/{:>2}]: {:s}", idx, len(blMaterials), blMaterial.name)

            material = Material()
            material.id = blMaterial.name

            mat_wrap = PrincipledBSDFWrapper(blMaterial)

            material.setProperty('diffuse', [mat_wrap.base_color[0], mat_wrap.base_color[1], mat_wrap.base_color[2]])
            material.setProperty('ior', [mat_wrap.ior])
            material.setProperty('metallic', [mat_wrap.metallic])
            material.setProperty('normalmap_strength', [mat_wrap.normalmap_strength])
            material.setProperty('roughness', [mat_wrap.roughness])
            material.setProperty('specular', [mat_wrap.specular])
            material.setProperty('normalmap_strength', [mat_wrap.normalmap_strength])
            if mat_wrap.transmission != 0.0:
                material.setProperty('opacity', [1.0 - mat_wrap.transmission])

            image_map = {
                "DIFFUSE": "base_color_texture",
                "IOR": "ior_texture",
                "METALLIC": "metallic_texture",
                "NORMAL": "normalmap_texture",
                "ROUGHNESS": "roughness_texture",
                "SPECULAR": "specular_texture"
            }

            for key, mat_wrap_key in image_map.items():
                if mat_wrap_key is None:
                    continue
                tex_wrap = getattr(mat_wrap, mat_wrap_key, None)
                if tex_wrap is None:
                    continue
                image = tex_wrap.image
                if image is None:
                    continue

                texture = Texture()
                texture.id = 'unnamed'
                texture.filename = path_reference(filepath=image.filepath, mode='RELATIVE', base_src=source_dir, base_dst=source_dir)
                texture.type = key
                material.textures.append(texture)
            materials.append(material)

        return materials

    @profile('generateNodes', 0)
    def generateNodes(self, context, parent=None, parentName=""):
        """Generates object nodes that attach mesh parts, materials and bones together"""
        nodes = []

        listOfBlenderObjects = None
        if parent is None:
            listOfBlenderObjects = self.bpyObjects
        elif isinstance(parent, bpy.types.Bone):
            listOfBlenderObjects = parent.children
        elif parent.type == 'MESH':
            listOfBlenderObjects = parent.children
        elif parent.type == 'ARMATURE':
            listOfBlenderObjects = parent.data.bones
            # If parent is an armature, we store it's name to concatenate with bone names later
            parentName = parent.name
        else:
            return None

        for blNode in listOfBlenderObjects:
            isBone = isinstance(blNode, bpy.types.Bone)
            if isBone:
                # If node is a bone see if parent is the armature.
                # If is, only export the bone if it's a root bone (doesn't have
                # another bone as a parent). Otherwise wait to export it
                # when the parent bone is being exported
                if parent is not None and not isinstance(parent, bpy.types.Bone) and parent.type == 'ARMATURE':
                    if blNode.parent is not None:
                        continue

            node = Node()
            if isBone:
                node.id = ("%s_%s" % (parentName, blNode.name))
            else:
                node.id = blNode.name

            utils.info("[??/??]: {:s}", node.id)

            try:
                transformMatrix = None

                if isBone:
                    transformMatrix = self.getTransformFromBone(blNode)
                elif blNode.parent is not None:
                    if (parent is None and blNode.parent.type == 'ARMATURE') or (parent is not None):
                        # Exporting a child node, so we get the local transform matrix.
                        # Obs: when exporting root mesh nodes parented to armatures, we consider it
                        # 'child' in relation to the armature so we get it's local transform, but the mesh node
                        # is still considered a root node.
                        transformMatrix = blNode.matrix_local
                    elif parent is None and blNode.parent.type == 'MESH':
                        # If this node is parented and we didn't pass a 'parent' parameter then we are only
                        # exporting root nodes at this time and we'll ignore this node.
                        continue
                else:
                    # Exporting a root node, we get it's transform matrix from the world transform matrix
                    transformMatrix = blNode.matrix_world

                translation, rotation, scale = transformMatrix.decompose()

                node.translation = self.convertTranslation(translation)
                node.rotation = self.convertRotation(rotation)
                node.scale = self.convertScale(scale)

            except:
                utils.warn("Error decomposing transform for node %s" % blNode.name)
                pass

            # If this is a mesh node, go through each part and material and associate with this node
            if not isBone and blNode.type == 'MESH':
                blMesh = blNode.data

                if blMesh.materials is None:
                    utils.warn("Ignored mesh %r, no materials found" % blMesh)
                    continue

                meshPartIndex = 0
                for blMaterialIndex in range(0, len(blMesh.materials)):
                    blMaterial = blMesh.materials[blMaterialIndex]
                    if blMaterial is None:
                        continue

                    wrGroups = self.cache.groups(node.id, blMaterialIndex, None)
                    for wrGroup in wrGroups:
                        nodePart = NodePart()
                        nodePart.meshPartId = blNode.name + "_" + str(meshPartIndex)
                        nodePart.materialId = blMaterial.name
                        meshPartIndex += 1

                        if blNode.bound_box is not None:
                            nodePart.bound_box = BoundBox(blNode.bound_box)

                        # Start writing bones
                        blArmature = blNode.find_armature()
                        if self.include_bones and len(blNode.vertex_groups) > 0 and blArmature is not None:
                            for wrGroupIndex in wrGroup.set:
                                blVertexGroup = blNode.vertex_groups[wrGroupIndex]
                                bone = Bone()
                                bone.node = ("%s_%s" % (blArmature.name, blVertexGroup.name))

                                try:
                                    blBone = blArmature.data.bones[blVertexGroup.name]

                                    boneTransformMatrix = blNode.matrix_local.inverted() @ blBone.matrix_local
                                    boneLocation, boneQuaternion, boneScale = boneTransformMatrix.decompose()

                                    bone.translation = self.convertTranslation(boneLocation)
                                    bone.rotation = self.convertRotation(boneQuaternion)
                                    bone.scale = self.convertScale(boneScale)
                                except:
                                    utils.error("Unexpected error exporting bone: %s" % blVertexGroup.name)
                                    bone.translation = [0.0, 0.0, 0.0]
                                    bone.rotation = [0.0, 0.0, 0.0, 1.0]
                                    bone.scale = [1.0, 1.0, 1.0]

                                nodePart.addBone(bone)
                        node.addPart(nodePart)

            childNodes = self.generateNodes(context, blNode, parentName)
            if childNodes is not None and len(childNodes) > 0:
                node.children = childNodes

            nodes.append(node)

        return nodes

    @profile('generateAnimations', 0)
    def generateAnimations(self, context):
        # TODO Detect if certain curve uses linear interpolation. If yes then
        # we can safely just save keyframes as LibGDX also uses linear interpolation
        """If selected by the user, generates keyframed animations for the bones"""
        if not self.include_animations:
            return

        animations = []

        # Save our time per currentFrameNumber (in miliseconds)
        fps = context.scene.render.fps
        frameTime = (1 / fps)

        # For each action we export currentFrameNumber data.
        # We are exporting all actions, but to avoid exporting deleted actions (actions with ZERO users)
        # each action must have at least one user. In Blender user the FAKE USER option to assign at least
        # one user to each action
        blActions = list(filter(lambda x: x.users > 0, bpy.data.actions))
        for idx, blAction in enumerate(blActions):
            utils.info("[{:>2}/{:>2}]: {:s}", idx, len(blActions), blAction.name)

            frameStart = int(blAction.frame_range[0])
            frameRange = int(blAction.frame_range[1])

            animation = Animation()
            animation.id = blAction.name
            animation.time = (frameRange - 1) * frameTime

            bonesIndex = 0
            for blArmature in self.bpyObjects:
                if blArmature.type != 'ARMATURE':
                    continue

                for blBone in blArmature.data.bones:
                    bone = NodeAnimation()
                    bone.boneId = ("%s_%s" % (blArmature.name, blBone.name))
                    bonesIndex += 1

                    translationFCurve = self.findFCurve(blAction, blBone, 'location')
                    rotationFCurve = self.findFCurve(blAction, blBone, 'rotation_quaternion')
                    scaleFCurve = self.findFCurve(blAction, blBone, 'scale')

                    # Rest transform of this bone, used as reference to calculate frames
                    restTransform = self.getTransformFromBone(blBone)

                    emptyAnimation = True
                    for frameNumber in range(frameStart, frameRange + 1):
                        keyframe = self.createKeyframe(translationFCurve, rotationFCurve, scaleFCurve, frameNumber, restTransform)
                        keyframe.keytime = (frameNumber - frameStart) * frameTime

                        emptyAnimation = False
                        if keyframe.translation is not None:
                            bone.addTranslation(keyframe.createSeparateTranslation())
                        if keyframe.rotation is not None:
                            bone.addRotation(keyframe.createSeparateRotation())
                        if keyframe.scaling is not None:
                            bone.addScaling(keyframe.createSeparateScaling())

                    if self.approx_animations:
                        if bone.translation is not None and len(bone.translation) > 0:
                            bone.translation = self.approximateKeyframes(bone.translation, 0, self.approx_err_translations)

                        if bone.rotation is not None and len(bone.rotation) > 0:
                            bone.rotation = self.approximateKeyframes(bone.rotation, 1, self.approx_err_rotations)

                        if bone.scaling is not None and len(bone.scaling) > 0:
                            bone.scaling = self.approximateKeyframes(bone.scaling, 2, self.approx_err_scales)

                    # Finally add bone node to animation
                    if not emptyAnimation or True:
                        animation.addBone(bone)

            # If this action animates at least one bone, add it to the list of actions
            if animation.bones is not None and len(animation.bones) > 0:
                animations.append(animation)

        # Finally return the generated animations
        return animations

    @profile('copyNode', 1)
    def copyNode(self, context, blNode):
        node = blNode.copy()
        node.data = node.to_mesh(context.depsgraph, self.use_mesh_modifiers)
        return node

    @profile('meshTriangulate', 1)
    def meshTriangulate(self, me):
        """
        Creates a triangulated copy of a mesh.

        This copy needs to later be removed or else it will be saved as new data on the Blender file.
        """

        import bmesh
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.triangulate(bm, faces=bm.faces)
        bm.to_mesh(me)
        bm.free()
        del bmesh

    @profile('wrapVertices', 1)
    def wrapVertices(self, blMesh, bones):
        vertices = [None] * len(blMesh.vertices)

        for i, vert in enumerate(blMesh.vertices):
            pos = vert.co
            vertices[i] = ExportQAM.WrappedVertex(self.convertTranslation(pos))
            if bones:
                vertices[i].setGroups(vert.groups, self.bones_per_vert_max)

        return vertices

    @profile('splitVertices', 1)
    def splitVertices(self, blMesh, blMaterialIndex, vertices, maxBones):
        groups = []
        polygonsGroup = [-1] * len(blMesh.polygons)

        def addPolyToGroup(group, poly):
            for loopIndex in poly.loop_indices:
                blLoop = blMesh.loops[loopIndex]
                if not group.addVert(vertices[blLoop.vertex_index]):
                    return False
            return True

        def tryAddPoly(poly):
            for group_i, group in enumerate(groups):
                if addPolyToGroup(group, poly):
                    return group_i
            return -1

        for poly_i, poly in enumerate(blMesh.polygons):
            if (poly.material_index == blMaterialIndex):
                idx = tryAddPoly(poly)
                if idx < 0:
                    new = ExportQAM.Group(maxBones)
                    groups.append(new)
                    addPolyToGroup(new, poly)
                    idx = len(groups) - 1
                polygonsGroup[poly_i] = idx

        return groups, polygonsGroup

    def convertTranslation(self, co):
        mapX = self.vector3AxisMapper[0]
        mapY = self.vector3AxisMapper[1]
        mapZ = self.vector3AxisMapper[2]
        return [co[mapX[0]] * mapX[1], co[mapY[0]] * mapY[1], co[mapZ[0]] * mapZ[1]]

    def convertRotation(self, co):
        mapX = self.vector4AxisMapper[0]
        mapY = self.vector4AxisMapper[1]
        mapZ = self.vector4AxisMapper[2]
        mapW = self.vector4AxisMapper[3]
        return [co[mapX[0]] * mapX[1], co[mapY[0]] * mapY[1], co[mapZ[0]] * mapZ[1], co[mapW[0]] * mapW[1]]

    def convertScale(self, co):
        return [co[self.vector3AxisMapper[0][0]], co[self.vector3AxisMapper[1][0]], co[self.vector3AxisMapper[2][0]]]

    @profile('getTransformFromBone', 2)
    def getTransformFromBone(self, bone):
        """Create a transform matrix based on the relative rest position of a bone"""

        if bone.parent is None:
            return bone.matrix_local
        else:
            return bone.parent.matrix_local.inverted() @ bone.matrix_local

    @profile('findFCurve', 1)
    def findFCurve(self, action, bone, prop):
        """
        Find a fcurve for the given action, bone and property. Returns an array with as many fcurves
        as there are indices in the property.
        Ex: The returned value for the location property will have 3 fcurves, one for each of the X, Y and Z coordinates
        """

        returnedFCurves = None

        dataPath = ("pose.bones[\"%s\"].%s" % (bone.name, prop))
        if prop == 'location':
            returnedFCurves = [None, None, None]
        elif prop == 'rotation_quaternion':
            returnedFCurves = [None, None, None, None]
        elif prop == 'scale':
            returnedFCurves = [None, None, None]
        else:
            self.error("FCurve Property not supported")
            raise Exception("FCurve Property not supported")

        for fcurve in action.fcurves:
            if fcurve.data_path == dataPath:
                returnedFCurves[fcurve.array_index] = fcurve

        return returnedFCurves

    @profile('createTransformMatrix', 2)
    def createTransformMatrix(self, locationVector, quaternionVector, scaleVector):
        """Create a transform matrix from a location vector, a rotation quaternion and a scale vector"""

        if isinstance(quaternionVector, mathutils.Quaternion):
            quat = quaternionVector.normalized()
        else:
            quat = mathutils.Quaternion(quaternionVector).normalized()

        translationMatrix = mathutils.Matrix(((0, 0, 0, locationVector[0]), (0, 0, 0, locationVector[1]), (0, 0, 0, locationVector[2]), (0, 0, 0, 0)))

        rotationMatrix = quat.to_matrix().to_4x4()

        scaleMatrix = mathutils.Matrix(((scaleVector[0], 0, 0, 0), (0, scaleVector[1], 0, 0), (0, 0, scaleVector[2], 0), (0, 0, 0, 1)))

        matrix = (rotationMatrix @ scaleMatrix) + translationMatrix

        return matrix

    @profile('createKeyframe', 2)
    def createKeyframe(self, translationFCurve, rotationFCurve, scaleFCurve, frameNumber, restTransform):
        keyframe = Keyframe()

        translationVector = [0.0, 0.0, 0.0, 0.0]
        rotationVector = [1.0, 0.0, 0.0, 0.0]
        scaleVector = [1.0, 1.0, 1.0]

        if translationFCurve is not None:
            if translationFCurve[0] is not None:
                translationVector[0] = translationFCurve[0].evaluate(frameNumber)
            if translationFCurve[1] is not None:
                translationVector[1] = translationFCurve[1].evaluate(frameNumber)
            if translationFCurve[2] is not None:
                translationVector[2] = translationFCurve[2].evaluate(frameNumber)

        if rotationFCurve is not None:
            if rotationFCurve[0] is not None:
                rotationVector[0] = rotationFCurve[0].evaluate(frameNumber)
            if rotationFCurve[1] is not None:
                rotationVector[1] = rotationFCurve[1].evaluate(frameNumber)
            if rotationFCurve[2] is not None:
                rotationVector[2] = rotationFCurve[2].evaluate(frameNumber)
            if rotationFCurve[3] is not None:
                rotationVector[3] = rotationFCurve[3].evaluate(frameNumber)

        if scaleFCurve is not None:
            if scaleFCurve[0] is not None:
                scaleVector[0] = scaleFCurve[0].evaluate(frameNumber)
            if scaleFCurve[1] is not None:
                scaleVector[1] = scaleFCurve[1].evaluate(frameNumber)
            if scaleFCurve[2] is not None:
                scaleVector[2] = scaleFCurve[2].evaluate(frameNumber)

        poseTransform = self.createTransformMatrix(translationVector, rotationVector, scaleVector)
        translationVector, rotationVector, scaleVector = (restTransform @ poseTransform).decompose()

        # If one of the transform attributes had to be evaluated above then this
        # is a keyframe, otherwise it's on rest pose and we don't need the keyframe
        keyframe.translation = self.convertTranslation(translationVector)
        keyframe.rotation = self.convertRotation(rotationVector)
        keyframe.scale = self.convertScale(scaleVector)
        return keyframe

    @profile('approximate', 1)
    def approximateKeyframes(self, separateList, type, err):
        if type == 1:
            elementSize = 5
        else:
            elementSize = 4

        points = array([array(p.value + [p.keytime]) for p in separateList])
        approx = Approximator(elementSize)
        indices = approx.approximate(points, err)
        out = [separateList[i] for i in indices]

        if len(out) == 2:
            out0 = out[0].value
            out1 = out[1].value
            for i in range(1, elementSize - 1):
                if utils.limitFloatPrecision(out0[i]) != utils.limitFloatPrecision(out1[i]):
                    return out

            if type == 0:
                if utils.testDefaultTransform(out0):
                    return []
            elif type == 1:
                if utils.testDefaultQuaternion(out0):
                    return []
            elif type == 2:
                if utils.testDefaultScale(out0):
                    return []

            out.pop()
        return out

    class Cache:
        def __init__(self):
            self.groups_dict = {}
            self.tasks = []

        def groups(self, name, blMaterialIndex, groups):
            key = name + '__' + str(blMaterialIndex)
            if groups is None:
                return self.groups_dict.get(key, None)
            else:
                self.groups_dict[key] = groups
                return groups

        def clear(self):
            self.groups_dict.clear()

            for task in self.tasks:
                task()
            self.tasks.clear()

    def setupAxisConversion(self, axisForward, axisUp):
        # W for quaternions takes from blender W which is index 0
        self.vector4AxisMapper[3][0] = 0
        self.vector4AxisMapper[3][1] = 1.0

        if axisForward == "X" or axisForward == "-X":
            self.vector3AxisMapper[0][0] = 1
            self.vector4AxisMapper[0][0] = 2

            if axisForward == "X":
                self.vector3AxisMapper[0][1] = 1.0
                self.vector4AxisMapper[0][1] = 1.0
            else:
                self.vector3AxisMapper[0][1] = -1.0
                self.vector4AxisMapper[0][1] = -1.0

            if axisUp == "Y" or axisUp == "-Y":
                self.vector3AxisMapper[1][0] = 2
                self.vector4AxisMapper[1][0] = 3

                if axisUp == "Y":
                    self.vector3AxisMapper[1][1] = 1.0
                    self.vector4AxisMapper[1][1] = 1.0
                else:
                    self.vector3AxisMapper[1][1] = -1.0
                    self.vector4AxisMapper[1][1] = -1.0

                # Z is right
                self.vector3AxisMapper[2][0] = 0
                self.vector4AxisMapper[2][0] = 1
                self.vector3AxisMapper[2][1] = 1.0
                self.vector4AxisMapper[2][1] = 1.0

            elif axisUp == "Z" or axisUp == "-Z":
                self.vector3AxisMapper[2][0] = 2
                self.vector4AxisMapper[2][0] = 3

                if axisUp == "Z":
                    self.vector3AxisMapper[2][1] = 1.0
                    self.vector4AxisMapper[2][1] = 1.0
                else:
                    self.vector3AxisMapper[2][1] = -1.0
                    self.vector4AxisMapper[2][1] = -1.0

                # Y is right
                self.vector3AxisMapper[1][0] = 0
                self.vector4AxisMapper[1][0] = 1
                self.vector3AxisMapper[1][1] = 1.0
                self.vector4AxisMapper[1][1] = 1.0

        elif axisForward == "Y" or axisForward == "-Y":
            self.vector3AxisMapper[1][0] = 1
            self.vector4AxisMapper[1][0] = 2

            if axisForward == "Y":
                self.vector3AxisMapper[1][1] = 1.0
                self.vector4AxisMapper[1][1] = 1.0
            else:
                self.vector3AxisMapper[1][1] = -1.0
                self.vector4AxisMapper[1][1] = -1.0

            if axisUp == "X" or axisUp == "-X":
                self.vector3AxisMapper[0][0] = 2
                self.vector4AxisMapper[0][0] = 3

                if axisUp == "X":
                    self.vector3AxisMapper[0][1] = 1.0
                    self.vector4AxisMapper[0][1] = 1.0
                else:
                    self.vector3AxisMapper[0][1] = -1.0
                    self.vector4AxisMapper[0][1] = -1.0

                # Z is right
                self.vector3AxisMapper[2][0] = 0
                self.vector4AxisMapper[2][0] = 1
                self.vector3AxisMapper[2][1] = 1.0
                self.vector4AxisMapper[2][1] = 1.0

            elif axisUp == "Z" or axisUp == "-Z":
                self.vector3AxisMapper[2][0] = 2
                self.vector4AxisMapper[2][0] = 3

                if axisUp == "Z":
                    self.vector3AxisMapper[2][1] = 1.0
                    self.vector4AxisMapper[2][1] = 1.0
                else:
                    self.vector3AxisMapper[2][1] = -1.0
                    self.vector4AxisMapper[2][1] = -1.0

                # X is right
                self.vector3AxisMapper[0][0] = 0
                self.vector4AxisMapper[0][0] = 1
                self.vector3AxisMapper[0][1] = 1.0
                self.vector4AxisMapper[0][1] = 1.0

        elif axisForward == "Z" or axisForward == "-Z":
            self.vector3AxisMapper[2][0] = 1
            self.vector4AxisMapper[2][0] = 2

            if axisForward == "Z":
                self.vector3AxisMapper[2][1] = 1.0
                self.vector4AxisMapper[2][1] = 1.0
            else:
                self.vector3AxisMapper[2][1] = -1.0
                self.vector4AxisMapper[2][1] = -1.0

            if axisUp == "Y" or axisUp == "-Y":
                self.vector3AxisMapper[1][0] = 2
                self.vector4AxisMapper[1][0] = 3

                if axisUp == "Y":
                    self.vector3AxisMapper[1][1] = 1.0
                    self.vector4AxisMapper[1][1] = 1.0
                else:
                    self.vector3AxisMapper[1][1] = -1.0
                    self.vector4AxisMapper[1][1] = -1.0

                # X is right
                self.vector3AxisMapper[0][0] = 0
                self.vector4AxisMapper[0][0] = 1
                self.vector3AxisMapper[0][1] = 1.0
                self.vector4AxisMapper[0][1] = 1.0

            elif axisUp == "X" or axisUp == "-X":
                self.vector3AxisMapper[0][0] = 2
                self.vector4AxisMapper[0][0] = 3

                if axisUp == "X":
                    self.vector3AxisMapper[0][1] = 1.0
                    self.vector4AxisMapper[0][1] = 1.0
                else:
                    self.vector3AxisMapper[0][1] = -1.0
                    self.vector4AxisMapper[0][1] = -1.0

                # Y is right
                self.vector3AxisMapper[1][0] = 0
                self.vector4AxisMapper[1][0] = 1
                self.vector3AxisMapper[1][1] = 1.0
                self.vector4AxisMapper[1][1] = 1.0

    class Group:
        def __init__(self, max):
            self.set = set()
            self.map = None
            self.max = max

        def isFull(self): return len(self.set) >= self.max

        def hasVert(self, vert):
            for g in vert.blendWeights:
                if g[0] not in self.set:
                    return False
            return True

        def addVert(self, vert):
            if len(self.set) >= self.max:
                return self.hasVert(vert)

            missing = 0
            for g in vert.blendWeights:
                if g[0] not in self.set:
                    missing += 1

            if len(self.set) + missing >= self.max:
                return False

            for g in vert.blendWeights:
                self.set.add(g[0])

            return True

        def remap(self):
            self.map = [-1] * (max(self.set, default=0) + 1)
            for i, it in enumerate(self.set):
                self.map[it] = i

    class WrappedVertex:
        def __init__(self, pos):
            self.pos = pos
            self.blendWeights = None
            self.blendWeightsAligned = None

        def setGroups(self, groups, max):
            if groups is None:
                self.blendWeights = None
                return

            filtered = list(map(lambda x: [x.group, x.weight], filter(lambda x: not utils.is0(x.weight), groups)))
            if len(filtered) > max:
                filtered.sort(key=lambda x: x[1])
                filtered = filtered[0:max]

            blendSum = 0.0
            for i in range(len(filtered)):
                blendSum += filtered[i][1]

            if not utils.is1(blendSum):
                for i in range(len(filtered)):
                    filtered[i][1] /= blendSum

            self.blendWeights = filtered

@profile('writeToFileDebugKeyframes', 0)
def writeToFileDebugKeyframes(filepath, model):
    def line(file, obj):
        file.write(obj)
        file.write('\n')

    def safe(obj):
        return obj if obj is not None else []

    def toStr(list, index, default):
        return str(list[index] if list is not None else default)

    name = os.path.splitext(filepath)[0]
    for animation in model.animations:
        for bone in animation.bones:
            path = os.path.join(name, animation.id, bone.boneId + ".txt")

            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                line(f, 'Default:')
                line(f, 'Timings:')
                line(f, ' '.join([str(x.keytime) for x in safe(bone.keyframes)]))
                line(f, 'Translation:')
                line(f, 'X:')
                line(f, ' '.join([toStr(x.translation, 0, 0.0) for x in safe(bone.keyframes)]))
                line(f, 'Y:')
                line(f, ' '.join([toStr(x.translation, 1, 0.0) for x in safe(bone.keyframes)]))
                line(f, 'Z:')
                line(f, ' '.join([toStr(x.translation, 2, 0.0) for x in safe(bone.keyframes)]))
                line(f, 'Rotation:')
                line(f, 'X:')
                line(f, ' '.join([toStr(x.rotation, 1, 0.0) for x in safe(bone.keyframes)]))
                line(f, 'Y:')
                line(f, ' '.join([toStr(x.rotation, 2, 0.0) for x in safe(bone.keyframes)]))
                line(f, 'Z:')
                line(f, ' '.join([toStr(x.rotation, 3, 0.0) for x in safe(bone.keyframes)]))
                line(f, 'W:')
                line(f, ' '.join([toStr(x.rotation, 0, 1.0) for x in safe(bone.keyframes)]))
                line(f, 'Scale:')
                line(f, 'X:')
                line(f, ' '.join([toStr(x.scale, 0, 1.0) for x in safe(bone.keyframes)]))
                line(f, 'Y:')
                line(f, ' '.join([toStr(x.scale, 1, 1.0) for x in safe(bone.keyframes)]))
                line(f, 'Z:')
                line(f, ' '.join([toStr(x.scale, 2, 1.0) for x in safe(bone.keyframes)]))
                line(f, 'Separate:')
                line(f, 'Translation:')
                line(f, 'Timings:')
                line(f, ' '.join([str(x.keytime) for x in safe(bone.translation)]))
                line(f, 'X:')
                line(f, ' '.join([toStr(x.value, 0, 0.0) for x in safe(bone.translation)]))
                line(f, 'Y:')
                line(f, ' '.join([toStr(x.value, 1, 0.0) for x in safe(bone.translation)]))
                line(f, 'Z:')
                line(f, ' '.join([toStr(x.value, 2, 0.0) for x in safe(bone.translation)]))
                line(f, 'Rotation:')
                line(f, 'Timings:')
                line(f, ' '.join([str(x.keytime) for x in safe(bone.rotation)]))
                line(f, 'X:')
                line(f, ' '.join([toStr(x.value, 1, 0.0) for x in safe(bone.rotation)]))
                line(f, 'Y:')
                line(f, ' '.join([toStr(x.value, 2, 0.0) for x in safe(bone.rotation)]))
                line(f, 'Z:')
                line(f, ' '.join([toStr(x.value, 3, 0.0) for x in safe(bone.rotation)]))
                line(f, 'W:')
                line(f, ' '.join([toStr(x.value, 0, 1.0) for x in safe(bone.rotation)]))
                line(f, 'Scale:')
                line(f, 'Timings:')
                line(f, ' '.join([str(x.keytime) for x in safe(bone.scale)]))
                line(f, 'X:')
                line(f, ' '.join([toStr(x.value, 0, 1.0) for x in safe(bone.scale)]))
                line(f, 'Y:')
                line(f, ' '.join([toStr(x.value, 1, 1.0) for x in safe(bone.scale)]))
                line(f, 'Z:')
                line(f, ' '.join([toStr(x.value, 2, 1.0) for x in safe(bone.scale)]))