"""The lossless :class:`LVTimestamp` integer pair and its byte helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from . import _codec, _convert


@dataclass(frozen=True)
class LVTimestamp:
    """A LabVIEW absolute time held without loss as two integers.

    ``seconds`` is the signed 64-bit count of whole seconds since 1904-01-01
    00:00:00 UTC; ``frac`` is the unsigned 64-bit fraction in units of 2**-64 s.
    Both fields are validated on construction.
    """

    seconds: int
    frac: int = 0

    def __post_init__(self) -> None:
        _convert.check_seconds(self.seconds)
        _convert.check_frac(self.frac)

    def to_datetime(self) -> datetime:
        """Return this instant as a UTC-aware datetime, rounded to the microsecond."""
        return _convert.to_datetime(self.seconds, self.frac)

    @classmethod
    def from_datetime(cls, dt: datetime) -> LVTimestamp:
        """Build a timestamp from a timezone-aware datetime."""
        seconds, frac = _convert.from_datetime(dt)
        return cls(seconds, frac)

    def to_bytes(self) -> bytes:
        """Return the 16-byte big-endian on-disk form."""
        return _codec.pack(self.seconds, self.frac)

    @classmethod
    def from_bytes(cls, data: bytes) -> LVTimestamp:
        """Build a timestamp from its 16-byte big-endian on-disk form."""
        seconds, frac = _codec.unpack(data)
        return cls(seconds, frac)


def read_timestamp(data: bytes) -> LVTimestamp:
    """Read a :class:`LVTimestamp` from its 16-byte big-endian on-disk form."""
    return LVTimestamp.from_bytes(data)


def write_timestamp(timestamp: LVTimestamp) -> bytes:
    """Write a :class:`LVTimestamp` as its 16-byte big-endian on-disk form."""
    return timestamp.to_bytes()
