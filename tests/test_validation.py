"""Every public entry point refuses bad input with the documented error type and a short message."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import pytest

import lvtime
from lvtime import LVTimestamp

PAIR_FUNCTIONS: list[Callable[[Any, Any], object]] = [
    lvtime.to_datetime,
    lvtime.to_float,
    lvtime.to_unix,
    lvtime.to_decimal,
    lvtime.to_unix_decimal,
    LVTimestamp,
]


class _Index:
    """An integer type that is not ``int`` (like a NumPy integer)."""

    def __init__(self, value: int) -> None:
        self.value = value

    def __index__(self) -> int:
        return self.value


@pytest.mark.parametrize("function", PAIR_FUNCTIONS)
@pytest.mark.parametrize("bad", [1.0, "1", True, None, Decimal(1)])
def test_pair_functions_refuse_non_integers(function: Callable[..., object], bad: object) -> None:
    with pytest.raises(TypeError):
        function(bad, 0)
    with pytest.raises(TypeError):
        function(0, bad)


@pytest.mark.parametrize("function", PAIR_FUNCTIONS)
@pytest.mark.parametrize(("seconds", "frac"), [(2**63, 0), (-(2**63) - 1, 0), (0, -1), (0, 2**64)])
def test_pair_functions_refuse_out_of_range_fields(
    function: Callable[..., object], seconds: int, frac: int
) -> None:
    with pytest.raises(ValueError):
        function(seconds, frac)


@pytest.mark.parametrize("function", PAIR_FUNCTIONS)
def test_pair_functions_accept_the_extreme_fields(function: Callable[..., object]) -> None:
    for seconds, frac in [(-(2**63), 0), (2**63 - 1, 2**64 - 1)]:
        try:
            function(seconds, frac)
        except OverflowError:
            assert function is lvtime.to_datetime


def test_integer_like_values_are_accepted_and_stored_as_int() -> None:
    ts = LVTimestamp(_Index(5), _Index(7))
    assert (ts.seconds, ts.frac) == (5, 7)
    assert type(ts.seconds) is int and type(ts.frac) is int
    assert lvtime.to_float(_Index(1), _Index(1 << 63)) == 1.5


def test_to_datetime_reports_the_datetime_range_as_overflow() -> None:
    with pytest.raises(OverflowError, match="years 1 to 9999"):
        lvtime.to_datetime(2**63 - 1)
    with pytest.raises(OverflowError):
        lvtime.to_datetime(-(2**63))


@pytest.mark.parametrize("bad", [None, "2024-01-01", date(2024, 1, 1), 0])
def test_from_datetime_refuses_non_datetimes(bad: object) -> None:
    with pytest.raises(TypeError):
        lvtime.from_datetime(bad)  # type: ignore[arg-type]


def test_from_datetime_refuses_naive_datetimes() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        lvtime.from_datetime(datetime(2024, 1, 1))


@pytest.mark.parametrize("function", [lvtime.from_float, lvtime.from_unix])
@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -float("inf"), 1e300, -1e300])
def test_float_inputs_must_be_finite_and_in_range(
    function: Callable[[float], object], bad: float
) -> None:
    with pytest.raises(ValueError):
        function(bad)


@pytest.mark.parametrize("function", [lvtime.from_float, lvtime.from_unix])
@pytest.mark.parametrize("bad", ["1.5", True, None, Decimal("1.5")])
def test_float_inputs_refuse_other_types(function: Callable[[Any], object], bad: object) -> None:
    with pytest.raises(TypeError):
        function(bad)


@pytest.mark.parametrize("function", [lvtime.from_float, lvtime.from_unix])
def test_float_inputs_accept_integers_exactly(function: Callable[[Any], object]) -> None:
    assert lvtime.from_float(2**62) == (2**62, 0)
    assert function(_Index(3)) == function(3)


@pytest.mark.parametrize("function", [lvtime.from_decimal, lvtime.from_unix_decimal])
@pytest.mark.parametrize("bad", [1.5, True, None, b"1", [1]])
def test_exact_inputs_refuse_other_types(function: Callable[[Any], object], bad: object) -> None:
    with pytest.raises(TypeError):
        function(bad)


@pytest.mark.parametrize("function", [lvtime.from_decimal, lvtime.from_unix_decimal])
@pytest.mark.parametrize(
    "bad", ["abc", "", "nan", "inf", "-Infinity", "sNaN", Decimal("nan"), "1e999999999", 2**200]
)
def test_exact_inputs_refuse_bad_values(function: Callable[[Any], object], bad: object) -> None:
    with pytest.raises(ValueError):
        function(bad)


def test_exact_range_edges() -> None:
    assert lvtime.from_decimal(2**63 - 1) == (2**63 - 1, 0)
    assert lvtime.from_decimal(-(2**63)) == (-(2**63), 0)
    top = lvtime.to_decimal(2**63 - 1, 2**64 - 1)
    assert lvtime.from_decimal(str(top)) == (2**63 - 1, 2**64 - 1)
    with pytest.raises(ValueError):
        lvtime.from_decimal(f"{2**63 - 1}.{'9' * 30}")
    assert lvtime.from_decimal(f"-{2**63}.000000000000000000001") == (-(2**63), 0)
    with pytest.raises(ValueError):
        lvtime.from_decimal(f"-{2**63}.0000000000000000001")


@pytest.mark.parametrize("bad", ["middle", "BIG", "", None, ["big"], b"big"])
def test_byte_order_must_be_big_or_little(bad: object) -> None:
    calls: list[Callable[[], object]] = [
        lambda: LVTimestamp(0).to_bytes(bad),  # type: ignore[arg-type]
        lambda: LVTimestamp.from_bytes(bytes(16), bad),  # type: ignore[arg-type]
        lambda: lvtime.read_timestamps(b"", bad),  # type: ignore[arg-type]
        lambda: lvtime.write_timestamps([], bad),  # type: ignore[arg-type]
    ]
    for call in calls:
        with pytest.raises(ValueError, match="byteorder"):
            call()


@pytest.mark.parametrize("bad", ["00" * 16, 16, None, [0] * 16])
def test_byte_readers_refuse_non_buffers(bad: object) -> None:
    with pytest.raises(TypeError):
        lvtime.read_timestamp(bad)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        lvtime.read_timestamps(bad)  # type: ignore[arg-type]


def test_byte_readers_accept_every_bytes_like_buffer() -> None:
    raw = LVTimestamp(7, 9).to_bytes()
    for buffer in (raw, bytearray(raw), memoryview(raw), memoryview(raw).cast("Q")):
        assert lvtime.read_timestamp(buffer) == LVTimestamp(7, 9)
        assert lvtime.read_timestamps(buffer) == [LVTimestamp(7, 9)]


@pytest.mark.parametrize("length", [0, 15, 17, 32])
def test_read_timestamp_needs_exactly_16_bytes(length: int) -> None:
    with pytest.raises(ValueError, match=f"got {length}"):
        lvtime.read_timestamp(bytes(length))


def test_writers_refuse_things_that_are_not_timestamps() -> None:
    with pytest.raises(TypeError):
        lvtime.write_timestamp((0, 0))  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        lvtime.write_timestamps([LVTimestamp(0), (0, 0)])  # type: ignore[list-item]
    with pytest.raises(TypeError):
        lvtime.write_timestamps(LVTimestamp(0))  # type: ignore[arg-type]


def test_from_hex_refuses_non_text_and_bad_hex() -> None:
    with pytest.raises(TypeError):
        LVTimestamp.from_hex(b"00" * 16)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        LVTimestamp.from_hex("zz" * 16)
