"""Suite-wide guard: a test that runs away (for example a search or a parse that turned
quadratic) aborts the run with a traceback instead of hanging the machine.

The traceback goes to a copy of the real stderr taken before pytest captures output, so it
reaches the terminal even under pytest's default capture.
"""

from __future__ import annotations

import faulthandler
import os
import sys
from collections.abc import Iterator

import pytest

_DEADLINE_SECONDS = 60
_STDERR: dict[str, int] = {}


def pytest_configure(config: pytest.Config) -> None:
    _STDERR["fd"] = os.dup(sys.stderr.fileno())


def pytest_unconfigure(config: pytest.Config) -> None:
    fd = _STDERR.pop("fd", None)
    if fd is not None:
        os.close(fd)


@pytest.fixture(autouse=True)
def _deadline() -> Iterator[None]:
    faulthandler.dump_traceback_later(_DEADLINE_SECONDS, exit=True, file=_STDERR["fd"])
    try:
        yield
    finally:
        faulthandler.cancel_dump_traceback_later()
