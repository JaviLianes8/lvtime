from decimal import Decimal

import pytest

from lvtime import (
    LABVIEW_UNIX_EPOCH_OFFSET,
    LVTimestamp,
    from_decimal,
    from_unix_decimal,
    to_decimal,
    to_unix_decimal,
)


def test_to_decimal_of_the_epoch_is_zero() -> None:
    assert to_decimal(0, 0) == Decimal(0)


def test_to_decimal_keeps_full_fixed_point_resolution() -> None:
    # One fraction unit is exactly 2**-64 s; a float cannot hold this, a Decimal can.
    one_unit = to_decimal(0, 1)
    assert one_unit == Decimal("5.42101086242752217003726400434970855712890625E-20")
    assert one_unit != Decimal(0)
    assert one_unit * Decimal(2**64) == Decimal(1)


def test_from_decimal_accepts_decimal_int_and_str() -> None:
    assert from_decimal(Decimal("10.5")) == (10, 1 << 63)
    assert from_decimal(10) == (10, 0)
    assert from_decimal("10.5") == (10, 1 << 63)


def test_from_decimal_refuses_float() -> None:
    with pytest.raises(TypeError):
        from_decimal(10.5)  # type: ignore[arg-type]


def test_from_decimal_floors_negative_values() -> None:
    assert from_decimal("-1.5") == (-2, 1 << 63)


def test_decimal_round_trip_is_exact_for_dyadic_fractions() -> None:
    for seconds, frac in [(0, 0), (1, 1 << 63), (-3, 1 << 62), (123456, 3 << 61)]:
        assert from_decimal(to_decimal(seconds, frac)) == (seconds, frac)


def test_to_unix_decimal_at_the_unix_epoch_is_zero() -> None:
    assert to_unix_decimal(LABVIEW_UNIX_EPOCH_OFFSET, 0) == Decimal(0)


def test_unix_decimal_round_trip() -> None:
    assert from_unix_decimal(to_unix_decimal(LABVIEW_UNIX_EPOCH_OFFSET, 1 << 63)) == (
        LABVIEW_UNIX_EPOCH_OFFSET,
        1 << 63,
    )


def test_from_unix_decimal_of_zero_is_the_unix_epoch_pair() -> None:
    assert from_unix_decimal("0") == (LABVIEW_UNIX_EPOCH_OFFSET, 0)


def test_type_methods_match_the_module_functions() -> None:
    ts = LVTimestamp(42, 1 << 63)
    assert ts.to_decimal() == to_decimal(42, 1 << 63)
    assert ts.to_unix_decimal() == to_unix_decimal(42, 1 << 63)
    assert LVTimestamp.from_decimal("42.5") == LVTimestamp(42, 1 << 63)
    assert LVTimestamp.from_unix_decimal("0") == LVTimestamp(LABVIEW_UNIX_EPOCH_OFFSET, 0)


def test_from_decimal_rejects_out_of_range_seconds() -> None:
    with pytest.raises(ValueError):
        from_decimal(str(2**63))


def test_hex_round_trip_on_the_type() -> None:
    ts = LVTimestamp(3092601600, 0)
    assert ts.hex() == "00000000b8555b000000000000000000"
    assert LVTimestamp.from_hex(ts.hex()) == ts


def test_hex_honours_byte_order() -> None:
    ts = LVTimestamp(1, 0)
    assert ts.hex("big") != ts.hex("little")
    assert LVTimestamp.from_hex(ts.hex("little"), "little") == ts
