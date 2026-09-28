"""Minimal, dependency-free MessagePack codec.

The Aos service runs on the unit's system Python with the standard library
only, so the PyPI ``msgpack`` package is not available. This module covers
the subset of the format used by AirSim's msgpack-RPC: nil, bool, int,
float (32/64), str, bin, array and map.
"""

import struct

__all__ = ["packb", "unpackb", "Unpacker", "OutOfData"]


class OutOfData(Exception):
    """Raised when the buffer does not yet contain a complete object."""


# --------------------------------------------------------------------------
# Packing
# --------------------------------------------------------------------------

def packb(obj):
    """Serialise ``obj`` to MessagePack bytes."""
    out = bytearray()
    _pack(obj, out)
    return bytes(out)


def _pack(obj, out):
    if obj is None:
        out.append(0xC0)
    elif obj is True:
        out.append(0xC3)
    elif obj is False:
        out.append(0xC2)
    elif isinstance(obj, int):
        _pack_int(obj, out)
    elif isinstance(obj, float):
        out.append(0xCB)
        out += struct.pack(">d", obj)
    elif isinstance(obj, str):
        data = obj.encode("utf-8")
        n = len(data)
        if n < 32:
            out.append(0xA0 | n)
        elif n < 0x100:
            out += bytes((0xD9, n))
        elif n < 0x10000:
            out.append(0xDA)
            out += struct.pack(">H", n)
        else:
            out.append(0xDB)
            out += struct.pack(">I", n)
        out += data
    elif isinstance(obj, (bytes, bytearray)):
        n = len(obj)
        if n < 0x100:
            out += bytes((0xC4, n))
        elif n < 0x10000:
            out.append(0xC5)
            out += struct.pack(">H", n)
        else:
            out.append(0xC6)
            out += struct.pack(">I", n)
        out += obj
    elif isinstance(obj, (list, tuple)):
        n = len(obj)
        if n < 16:
            out.append(0x90 | n)
        elif n < 0x10000:
            out.append(0xDC)
            out += struct.pack(">H", n)
        else:
            out.append(0xDD)
            out += struct.pack(">I", n)
        for item in obj:
            _pack(item, out)
    elif isinstance(obj, dict):
        n = len(obj)
        if n < 16:
            out.append(0x80 | n)
        elif n < 0x10000:
            out.append(0xDE)
            out += struct.pack(">H", n)
        else:
            out.append(0xDF)
            out += struct.pack(">I", n)
        for key, value in obj.items():
            _pack(key, out)
            _pack(value, out)
    else:
        raise TypeError("msgpack_lite cannot serialise %r" % type(obj))


def _pack_int(n, out):
    if 0 <= n < 0x80:
        out.append(n)
    elif -32 <= n < 0:
        out.append(n & 0xFF)
    elif 0 <= n < 0x100:
        out += bytes((0xCC, n))
    elif 0 <= n < 0x10000:
        out.append(0xCD)
        out += struct.pack(">H", n)
    elif 0 <= n < 0x100000000:
        out.append(0xCE)
        out += struct.pack(">I", n)
    elif 0 <= n < 0x10000000000000000:
        out.append(0xCF)
        out += struct.pack(">Q", n)
    elif -0x80 <= n < 0:
        out.append(0xD0)
        out += struct.pack(">b", n)
    elif -0x8000 <= n < 0:
        out.append(0xD1)
        out += struct.pack(">h", n)
    elif -0x80000000 <= n < 0:
        out.append(0xD2)
        out += struct.pack(">i", n)
    elif -0x8000000000000000 <= n < 0:
        out.append(0xD3)
        out += struct.pack(">q", n)
    else:
        raise OverflowError("integer out of msgpack range: %d" % n)


# --------------------------------------------------------------------------
# Unpacking
# --------------------------------------------------------------------------

_FIXED = {
    0xCC: (">B", 1), 0xCD: (">H", 2), 0xCE: (">I", 4), 0xCF: (">Q", 8),
    0xD0: (">b", 1), 0xD1: (">h", 2), 0xD2: (">i", 4), 0xD3: (">q", 8),
    0xCA: (">f", 4), 0xCB: (">d", 8),
}


def unpackb(data):
    """Deserialise exactly one object from ``data``."""
    obj, end = _unpack(memoryview(data), 0)
    if end != len(data):
        raise ValueError("extra bytes after msgpack object")
    return obj


def _need(buf, pos, n):
    if pos + n > len(buf):
        raise OutOfData()


def _unpack(buf, pos):
    _need(buf, pos, 1)
    b = buf[pos]
    pos += 1

    if b <= 0x7F:
        return b, pos
    if b >= 0xE0:
        return b - 0x100, pos
    if 0xA0 <= b <= 0xBF:
        return _read_str(buf, pos, b & 0x1F)
    if 0x90 <= b <= 0x9F:
        return _read_array(buf, pos, b & 0x0F)
    if 0x80 <= b <= 0x8F:
        return _read_map(buf, pos, b & 0x0F)
    if b == 0xC0:
        return None, pos
    if b == 0xC2:
        return False, pos
    if b == 0xC3:
        return True, pos
    if b in _FIXED:
        fmt, size = _FIXED[b]
        _need(buf, pos, size)
        return struct.unpack_from(fmt, buf, pos)[0], pos + size
    if b in (0xD9, 0xDA, 0xDB):
        n, pos = _read_len(buf, pos, b - 0xD9)
        return _read_str(buf, pos, n)
    if b in (0xC4, 0xC5, 0xC6):
        n, pos = _read_len(buf, pos, b - 0xC4)
        _need(buf, pos, n)
        return bytes(buf[pos:pos + n]), pos + n
    if b in (0xDC, 0xDD):
        n, pos = _read_len(buf, pos, b - 0xDC + 1)
        return _read_array(buf, pos, n)
    if b in (0xDE, 0xDF):
        n, pos = _read_len(buf, pos, b - 0xDE + 1)
        return _read_map(buf, pos, n)
    raise ValueError("unsupported msgpack type byte 0x%02X" % b)


def _read_len(buf, pos, width_index):
    fmt, size = ((">B", 1), (">H", 2), (">I", 4))[width_index]
    _need(buf, pos, size)
    return struct.unpack_from(fmt, buf, pos)[0], pos + size


def _read_str(buf, pos, n):
    _need(buf, pos, n)
    return bytes(buf[pos:pos + n]).decode("utf-8", errors="replace"), pos + n


def _read_array(buf, pos, n):
    items = []
    for _ in range(n):
        item, pos = _unpack(buf, pos)
        items.append(item)
    return items, pos


def _read_map(buf, pos, n):
    result = {}
    for _ in range(n):
        key, pos = _unpack(buf, pos)
        value, pos = _unpack(buf, pos)
        if isinstance(key, bytes):
            key = key.decode("utf-8", errors="replace")
        result[key] = value
    return result, pos


class Unpacker(object):
    """Streaming unpacker: ``feed()`` bytes, iterate complete objects."""

    def __init__(self):
        self._buf = bytearray()

    def feed(self, data):
        self._buf += data

    def __iter__(self):
        return self

    def __next__(self):
        if not self._buf:
            raise StopIteration
        try:
            # Copy so no memoryview export blocks resizing the bytearray below.
            obj, end = _unpack(bytes(self._buf), 0)
        except OutOfData:
            raise StopIteration
        del self._buf[:end]
        return obj

    next = __next__
