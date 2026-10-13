"""The lossless :class:`LVTimestamp` integer pair."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import SupportsIndex, cast

from . import _codec, _convert, _exact
from ._codec import ByteOrder, BytesLike
from ._exact import ExactInput
from ._validate import check_pair, type_name


@dataclass(frozen=True, order=True, init=False)
class LVTimestamp:
    """A LabVIEW absolute time held without loss as two integers.

    ``seconds`` is the signed 64-bit count of whole seconds since 1904-01-01
    00:00:00 UTC; ``frac`` is the unsigned 64-bit fraction in units of 2**-64 s.
    Both are checked on construction (:class:`TypeError` for a non-integer,
    :class:`ValueError` when out of range) and stored as plain ints, so any
    integer type with ``__index__`` (a NumPy integer, say) is accepted. Instances
    are immutable, hashable and ordered in time.

    >>> ts = LVTimestamp(3810888000, 1 << 63)
    >>> ts.to_datetime().isoformat()
    '2024-10-04T12:00:00.500000+00:00'
    >>> ts.hex()
    '00000000e32589408000000000000000'
    >>> LVTimestamp(-1, 0) < LVTimestamp(0, 0) < LVTimestamp(0, 1)
    True
    """

    seconds: int
    frac: int = 0

    def __init__(self, seconds: SupportsIndex, frac: SupportsIndex = 0) -> None:
        checked_seconds, checked_frac = check_pair(seconds, frac)
        object.__setattr__(self, "seconds", checked_seconds)
        object.__setattr__(self, "frac", checked_frac)

    def to_datetime(self) -> datetime:
        """Return a UTC-aware datetime rounded to the microsecond; see :func:`to_datetime`.

        >>> LVTimestamp(0, 1 << 63).to_datetime().isoformat()
        '1904-01-01T00:00:00.500000+00:00'
        """
        return _convert.to_datetime(self.seconds, self.frac)

    @classmethod
    def from_datetime(cls, dt: datetime) -> LVTimestamp:
        """Build a timestamp from a timezone-aware datetime; see :func:`from_datetime`.

        >>> from datetime import datetime, timezone
        >>> LVTimestamp.from_datetime(datetime(1904, 1, 1, tzinfo=timezone.utc))
        LVTimestamp(seconds=0, frac=0)
        """
        return cls(*_convert.from_datetime(dt))

    def to_unix(self) -> float:
        """Return float seconds since 1970-01-01 UTC; see :func:`to_unix`.

        >>> LVTimestamp(2082844800, 1 << 62).to_unix()
        0.25
        """
        return _convert.to_unix(self.seconds, self.frac)

    @classmethod
    def from_unix(cls, value: float) -> LVTimestamp:
        """Build a timestamp from float Unix time; see :func:`from_unix`.

        >>> LVTimestamp.from_unix(0.0).seconds
        2082844800
        """
        return cls(*_convert.from_unix(value))

    def to_float(self) -> float:
        """Return float seconds since the 1904 epoch; see :func:`to_float`.

        >>> LVTimestamp(-1, 1 << 63).to_float()
        -0.5
        """
        return _convert.to_float(self.seconds, self.frac)

    @classmethod
    def from_float(cls, value: float) -> LVTimestamp:
        """Build a timestamp from float seconds since 1904; see :func:`from_float`.

        >>> LVTimestamp.from_float(-0.5)
        LVTimestamp(seconds=-1, frac=9223372036854775808)
        """
        return cls(*_convert.from_float(value))

    def to_decimal(self) -> Decimal:
        """Return exact seconds since the 1904 epoch; see :func:`to_decimal`.

        >>> LVTimestamp(10, 1 << 63).to_decimal()
        Decimal('10.5')
        """
        return _exact.to_decimal(self.seconds, self.frac)

    @classmethod
    def from_decimal(cls, value: ExactInput) -> LVTimestamp:
        """Build a timestamp from exact seconds since 1904; see :func:`from_decimal`.

        >>> LVTimestamp.from_decimal("-5.2").hex()
        'fffffffffffffffacccccccccccccccd'
        """
        return cls(*_exact.from_decimal(value))

    def to_unix_decimal(self) -> Decimal:
        """Return exact Unix time as a Decimal; see :func:`to_unix_decimal`.

        >>> LVTimestamp(2082844800, 1).to_unix_decimal()
        Decimal('5.42101086242752217003726400434970855712890625E-20')
        """
        return _exact.to_unix_decimal(self.seconds, self.frac)

    @classmethod
    def from_unix_decimal(cls, value: ExactInput) -> LVTimestamp:
        """Build a timestamp from exact Unix time; see :func:`from_unix_decimal`.

        >>> LVTimestamp.from_unix_decimal("0").to_unix_decimal()
        Decimal('0')
        """
        return cls(*_exact.from_unix_decimal(value))

    def to_bytes(self, byteorder: ByteOrder = "big") -> bytes:
        """Return the 16-byte on-disk form (default big-endian).

        >>> LVTimestamp(1, 2).to_bytes("little").hex()
        '02000000000000000100000000000000'
        """
        return _codec.pack(self.seconds, self.frac, byteorder)

    @classmethod
    def from_bytes(cls, data: BytesLike, byteorder: ByteOrder = "big") -> LVTimestamp:
        """Build a timestamp from its 16-byte on-disk form (default big-endian).

        Raises :class:`ValueError` unless ``data`` is exactly 16 bytes.

        >>> LVTimestamp.from_bytes(bytes(15) + b"\\x01")
        LVTimestamp(seconds=0, frac=1)
        """
        return cls(*_codec.unpack(data, byteorder))

    def hex(self, byteorder: ByteOrder = "big") -> str:
        """Return the 16-byte on-disk form as 32 lower-case hex digits (default big-endian).

        >>> LVTimestamp(-1, 0).hex()
        'ffffffffffffffff0000000000000000'
        """
        return self.to_bytes(byteorder).hex()

    @classmethod
    def from_hex(cls, text: str, byteorder: ByteOrder = "big") -> LVTimestamp:
        """Build a timestamp from 32 hex digits (spaces between bytes allowed).

        Raises :class:`ValueError` for text that is not 16 bytes of hex.

        >>> LVTimestamp.from_hex("00000000 b8555b00 00000000 00000000")
        LVTimestamp(seconds=3092601600, frac=0)
        """
        if not isinstance(text, str):
            raise TypeError(f"text must be a str, got {type_name(text)}")
        return cls.from_bytes(bytes.fromhex(text), byteorder)


def require_timestamp(value: object) -> LVTimestamp:
    """Return ``value`` if it is an :class:`LVTimestamp`, else raise :class:`TypeError`."""
    if not issubclass(type(value), LVTimestamp):  # type() cannot be faked like __class__
        raise TypeError(f"expected an LVTimestamp, got {type_name(value)}")
    return cast(LVTimestamp, value)
