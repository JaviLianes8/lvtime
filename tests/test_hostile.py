"""Hostile input stays cheap and error messages stay short."""

from __future__ import annotations

import contextlib
import time
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

import pytest

import lvtime
from lvtime import LVTimestamp


@pytest.mark.parametrize(
    "call",
    [
        lambda: lvtime.from_float(1e300),
        lambda: lvtime.from_unix(-1e300),
        lambda: lvtime.from_decimal(10**60),
        lambda: lvtime.from_decimal(2**63),
        lambda: lvtime.from_decimal("9223372036854775807.99999999999999999999999"),
        lambda: lvtime.from_unix_decimal("-1e30"),
    ],
)
def test_out_of_range_values_share_one_message(call: Callable[[], object]) -> None:
    with pytest.raises(ValueError, match=r"^the value is outside the timestamp range \(") as caught:
        call()
    assert ", got" not in str(caught.value)


@pytest.mark.parametrize(
    "call",
    [
        lambda: LVTimestamp(10**30_000, 0),
        lambda: LVTimestamp(10**4000, 0),
        lambda: lvtime.to_float(0, -(2**5000)),
        lambda: LVTimestamp(0, -(10**30_000)),
        lambda: lvtime.from_decimal("9" * 1_000_000),
        lambda: lvtime.from_decimal("x" * 1_000_000),
        lambda: LVTimestamp(0).to_bytes("x" * 1_000_000),  # type: ignore[arg-type]
        lambda: lvtime.from_datetime(datetime(2024, 1, 1)),
    ],
)
def test_error_messages_stay_short(call: Callable[[], object]) -> None:
    with pytest.raises((TypeError, ValueError)) as caught:
        call()
    assert len(str(caught.value)) < 120


@pytest.mark.parametrize(
    "text",
    [
        "1e999999999",
        "1e-999999999",
        "-1e-999999999",
        "0e999999999",
        "9" * 2_000_000,
        "0." + "7" * 2_000_000,
    ],
    ids=["huge-exponent", "tiny-exponent", "negative-tiny", "zero-huge", "long-int", "long-frac"],
)
def test_hostile_decimal_text_is_handled_quickly(text: str) -> None:
    start = time.perf_counter()
    with contextlib.suppress(ValueError):
        lvtime.from_decimal(text)
    assert time.perf_counter() - start < 5


def test_aware_datetimes_in_any_zone_give_the_same_instant() -> None:
    utc = datetime(2024, 10, 4, 12, tzinfo=timezone.utc)
    shifted = utc.astimezone(timezone(timedelta(hours=-7, minutes=-30)))
    assert lvtime.from_datetime(shifted) == lvtime.from_datetime(utc)


def test_a_value_is_shown_whole_up_to_the_limit_and_cut_after_it() -> None:
    from lvtime._validate import short

    assert short("x" * 38) == repr("x" * 38)  # 40 characters with the quotes
    assert short("x" * 39).endswith("... (41 characters)")


def test_a_64_bit_value_is_printed_and_a_wider_one_described() -> None:
    with pytest.raises(ValueError, match=r"got 9223372036854775808$"):
        LVTimestamp(2**63)
    with pytest.raises(ValueError, match=r"got an integer of 65 bits$"):
        LVTimestamp(2**64)


def test_from_float_names_both_accepted_types() -> None:
    with pytest.raises(TypeError, match=r"^value must be a float or an integer, got str$"):
        lvtime.from_float("abc")  # type: ignore[arg-type]


def test_a_type_name_is_shown_whole_up_to_the_limit() -> None:
    exact = type("T" * 40, (), {})
    with pytest.raises(TypeError) as caught:
        LVTimestamp(exact())
    assert str(caught.value).endswith("T" * 40)
