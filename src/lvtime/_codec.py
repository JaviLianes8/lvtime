"""The 16-byte on-disk form of a LabVIEW timestamp, big- or little-endian.

The default layout is the one LabVIEW "Flatten To String" and the timestamp
channels in TDMS write: eight bytes of signed whole seconds followed by eight
bytes of unsigned fraction, each most significant byte first. Pass ``"little"``
for the byte-reversed form some payloads use.
"""

from __future__ import annotations

import struct
from typing import Literal

ByteOrder = Literal["big", "little"]

_LAYOUTS: dict[str, struct.Struct] = {
    "big": struct.Struct(">qQ"),
    "little": struct.Struct("<qQ"),
}

TIMESTAMP_SIZE = _LAYOUTS["big"].size


def _layout(byteorder: ByteOrder) -> struct.Struct:
    try:
        return _LAYOUTS[byteorder]
    except KeyError:
        raise ValueError(f"byteorder must be 'big' or 'little', got {byteorder!r}") from None


def pack(seconds: int, frac: int, byteorder: ByteOrder = "big") -> bytes:
    """Encode a ``(seconds, frac)`` pair as 16 bytes in the given byte order."""
    return _layout(byteorder).pack(seconds, frac)


def unpack(data: bytes, byteorder: ByteOrder = "big") -> tuple[int, int]:
    """Decode 16 bytes into a ``(seconds, frac)`` pair.

    Raises :class:`ValueError` if the buffer is not exactly 16 bytes long.
    """
    if len(data) != TIMESTAMP_SIZE:
        raise ValueError(f"expected {TIMESTAMP_SIZE} bytes, got {len(data)}")
    seconds, frac = _layout(byteorder).unpack(data)
    return seconds, frac


def pack_many(pairs: list[tuple[int, int]], byteorder: ByteOrder = "big") -> bytes:
    """Encode a list of ``(seconds, frac)`` pairs into one contiguous buffer."""
    layout = _layout(byteorder)
    return b"".join(layout.pack(seconds, frac) for seconds, frac in pairs)


def unpack_many(data: bytes, byteorder: ByteOrder = "big") -> list[tuple[int, int]]:
    """Decode a buffer of back-to-back 16-byte records into pairs.

    Raises :class:`ValueError` if the length is not a multiple of 16 bytes.
    """
    if len(data) % TIMESTAMP_SIZE != 0:
        raise ValueError(f"length must be a multiple of {TIMESTAMP_SIZE} bytes, got {len(data)}")
    layout = _layout(byteorder)
    return [layout.unpack_from(data, offset) for offset in range(0, len(data), TIMESTAMP_SIZE)]
