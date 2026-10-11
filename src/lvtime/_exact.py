"""Exact conversions through integers and :class:`~decimal.Decimal`, no float.

A float keeps only about 52 bits of mantissa, so 0.8 s lands on
``0xCCCCCCCCCCCCC000`` in 2**-64 units instead of its true ``0xCCCCCCCCCCCCCCCD``.
These helpers never touch a float, so they reproduce the exact fixed-point value
NI documents and keep the full 2**-64 s resolution end to end.
"""

from __future__ import annotations

from decimal import ROUND_FLOOR, ROUND_HALF_EVEN, Context, Decimal, localcontext

from ._convert import LABVIEW_UNIX_EPOCH_OFFSET, check_frac, check_seconds

# 2**-64 = 5**64 * 10**-64 exactly, so a fraction scaled this way is exact.
_FRAC_UNIT = 1 << 64
_POW5_64 = 5**64
# Enough precision for a 19-digit second count plus 64 fractional digits.
_CONTEXT = Context(prec=96)

ExactInput = Decimal | int | str


def _as_decimal(value: ExactInput) -> Decimal:
    if isinstance(value, float):  # pragma: no cover - guarded by typing too
        raise TypeError("pass a Decimal, int or str, not a float, for an exact value")
    return Decimal(value)


def to_decimal(seconds: int, frac: int = 0) -> Decimal:
    """Return seconds since the 1904 epoch as an exact :class:`~decimal.Decimal`."""
    check_frac(frac)
    with localcontext(_CONTEXT):
        return Decimal(seconds) + Decimal(frac * _POW5_64).scaleb(-64)


def from_decimal(value: ExactInput) -> tuple[int, int]:
    """Convert exact seconds since the 1904 epoch to a ``(seconds, frac)`` pair.

    Accepts a :class:`~decimal.Decimal`, :class:`int` or :class:`str`. A
    :class:`float` is refused so a lossy value cannot slip in; use
    :func:`lvtime.from_float` for the float path.
    """
    with localcontext(_CONTEXT):
        total = _as_decimal(value)
        seconds = int(total.to_integral_value(rounding=ROUND_FLOOR))
        remainder = total - seconds
        frac = int((remainder * _FRAC_UNIT).to_integral_value(rounding=ROUND_HALF_EVEN))
    if frac == _FRAC_UNIT:
        seconds += 1
        frac = 0
    check_seconds(seconds)
    check_frac(frac)
    return seconds, frac


def to_unix_decimal(seconds: int, frac: int = 0) -> Decimal:
    """Return exact Unix time (seconds since 1970-01-01 UTC) as a :class:`~decimal.Decimal`."""
    with localcontext(_CONTEXT):
        return to_decimal(seconds, frac) - LABVIEW_UNIX_EPOCH_OFFSET


def from_unix_decimal(value: ExactInput) -> tuple[int, int]:
    """Convert exact Unix time (seconds since 1970-01-01 UTC) to a ``(seconds, frac)`` pair."""
    with localcontext(_CONTEXT):
        return from_decimal(_as_decimal(value) + LABVIEW_UNIX_EPOCH_OFFSET)
