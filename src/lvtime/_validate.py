"""Argument checks shared by every public entry point, with short, safe messages."""

from __future__ import annotations

import operator
from typing import SupportsIndex

I64_MIN = -(2**63)
I64_MAX = 2**63 - 1
U64_MAX = 2**64 - 1

# Error messages never echo more than this many characters of a caller's value.
_SHOW_LIMIT = 40


def short(value: object) -> str:
    """Return a bounded description of ``value`` for an error message."""
    if isinstance(value, int) and not isinstance(value, bool):
        if value.bit_length() > 64:
            return f"an integer of {value.bit_length()} bits"
        return str(value)
    try:
        text = repr(value)
    except Exception:
        return f"a {type(value).__name__} object"
    if len(text) > _SHOW_LIMIT:
        return f"{text[:_SHOW_LIMIT]}... ({len(text)} characters)"
    return text


def as_int(name: str, value: SupportsIndex) -> int:
    """Return ``value`` as a plain int; refuse bools, floats and other non-integers."""
    if isinstance(value, bool):
        raise TypeError(f"{name} must be an integer, not a bool")
    try:
        return operator.index(value)
    except TypeError:
        raise TypeError(f"{name} must be an integer, got {type(value).__name__}") from None


def check_seconds(seconds: SupportsIndex) -> int:
    """Return ``seconds`` as an int after checking it fits a signed 64-bit integer."""
    number = as_int("seconds", seconds)
    if not I64_MIN <= number <= I64_MAX:
        raise ValueError(f"seconds must fit a signed 64-bit integer, got {short(number)}")
    return number


def check_frac(frac: SupportsIndex) -> int:
    """Return ``frac`` as an int after checking it fits an unsigned 64-bit integer."""
    number = as_int("frac", frac)
    if not 0 <= number <= U64_MAX:
        raise ValueError(f"frac must be in [0, 2**64), got {short(number)}")
    return number


def check_pair(seconds: SupportsIndex, frac: SupportsIndex) -> tuple[int, int]:
    """Validate and normalise a ``(seconds, frac)`` pair."""
    return check_seconds(seconds), check_frac(frac)


def div_round_half_even(numerator: int, denominator: int) -> int:
    """Divide two ints (positive denominator), rounding to the nearest, ties to even."""
    quotient, remainder = divmod(numerator, denominator)
    twice = 2 * remainder
    if twice > denominator or (twice == denominator and quotient % 2 == 1):
        quotient += 1
    return quotient
