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
