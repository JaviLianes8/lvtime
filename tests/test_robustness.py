"""Hostile callers and environments: subclasses that lie, odd decimal contexts, broken streams."""

from __future__ import annotations

import decimal
import io
import subprocess
import sys
from decimal import Decimal

import pytest
from _cli_command import cli_command, cli_env, run_cli

import lvtime
from lvtime._cli import main


def test_a_customised_default_context_does_not_leak_in() -> None:
    code = (
        "import decimal\n"
        "decimal.DefaultContext.traps[decimal.Inexact] = True\n"
        "decimal.DefaultContext.traps[decimal.Rounded] = True\n"
        "decimal.DefaultContext.prec = 3\n"
        "import lvtime\n"
        "print(lvtime.from_decimal('0.' + '3' * 120))\n"
        "print(lvtime.to_decimal(3810888000, 1))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, env=cli_env(), timeout=60
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines()[0] == str(lvtime.from_decimal(Decimal("0." + "3" * 120)))


def test_rejected_text_leaves_the_callers_flags_clean() -> None:
    with decimal.localcontext() as context:
        context.traps[decimal.InvalidOperation] = False
        context.clear_flags()
        with pytest.raises(ValueError):
            lvtime.from_decimal("abc")
        assert not any(context.flags.values())


class _LoudFloat(float):
    def __repr__(self) -> str:
        return "x" * 1_000_000

    def as_integer_ratio(self) -> tuple[int, int]:
        return (1, 0)


def test_float_subclasses_cannot_lie_about_themselves() -> None:
    assert lvtime.from_float(_LoudFloat(1.5)) == (1, 1 << 63)
    with pytest.raises(ValueError) as caught:
        lvtime.from_float(_LoudFloat("nan"))
    assert len(str(caught.value)) < 120


class _LyingDecimal(Decimal):
    def __lt__(self, other: object) -> bool:
        return True


def test_decimal_subclasses_cannot_skip_the_range_check() -> None:
    with pytest.raises(ValueError, match="outside the timestamp range"):
        lvtime.from_decimal(_LyingDecimal("1e30"))


def test_missing_stdin_is_bad_input(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "stdin", None)
    assert main(["decode"]) == 1


class _BrokenStdin(io.StringIO):
    def read(self, size: int | None = -1) -> str:
        raise OSError(5, "I/O error")


def test_a_failing_stdin_is_bad_input(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "stdin", _BrokenStdin())
    assert main(["encode"]) == 1


def test_bad_input_with_a_closed_stderr_still_exits_one() -> None:
    process = subprocess.Popen(
        [*cli_command(), "decode", "zz"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=cli_env(),
    )
    assert process.stdout is not None and process.stderr is not None
    process.stderr.close()
    process.stdout.read()
    process.stdout.close()
    assert process.wait(timeout=60) == 1


def test_usage_errors_do_not_echo_huge_arguments() -> None:
    result = run_cli("decode", "--byteorder", "x" * 30_000)
    assert result.returncode == 2
    assert len(result.stderr) < 1000


def test_non_ascii_digits_are_not_a_fraction() -> None:
    result = run_cli("encode", "2024-10-04T12:00:00." + chr(0x661) + "Z")
    assert result.returncode == 1
