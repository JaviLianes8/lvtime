from __future__ import annotations

import dataclasses
import importlib.resources
import inspect
import sys
import typing
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

import lvtime

# The public API. Add every exported name here as the library grows; this list is the
# contract and the test below fails if the module and this list disagree.
PUBLIC_API: list[str] = [
    "LABVIEW_UNIX_EPOCH_OFFSET",
    "ByteOrder",
    "LVTimestamp",
    "from_datetime",
    "from_decimal",
    "from_float",
    "from_unix",
    "from_unix_decimal",
    "read_timestamp",
    "read_timestamps",
    "to_datetime",
    "to_decimal",
    "to_float",
    "to_unix",
    "to_unix_decimal",
    "write_timestamp",
    "write_timestamps",
]


def test_all_lists_exactly_the_public_api() -> None:
    assert sorted(lvtime.__all__) == sorted(PUBLIC_API)


def test_every_exported_name_resolves() -> None:
    for name in lvtime.__all__:
        assert hasattr(lvtime, name)


def test_version_is_a_three_part_string() -> None:
    parts = lvtime.__version__.split(".")
    assert len(parts) == 3
    assert all(part.isdigit() for part in parts)


def test_the_package_ships_type_information() -> None:
    assert importlib.resources.files("lvtime").joinpath("py.typed").is_file()


def _pyproject() -> dict[str, Any]:
    text = (Path(__file__).resolve().parent.parent / "pyproject.toml").read_text(encoding="utf-8")
    if sys.version_info >= (3, 11):
        import tomllib

        return dict(tomllib.loads(text))
    pytest.skip("tomllib needs Python 3.11")


def test_version_matches_pyproject() -> None:
    assert _pyproject()["project"]["version"] == lvtime.__version__


def test_package_has_no_runtime_dependencies_and_is_stable() -> None:
    project = _pyproject()["project"]
    assert project["dependencies"] == []
    assert "Development Status :: 5 - Production/Stable" in project["classifiers"]
    assert project["requires-python"] == ">=3.10"
    for minor in range(10, 15):
        assert f"Programming Language :: Python :: 3.{minor}" in project["classifiers"]
    assert set(project["urls"]) >= {"Homepage", "Source", "Issues", "Changelog"}
    assert project["scripts"] == {"lvtime": "lvtime._cli:main"}


def test_timestamp_promise() -> None:
    ts = lvtime.LVTimestamp(-6, 0xCCCCCCCCCCCCCCCD)
    assert (ts.seconds, ts.frac) == (-6, 0xCCCCCCCCCCCCCCCD)
    assert lvtime.LVTimestamp(7) == lvtime.LVTimestamp(7, 0)
    assert hash(ts) == hash(lvtime.LVTimestamp(-6, 0xCCCCCCCCCCCCCCCD))
    with pytest.raises(dataclasses.FrozenInstanceError):
        ts.seconds = 0  # type: ignore[misc]
    assert [f.name for f in dataclasses.fields(ts)] == ["seconds", "frac"]


def test_conversion_promises_on_one_instant() -> None:
    seconds, frac = 3810888000, 1 << 63
    instant = datetime(2024, 10, 4, 12, 0, 0, 500000, tzinfo=timezone.utc)
    assert lvtime.to_datetime(seconds, frac) == instant
    assert lvtime.from_datetime(instant) == (seconds, frac)
    assert lvtime.to_unix(seconds, frac) == 1728043200.5
    assert lvtime.from_unix(1728043200.5) == (seconds, frac)
    assert lvtime.to_float(seconds, frac) == 3810888000.5
    assert lvtime.from_float(3810888000.5) == (seconds, frac)
    assert lvtime.to_decimal(seconds, frac) == Decimal("3810888000.5")
    assert lvtime.from_decimal("3810888000.5") == (seconds, frac)
    assert lvtime.to_unix_decimal(seconds, frac) == Decimal("1728043200.5")
    assert lvtime.from_unix_decimal("1728043200.5") == (seconds, frac)
    assert lvtime.LABVIEW_UNIX_EPOCH_OFFSET == 2082844800
    assert lvtime.to_datetime(lvtime.LABVIEW_UNIX_EPOCH_OFFSET) == datetime(
        1970, 1, 1, tzinfo=timezone.utc
    )


def test_byte_promises() -> None:
    ts = lvtime.LVTimestamp(1, 2)
    big = bytes.fromhex("00000000000000010000000000000002")
    order: lvtime.ByteOrder = "little"
    assert lvtime.write_timestamp(ts) == big == ts.to_bytes()
    assert lvtime.write_timestamp(ts, order) == big[::-1]
    assert lvtime.read_timestamp(big) == ts == lvtime.read_timestamp(big[::-1], order)
    assert lvtime.write_timestamps([ts, ts]) == big * 2
    assert lvtime.read_timestamps(big[::-1] * 3, order) == [ts] * 3
    assert lvtime.read_timestamps(b"") == []
    assert ts.hex() == big.hex() and lvtime.LVTimestamp.from_hex(big.hex()) == ts
    assert typing.get_args(lvtime.ByteOrder) == ("big", "little")


def test_public_signatures_are_the_stable_ones() -> None:
    expected = {
        "to_datetime": "(seconds: 'SupportsIndex', frac: 'SupportsIndex' = 0) -> 'datetime'",
        "from_datetime": "(dt: 'datetime') -> 'tuple[int, int]'",
        "to_float": "(seconds: 'SupportsIndex', frac: 'SupportsIndex' = 0) -> 'float'",
        "from_float": "(value: 'float') -> 'tuple[int, int]'",
        "to_unix": "(seconds: 'SupportsIndex', frac: 'SupportsIndex' = 0) -> 'float'",
        "from_unix": "(value: 'float') -> 'tuple[int, int]'",
        "to_decimal": "(seconds: 'SupportsIndex', frac: 'SupportsIndex' = 0) -> 'Decimal'",
        "from_decimal": "(value: 'ExactInput') -> 'tuple[int, int]'",
        "to_unix_decimal": "(seconds: 'SupportsIndex', frac: 'SupportsIndex' = 0) -> 'Decimal'",
        "from_unix_decimal": "(value: 'ExactInput') -> 'tuple[int, int]'",
        "read_timestamp": "(data: 'BytesLike', byteorder: 'ByteOrder' = 'big') -> 'LVTimestamp'",
        "write_timestamp": "(timestamp: 'LVTimestamp', byteorder: 'ByteOrder' = 'big') -> 'bytes'",
        "read_timestamps": (
            "(data: 'BytesLike', byteorder: 'ByteOrder' = 'big') -> 'list[LVTimestamp]'"
        ),
        "write_timestamps": (
            "(timestamps: 'Iterable[LVTimestamp]', byteorder: 'ByteOrder' = 'big') -> 'bytes'"
        ),
    }
    assert str(inspect.signature(lvtime.LVTimestamp)) == (
        "(seconds: 'SupportsIndex', frac: 'SupportsIndex' = 0) -> 'None'"
    )
    for name, signature in expected.items():
        assert str(inspect.signature(getattr(lvtime, name))) == signature, name


def test_type_hints_resolve_at_runtime() -> None:
    for name in lvtime.__all__:
        value = getattr(lvtime, name)
        if inspect.isfunction(value):
            assert typing.get_type_hints(value)
    for _, method in inspect.getmembers(lvtime.LVTimestamp, inspect.isroutine):
        if not method.__name__.startswith("_"):
            typing.get_type_hints(method)
