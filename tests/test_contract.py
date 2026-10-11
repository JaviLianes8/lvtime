import importlib.resources

import lvtime

# The public API. Add every exported name here as the library grows; this list is the
# contract and the test below fails if the module and this list disagree.
PUBLIC_API: list[str] = [
    "LABVIEW_UNIX_EPOCH_OFFSET",
    "ByteOrder",
    "LVTimestamp",
    "from_datetime",
    "from_float",
    "from_unix",
    "read_timestamp",
    "read_timestamps",
    "to_datetime",
    "to_float",
    "to_unix",
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
