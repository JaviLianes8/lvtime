"""Convert LabVIEW absolute time to and from datetime, Unix time and float seconds.

LabVIEW absolute time counts from 1904-01-01 00:00:00 UTC. A value is a signed
64-bit count of whole seconds plus an unsigned 64-bit fraction in units of
2**-64 seconds. :mod:`datetime` resolves only to microseconds and a float holds
53 bits of mantissa, so those two views round; the lossless path is the
integer pair itself.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Final, SupportsIndex

from ._validate import I64_MAX, I64_MIN, as_int, check_pair, check_seconds, div_round_half_even

OUT_OF_RANGE = (
    "the value is outside the timestamp range (whole seconds must fit a signed 64-bit integer)"
)

LABVIEW_UNIX_EPOCH_OFFSET: Final[int] = 2082844800
"""Seconds from the LabVIEW epoch (1904-01-01 UTC) to the Unix epoch (1970-01-01 UTC)."""

_EPOCH = datetime(1904, 1, 1, tzinfo=timezone.utc)
_MICROS = 1_000_000
_FRAC_BITS = 64
_FRAC_UNIT = 1 << _FRAC_BITS
_HALF_FRAC_UNIT = 1 << (_FRAC_BITS - 1)


def to_datetime(seconds: SupportsIndex, frac: SupportsIndex = 0) -> datetime:
    """Convert a LabVIEW timestamp to a UTC-aware :class:`datetime.datetime`.

    The fraction is rounded to the nearest microsecond (an exact half rounds up,
    towards the later instant). Raises :class:`OverflowError` if the instant is
    outside the years 1 to 9999 that :class:`datetime.datetime` can hold.

    >>> to_datetime(3810888000, 1 << 63)
    datetime.datetime(2024, 10, 4, 12, 0, 0, 500000, tzinfo=datetime.timezone.utc)
    """
    seconds, frac = check_pair(seconds, frac)
    micros = (frac * _MICROS + _HALF_FRAC_UNIT) >> _FRAC_BITS
    try:
        return _EPOCH + timedelta(seconds=seconds, microseconds=micros)
    except OverflowError:
        message = "the instant is outside the datetime range (years 1 to 9999)"
        raise OverflowError(message) from None


def from_datetime(dt: datetime) -> tuple[int, int]:
    """Convert a timezone-aware :class:`datetime.datetime` to ``(seconds, frac)``.

    A naive datetime raises :class:`ValueError`, so the instant is never
    ambiguous. The microsecond maps to the nearest 2**-64 s fraction, so
    ``to_datetime(*from_datetime(dt)) == dt`` for every aware ``dt``.

    >>> from datetime import datetime, timezone
    >>> from_datetime(datetime(2024, 10, 4, 12, 0, 0, 500000, tzinfo=timezone.utc))
    (3810888000, 9223372036854775808)
    """
    if not isinstance(dt, datetime):
        raise TypeError(f"dt must be a datetime, got {type(dt).__name__}")
    if datetime.utcoffset(dt) is None:  # the plain method, whatever a subclass overrides
        raise ValueError("dt must be timezone-aware (naive datetimes are ambiguous)")
    delta = datetime.__sub__(dt, _EPOCH)  # the plain operation, whatever a subclass overrides
    total_micros = (delta.days * 86400 + delta.seconds) * _MICROS + delta.microseconds
    seconds, micros = divmod(total_micros, _MICROS)
    frac = (micros * _FRAC_UNIT + _MICROS // 2) // _MICROS
    return check_seconds(seconds), frac


def _ratio(value: float) -> tuple[int, int]:
    if isinstance(value, float):
        number = float.__float__(value)  # the plain value, whatever a subclass overrides
        if not math.isfinite(number):
            raise ValueError(f"value must be a finite number, got {number!r}")
        return number.as_integer_ratio()
    if not hasattr(type(value), "__index__"):
        raise TypeError(f"value must be a float or an integer, got {type(value).__name__}")
    return as_int("value", value), 1


def split_units(units: int) -> tuple[int, int]:
    """Split a count of 2**-64 s units into a checked ``(seconds, frac)`` pair."""
    seconds, frac = divmod(units, _FRAC_UNIT)
    if not I64_MIN <= seconds <= I64_MAX:
        raise ValueError(OUT_OF_RANGE)
    return seconds, frac


def to_float(seconds: SupportsIndex, frac: SupportsIndex = 0) -> float:
    """Return seconds since the 1904 epoch as the nearest float.

    This is the value you get by converting a LabVIEW timestamp to a double. A
    float keeps 53 significant bits, so detail below about half a microsecond is
    lost at present-day magnitudes.

    >>> to_float(3810888000, 1 << 63)
    3810888000.5
    """
    seconds, frac = check_pair(seconds, frac)
    return (seconds * _FRAC_UNIT + frac) / _FRAC_UNIT


def from_float(value: float) -> tuple[int, int]:
    """Convert float seconds since the 1904 epoch to ``(seconds, frac)``.

    The exact value of the float is rounded to the nearest 2**-64 s (ties to
    even). NaN and infinities raise :class:`ValueError`.

    >>> from_float(3810888000.5)
    (3810888000, 9223372036854775808)
    """
    numerator, denominator = _ratio(value)
    return split_units(div_round_half_even(numerator << _FRAC_BITS, denominator))


def to_unix(seconds: SupportsIndex, frac: SupportsIndex = 0) -> float:
    """Return Unix time (float seconds since 1970-01-01 UTC), like :func:`time.time`.

    >>> to_unix(3810888000, 1 << 63)
    1728043200.5
    """
    seconds, frac = check_pair(seconds, frac)
    return ((seconds - LABVIEW_UNIX_EPOCH_OFFSET) * _FRAC_UNIT + frac) / _FRAC_UNIT


def from_unix(value: float) -> tuple[int, int]:
    """Convert Unix time (float seconds since 1970-01-01 UTC) to ``(seconds, frac)``.

    Exact like :func:`from_float`: the epoch offset is added in integers.

    >>> from_unix(1728043200.5)
    (3810888000, 9223372036854775808)
    """
    numerator, denominator = _ratio(value)
    units = div_round_half_even(numerator << _FRAC_BITS, denominator)
    return split_units(units + (LABVIEW_UNIX_EPOCH_OFFSET << _FRAC_BITS))
