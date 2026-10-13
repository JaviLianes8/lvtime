"""Lossless LabVIEW 128-bit timestamp to and from datetime, UTC, sub-microsecond preserved.

A LabVIEW timestamp is a signed 64-bit count of whole seconds since 1904-01-01
00:00:00 UTC plus an unsigned 64-bit fraction in units of 2**-64 s.

>>> import lvtime
>>> lvtime.LABVIEW_UNIX_EPOCH_OFFSET
2082844800
>>> ts = lvtime.read_timestamp(bytes.fromhex("00000000e32589408000000000000000"))
>>> ts.to_datetime().isoformat()
'2024-10-04T12:00:00.500000+00:00'
>>> order: lvtime.ByteOrder = "little"
>>> lvtime.LVTimestamp.from_bytes(ts.to_bytes(order), order) == ts
True
"""

from __future__ import annotations

from ._codec import ByteOrder
from ._convert import (
    LABVIEW_UNIX_EPOCH_OFFSET,
    from_datetime,
    from_float,
    from_unix,
    to_datetime,
    to_float,
    to_unix,
)
from ._exact import (
    from_decimal,
    from_unix_decimal,
    to_decimal,
    to_unix_decimal,
)
from ._io import read_timestamp, read_timestamps, write_timestamp, write_timestamps
from ._timestamp import LVTimestamp

__version__ = "1.0.0"

__all__ = [
    "LABVIEW_UNIX_EPOCH_OFFSET",
    "ByteOrder",
    "LVTimestamp",
    "from_datetime",
    "from_decimal",
    "from_float",
    "from_unix",
    "from_unix_decimal",
    "read_timestamp",
    "read_timestamps",
    "to_datetime",
    "to_decimal",
    "to_float",
    "to_unix",
    "to_unix_decimal",
    "write_timestamp",
    "write_timestamps",
]
