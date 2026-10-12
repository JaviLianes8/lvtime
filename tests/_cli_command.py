"""Find the ``lvtime`` command that belongs to the interpreter running the tests.

The CLI end-to-end tests must drive the build under test, never whatever ``lvtime``
happens to be first on PATH. The console script installed next to this interpreter is
used when present; otherwise the CLI module runs in a fresh interpreter that imports the
very package this test process imports. Nothing is ever installed by the tests.
"""

from __future__ import annotations

import os
import subprocess
import sys
import sysconfig
from pathlib import Path

import lvtime

_SCRIPT_NAME = "lvtime.exe" if os.name == "nt" else "lvtime"


def cli_command() -> list[str]:
    """Return the argv prefix that runs the CLI of the package under test."""
    script = Path(sysconfig.get_path("scripts")) / _SCRIPT_NAME
    if script.is_file():
        return [str(script)]
    return [sys.executable, "-m", "lvtime"]


def cli_env() -> dict[str, str]:
    """Return an environment whose import path starts at the package under test."""
    env = dict(os.environ)
    package_parent = str(Path(lvtime.__file__).resolve().parent.parent)
    env["PYTHONPATH"] = package_parent + os.pathsep + env.get("PYTHONPATH", "")
    return env


def run_cli(*args: str, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    """Run the CLI of the package under test as a separate process."""
    return subprocess.run(
        [*cli_command(), *args],
        input=stdin,
        capture_output=True,
        text=True,
        env=cli_env(),
        timeout=60,
    )
