"""The complete promise, pinned to NI's own documented byte values.

The authoritative reference is NI's value table (decimal and hex byte pairs), not
the human-readable labels beside them. NI's page mislabels {3092601600, 0} as
"01/01/2002 00:00:00.000 UTC", but that value is 2001-12-31 00:00:00 UTC, one day
earlier; the byte value is the truth and is what we pin here.
"""

from datetime import datetime, timezone
from decimal import Decimal

from lvtime import (
    LVTimestamp,
    from_decimal,
    read_timestamp,
    to_decimal,
    write_timestamp,
)

UTC = timezone.utc

# Each NI row: label, seconds, fraction, big-endian 16-byte hex, exact UTC instant.
EPOCH = (0, 0x0, "00000000000000000000000000000000", datetime(1904, 1, 1, tzinfo=UTC))
Y2002 = (3092601600, 0x0, "00000000b8555b000000000000000000", datetime(2001, 12, 31, tzinfo=UTC))
NEG_HALF = (
    -1,
    0x8000000000000000,
    "ffffffffffffffff8000000000000000",
    datetime(1903, 12, 31, 23, 59, 59, 500000, tzinfo=UTC),
)
NEG_FIVE_TWO = (
    -6,
    0xCCCCCCCCCCCCCCCD,
    "fffffffffffffffacccccccccccccccd",
    datetime(1903, 12, 31, 23, 59, 54, 800000, tzinfo=UTC),
)

GOLDEN = [EPOCH, Y2002, NEG_HALF, NEG_FIVE_TWO]


def test_golden_pairs_flatten_to_the_documented_big_endian_bytes() -> None:
    for seconds, frac, hex_text, _ in GOLDEN:
        assert write_timestamp(LVTimestamp(seconds, frac)).hex() == hex_text


def test_golden_bytes_unflatten_to_the_documented_pairs() -> None:
    for seconds, frac, hex_text, _ in GOLDEN:
        assert read_timestamp(bytes.fromhex(hex_text)) == LVTimestamp(seconds, frac)


def test_golden_pairs_decode_to_the_true_utc_instant() -> None:
    for seconds, frac, _, instant in GOLDEN:
        assert LVTimestamp(seconds, frac).to_datetime() == instant


def test_2002_row_is_really_2001_12_31_not_the_mislabelled_date() -> None:
    # Guards against "fixing" the code to match NI's wrong label.
    assert LVTimestamp(3092601600, 0).to_datetime() == datetime(2001, 12, 31, tzinfo=UTC)
    assert LVTimestamp(3092601600, 0).to_datetime() != datetime(2002, 1, 1, tzinfo=UTC)


def test_the_exact_decimal_path_reproduces_the_ni_fraction_bytes() -> None:
    # 0.8 s is exactly 0xCCCCCCCCCCCCCCCD in 2**-64 units; the Decimal path hits it.
    assert from_decimal("-5.2") == (-6, 0xCCCCCCCCCCCCCCCD)
    assert from_decimal("-0.5") == (-1, 0x8000000000000000)


def test_the_float_path_cannot_reach_the_ni_fraction_bytes() -> None:
    # Documents the NI rounding caveat: a double collapses 0.8 to 0xCCCCCCCCCCCCC000.
    from lvtime import from_float

    assert from_float(-5.2) == (-6, 0xCCCCCCCCCCCCC000)
    assert from_float(-5.2) != from_decimal("-5.2")


def test_dyadic_fractions_round_trip_through_decimal_exactly() -> None:
    assert to_decimal(-1, 0x8000000000000000) == Decimal("-0.5")
    assert to_decimal(0, 0x8000000000000000) == Decimal("0.5")
    assert from_decimal(to_decimal(0, 0x4000000000000000)) == (0, 0x4000000000000000)
