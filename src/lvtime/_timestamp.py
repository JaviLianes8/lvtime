"""The lossless :class:`LVTimestamp` integer pair and its byte and stream helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from . import _codec, _convert, _exact
from ._codec import ByteOrder
from ._exact import ExactInput


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

    def to_unix(self) -> float:
        """Return this instant as Unix time (float seconds since 1970-01-01 UTC)."""
        return _convert.to_unix(self.seconds, self.frac)

    @classmethod
    def from_unix(cls, value: float) -> LVTimestamp:
        """Build a timestamp from Unix time (float seconds since 1970-01-01 UTC)."""
        seconds, frac = _convert.from_unix(value)
        return cls(seconds, frac)

    def to_float(self) -> float:
        """Return seconds since the 1904 epoch as a float (LabVIEW DBL coercion)."""
        return _convert.to_float(self.seconds, self.frac)

    @classmethod
    def from_float(cls, value: float) -> LVTimestamp:
        """Build a timestamp from float seconds since the 1904 epoch."""
        seconds, frac = _convert.from_float(value)
        return cls(seconds, frac)

    def to_decimal(self) -> Decimal:
        """Return seconds since the 1904 epoch as an exact Decimal (no float)."""
        return _exact.to_decimal(self.seconds, self.frac)

    @classmethod
    def from_decimal(cls, value: ExactInput) -> LVTimestamp:
        """Build a timestamp from exact seconds since the epoch (Decimal, int or str)."""
        seconds, frac = _exact.from_decimal(value)
        return cls(seconds, frac)

    def to_unix_decimal(self) -> Decimal:
        """Return this instant as exact Unix time (Decimal seconds since 1970-01-01 UTC)."""
        return _exact.to_unix_decimal(self.seconds, self.frac)

    @classmethod
    def from_unix_decimal(cls, value: ExactInput) -> LVTimestamp:
        """Build a timestamp from exact Unix time (Decimal, int or str)."""
        seconds, frac = _exact.from_unix_decimal(value)
        return cls(seconds, frac)

    def to_bytes(self, byteorder: ByteOrder = "big") -> bytes:
        """Return the 16-byte on-disk form in the given byte order (default big)."""
        return _codec.pack(self.seconds, self.frac, byteorder)

    @classmethod
    def from_bytes(cls, data: bytes, byteorder: ByteOrder = "big") -> LVTimestamp:
        """Build a timestamp from its 16-byte on-disk form (default big-endian)."""
        seconds, frac = _codec.unpack(data, byteorder)
        return cls(seconds, frac)

    def hex(self, byteorder: ByteOrder = "big") -> str:
        """Return the 16-byte on-disk form as a 32-character hex string (default big)."""
        return self.to_bytes(byteorder).hex()

    @classmethod
    def from_hex(cls, text: str, byteorder: ByteOrder = "big") -> LVTimestamp:
        """Build a timestamp from a 32-character hex string (default big-endian)."""
        return cls.from_bytes(bytes.fromhex(text), byteorder)


def read_timestamp(data: bytes, byteorder: ByteOrder = "big") -> LVTimestamp:
    """Read a :class:`LVTimestamp` from its 16-byte on-disk form (default big-endian)."""
    return LVTimestamp.from_bytes(data, byteorder)


def write_timestamp(timestamp: LVTimestamp, byteorder: ByteOrder = "big") -> bytes:
    """Write a :class:`LVTimestamp` as its 16-byte on-disk form (default big-endian)."""
    return timestamp.to_bytes(byteorder)


def read_timestamps(data: bytes, byteorder: ByteOrder = "big") -> list[LVTimestamp]:
    """Read back-to-back 16-byte records into a list of :class:`LVTimestamp`.

    Raises :class:`ValueError` if the length is not a multiple of 16 bytes.
    """
    return [LVTimestamp(seconds, frac) for seconds, frac in _codec.unpack_many(data, byteorder)]


def write_timestamps(timestamps: list[LVTimestamp], byteorder: ByteOrder = "big") -> bytes:
    """Write a list of :class:`LVTimestamp` as one contiguous buffer of 16-byte records."""
    return _codec.pack_many([(ts.seconds, ts.frac) for ts in timestamps], byteorder)
