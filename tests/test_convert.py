from datetime import datetime, timezone

import pytest

from lvtime import (
    LABVIEW_UNIX_EPOCH_OFFSET,
    from_datetime,
    from_float,
    from_unix,
    to_datetime,
    to_float,
    to_unix,
)

UTC = timezone.utc


def test_epoch_offset_matches_the_published_constant() -> None:
    assert LABVIEW_UNIX_EPOCH_OFFSET == 2082844800


def test_zero_is_the_labview_epoch() -> None:
    assert to_datetime(0) == datetime(1904, 1, 1, tzinfo=UTC)


def test_the_unix_epoch_offset_lands_on_1970() -> None:
    assert to_datetime(LABVIEW_UNIX_EPOCH_OFFSET) == datetime(1970, 1, 1, tzinfo=UTC)


def test_from_datetime_of_the_epoch_is_the_zero_pair() -> None:
    assert from_datetime(datetime(1904, 1, 1, tzinfo=UTC)) == (0, 0)


def test_half_fraction_is_half_a_second() -> None:
    result = to_datetime(0, 1 << 63)
    assert result == datetime(1904, 1, 1, 0, 0, 0, 500000, tzinfo=UTC)


def test_negative_seconds_predate_the_epoch() -> None:
    assert to_datetime(-86400) == datetime(1903, 12, 31, tzinfo=UTC)


def test_datetime_round_trip_is_microsecond_exact() -> None:
    dt = datetime(2020, 6, 15, 12, 30, 45, 123456, tzinfo=UTC)
    seconds, frac = from_datetime(dt)
    assert to_datetime(seconds, frac) == dt


def test_result_is_timezone_aware_utc() -> None:
    assert to_datetime(0).tzinfo == UTC


def test_from_datetime_accepts_other_timezones() -> None:
    from datetime import timedelta

    tz = timezone(timedelta(hours=2))
    aware = datetime(1970, 1, 1, 2, 0, 0, tzinfo=tz)
    assert from_datetime(aware) == (LABVIEW_UNIX_EPOCH_OFFSET, 0)


def test_from_datetime_rejects_naive_datetime() -> None:
    with pytest.raises(ValueError):
        from_datetime(datetime(1970, 1, 1))


def test_to_datetime_rejects_fraction_above_the_range() -> None:
    with pytest.raises(ValueError):
        to_datetime(0, 1 << 64)


def test_to_datetime_rejects_negative_fraction() -> None:
    with pytest.raises(ValueError):
        to_datetime(0, -1)


def test_to_datetime_overflows_outside_the_datetime_range() -> None:
    with pytest.raises(OverflowError):
        to_datetime(1 << 62)


def test_to_unix_at_the_unix_epoch_is_zero() -> None:
    assert to_unix(LABVIEW_UNIX_EPOCH_OFFSET) == 0.0


def test_to_unix_keeps_the_half_second_fraction() -> None:
    assert to_unix(LABVIEW_UNIX_EPOCH_OFFSET, 1 << 63) == 0.5


def test_from_unix_of_zero_is_the_unix_epoch_pair() -> None:
    assert from_unix(0.0) == (LABVIEW_UNIX_EPOCH_OFFSET, 0)


def test_unix_round_trip_matches_datetime_timestamp() -> None:
    dt = datetime(2021, 3, 14, 15, 9, 26, tzinfo=UTC)
    seconds, frac = from_datetime(dt)
    assert to_unix(seconds, frac) == dt.timestamp()


def test_from_unix_handles_times_before_the_unix_epoch() -> None:
    seconds, frac = from_unix(-0.5)
    assert to_datetime(seconds, frac) == datetime(1969, 12, 31, 23, 59, 59, 500000, tzinfo=UTC)


def test_to_float_is_seconds_since_the_1904_epoch() -> None:
    assert to_float(10, 1 << 63) == 10.5


def test_from_float_splits_into_seconds_and_fraction() -> None:
    assert from_float(10.5) == (10, 1 << 63)


def test_from_float_floors_negative_values() -> None:
    seconds, frac = from_float(-1.5)
    assert seconds == -2
    assert frac == 1 << 63


def test_to_float_rejects_fraction_out_of_range() -> None:
    with pytest.raises(ValueError):
        to_float(0, 1 << 64)
