from datetime import datetime, timezone

import pytest

from lvtime import (
    LABVIEW_UNIX_EPOCH_OFFSET,
    LVTimestamp,
    read_timestamp,
    read_timestamps,
    write_timestamp,
    write_timestamps,
)

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


def test_little_endian_reverses_each_eight_byte_field() -> None:
    ts = LVTimestamp(1, 1 << 63)
    expected = (1).to_bytes(8, "little") + (1 << 63).to_bytes(8, "little")
    assert write_timestamp(ts, "little") == expected


def test_little_endian_round_trip() -> None:
    ts = LVTimestamp(-1234567890, 9876543210123456789)
    assert read_timestamp(write_timestamp(ts, "little"), "little") == ts


def test_byte_order_matters_for_non_palindromes() -> None:
    ts = LVTimestamp(1, 0)
    assert write_timestamp(ts, "big") != write_timestamp(ts, "little")


def test_from_bytes_rejects_unknown_byte_order() -> None:
    with pytest.raises(ValueError):
        LVTimestamp.from_bytes(bytes(16), "middle")  # type: ignore[arg-type]


def test_min_and_max_seconds_survive_the_byte_round_trip() -> None:
    for seconds in (-(2**63), 2**63 - 1):
        ts = LVTimestamp(seconds, 2**64 - 1)
        assert read_timestamp(write_timestamp(ts)) == ts


def test_unix_round_trip_through_the_type() -> None:
    ts = LVTimestamp.from_unix(0.0)
    assert ts == LVTimestamp(LABVIEW_UNIX_EPOCH_OFFSET, 0)
    assert ts.to_unix() == 0.0


def test_float_round_trip_through_the_type() -> None:
    ts = LVTimestamp.from_float(10.5)
    assert ts == LVTimestamp(10, 1 << 63)
    assert ts.to_float() == 10.5


def test_write_and_read_timestamps_round_trip_a_batch() -> None:
    batch = [LVTimestamp(0, 0), LVTimestamp(1, 1 << 63), LVTimestamp(-5, 42)]
    assert read_timestamps(write_timestamps(batch)) == batch


def test_write_timestamps_concatenates_each_record() -> None:
    batch = [LVTimestamp(1, 0), LVTimestamp(2, 0)]
    assert write_timestamps(batch) == write_timestamp(batch[0]) + write_timestamp(batch[1])


def test_read_timestamps_of_empty_bytes_is_empty() -> None:
    assert read_timestamps(b"") == []


def test_read_timestamps_rejects_a_partial_record() -> None:
    with pytest.raises(ValueError):
        read_timestamps(bytes(17))


def test_batch_honours_little_endian() -> None:
    batch = [LVTimestamp(7, 9), LVTimestamp(-7, 9)]
    assert read_timestamps(write_timestamps(batch, "little"), "little") == batch
