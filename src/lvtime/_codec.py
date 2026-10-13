"""The 16-byte on-disk form of a LabVIEW timestamp, big- or little-endian.

LabVIEW treats a timestamp as one signed 128-bit fixed-point number whose upper
64 bits are the whole seconds and whose lower 64 bits are the fraction. Big-endian
(``"big"``, the default, as datalog files, big-endian TDMS and Flatten To String
write it) puts the seconds first, most significant byte first. Little-endian
(``"little"``, as little-endian TDMS files, the TDMS default, write it) is the
same 16 bytes reversed: the fraction first, then the seconds, each least
significant byte first.
"""

from __future__ import annotations

import struct
from typing import Literal

from ._validate import check_pair, short, type_name

ByteOrder = Literal["big", "little"]
BytesLike = bytes | bytearray | memoryview

_BIG = struct.Struct(">qQ")
_LITTLE = struct.Struct("<Qq")

TIMESTAMP_SIZE = _BIG.size


def _layout(byteorder: ByteOrder) -> tuple[struct.Struct, bool]:
    """Return the struct and whether its fields come fraction first."""
    if isinstance(byteorder, str):
        if str.__eq__(byteorder, "big") is True:
            return _BIG, False
        if str.__eq__(byteorder, "little") is True:
            return _LITTLE, True
    raise ValueError(f"byteorder must be 'big' or 'little', got {short(byteorder)}")


def check_byteorder(byteorder: ByteOrder) -> None:
    """Raise :class:`ValueError` unless ``byteorder`` is ``"big"`` or ``"little"``."""
    _layout(byteorder)


def as_bytes(data: BytesLike) -> bytes:
    """Return ``data`` as bytes; refuse anything that is not a bytes-like buffer."""
    if type(data) is bytes:
        return data
    if isinstance(data, (bytes, bytearray, memoryview)):
        # Copy the raw buffer: neither __bytes__ nor __len__ of a subclass is consulted.
        with memoryview(data) as view:
            return view.tobytes()
    raise TypeError(f"data must be bytes, bytearray or memoryview, got {type_name(data)}")


def pack(seconds: int, frac: int, byteorder: ByteOrder = "big") -> bytes:
    """Encode a validated ``(seconds, frac)`` pair as 16 bytes in the given byte order."""
    layout, frac_first = _layout(byteorder)
    seconds, frac = check_pair(seconds, frac)  # cheap, and no subclass can sneak past it
    return layout.pack(frac, seconds) if frac_first else layout.pack(seconds, frac)


def unpack(data: BytesLike, byteorder: ByteOrder = "big") -> tuple[int, int]:
    """Decode 16 bytes into a ``(seconds, frac)`` pair.

    Raises :class:`ValueError` if the buffer is not exactly 16 bytes long.
    """
    layout, frac_first = _layout(byteorder)
    raw = as_bytes(data)
    if len(raw) != TIMESTAMP_SIZE:
        raise ValueError(f"expected {TIMESTAMP_SIZE} bytes, got {len(raw)}")
    first, second = layout.unpack(raw)
    return (second, first) if frac_first else (first, second)


def unpack_many(data: BytesLike, byteorder: ByteOrder = "big") -> list[tuple[int, int]]:
    """Decode a buffer of back-to-back 16-byte records into pairs.

    Raises :class:`ValueError` if the length is not a multiple of 16 bytes.
    """
    layout, frac_first = _layout(byteorder)
    raw = as_bytes(data)
    if len(raw) % TIMESTAMP_SIZE != 0:
        raise ValueError(f"length must be a multiple of {TIMESTAMP_SIZE} bytes, got {len(raw)}")
    if frac_first:
        return [(seconds, frac) for frac, seconds in layout.iter_unpack(raw)]
    return list(layout.iter_unpack(raw))
