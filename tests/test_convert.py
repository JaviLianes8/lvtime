from datetime import datetime, timezone

import pytest

from lvtime import LABVIEW_UNIX_EPOCH_OFFSET, from_datetime, to_datetime

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
