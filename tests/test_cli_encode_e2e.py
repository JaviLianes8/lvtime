"""Real end-to-end tests of ``lvtime encode``: fractions, offsets and errors, by subprocess."""

from __future__ import annotations

import time

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
    ],
)
def test_encode_applies_the_offset_exactly(text: str, exact: str) -> None:
    result = run_cli("encode", text)
    assert result.returncode == 0, result.stderr
    assert result.stdout == lvtime.LVTimestamp.from_decimal(exact).hex() + "\n"


@pytest.mark.parametrize(
    "text",
    [
        "2024-10-04T12:00:00+05:30:00.5",
        "2024-10-04T12:00:00.5-00:30:00.25",
        "2024-01-01T00:00:00+00:00:00.5",
        "20241004T120000.5+053015",
        "2024-01-01T00:00.5Z",
        "2024-01-01T00.5Z",
        "20240101T0000.5Z",
        "2024-10-04t12:00:00.123456789Z",
        "2024-10-04x12:00:00.5",
        "2024-W40-5T12:00:00.5Z",
        "2024100411200001234567",
        "2024-1004T12:00:00.5Z",
        "2024-10-04T1200:00.5Z",
        "2024-10-04T120000.5Z",
        "2024-10-04T24:00:00.5Z",
        "2024-10-04T12:00:00.5+24:00",
        "2024-10-04T12:00:00.5+05:60",
        "0000-01-01T00:00:00Z",
        "999-01-01T00:00:00Z",
        "0241004T000000Z",
        "12024-01-01T00:00:00Z",
        "120240101T000000Z",
    ],
)
def test_encode_refuses_everything_outside_its_grammar(text: str) -> None:
    result = run_cli("encode", text)
    assert result.returncode == 1
    assert result.stderr.startswith("lvtime: not an ISO 8601 datetime")


def test_encode_stays_linear_on_a_long_fraction_with_junk_after_it() -> None:
    start = time.perf_counter()
    result = run_cli("encode", stdin="2024-10-04T12:00:00." + "1" * 200_000 + "\nx")
    assert result.returncode == 1
    assert time.perf_counter() - start < 10


@pytest.mark.parametrize(
    ("text", "exact"),
    [
        ("20241004T120000.123456789Z", "3810888000.123456789"),
        ("20241004T140000.5+0200", "3810888000.5"),
        ("2024-10-04T14:00:00.5+02", "3810888000.5"),
    ],
)
def test_encode_takes_the_basic_form_and_short_offsets(text: str, exact: str) -> None:
    result = run_cli("encode", text)
    assert result.returncode == 0, result.stderr
    assert result.stdout == lvtime.LVTimestamp.from_decimal(exact).hex() + "\n"


def test_encode_errors_quote_what_the_user_typed() -> None:
    result = run_cli("encode", "2024-10-04T12:00:00.5+02:00x")
    assert result.stderr == "lvtime: not an ISO 8601 datetime: '2024-10-04T12:00:00.5+02:00x'\n"


def test_encode_ignores_surrounding_whitespace() -> None:
    expected = "00000000e32589400000000000000000\n"
    assert run_cli("encode", "  2024-10-04T12:00:00Z  ").stdout == expected
    assert run_cli("encode", stdin="  2024-10-04T12:00:00Z  \n").stdout == expected
