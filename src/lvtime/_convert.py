"""Conversion between LabVIEW absolute time and :class:`datetime.datetime`.

LabVIEW absolute time counts from 1904-01-01 00:00:00 UTC. A value is a signed
64-bit count of whole seconds plus an unsigned 64-bit fraction in units of
2**-64 seconds. :mod:`datetime` resolves only to microseconds, so these helpers
round to the nearest microsecond; the lossless path is the integer pair itself.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

# Seconds between the LabVIEW epoch (1904-01-01) and the Unix epoch (1970-01-01).
LABVIEW_UNIX_EPOCH_OFFSET = 2082844800

I64_MIN = -(2**63)
I64_MAX = 2**63 - 1
U64_MAX = 2**64 - 1

_EPOCH = datetime(1904, 1, 1, tzinfo=timezone.utc)
_MICROS_PER_SECOND = 1_000_000
_FRAC_UNIT = 1 << 64
_HALF_FRAC_UNIT = 1 << 63


def check_seconds(seconds: int) -> None:
    """Reject whole-second counts that do not fit a signed 64-bit integer."""
    if not I64_MIN <= seconds <= I64_MAX:
        raise ValueError(f"seconds must fit a signed 64-bit integer, got {seconds}")


def check_frac(frac: int) -> None:
    """Reject fractions outside the unsigned 64-bit range."""
    if not 0 <= frac <= U64_MAX:
        raise ValueError(f"frac must be in [0, 2**64), got {frac}")


def to_datetime(seconds: int, frac: int = 0) -> datetime:
    """Convert a LabVIEW timestamp to a UTC-aware :class:`datetime.datetime`.

    ``seconds`` is whole seconds since 1904-01-01 UTC and ``frac`` the 2**-64 s
    fraction. The fraction is rounded to the nearest microsecond. Raises
    :class:`ValueError` if ``frac`` is out of range and :class:`OverflowError`
    if the instant falls outside the range of :class:`datetime.datetime`.
    """
    check_frac(frac)
    micros = (frac * _MICROS_PER_SECOND + _HALF_FRAC_UNIT) >> 64
    return _EPOCH + timedelta(microseconds=seconds * _MICROS_PER_SECOND + micros)


def from_datetime(dt: datetime) -> tuple[int, int]:
    """Convert a timezone-aware :class:`datetime.datetime` to ``(seconds, frac)``.

    The input must carry a timezone so the instant is unambiguous; a naive
    datetime raises :class:`ValueError`. The microsecond field maps back to the
    nearest 2**-64 s fraction, so a round trip is exact to the microsecond.
    """
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        raise ValueError("dt must be timezone-aware")
    delta = dt - _EPOCH
    total_micros = (delta.days * 86400 + delta.seconds) * _MICROS_PER_SECOND + delta.microseconds
    seconds, micro_remainder = divmod(total_micros, _MICROS_PER_SECOND)
    frac = (micro_remainder * _FRAC_UNIT + _MICROS_PER_SECOND // 2) // _MICROS_PER_SECOND
    check_seconds(seconds)
    return seconds, frac
