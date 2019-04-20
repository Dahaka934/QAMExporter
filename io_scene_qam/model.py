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
    NBTTagUShortArray
)

__all__ = (
    'QamModel', 'VertexAttributes', 'VertexAttribute',
    'Vertex', 'Mesh', 'MeshPart', 'Node', 'NodePart', 'BoundBox', 'Bone', 'Texture',
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

class VertexAttributeType:
    __slots__ = ('name')

    def __init__(self):
        self.name = None

    def init(self, list, obj):
        list.append(self.name)

class VertexAttributeVectorF(VertexAttributeType):
    def __init__(self, name):
        self.name = name

class VertexAttributeBoneIndices(VertexAttributeType):
    def __init__(self, name):
        self.name = name

    def init(self, list, obj):
        count = len(obj.value)
        for i in range(count):
            list.append(self.name + str(i))

class VertexAttributeBoneWeights(VertexAttributeType):
    def __init__(self, name):
        self.name = name

    def init(self, list, obj):
        idx = 0
        count = len(obj.value)
        while count > 0:
            list.append('{}{}{}'.format(self.name, idx, min(count, 4)))
            idx += 1
            count -= 4

class VertexAttributes(object):
    POSITION = 10
    NORMAL = 20
    TANGENT = 30
    BINORMAL = 40
    COLOR = 50
    TEXCOORD0 = 60
    TEXCOORD1 = 61
    TEXCOORD2 = 62
    TEXCOORD3 = 63
    TEXCOORD4 = 64
    TEXCOORD5 = 65
    TEXCOORD6 = 66
    TEXCOORD7 = 67
    TEXCOORD8 = 68
    TEXCOORD9 = 69
    BONEINDICES = 70
    BONEWEIGHTS = 80

    ATTRIBUTE_MAP = {}
    ATTRIBUTE_MAP[POSITION] = VertexAttributeVectorF('POSITION')
    ATTRIBUTE_MAP[NORMAL] = VertexAttributeVectorF('NORMAL')
    ATTRIBUTE_MAP[TANGENT] = VertexAttributeVectorF('TANGENT')
    ATTRIBUTE_MAP[BINORMAL] = VertexAttributeVectorF('BINORMAL')
    ATTRIBUTE_MAP[COLOR] = VertexAttributeVectorF('COLOR')
    ATTRIBUTE_MAP[TEXCOORD0] = VertexAttributeVectorF('TEXCOORD0')
    ATTRIBUTE_MAP[TEXCOORD1] = VertexAttributeVectorF('TEXCOORD1')
    ATTRIBUTE_MAP[TEXCOORD2] = VertexAttributeVectorF('TEXCOORD2')
    ATTRIBUTE_MAP[TEXCOORD3] = VertexAttributeVectorF('TEXCOORD3')
    ATTRIBUTE_MAP[TEXCOORD4] = VertexAttributeVectorF('TEXCOORD4')
    ATTRIBUTE_MAP[TEXCOORD5] = VertexAttributeVectorF('TEXCOORD5')
    ATTRIBUTE_MAP[TEXCOORD6] = VertexAttributeVectorF('TEXCOORD6')
    ATTRIBUTE_MAP[TEXCOORD7] = VertexAttributeVectorF('TEXCOORD7')
    ATTRIBUTE_MAP[TEXCOORD8] = VertexAttributeVectorF('TEXCOORD8')
    ATTRIBUTE_MAP[TEXCOORD9] = VertexAttributeVectorF('TEXCOORD9')
    ATTRIBUTE_MAP[BONEINDICES] = VertexAttributeBoneIndices('BONEINDICES')
    ATTRIBUTE_MAP[BONEWEIGHTS] = VertexAttributeBoneWeights('BONEWEIGHTS')

    @staticmethod
    def of(type):
        return VertexAttributes.ATTRIBUTE_MAP[type]

    @staticmethod
    def name(type):
        return VertexAttributes.ATTRIBUTE_MAP[type].name

    @staticmethod
    def isTexCoord(type):
        return VertexAttributes.TEXCOORD0 <= type and type <= VertexAttributes.TEXCOORD9

# end VertexAttributes

class VertexAttribute(NBTSerializable):
    __slots__ = ('type', 'value', 'hashCache')

    def __init__(self, type, value):
        self.type = type
        self.value = value
        self.limitPrecision()
        self.hashCache = None

    def markDirty(self):
        self.hashCache = None

    @profile('limitPrecision', 3)
    def limitPrecision(self):
        utils.limitFloatListPrecision(self.value)
        self.markDirty()

    @profile('hashVertexAttribute', 3)
    def __hash__(self):
        if self.hashCache is None:
            self.hashCache = self.type
            self.hashCache = 81 * self.hashCache + utils.hashList(self.value)
        return self.hashCache

    @profile('eqVertexAttribute', 3)
    def __eq__(self, another):
        """Compare this attribute with another for value"""
        if another is None or not isinstance(another, VertexAttribute):
            return False

        if self.type != another.type:
            return False

        if len(self.value) != len(another.value):
            return False

        for pos in range(0, len(self.value)):
            if self.value[pos] != another.value[pos]:
                return False

        return True

    def __ne__(self, another):
        return not self.__eq__(another)

    def __repr__(self):
        value = "{!s} {!r}".format(VertexAttributes.name(self.type), self.value)
        return value

# end VertexAttribute

class Vertex(NBTSerializable):
    __slots__ = ('attributes', 'attrBoneIndices', 'attrBoneWeights', 'hashCache')

    def __init__(self):
        self.attributes = []
        self.attrBoneIndices = None
        self.attrBoneWeights = None
        self.hashCache = None

    def markDirty(self):
        self.hashCache = None

    def add(self, attribute):
        self.attributes.append(attribute)

    def addBlendWeight(self, idx, weight, max_bones):
        if self.attrBoneIndices is None:
            self.attrBoneIndices = VertexAttribute(VertexAttributes.BONEINDICES, [])
            self.attrBoneWeights = VertexAttribute(VertexAttributes.BONEWEIGHTS, [weight])
            self.attrBoneIndices.value.append(int(idx))
            self.attributes.append(self.attrBoneIndices)
            self.attributes.append(self.attrBoneWeights)
        else:
            idx = utils.binaryInsert(self.attrBoneWeights.value, weight)
            self.attrBoneIndices.value.insert(idx, int(idx))
            if len(self.attrBoneWeights.value) > max_bones:
                self.attrBoneWeights.value.pop()
                self.attrBoneIndices.value.pop()

    @profile('normalizeBlendWeight', 2)
    def normalizeBlendWeight(self, mod):
        if self.attributes is None or self.attrBoneIndices is None:
            return

        blendWeightSum = 0.0
        for i in range(len(self.attrBoneWeights.value)):
            blendWeightSum = blendWeightSum + self.attrBoneWeights.value[i]

        for i in range(len(self.attrBoneWeights.value)):
           self.attrBoneWeights.value[i] /= blendWeightSum

        addit = len(self.attrBoneWeights.value)
        addit = ((addit - 1) // mod * mod) + mod
        addit -= len(self.attrBoneWeights.value)
        while addit > 0:
            self.attrBoneIndices.value.append(0)
            self.attrBoneWeights.value.append(0.0)
            addit -= 1

        self.attrBoneWeights.limitPrecision()
        self.markDirty()

    @profile('hashVertex', 3)
    def __hash__(self):
        if self.hashCache is None:
            self.hashCache = utils.hashList(self.attributes)
        return self.hashCache

    @profile('eqVertex', 3)
    def __eq__(self, another):
        if another is None or not isinstance(another, Vertex):
            raise TypeError("'another' must be a Vertex")
        return hash(self) == hash(another)

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

    @profile('addVertex', 2)
    def addVertex(self, vertex):
        vertexHash = hash(vertex)
        idx = self.vertexIndices.get(vertexHash, -1)
        if idx < 0:
            self.vertices.append(vertex)
            idx = len(self.vertices) - 1
            self.vertexIndices[vertexHash] = idx
        return idx

    def addPart(self, meshPart):
        self.parts.append(meshPart)
        meshPart.parentMesh = self

    @profile('normalizeAttributes', 2)
    def normalizeAttributes(self):
        if len(self.vertices) > 0:
           self.attributes = [it.type for it in self.vertices[0].attributes]

        attrColorInx = -1
        for i in range(len(self.attributes)):
            if self.attributes[i] == VertexAttributes.COLOR:
                attrColorInx = i

        bonesCount = 0
        for it in self.vertices:
            if it.attrBoneWeights is not None and bonesCount < len(it.attrBoneWeights.value):
                bonesCount = len(it.attrBoneWeights.value)

        if bonesCount > 0:
            indicesCount = ((bonesCount - 1) >> 2 << 2) + 4
            indicesFmtPack = '>{}B'.format(indicesCount)
            indicesFmtUnpack = '>{}f'.format(indicesCount // 4)

            for vert in self.vertices:
                for i in range(bonesCount - len(vert.attrBoneIndices.value)):
                    vert.attrBoneIndices.value.append(0)
                    vert.attrBoneWeights.value.append(0.0)
                for i in range(indicesCount - len(vert.attrBoneIndices.value)):
                    vert.attrBoneIndices.value.append(0)

                tmp = struct.pack(indicesFmtPack, *vert.attrBoneIndices.value)
                vert.attrBoneIndices.value = struct.unpack(indicesFmtUnpack, tmp)

        if attrColorInx >= 0:
            for vert in self.vertices:
                attr = vert.attributes[attrColorInx]
                tmp = struct.pack('>4B', *[int(it * 255) for it in attr.value])
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
        transform.extend(self.rotation if self.rotation != None else [1.0, 0.0, 0.0, 0.0])
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
    __slots__ = ('meshPartId', 'materialId', 'bones', 'bound_box')

    def __init__(self):
        self.meshPartId = ""
        self.materialId = ""
        self.bones = None
        self.bound_box = None

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
        if self.bound_box is not None:
            nbt['boundBox'] = self.bound_box.packNBT()
        return nbt

# end NodePart

class BoundBox(NBTSerializable):
    __slots__ = ('values')

    def __init__(self, values):
        self.values = values

    def packNBT(self):
        return NBTTagList(NBTTagFloatArray, [NBTTagFloatArray(it) for it in self.values])

# end BoundBox

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
        transform.extend(self.rotation if self.rotation != None else [1.0, 0.0, 0.0, 0.0])
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
        list.extend(self.rotation if self.rotation is not None else [1.0, 0.0, 0.0, 0.0])
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
