"""The 16-byte big-endian on-disk form of a LabVIEW timestamp.

This is the layout used by LabVIEW "Flatten To String" and by the timestamp
channels in TDMS: eight bytes of signed whole seconds followed by eight bytes of
unsigned fraction, each stored most significant byte first.
"""

from __future__ import annotations

import struct

_LAYOUT = struct.Struct(">qQ")

TIMESTAMP_SIZE = _LAYOUT.size


def pack(seconds: int, frac: int) -> bytes:
    """Encode a ``(seconds, frac)`` pair as 16 big-endian bytes."""
    return _LAYOUT.pack(seconds, frac)


def unpack(data: bytes) -> tuple[int, int]:
    """Decode 16 big-endian bytes into a ``(seconds, frac)`` pair.

    Raises :class:`ValueError` if the buffer is not exactly 16 bytes long.
    """
    if len(data) != TIMESTAMP_SIZE:
        raise ValueError(f"expected {TIMESTAMP_SIZE} bytes, got {len(data)}")
    seconds, frac = _LAYOUT.unpack(data)
    return seconds, frac
