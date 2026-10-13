"""Exact conversions through integers and :class:`~decimal.Decimal`, no float.

A float keeps 53 significant bits, so the fraction of -5.2 s lands on
``0xCCCCCCCCCCCCC000`` in 2**-64 units instead of its true ``0xCCCCCCCCCCCCCCCD``.
These helpers never touch a float: every result is the exact value, or the input
rounded once to the nearest 2**-64 s (ties to even).
"""

from __future__ import annotations

from decimal import (
    MAX_EMAX,
    MIN_EMIN,
    ROUND_05UP,
    ROUND_HALF_EVEN,
    Context,
    Decimal,
    InvalidOperation,
    localcontext,
)
from typing import SupportsIndex

from ._convert import LABVIEW_UNIX_EPOCH_OFFSET, OUT_OF_RANGE, split_units
from ._validate import I64_MAX, I64_MIN, check_pair, div_round_half_even, short, type_name

ExactInput = Decimal | int | str

_FRAC_BITS = 64
# 2**-64 = 5**64 * 10**-64 exactly, so a fraction scaled this way is exact.
_POW5_64 = 5**64
# Inputs are first cut to 100 decimal places with ROUND_05UP, which keeps the side
# of every tie (ties have 65 places), so the single rounding to 2**-64 stays exact.
_PLACES = 100
_QUANTUM = Decimal((0, (1,), -_PLACES))  # built from digits, so no context applies


# Every setting is explicit, so a customised decimal.DefaultContext cannot leak in.
def exact_context(prec: int) -> Context:
    """Return a decimal context with every setting explicit and only invalid operations trapped."""
    return Context(
        prec=prec,
        rounding=ROUND_HALF_EVEN,
        Emin=MIN_EMIN,
        Emax=MAX_EMAX,
        capitals=1,
        clamp=0,
        flags=[],
        traps=[InvalidOperation],
    )


_CONTEXT = exact_context(_PLACES + 30)


def _as_decimal(value: ExactInput) -> Decimal:
    if isinstance(value, bool):
        raise TypeError("value must be a Decimal, int or str, not a bool")
    if isinstance(value, Decimal):
        number = Decimal(value)  # drops any subclass behaviour
    elif isinstance(value, int):
        if int.bit_length(value) > 2 * _FRAC_BITS:
            raise ValueError(OUT_OF_RANGE)
        number = Decimal(value)
    elif isinstance(value, str):
        try:
            with localcontext(_CONTEXT):  # keeps the caller's flags clean
                number = Decimal(value)
        except InvalidOperation:
            raise ValueError(f"not a decimal number: {short(value)}") from None
    else:
        hint = " (use from_float for a float)" if isinstance(value, float) else ""
        raise TypeError(f"value must be a Decimal, int or str, got {type_name(value)}{hint}")
    if not number.is_finite():
        raise ValueError(f"value must be a finite number, got {short(value)}")
    return number


def _units(value: ExactInput, offset: int) -> int:
    """Return ``value + offset`` seconds as a count of 2**-64 s units, exactly rounded."""
    number = _as_decimal(value)
    if not I64_MIN - 1 - offset < number < I64_MAX + 1 - offset:
        raise ValueError(OUT_OF_RANGE)
    with localcontext(_CONTEXT):
        number = number.quantize(_QUANTUM, rounding=ROUND_05UP)
    numerator, denominator = number.as_integer_ratio()
    units = div_round_half_even(numerator << _FRAC_BITS, denominator)
    return units + (offset << _FRAC_BITS)


def _exact(seconds: int, frac: int) -> Decimal:
    if frac == 0:
        return Decimal(seconds)
    with localcontext(_CONTEXT):
        return (Decimal(seconds) + Decimal(frac * _POW5_64).scaleb(-64)).normalize()


def to_decimal(seconds: SupportsIndex, frac: SupportsIndex = 0) -> Decimal:
    """Return seconds since the 1904 epoch as an exact :class:`~decimal.Decimal`.

    Every 2**-64 s fraction has a finite decimal expansion, so nothing is rounded.

    >>> to_decimal(-6, 0xCCCCCCCCCCCCCCCD)
    Decimal('-5.1999999999999999999891579782751449556599254719913005828857421875')
    >>> to_decimal(10, 1 << 63)
    Decimal('10.5')
    """
    seconds, frac = check_pair(seconds, frac)
    return _exact(seconds, frac)


def from_decimal(value: ExactInput) -> tuple[int, int]:
    """Convert exact seconds since the 1904 epoch to a ``(seconds, frac)`` pair.

    Accepts a :class:`~decimal.Decimal`, :class:`int` or :class:`str` and rounds
    once to the nearest 2**-64 s (ties to even). A :class:`float` is refused with
    :class:`TypeError` so a lossy value cannot slip in (use :func:`from_float`);
    text that is not a finite decimal number raises :class:`ValueError`.

    >>> from_decimal("-5.2") == (-6, 0xCCCCCCCCCCCCCCCD)
    True
    """
    return split_units(_units(value, 0))


def to_unix_decimal(seconds: SupportsIndex, frac: SupportsIndex = 0) -> Decimal:
    """Return exact Unix time (seconds since 1970-01-01 UTC) as a :class:`~decimal.Decimal`.

    >>> to_unix_decimal(3810888000, 1 << 63)
    Decimal('1728043200.5')
    """
    seconds, frac = check_pair(seconds, frac)
    return _exact(seconds - LABVIEW_UNIX_EPOCH_OFFSET, frac)


def from_unix_decimal(value: ExactInput) -> tuple[int, int]:
    """Convert exact Unix time (seconds since 1970-01-01 UTC) to a ``(seconds, frac)`` pair.

    Rounds like :func:`from_decimal`; the epoch offset is added in integers.

    >>> from_unix_decimal("1728043200.5")
    (3810888000, 9223372036854775808)
    """
    return split_units(_units(value, LABVIEW_UNIX_EPOCH_OFFSET))
