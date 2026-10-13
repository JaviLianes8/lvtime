"""Edge promises of the command line: ISO offsets and fractions, interrupt and pipe exit codes."""

from __future__ import annotations

import io
import sys

import pytest

import lvtime
from lvtime._cli import main

NOON_HEX = "00000000e32589400000000000000000"


def _encode(capsys: pytest.CaptureFixture[str], text: str) -> str:
    assert main(["encode", text]) == 0
    return capsys.readouterr().out.strip()


class _Interrupting(io.StringIO):
    def read(self, size: int | None = -1) -> str:
        raise KeyboardInterrupt


class _ClosedPipe(io.StringIO):
    def write(self, text: str) -> int:
        raise BrokenPipeError(32, "Broken pipe")


@pytest.mark.parametrize(
    "text",
    [
        "2024-10-04T05:00:00-07:00",
        "2024-10-04T05:00-0700",
        "20241004T050000-07",
        "2024-10-04T17:30:00+05:30",
        "2024-10-04T12:00:00z",
        "2024-10-04 12:00:00Z",
    ],
)
def test_every_offset_form_names_the_same_instant(
    capsys: pytest.CaptureFixture[str], text: str
) -> None:
    assert _encode(capsys, text) == NOON_HEX


def test_a_negative_offset_is_not_read_as_positive(capsys: pytest.CaptureFixture[str]) -> None:
    west = _encode(capsys, "2024-10-04T12:00:00-01:00")
    east = _encode(capsys, "2024-10-04T12:00:00+01:00")
    assert lvtime.LVTimestamp.from_hex(west).seconds - 3810888000 == 3600
    assert lvtime.LVTimestamp.from_hex(east).seconds - 3810888000 == -3600


@pytest.mark.parametrize(
    "digits",
    ["1234567890", "1234567890123456789012345", "0000000000000000000542101086242752217", "9" * 90],
)
def test_every_fraction_digit_is_kept(capsys: pytest.CaptureFixture[str], digits: str) -> None:
    got = lvtime.LVTimestamp.from_hex(_encode(capsys, f"2024-10-04T12:00:00.{digits}Z"))
    assert got == lvtime.LVTimestamp.from_decimal(f"3810888000.{digits}")
    comma = lvtime.LVTimestamp.from_hex(_encode(capsys, f"2024-10-04T12:00:00,{digits}Z"))
    assert comma == got


@pytest.mark.parametrize(
    "text",
    [
        "2024-10-04T12:0000Z",
        "20241004T1200:00Z",
        "2024-1004T12:00:00Z",
        "2024-10-04T12:00:00+24:00",
    ],
)
def test_mixed_separators_and_bad_offsets_are_bad_input(
    capsys: pytest.CaptureFixture[str], text: str
) -> None:
    assert main(["encode", text]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.startswith("lvtime: not an ISO 8601 datetime")


def test_an_interrupt_while_reading_stdin_exits_130(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "stdin", _Interrupting())
    assert main(["decode"]) == 130
    assert main(["encode"]) == 130


def test_a_reader_that_went_away_gives_exit_1(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "stdout", _ClosedPipe())
    assert main(["decode", NOON_HEX]) == 1
    assert main(["encode", "2024-10-04T12:00:00Z"]) == 1
