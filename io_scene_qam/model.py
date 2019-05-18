import math
import struct
from . import utils
from .profiler import profile
from .nbt import (
    NBTSerializable,
    NBTTagCompound,
    NBTTagList,
    NBTTagString,
    NBTTagFloat,
    NBTTagFloatArray,
    NBTTagUShortArray,
    NBTTagIntArray
)

__all__ = (
    'QamModel', 'VertexAttributes', 'VertexAttribute', 'VertexAttributeObj',
    'Vertex', 'Mesh', 'MeshPart', 'Node', 'NodePart', 'Bone', 'Texture',
    'Material', 'Animation', 'NodeAnimation', 'Keyframe', 'KeyframeSeparate'
)

class QamModel(NBTSerializable):
    __slots__ = ('meshes', 'materials', 'nodes', 'animations')

    def __init__(self):
        self.meshes = []
        self.materials = []
        self.nodes = []
        self.animations = []

    def addMesh(self, mesh):
        self.meshes.append(mesh)

    def hasMesh(self, meshId):
        for mesh in self.meshes:
            if mesh.id() == meshId:
                return True
        return False

    def packNBT(self):
        nbt = NBTTagCompound()
        if self.meshes is not None:
            nbt['meshes'] = NBTTagList(NBTTagCompound, [it.packNBT() for it in self.meshes])
        if self.materials is not None:
            nbt['materials'] = NBTTagList(NBTTagCompound, [it.packNBT() for it in self.materials])
        if self.nodes is not None:
            nbt['nodes'] = NBTTagList(NBTTagCompound, [it.packNBT() for it in self.nodes])
        if self.animations is not None:
            nbt['animations'] = NBTTagList(NBTTagCompound, [it.packNBT() for it in self.animations])
        return nbt

# end QamModel

class VertexAttribute:
    __slots__ = ('name', 'id')

    def __init__(self, name, id, map):
        self.name = name
        self.id = id
        map[id] = self

    def init(self, list, obj):
        list.append(self.name)

    def of(self, value, hash=None):
        return VertexAttributeObj(self.id, value, hash)

class VertexAttributeBoneIndices(VertexAttribute):

    def init(self, list, obj):
        count = len(obj.value)
        for i in range(0, count):
            list.append(self.name + str(i))

class VertexAttributeBoneWeights(VertexAttribute):

    def init(self, list, obj):
        idx = 0
        count = len(obj.value)
        while count > 0:
            list.append('{}{}{}'.format(self.name, idx, min(count, 4)))
            idx += 1
            count -= 4

class VertexAttributes(object):
    ATTRIBUTE_MAP = {}

    POSITION = VertexAttribute('POSITION', 10, ATTRIBUTE_MAP)
    NORMAL = VertexAttribute('NORMAL', 20, ATTRIBUTE_MAP)
    TANGENT = VertexAttribute('TANGENT', 30, ATTRIBUTE_MAP)
    BINORMAL = VertexAttribute('BINORMAL', 40, ATTRIBUTE_MAP)
    COLOR = VertexAttribute('COLOR', 50, ATTRIBUTE_MAP)
    TEXCOORD0 = VertexAttribute('TEXCOORD0', 60, ATTRIBUTE_MAP)
    TEXCOORD1 = VertexAttribute('TEXCOORD1', 61, ATTRIBUTE_MAP)
    TEXCOORD2 = VertexAttribute('TEXCOORD2', 62, ATTRIBUTE_MAP)
    TEXCOORD3 = VertexAttribute('TEXCOORD3', 63, ATTRIBUTE_MAP)
    TEXCOORD4 = VertexAttribute('TEXCOORD4', 64, ATTRIBUTE_MAP)
    TEXCOORD5 = VertexAttribute('TEXCOORD5', 65, ATTRIBUTE_MAP)
    TEXCOORD6 = VertexAttribute('TEXCOORD6', 66, ATTRIBUTE_MAP)
    TEXCOORD7 = VertexAttribute('TEXCOORD7', 67, ATTRIBUTE_MAP)
    TEXCOORD8 = VertexAttribute('TEXCOORD8', 68, ATTRIBUTE_MAP)
    TEXCOORD9 = VertexAttribute('TEXCOORD9', 69, ATTRIBUTE_MAP)
    BONEINDICES = VertexAttributeBoneIndices('BONEINDICES', 70, ATTRIBUTE_MAP)
    BONEWEIGHTS = VertexAttributeBoneWeights('BONEWEIGHTS', 80, ATTRIBUTE_MAP)

    @staticmethod
    def of(type):
        return VertexAttributes.ATTRIBUTE_MAP[type]

    @staticmethod
    def name(type):
        return VertexAttributes.ATTRIBUTE_MAP[type].name

    @staticmethod
    def isTexCoord(id):
        return VertexAttributes.TEXCOORD0.id <= type and type <= VertexAttributes.TEXCOORD9.id

# end VertexAttributes

class VertexAttributeObj:
    __slots__ = ('type', 'value', 'hash')

    def __init__(self, type, value, hash=None):
        self.type = type
        self.value = value
        if hash is None:
            self.rehash()
        else:
            self.hash = hash

    @profile('rehashVertexAttribute', 3)
    def rehash(self):
        self.hash = 81 * self.type + utils.hashList(self.value)

    def __hash__(self):
        return self.hash

    def __eq__(self, another):
        """Compare this attribute with another for value"""
        if len(self.value) != len(another.value):
            return False

        for pos in range(0, len(self.value)):
            if self.value[pos] != another.value[pos]:
                return False

        return True

    def __ne__(self, another):
        return not self.__eq__(another)

    def __repr__(self):
        value = "{!s} {!r}".format(VertexAttributes.of(self.type).name, self.value)
        return value

# end VertexAttributeObj

class Vertex(NBTSerializable):
    __slots__ = ('attributes', 'attrBoneIndices', 'attrBoneWeights', 'hash')

    def __init__(self):
        self.attributes = []
        self.attrBoneIndices = None
        self.attrBoneWeights = None
        self.hash = None

    def add(self, attribute):
        self.attributes.append(attribute)

    def addBlendWeight(self, idx, weight):
        if self.attrBoneIndices is None:
            self.attrBoneIndices = VertexAttributes.BONEINDICES.of([])
            self.attrBoneWeights = VertexAttributes.BONEWEIGHTS.of([])
            self.attributes.append(self.attrBoneIndices)
            self.attributes.append(self.attrBoneWeights)
        self.attrBoneWeights.value.append(weight)
        self.attrBoneIndices.value.append(int(idx))

    @profile('rehashVertex', 3)
    def rehash(self):
        self.hash = utils.hashList(self.attributes)

    @profile('hashVertex', 3)
    def __hash__(self):
        return self.hash

    @profile('eqVertex', 3)
    def __eq__(self, another):
        for pos in range(len(self.attributes)):
            if self.attributes[pos] != another.attributes[pos]:
                return False
        return True

    def __ne__(self, another):
        return not self.__eq__(another)

    def __repr__(self):
        reprStr = "{ "

        firstTime = True
        for attr in self.attributes:
            if firstTime:
                firstTime = False
            else:
                reprStr = reprStr + ", "
            reprStr = reprStr + ("{!r}".format(attr))

        reprStr = reprStr + (" }")

        return reprStr

# end Vertex

class Mesh(NBTSerializable):
    __slots__ = ('id', 'vertices', 'parts', 'attributes', 'vertexIndices')

    def __init__(self):
        self.id = ""
        self.vertices = []
        self.parts = []
        self.attributes = []
        self.vertexIndices = {}

    def isEmpty(self):
        return len(self.attributes) == 0 or len(self.parts) == 0 or len(self.vertices) == 0

    @profile('addVertex', 3)
    def addVertex(self, vertex):
        idx = self.vertexIndices.get(vertex, -1)
        if idx < 0:
            self.vertices.append(vertex)
            idx = len(self.vertices) - 1
            self.vertexIndices[vertex] = idx
        return idx

    def addPart(self, meshPart):
        self.parts.append(meshPart)
        meshPart.parentMesh = self

    @profile('normalizeAttributes', 2)
    def normalizeAttributes(self, mod):
        if len(self.vertices) > 0:
           self.attributes = [it.type for it in self.vertices[0].attributes]

        attrColorInx = -1
        for i in range(len(self.attributes)):
            if self.attributes[i] == VertexAttributes.COLOR.id:
                attrColorInx = i

        bonesCount = 0
        for it in self.vertices:
            if it.attrBoneWeights is not None and bonesCount < len(it.attrBoneWeights.value):
                bonesCount = len(it.attrBoneWeights.value)

        if bonesCount > 0:
            bonesCount = ((bonesCount - 1) // mod * mod) + mod

            indicesCount = ((bonesCount - 1) >> 2 << 2) + 4
            indicesFmtPack = '>{}B'.format(indicesCount)
            indicesFmtUnpack = '>{}f'.format(indicesCount // 4)

            for vert in self.vertices:
                for i in range(bonesCount - len(vert.attrBoneIndices.value)):
                    vert.attrBoneIndices.value.append(0)
                    vert.attrBoneWeights.value.append(0.0)
                for i in range(indicesCount - len(vert.attrBoneIndices.value)):
                    vert.attrBoneIndices.value.append(0)

                tmp = struct.pack(indicesFmtPack, *vert.attrBoneIndices.value[::-1])
                vert.attrBoneIndices.value = struct.unpack(indicesFmtUnpack, tmp)

        if attrColorInx >= 0:
            for vert in self.vertices:
                attr = vert.attributes[attrColorInx]
                tmp = struct.pack('>4B', *[int(it * 255) for it in attr.value[::-1]])
                attr.value = struct.unpack('>f', tmp)

    def packNBT(self):
        attr_names = []
        for i in range(len(self.attributes)):
            attr = VertexAttributes.of(self.attributes[i])
            attr.init(attr_names, self.vertices[0].attributes[i])

        verts = [v for vert in self.vertices for attr in vert.attributes for v in attr.value]

        nbt = NBTTagCompound()
        nbt['id'] = NBTTagString(self.id)
        nbt['attributes'] = NBTTagList(NBTTagString, [NBTTagString(it) for it in attr_names])
        nbt['vertices'] = NBTTagFloatArray(verts)
        nbt['parts'] = NBTTagList(NBTTagCompound, [it.packNBT() for it in self.parts])
        return nbt

    def __repr__(self):
        value = "VERTICES:\n{!r}\n\nPARTS:\n{!r}\n\n".format(self.vertices, self.parts)
        return value

# end Mesh

class MeshPart(NBTSerializable):
    __slots__ = ('id', 'type', 'indices', 'parentMesh', 'maxIndex')

    def __init__(self, id="", type="TRIANGLES", indices=None, parentMesh=None):
        self.id = id
        self.type = type
        self.indices = indices
        self.parentMesh = parentMesh
        self.maxIndex = 0

    def addIndex(self, value):
        if self.indices is None:
            self.indices = []
        self.indices.append(value)
        if value > self.maxIndex:
            self.maxIndex = value

    def packNBT(self):
        nbt = NBTTagCompound()
        nbt['id'] = NBTTagString(self.id)
        nbt['type'] = NBTTagString(self.type)
        if self.indices is not None:
            if self.maxIndex >= 1 << 16:
                nbt['indices'] = NBTTagIntArray(self.indices)
            else:
                nbt['indices'] = NBTTagUShortArray(self.indices)
        return nbt

    def __repr__(self):
        reprStr = r"{" + "\n    ID: {!s}\n    TYPE: {!s}\n".format(self.id, self.type)
        if self.parentMesh is not None and self.indices is not None:
            reprStr = reprStr + ("    TOTAL INDICES: {:d}\n    VERTICES: [\n".format(len(self.indices)))
            for ver in self.indices:
                reprStr = reprStr + ("        {!r}\n".format(ver))
            reprStr = reprStr + "    ]\n"
        reprStr = reprStr + "}\n"
        return reprStr

# end MeshPart

class Node(NBTSerializable):
    __slots__ = ('id', 'translation', 'rotation', 'scale', 'parts', 'children')

    def __init__(self):
        self.id = ""
        self.translation = None
        self.rotation = None
        self.scale = None
        self.parts = None
        self.children = None

    def addPart(self, value):
        if self.parts is None:
            self.parts = []
        self.parts.append(value)

    def addChild(self, value):
        if self.children is None:
            self.children = []
        self.children.append(value)

    def packNBT(self):
        transform = []
        transform.extend(self.translation if self.translation != None else [0.0, 0.0, 0.0])
        transform.extend(self.rotation if self.rotation != None else [0.0, 0.0, 0.0, 1.0])
        transform.extend(self.scale if self.scale != None else [1.0, 1.0, 1.0])

        nbt = NBTTagCompound()
        nbt['id'] = NBTTagString(self.id)
        nbt['transform'] = NBTTagFloatArray(transform)
        if self.parts is not None:
            nbt['parts'] = NBTTagList(NBTTagCompound, [it.packNBT() for it in self.parts])
        if self.children is not None:
            nbt['children'] = NBTTagList(NBTTagCompound, [it.packNBT() for it in self.children])
        return nbt

# end Node

class NodePart(NBTSerializable):
    __slots__ = ('meshPartId', 'materialId', 'bones')

    def __init__(self):
        self.meshPartId = ""
        self.materialId = ""
        self.bones = None

    def addBone(self, value):
        if self.bones is None:
            self.bones = []
        self.bones.append(value)

    def packNBT(self):
        nbt = NBTTagCompound()
        nbt['meshPartId'] = NBTTagString(self.meshPartId)
        nbt['materialId'] = NBTTagString(self.materialId)
        if self.bones is not None:
            nbt['bones'] = NBTTagList(NBTTagCompound, [it.packNBT() for it in self.bones])
        return nbt

# end NodePart

class Bone(NBTSerializable):
    __slots__ = ('node', 'translation', 'rotation', 'scale')

    def __init__(self):
        self.node = ""
        self.translation = None
        self.rotation = None
        self.scale = None

    def packNBT(self):
        transform = []
        transform.extend(self.translation if self.translation != None else [0.0, 0.0, 0.0])
        transform.extend(self.rotation if self.rotation != None else [0.0, 0.0, 0.0, 1.0])
        transform.extend(self.scale if self.scale != None else [1.0, 1.0, 1.0])

        nbt = NBTTagCompound()
        nbt['node'] = NBTTagString(self.node)
        nbt['transform'] = NBTTagFloatArray(transform)
        return nbt

# end Bone

class Texture(NBTSerializable):
    __slots__ = ('id', 'filename', 'type')

    def __init__(self, id="", filename="", type=""):
        self.id = id
        self.filename = filename
        self.type = type

    def packNBT(self):
        nbt = NBTTagCompound()
        nbt['id'] = NBTTagString(self.id)
        nbt['fileName'] = NBTTagString(self.filename)
        nbt['type'] = NBTTagString(self.type)
        return nbt

# end Texture

class Material(NBTSerializable):
    __slots__ = ('id', 'properties', 'textures')

    def __init__(self):
        self.id = ""
        self.properties = {}
        self.textures = []

    def setProperty(self, name, value):
        self.properties[name] = value

    def packNBT(self):
        nbt = NBTTagCompound()
        nbt['id'] = NBTTagString(self.id)

        for k, v in self.properties.items():
            nbt[k] = NBTTagFloatArray(v)

        nbt['textures'] = NBTTagList(NBTTagCompound, [it.packNBT() for it in self.textures])
        return nbt

# end Material

class Animation(NBTSerializable):
    __slots__ = ('id', 'time', 'bones')

    def __init__(self):
        self.id = ""
        self.time = 0.0
        self.bones = None

    def addBone(self, value):
        if self.bones is None:
            self.bones = []
        self.bones.append(value)

    def packNBT(self):
        nbt = NBTTagCompound()
        nbt['id'] = NBTTagString(self.id)
        nbt['time'] = NBTTagFloat(self.time)
        if self.bones is not None:
            nbt['bones'] = NBTTagList(NBTTagCompound, [it.packNBT() for it in self.bones])
        return nbt

# end Animation

class NodeAnimation(NBTSerializable):
    __slots__ = ('boneId', 'keyframes', 'translation', 'rotation', 'scaling')

    def __init__(self):
        self.boneId = ""
        self.keyframes = None
        self.translation = None
        self.rotation = None
        self.scaling = None

    def addKeyframe(self, value):
        if self.keyframes is None:
            self.keyframes = []
        self.keyframes.append(value)

    def addTranslation(self, value):
        if self.translation is None:
            self.translation = []
        self.translation.append(value)

    def addRotation(self, value):
        if self.rotation is None:
            self.rotation = []
        self.rotation.append(value)

    def addScaling(self, value):
        if self.scaling is None:
            self.scaling = []
        self.scaling.append(value)

    def packNBT(self):
        nbt = NBTTagCompound()
        nbt['boneId'] = NBTTagString(self.boneId)
        if self.keyframes is not None:
            nbt['keyFrames'] = NBTTagList(NBTTagFloatArray, [it.packNBT() for it in self.keyframes])
        if self.translation is not None:
            nbt['translation'] = NBTTagList(NBTTagFloatArray, [it.packNBT() for it in self.translation])
        if self.rotation is not None:
            nbt['rotation'] = NBTTagList(NBTTagFloatArray, [it.packNBT() for it in self.rotation])
        if self.scaling is not None:
            nbt['scaling'] = NBTTagList(NBTTagFloatArray, [it.packNBT() for it in self.scaling])
        return nbt

# end NodeAnimation

class Keyframe(NBTSerializable):
    __slots__ = ('keytime', 'translation', 'rotation', 'scaling')

    def __init__(self):
        self.keytime = 0.0
        self.translation = None
        self.rotation = None
        self.scaling = None

    def createSeparateTranslation(self):
        return KeyframeSeparate(self.keytime, self.translation)

    def createSeparateRotation(self):
        return KeyframeSeparate(self.keytime, self.rotation)

    def createSeparateScaling(self):
        return KeyframeSeparate(self.keytime, self.scale)

    def packNBT(self):
        list = [self.keytime]
        list.extend(self.translation if self.translation is not None else [0.0, 0.0, 0.0])
        list.extend(self.rotation if self.rotation is not None else [0.0, 0.0, 0.0, 1.0])
        list.extend(self.scaling if self.scaling is not None else [1.0, 1.0, 1.0])
        return NBTTagFloatArray(list)

# end Keyframe

class KeyframeSeparate(NBTSerializable):
    __slots__ = ('keytime', 'value')

    def __init__(self, keytime=0.0, value=None):
        self.keytime = keytime
        self.value = value

    def packNBT(self):
        list = [self.keytime]
        list.extend(self.value)
        return NBTTagFloatArray(list)

# end KeyframeSeparate
