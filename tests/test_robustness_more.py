"""More hostile callers: buffers and reprs that lie, decimal contexts set before import."""

from __future__ import annotations

import decimal
import subprocess
import sys

import pytest
from _cli_command import cli_env

import lvtime
from lvtime import LVTimestamp
from lvtime._cli import main


class _ShortBytes(bytes):
    def __len__(self) -> int:
        return 16


class _SneakyBytes(bytes):
    def __bytes__(self) -> bytes:
        return _ShortBytes(b"\0" * 8)


def test_a_buffer_cannot_swap_itself_for_another() -> None:
    with pytest.raises(ValueError, match="got 1"):
        lvtime.read_timestamp(_SneakyBytes(b"x"))
    with pytest.raises(ValueError):
        lvtime.read_timestamps(_SneakyBytes(b"x"))


class _ZeroLength(str):
    def __len__(self) -> int:
        return 0


class _LoudText(str):
    def __repr__(self) -> str:
        return _ZeroLength("q" * 1_000_000)


def test_a_lying_repr_cannot_blow_up_messages() -> None:
    for call in (
        lambda: lvtime.from_decimal(_LoudText("abc")),
        lambda: LVTimestamp(0).to_bytes(_LoudText("nope")),  # type: ignore[arg-type]
    ):
        with pytest.raises(ValueError) as caught:
            call()
        assert len(str(caught.value)) < 120


_NEAR_TIE = "0.0000000000000000000271050543121376108501863200217485427856445312" + "4" + "9" * 30


@pytest.mark.parametrize(
    "setup",
    [
        "decimal.getcontext().Emax = 5",
        "decimal.getcontext().Emin = -30",
        "decimal.setcontext(decimal.Context(prec=2, Emin=-5, Emax=5, traps=[decimal.Inexact]))",
    ],
)
def test_the_decimal_context_at_import_time_does_not_matter(setup: str) -> None:
    code = (
        f"import decimal\n{setup}\nimport lvtime\n"
        f"print(lvtime.from_decimal({_NEAR_TIE!r}), lvtime.from_decimal('-5.2'))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, env=cli_env(), timeout=60
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == f"(0, 0) {lvtime.from_decimal('-5.2')}"


def test_the_cli_ignores_a_customised_default_context(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(decimal.DefaultContext, "Emax", 5)
    assert main(["encode", "2024-10-04T12:00:00.5Z"]) == 0
