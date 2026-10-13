"""Read and write one or many timestamps in their 16-byte on-disk form."""

from __future__ import annotations

from collections.abc import Iterable

from . import _codec
from ._codec import ByteOrder, BytesLike
from ._timestamp import LVTimestamp, require_timestamp
from ._validate import type_name


def read_timestamp(data: BytesLike, byteorder: ByteOrder = "big") -> LVTimestamp:
    """Read an :class:`LVTimestamp` from exactly 16 bytes (default big-endian).

    >>> read_timestamp(bytes.fromhex("00000000b8555b000000000000000000"))
    LVTimestamp(seconds=3092601600, frac=0)
    """
    return LVTimestamp.from_bytes(data, byteorder)


def write_timestamp(timestamp: LVTimestamp, byteorder: ByteOrder = "big") -> bytes:
    """Write an :class:`LVTimestamp` as its 16-byte on-disk form (default big-endian).

    >>> write_timestamp(LVTimestamp(-1, 1 << 63)).hex()
    'ffffffffffffffff8000000000000000'
    """
    return LVTimestamp.to_bytes(require_timestamp(timestamp), byteorder)


def read_timestamps(data: BytesLike, byteorder: ByteOrder = "big") -> list[LVTimestamp]:
    """Read back-to-back 16-byte records into a list of :class:`LVTimestamp`.

    An empty buffer gives an empty list. Raises :class:`ValueError` if the
    length is not a multiple of 16 bytes.

    >>> read_timestamps(bytes(32))
    [LVTimestamp(seconds=0, frac=0), LVTimestamp(seconds=0, frac=0)]
    """
    return [LVTimestamp(seconds, frac) for seconds, frac in _codec.unpack_many(data, byteorder)]


def write_timestamps(timestamps: Iterable[LVTimestamp], byteorder: ByteOrder = "big") -> bytes:
    """Write any iterable of :class:`LVTimestamp` as one buffer of 16-byte records.

    >>> len(write_timestamps([LVTimestamp(0), LVTimestamp(1)], "little"))
    32
    """
    if isinstance(timestamps, (LVTimestamp, bytes, bytearray, memoryview, str)):
        raise TypeError(
            f"timestamps must be an iterable of LVTimestamp, not {type_name(timestamps)}"
        )
    _codec.check_byteorder(byteorder)
    return b"".join(LVTimestamp.to_bytes(require_timestamp(ts), byteorder) for ts in timestamps)
