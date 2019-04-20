#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Implements reading & writing for the Minecraft Named Binary Tag (NBT) format,
created by Markus Petersson.

.. moduleauthor:: Tyler Kennedy <tk@tkte.ch>
"""
__all__ = (
    'NBTFile', 'NBTTagByte', 'NBTTagShort', 'NBTTagInt', 'NBTTagLong', 'NBTTagFloat',
    'NBTTagDouble', 'NBTTagByteArray', 'NBTTagString', 'NBTTagList', 'NBTTagCompound',
    'NBTTagIntArray', 'NBTTagLongArray', 'NBTTagShortArray', 'NBTTagFloatArray'
)

from struct import unpack, pack

class NBTType:
    END             = 0x00
    BYTE            = 0x01
    SHORT           = 0x02
    INT             = 0x03
    LONG            = 0x04
    FLOAT           = 0x05
    DOUBLE          = 0x06
    BYTE_ARRAY      = 0x07
    STRING          = 0x08
    LIST            = 0x09
    COMPOUND        = 0x0A
    INT_ARRAY       = 0x0B
    LONG_ARRAY      = 0x0C
    SHORT_ARRAY     = 0x0D
    FLOAT_ARRAY     = 0x0E


class NBTBase(object):
    def __init__(self, value, name=None):
        self.value = value

    @property
    def fmt(self): return ''

    @classmethod
    def type(cls): return NBTType.END

    @staticmethod
    def _read_utf8(read):
        """Reads a length-prefixed UTF-8 string."""
        name_length = read('h', 2)[0]
        return read.io.read(name_length).decode('utf-8')

    @staticmethod
    def _write_utf8(write, value):
        """Writes a length-prefixed UTF-8 string."""
        write('h', len(value))
        write.io.write(value.encode('utf-8'))

    @classmethod
    def read(cls, read):
        return None

    def write(self, write):
        write(self.fmt, self.value)

    def pretty(self, indent_rest=0, indent_str='  '):
        return repr(self)

    def __repr__(self):
        return '{}({!r})'.format(self.__class__.__name__, self.value)

    def __str__(self):
        return repr(self)

    def __unicode__(self):
        return unicode(repr(self), 'utf-8')

class NBTTagByte(NBTBase):
    __slots__ = ('value')

    @classmethod
    def type(cls): return NBTType.BYTE

    @property
    def fmt(self): return 'b'

    @classmethod
    def read(cls, read): return cls(read('b', 1)[0])

    def pretty(self, indent_rest=0, indent_str='  '):
        return '{}B'.format(self.value)

class NBTTagShort(NBTBase):
    __slots__ = ('value')

    @classmethod
    def type(cls): return NBTType.SHORT

    @property
    def fmt(self): return 'h'

    @classmethod
    def read(cls, read): return cls(read('h', 2)[0])

    def pretty(self, indent_rest=0, indent_str='  '):
        return '{}S'.format(self.value)

class NBTTagInt(NBTBase):
    __slots__ = ('value')

    @classmethod
    def type(cls): return NBTType.INT

    @property
    def fmt(self): return 'i'

    @classmethod
    def read(cls, read): return cls(read('i', 4)[0])

class NBTTagLong(NBTBase):
    __slots__ = ('value')

    @classmethod
    def type(cls): return NBTType.LONG

    @property
    def fmt(self): return 'q'

    @classmethod
    def read(cls, read): return cls(read('q', 8)[0])

    def pretty(self, indent_rest=0, indent_str='  '):
        return '{}L'.format(self.value)

class NBTTagFloat(NBTBase):
    __slots__ = ('value')

    @classmethod
    def type(cls): return NBTType.FLOAT

    @property
    def fmt(self): return 'f'

    @classmethod
    def read(cls, read): return cls(read('f', 4)[0])

    def pretty(self, indent_rest=0, indent_str='  '):
        return '{}F'.format(self.value)

class NBTTagDouble(NBTBase):
    __slots__ = ('value')

    @classmethod
    def type(cls): return NBTType.DOUBLE

    @property
    def fmt(self): return 'd'

    @classmethod
    def read(cls, read): return cls(read('d', 8)[0])

    def pretty(self, indent_rest=0, indent_str='  '):
        return '{}D'.format(self.value)

class NBTTagString(NBTBase):
    __slots__ = ('value')

    @classmethod
    def type(cls): return NBTType.STRING

    def write(self, write):
        self._write_utf8(write, self.value)

    @classmethod
    def read(cls, read): return cls(cls._read_utf8(read))

    def pretty(self, indent_rest=0, indent_str='  '):
        return '\'{}\''.format(self.value)

class NBTTagEnd(NBTBase):
    __slots__ = ('value')

    @classmethod
    def read(cls, read): return cls(read('2b', 2)[0])

class NBTTagCompound(NBTBase, dict):
    @classmethod
    def type(cls): return NBTType.COMPOUND

    def __init__(self, value=None):
        self.value = self
        if value is not None:
            self.update(value)

    def write(self, write):
        for k, v in self.value.items():
            write('b', v.__class__.type())
            self._write_utf8(write, k)
            v.write(write)
        # A tag of type 0 (TAg_End) terminates a NBTTagCompound.
        write('b', 0)

    @classmethod
    def read(cls, read):
        # A NBTTagCompound is almost identical to Python's native dict()
        # object, or a Java HashMap.
        final = {}
        while True:
            # Find the type of each tag in a compound in turn.
            tag = read('b', 1)[0]
            if tag == 0:
                # A tag of 0 means we've reached NBTTagEnd, used to terminate
                # a NBTTagCompound.
                break
            # We read in each tag in turn, using its name as the key in
            # the dict (Since a compound cannot have repeating names,
            # this works fine).
            name = cls._read_utf8(read)
            final[name] = _tags[tag].read(read)
        return cls(final)

    def pretty(self, rest_indent=0, indent_str='  '):
        t = []
        if len(self.value) > 0:
            t.append('{{ {} entries'.format(len(self.value)))
            for k, v in self.items():
                it_pretty = v.pretty(rest_indent + 1, indent_str)
                t.append('{}{}: {}'.format(indent_str * (rest_indent + 1), k, it_pretty))
            t.append('{}}}'.format(indent_str * rest_indent))
        else:
            t.append('{}')
        return '\n'.join(t)

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, len(self))

    def __setitem__(self, key, value):
        super(NBTTagCompound, self).__setitem__(key, value)

    def update(self, *args, **kwargs):
        super(NBTTagCompound, self).update(*args, **kwargs)

class NBTTagList(NBTBase, list):
    @classmethod
    def type(cls): return NBTType.LIST

    def __init__(self, type, value=None):
        """
        Creates a new homogeneous list of `type` items, copying `value`
        if provided.
        """
        self.value = self
        self.type = type
        if value is not None:
            self.extend(value)

    def write(self, write):
        write('bi', self.type.type(), len(self.value))
        for item in self.value:
            # If our list item isn't of type self._type, convert
            # it before writing.
            if not isinstance(item, self.type):
                item = self.type(item)
            item.write(write)

    @classmethod
    def read(cls, read):
        # A NBTTagList is a very simple homogeneous array, similar to
        # Python's native list() object, but restricted to a single type.
        tag_type, length = read('bi', 5)
        tag_read = _tags[tag_type].read
        return cls(
            _tags[tag_type],
            [tag_read(read) for x in range(0, length)]
        )

    def pretty(self, rest_indent=0, indent_str='  '):
        t = []
        if len(self.value) > 0:
            t.append('[ {} entries'.format(len(self.value)))
            for v in self.value:
                it_pretty = v.pretty(rest_indent + 1, indent_str)
                t.append('{}{}'.format(indent_str * (rest_indent + 1), it_pretty))
            t.append('{}]'.format(indent_str * rest_indent))
        else:
            t.append('[]')
        return '\n'.join(t)

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, len(self))

class NBTTagArray(NBTBase):
    __slots__ = ('value')

    @property
    def fmt(self): return ''

    def write(self, write):
        l = len(self.value)
        write(self.fmt.format(l), l, *self.value)

    def pretty(self, rest_indent=0, indent_str='  '):
        if len(self.value) <= 11:
            return '{} {}'.format(self.__class__.__name__, list(self.value))
        else:
            return '{} [ {} elements ]'.format(self.__class__.__name__, len(self.value))

class NBTTagByteArray(NBTTagArray):
    @property
    def fmt(self): return 'i{0}b'

    @classmethod
    def type(cls): return NBTType.BYTE_ARRAY

    @classmethod
    def read(cls, read):
        length = read('i', 4)[0]
        return cls(read('{0}b'.format(length), length))

class NBTTagIntArray(NBTTagArray):
    @property
    def fmt(self): return 'i{0}i'

    @classmethod
    def type(cls): return NBTType.INT_ARRAY

    @classmethod
    def read(cls, read):
        length = read('i', 4)[0]
        return cls(read('{0}i'.format(length), length * 4))

class NBTTagLongArray(NBTTagArray):
    @property
    def fmt(self): return 'i{0}q'

    @classmethod
    def type(cls): return NBTType.LONG_ARRAY

    @classmethod
    def read(cls, read):
        length = read('i', 4)[0]
        return cls(read('{0}q'.format(length), length * 8))

class NBTTagShortArray(NBTTagArray):
    @property
    def fmt(self): return 'i{0}h'

    @classmethod
    def type(cls): return NBTType.SHORT_ARRAY

    @classmethod
    def read(cls, read):
        length = read('i', 4)[0]
        return cls(read('{0}h'.format(length), length * 2))

class NBTTagFloatArray(NBTTagArray):
    @property
    def fmt(self): return 'i{0}f'

    @classmethod
    def type(cls): return NBTType.FLOAT_ARRAY

    @classmethod
    def read(cls, read):
        length = read('i', 4)[0]
        return cls(read('{0}f'.format(length), length * 4))

class NBTTagUShortArray(NBTTagShortArray):
    @property
    def fmt(self): return 'i{0}H'

# The NBTTag* types have the convienient property of being continuous.
# The code is written in such a way that if this were to no longer be
# true in the future, _tags can simply be replaced with a dict().
_tags = (
    NBTTagEnd,         # 0x00
    NBTTagByte,        # 0x01
    NBTTagShort,       # 0x02
    NBTTagInt,         # 0x03
    NBTTagLong,        # 0x04
    NBTTagFloat,       # 0x05
    NBTTagDouble,      # 0x06
    NBTTagByteArray,   # 0x07
    NBTTagString,      # 0x08
    NBTTagList,        # 0x09
    NBTTagCompound,    # 0x0A
    NBTTagIntArray,    # 0x0B
    NBTTagLongArray,   # 0x0C
    NBTTagShortArray,  # 0x0D
    NBTTagFloatArray   # 0x0E
)


class NBTFile(NBTTagCompound):
    def __init__(self, io=None, value=None, little_endian=False):
        """
        Creates a new NBTFile or loads one from any file-like object providing
        `read()`.

        Whereas loading an existing one is most often done:
        with open('my_file.nbt', 'rb') as io:
        ...     nbt = NBTFile(io=io)
        """
        # No file or path given, so we're creating a new NBTFile.
        if io is None:
            super(NBTFile, self).__init__(value if value else {})
            return

        # The pocket edition uses little-endian NBT files, but annoyingly
        # without any kind of header we can't determine that ourselves,
        # not even a magic number we could flip.
        if little_endian:
            read = lambda fmt, size: unpack('<' + fmt, io.read(size))
        else:
            read = lambda fmt, size: unpack('>' + fmt, io.read(size))
        read.io = io

        # All valid NBT files will begin with 0x0A, which is a NBTTagCompound.
        if read('b', 1)[0] != 0x0A:
            raise IOError('NBTFile does not begin with 0x0A.')
        NBTTagCompound._read_utf8(read)

        tmp = NBTTagCompound.read(read)
        super(NBTFile, self).__init__(tmp)

    def save(self, io, little_endian=False):
        """
        Saves the `NBTFile()` to `io`, which can be any file-like object
        providing `write()`.
        """
        if little_endian:
            write = lambda fmt, *args: io.write(pack('<' + fmt, *args))
        else:
            write = lambda fmt, *args: io.write(pack('>' + fmt, *args))
        write.io = io

        self.write(write)

    def write(self, write):
        write('b', 0x0A)
        self._write_utf8(write, 'qwe')
        super().write(write)


class NBTSerializable:

    def packNBT(self):
        return NBTTagString('empty')


def test():
    nbt = NBTFile(value={
        'test_long': NBTTagLong(104005),
        # 'test_compaund': NBTTagCompound({
        #     'float': NBTTagFloat(1.0)
        # }),
        'test_list': NBTTagList(NBTTagString, [
            NBTTagString('Timmy')
        ]),
        # 'test_short_array': NBTTagUShortArray([0xffff, 2]),
        'empty_compaund': NBTTagCompound(),
        'empty_list': NBTTagList(NBTTagString)
    })

    with open('out.nbt', 'wb') as io:
        nbt.save(io)

    with open('out.nbt', 'rb') as io:
        nbt = NBTFile(io)
        print(nbt.pretty())

    import gzip
    with gzip.open('out.nbt.gz', 'wb') as io:
        nbt.save(io)
