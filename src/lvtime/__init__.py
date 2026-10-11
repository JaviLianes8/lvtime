"""Lossless LabVIEW 128-bit timestamp to and from datetime, UTC, sub-microsecond preserved."""

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
from ._timestamp import (
    LVTimestamp,
    read_timestamp,
    read_timestamps,
    write_timestamp,
    write_timestamps,
)

__version__ = "0.2.0"

__all__ = [
    "LABVIEW_UNIX_EPOCH_OFFSET",
    "ByteOrder",
    "LVTimestamp",
    "from_datetime",
    "from_float",
    "from_unix",
    "read_timestamp",
    "read_timestamps",
    "to_datetime",
    "to_float",
    "to_unix",
    "write_timestamp",
    "write_timestamps",
]
