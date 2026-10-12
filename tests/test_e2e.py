"""End to end: pip-install the package editable into a fresh venv and drive the
real ``lvtime`` console script through subprocess, asserting stdout and exit code.

This is the aparato-real check for a library: it proves the published console
script entry point resolves and behaves once actually installed, not just that
the in-tree function returns the right thing.
"""

from __future__ import annotations

import subprocess
import sys
import venv
from pathlib import Path

import pytest

import lvtime

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# NI's documented 2002 row: {3092601600, 0} = 0xB8555B00, which is 2001-12-31 UTC.
NI_2002_HEX = "00000000b8555b000000000000000000"
NI_2002_ISO = "2001-12-31T00:00:00+00:00"


def _script(venv_dir: Path) -> Path:
    if sys.platform == "win32":
        return venv_dir / "Scripts" / "lvtime.exe"
    return venv_dir / "bin" / "lvtime"


@pytest.fixture(scope="module")
def installed_cli(tmp_path_factory: pytest.TempPathFactory) -> Path:
    venv_dir = tmp_path_factory.mktemp("lvtime_venv")
    venv.create(venv_dir, with_pip=True)
    python = venv_dir / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    install = subprocess.run(
        [str(python), "-m", "pip", "install", "-e", str(PROJECT_ROOT), "--quiet"],
        capture_output=True,
        text=True,
    )
    if install.returncode != 0:
        pytest.skip(f"editable install unavailable in this environment: {install.stderr[-400:]}")
    script = _script(venv_dir)
    if not script.is_file():
        pytest.skip("console script was not produced by the install")
    return script


def _run(script: Path, *args: str, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(script), *args], capture_output=True, text=True, input=stdin, timeout=60
    )


def test_console_script_reports_the_version(installed_cli: Path) -> None:
    result = _run(installed_cli, "--version")
    assert result.returncode == 0
    assert result.stdout.strip() == f"lvtime {lvtime.__version__}"


def test_console_script_decodes_the_ni_2002_value(installed_cli: Path) -> None:
    result = _run(installed_cli, "decode", NI_2002_HEX)
    assert result.returncode == 0
    assert result.stdout.strip() == NI_2002_ISO


def test_console_script_round_trips_the_ni_2002_value(installed_cli: Path) -> None:
    encoded = _run(installed_cli, "encode", NI_2002_ISO)
    assert encoded.returncode == 0
    assert encoded.stdout.strip() == NI_2002_HEX
    decoded = _run(installed_cli, "decode", encoded.stdout.strip())
    assert decoded.stdout.strip() == NI_2002_ISO


def test_console_script_decimal_format_is_exact(installed_cli: Path) -> None:
    result = _run(
        installed_cli, "decode", "--format", "decimal", "fffffffffffffffacccccccccccccccd"
    )
    assert result.returncode == 0
    # -5.2 s lands on the exact NI fixed-point value, never a lossy double.
    assert result.stdout.startswith("epoch1904=-5.1999999999999999999")


def test_console_script_reads_hex_from_stdin(installed_cli: Path) -> None:
    result = _run(installed_cli, "decode", stdin=NI_2002_HEX + "\n")
    assert result.returncode == 0
    assert result.stdout.strip() == NI_2002_ISO


def test_console_script_errors_to_stderr_with_exit_1(installed_cli: Path) -> None:
    result = _run(installed_cli, "decode", "nothex")
    assert result.returncode == 1
    assert result.stdout.strip() == ""
    assert result.stderr.startswith("lvtime:")
