"""Real end-to-end tests: run the ``lvtime`` command of the package under test as a user does.

Each test spawns a fresh process (the console script installed next to the test interpreter,
or ``python -m lvtime``) and checks the real stdout, stderr and exit code. No mocks.
"""

from __future__ import annotations

import json
import subprocess
import sys

import pytest
from _cli_command import cli_command, cli_env, run_cli

import lvtime

# NI's documented row {3092601600, 0} = 0xB8555B00, which is 2001-12-31 UTC.
NI_2002_HEX = "00000000b8555b000000000000000000"
NI_2002_ISO = "2001-12-31T00:00:00+00:00"
HALF_HEX = "00000000e32589408000000000000000"


def test_version_flag_prints_the_package_version() -> None:
    result = run_cli("--version")
    assert result.returncode == 0
    assert result.stdout == f"lvtime {lvtime.__version__}\n"


def test_decode_prints_the_iso_instant() -> None:
    result = run_cli("decode", NI_2002_HEX)
    assert (result.returncode, result.stdout, result.stderr) == (0, NI_2002_ISO + "\n", "")


def test_encode_then_decode_round_trips() -> None:
    encoded = run_cli("encode", NI_2002_ISO)
    assert (encoded.returncode, encoded.stdout) == (0, NI_2002_HEX + "\n")
    assert run_cli("decode", encoded.stdout.strip()).stdout == NI_2002_ISO + "\n"


def test_decode_reads_stdin_when_no_argument_is_given() -> None:
    result = run_cli("decode", stdin=NI_2002_HEX + "\n")
    assert (result.returncode, result.stdout) == (0, NI_2002_ISO + "\n")


def test_encode_reads_stdin_and_treats_naive_input_as_utc() -> None:
    result = run_cli("encode", stdin="2001-12-31T00:00:00\n")
    assert (result.returncode, result.stdout) == (0, NI_2002_HEX + "\n")


def test_decimal_format_prints_the_exact_ni_value() -> None:
    result = run_cli("decode", "--format", "decimal", "fffffffffffffffacccccccccccccccd")
    exact = "-5.1999999999999999999891579782751449556599254719913005828857421875"
    unix = "-2082844805" + exact[2:]
    assert result.returncode == 0
    assert result.stdout == f"epoch1904={exact} unix={unix}\n"


def test_fields_and_json_formats_carry_the_pair() -> None:
    fields = run_cli("decode", "--format", "fields", HALF_HEX)
    assert fields.stdout == (
        "seconds=3810888000 frac=9223372036854775808 "
        "iso=2024-10-04T12:00:00.500000+00:00 unix=1728043200.5\n"
    )
    payload = json.loads(run_cli("decode", "--format", "json", HALF_HEX).stdout)
    assert payload == {
        "seconds": 3810888000,
        "frac": 9223372036854775808,
        "iso": "2024-10-04T12:00:00.500000+00:00",
        "unix": 1728043200.5,
    }


def test_little_endian_is_the_reversed_big_endian_form() -> None:
    little = run_cli("encode", "--byteorder", "little", "2024-10-04T12:00:00.5Z").stdout.strip()
    assert little == bytes.fromhex(HALF_HEX)[::-1].hex()
    decoded = run_cli("decode", "--byteorder", "little", little)
    assert decoded.stdout == "2024-10-04T12:00:00.500000+00:00\n"


@pytest.mark.parametrize(
    "args",
    [
        ("decode", "nothex"),
        ("decode", "00ff"),
        ("encode", "yesterday"),
        ("decode", "7fffffffffffffff0000000000000000"),
        ("decode", "--format", "json", "8000000000000000ffffffffffffffff"),
    ],
)
def test_bad_input_exits_one_with_a_short_message(args: tuple[str, ...]) -> None:
    result = run_cli(*args)
    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.startswith("lvtime: ")
    assert result.stderr.count("\n") == 1
    assert "Traceback" not in result.stderr


def test_out_of_datetime_range_still_decodes_as_decimal() -> None:
    result = run_cli("decode", "--format", "decimal", "7fffffffffffffff0000000000000000")
    assert result.returncode == 0
    assert result.stdout.startswith("epoch1904=9223372036854775807 ")


def test_huge_bad_input_is_not_echoed_back() -> None:
    result = run_cli("decode", stdin="zz" * 500_000)
    assert result.returncode == 1
    assert len(result.stderr) < 200


def test_empty_input_exits_one() -> None:
    result = run_cli("decode", stdin="  \n")
    assert result.returncode == 1
    assert result.stderr.startswith("lvtime: no input")


def test_bad_usage_exits_two() -> None:
    assert run_cli().returncode == 2
    assert run_cli("decode", "--format", "nope", HALF_HEX).returncode == 2


def test_module_form_runs_the_same_tool() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "lvtime", "decode", NI_2002_HEX],
        capture_output=True,
        text=True,
        env=cli_env(),
        timeout=60,
    )
    assert (result.returncode, result.stdout) == (0, NI_2002_ISO + "\n")


def test_help_names_the_program_and_lists_the_exit_codes() -> None:
    result = run_cli("--help")
    assert result.returncode == 0
    assert result.stdout.startswith("usage: lvtime ")
    assert "exit codes: 0 success, 1 bad input or closed output, 2 bad usage, 130 interrupted" in (
        result.stdout
    )


def test_a_closed_stdout_pipe_exits_quietly() -> None:
    process = subprocess.Popen(
        [*cli_command(), "decode", HALF_HEX],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=cli_env(),
    )
    assert process.stdout is not None and process.stderr is not None
    process.stdout.close()
    process.wait(timeout=60)
    err = process.stderr.read()
    process.stderr.close()
    assert b"Traceback" not in err
    assert process.returncode in (0, 1)
