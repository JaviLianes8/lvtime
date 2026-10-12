"""Real end-to-end tests of ``lvtime encode``: fractions, offsets and errors, by subprocess."""

from __future__ import annotations

import pytest
from _cli_command import run_cli

import lvtime


@pytest.mark.parametrize(
    ("text", "exact"),
    [
        ("2024-10-04T12:00:00.5Z", "3810888000.5"),
        ("2024-10-04T12:00:00.123456789Z", "3810888000.123456789"),
        ("2024-10-04 14:00:00,25+02:00", "3810888000.25"),
        ("1903-12-31T23:59:59.75Z", "-0.25"),
        ("1904-01-01T00:00:00.0000000000000000000000001Z", "0.0000000000000000000000001"),
    ],
)
def test_encode_keeps_every_fractional_digit(text: str, exact: str) -> None:
    result = run_cli("encode", text)
    assert result.returncode == 0, result.stderr
    assert result.stdout == lvtime.LVTimestamp.from_decimal(exact).hex() + "\n"


@pytest.mark.parametrize("text", ["2024-10-04T12:00:00.5abc", "2024-13-04T12:00:00.5Z", "12:00"])
def test_encode_refuses_text_that_is_not_an_iso_datetime(text: str) -> None:
    result = run_cli("encode", text)
    assert result.returncode == 1
    assert result.stderr.startswith("lvtime: not an ISO 8601 datetime")


@pytest.mark.parametrize(
    ("text", "exact"),
    [
        ("2024-10-04T12:00:00.5+0200", "3810880800.5"),
        ("2024-10-04T12:00:00.5-00:30:00.25", "3810889800.75"),
    ],
)
def test_encode_applies_the_offset_exactly(text: str, exact: str) -> None:
    result = run_cli("encode", text)
    assert result.returncode == 0, result.stderr
    assert result.stdout == lvtime.LVTimestamp.from_decimal(exact).hex() + "\n"


def test_encode_never_takes_the_offset_fraction_for_the_time_fraction() -> None:
    result = run_cli("encode", "2024-10-04T12:00:00+05:30:00.5")
    expected = lvtime.LVTimestamp.from_decimal("3810868199.5").hex()
    assert (result.returncode, result.stdout) == (0, expected + "\n")


def test_encode_errors_quote_what_the_user_typed() -> None:
    result = run_cli("encode", "2024-10-04T12:00:00.5+02:00x")
    assert result.stderr == "lvtime: not an ISO 8601 datetime: '2024-10-04T12:00:00.5+02:00x'\n"
