from math import fabs, isclose
import struct

# Global rounding factor for floats
FROUND = 6
FROUND_FMT = "{:" + str(FROUND + 3) + "." + str(FROUND) + "f}"
FROUND_VALUE = 1 / pow(10, 6)

_DEBUG_ = 4
_INFO_ = 3
_WARN_ = 2
_ERROR_ = 1

LOG_LEVEL = _INFO_

def limitFloatPrecision(floatNumber):
    return float(round(floatNumber, FROUND))

def limitFloatListPrecision(listOfFloats):
    for i in range(0, len(listOfFloats)):
        listOfFloats[i] = float(round(listOfFloats[i], FROUND))
    return listOfFloats

def hashList(list):
    out = 0
    if list is not None:
        for i in range(0, len(list)):
            out = 31 * out + hash(list[i])
    return out

def eq(v1, v2):
    return abs(v1 - v2) <= 0.000001

def is0(v):
    return eq(v, 0.0)

def is1(v):
    return eq(v, 1.0)

def testDefaultQuaternion(vec):
    return vec is None \
        or (is1(vec[0]) and is0(vec[1]) and is0(vec[2]) and is0(vec[3]))

def testDefaultScale(vec):
    return vec is None \
        or (is1(vec[0]) and is1(vec[1]) and is1(vec[2]))

def testDefaultTransform(vec):
    return vec is None \
        or (is0(vec[0]) and is0(vec[1]) and is0(vec[2]))

def bitsToFloat(b):
    s = struct.pack('>I', b)
    return struct.unpack('>f', s)[0]

def floatToBits(f):
    s = struct.pack('>f', f)
    return struct.unpack('>I', s)[0]

def wrapFloat4(v1, v2, v3, v4):
    b = ((int(v1 * 255.0) & 255) << 24) | \
        ((int(v2 * 255.0) & 255) << 16) | \
        ((int(v3 * 255.0) & 255) << 8) | \
        ((int(v4 * 255.0) & 255) << 0)
    return bitsToFloat(b)

def unwrapFloat4(v):
    b = floatToBits(v)
    return ((b >> 24) & 255) / 255.0, \
           ((b >> 16) & 255) / 255.0, \
           ((b >> 8) & 255) / 255.0, \
           ((b >> 0) & 255) / 255.0

# ## DEBUG METHODS ###
def debug(message, *args):
    if LOG_LEVEL >= _DEBUG_:
        finalMessage = message.format(*args)
        print("[DEBUG] {!s}".format(finalMessage))

def info(message, *args):
    if LOG_LEVEL >= _INFO_:
        finalMessage = message.format(*args)
        print("[INFO] {!s}".format(finalMessage))

def warn(message, *args):
    if LOG_LEVEL >= _WARN_:
        finalMessage = message.format(*args)
        print("[WARN] {!s}".format(finalMessage))

def error(message, *args):
    if LOG_LEVEL >= _ERROR_:
        finalMessage = message.format(*args)
        print("[ERROR] {!s}".format(finalMessage))

def infoCaps(message, *args):
    if LOG_LEVEL >= _INFO_:
        finalMessage = message.format(*args).upper()
        print("")
        print("[INFO] {!s}".format(finalMessage))

def binaryInsert(list, item):
    low = 0
    high = len(list) - 1
    while low <= high:
        mid = (low + high) // 2
        midValue = list[mid]
        cmp = midValue - item

        if cmp < 0:
            low = mid + 1
        elif cmp > 0:
            high = mid - 1
        else:
            low = mid
            break
    list.insert(low, item)
    return low
