from datetime import datetime, timezone

import pytest

from lvtime import LVTimestamp, read_timestamp, write_timestamp

UTC = timezone.utc


def test_bytes_round_trip_preserves_both_fields() -> None:
    ts = LVTimestamp(1234567890, 9876543210123456789)
    assert read_timestamp(write_timestamp(ts)) == ts


def test_on_disk_form_is_sixteen_bytes() -> None:
    assert len(write_timestamp(LVTimestamp(0, 0))) == 16


def test_known_big_endian_layout() -> None:
    ts = LVTimestamp(1, 1 << 63)
    expected = (1).to_bytes(8, "big") + (1 << 63).to_bytes(8, "big")
    assert write_timestamp(ts) == expected


def test_all_zero_bytes_are_the_epoch() -> None:
    ts = read_timestamp(bytes(16))
    assert ts == LVTimestamp(0, 0)
    assert ts.to_datetime() == datetime(1904, 1, 1, tzinfo=UTC)


def test_negative_seconds_use_signed_encoding() -> None:
    ts = LVTimestamp(-1, 0)
    data = write_timestamp(ts)
    assert data[:8] == b"\xff\xff\xff\xff\xff\xff\xff\xff"
    assert read_timestamp(data) == ts


def test_datetime_round_trip_through_the_type() -> None:
    dt = datetime(1999, 12, 31, 23, 59, 59, 654321, tzinfo=UTC)
    assert LVTimestamp.from_datetime(dt).to_datetime() == dt


def test_one_fraction_unit_is_below_datetime_resolution() -> None:
    # The integer pair keeps sub-microsecond detail that datetime cannot hold.
    coarse = LVTimestamp(0, 0)
    fine = LVTimestamp(0, 1)
    assert fine != coarse
    assert fine.to_bytes() != coarse.to_bytes()
    assert fine.to_datetime() == coarse.to_datetime()


def test_frac_defaults_to_zero() -> None:
    assert LVTimestamp(5).frac == 0


def test_timestamp_is_immutable() -> None:
    ts = LVTimestamp(0, 0)
    with pytest.raises(AttributeError):
        ts.seconds = 1  # type: ignore[misc]


def test_rejects_seconds_above_signed_64_bit() -> None:
    with pytest.raises(ValueError):
        LVTimestamp(1 << 63, 0)


def test_rejects_seconds_below_signed_64_bit() -> None:
    with pytest.raises(ValueError):
        LVTimestamp(-(1 << 63) - 1, 0)


def test_rejects_fraction_above_unsigned_64_bit() -> None:
    with pytest.raises(ValueError):
        LVTimestamp(0, 1 << 64)


def test_rejects_negative_fraction() -> None:
    with pytest.raises(ValueError):
        LVTimestamp(0, -1)


def test_read_timestamp_rejects_wrong_length() -> None:
    with pytest.raises(ValueError):
        read_timestamp(b"\x00\x00\x00")
