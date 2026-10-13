"""Edge promises of the library API that a single wrong token would silently break."""

from __future__ import annotations

import time
from datetime import datetime, timedelta, tzinfo
from decimal import Decimal

import pytest

import lvtime
from lvtime import LABVIEW_UNIX_EPOCH_OFFSET as OFFSET
from lvtime import LVTimestamp

I64_MIN = -(2**63)
I64_MAX = 2**63 - 1


class _NoOffset(tzinfo):
    """A tzinfo that is attached but declines to give an offset, so the instant is naive."""

    def utcoffset(self, dt: datetime | None) -> timedelta | None:
        return None

    def dst(self, dt: datetime | None) -> timedelta | None:
        return None

    def tzname(self, dt: datetime | None) -> str | None:
        return None


class _ShortInt(int):
    """An int that understates its size."""

    def bit_length(self) -> int:
        return 1


def test_a_tzinfo_without_an_offset_counts_as_naive() -> None:
    dt = datetime(2024, 10, 4, 12, tzinfo=_NoOffset())
    with pytest.raises(ValueError, match="timezone-aware"):
        lvtime.from_datetime(dt)
    with pytest.raises(ValueError, match="timezone-aware"):
        LVTimestamp.from_datetime(dt)


@pytest.mark.parametrize("convert", [lvtime.from_decimal, lvtime.from_unix_decimal])
@pytest.mark.parametrize("make", [int, _ShortInt])
def test_huge_integers_are_refused_at_once(convert: object, make: type[int]) -> None:
    value = make(1 << 4_000_000)
    assert callable(convert)
    start = time.perf_counter()
    with pytest.raises(ValueError, match="outside the timestamp range"):
        convert(value)
    assert time.perf_counter() - start < 1.0


@pytest.mark.parametrize("seconds", [0, 10, 3810888000, -1, -3810888000, I64_MIN, I64_MAX])
def test_whole_seconds_print_as_plain_integers(seconds: int) -> None:
    assert str(lvtime.to_decimal(seconds)) == str(seconds)
    assert str(LVTimestamp(seconds).to_decimal()) == str(seconds)
    assert str(lvtime.to_unix_decimal(seconds, 0)) == str(seconds - OFFSET)


def test_whole_unix_seconds_print_as_plain_integers() -> None:
    assert str(lvtime.to_unix_decimal(OFFSET + 1728043200)) == "1728043200"
    assert str(lvtime.to_unix_decimal(OFFSET + 10)) == "10"


def test_from_unix_decimal_reaches_both_ends_of_the_range() -> None:
    assert lvtime.from_unix_decimal(I64_MIN - OFFSET) == (I64_MIN, 0)
    assert lvtime.from_unix_decimal(Decimal(I64_MIN - OFFSET) + Decimal("0.5")) == (
        I64_MIN,
        1 << 63,
    )
    assert lvtime.from_unix_decimal(str(I64_MIN)) == (I64_MIN + OFFSET, 0)
    assert lvtime.from_unix_decimal(I64_MAX - OFFSET) == (I64_MAX, 0)
    for outside in (I64_MIN - OFFSET - 1, I64_MAX - OFFSET + 1):
        with pytest.raises(ValueError, match="outside the timestamp range"):
            lvtime.from_unix_decimal(outside)


def test_from_decimal_reaches_both_ends_of_the_range() -> None:
    assert lvtime.from_decimal(I64_MIN) == (I64_MIN, 0)
    assert lvtime.from_decimal(I64_MAX) == (I64_MAX, 0)
    for outside in (I64_MIN - 1, I64_MAX + 1):
        with pytest.raises(ValueError, match="outside the timestamp range"):
            lvtime.from_decimal(outside)


class _ClaimsUtc(datetime):
    """A naive datetime subclass that claims a UTC offset."""

    def utcoffset(self) -> timedelta | None:
        return timedelta(0)


def test_a_datetime_subclass_cannot_claim_an_offset_it_does_not_have() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        lvtime.from_datetime(_ClaimsUtc(2024, 10, 4, 12))


@pytest.mark.parametrize("convert", [lvtime.from_decimal, lvtime.from_unix_decimal])
@pytest.mark.parametrize("text", ["abc", "1.2.3", "", "0x10", "1e"])
def test_text_that_is_not_a_number_is_named_as_such(convert: object, text: str) -> None:
    assert callable(convert)
    with pytest.raises(ValueError, match="not a decimal number"):
        convert(text)
