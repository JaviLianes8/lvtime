"""Contracts over bytes written by real LabVIEW 2026 (26.3.1f1, Windows x64).

Every file in ``fixtures/real_labview`` is LabVIEW's own output, copied unchanged;
``manifest.json`` records how each was produced and where each timestamp sits. The same
LabVIEW instants appear little-endian in a TDMS file and big-endian in a datalog of the
same run, which pins both byte orders to what LabVIEW really writes.
"""

from __future__ import annotations

import hashlib
import io
import json
import struct
from decimal import Context, Decimal, localcontext
from pathlib import Path
from typing import Any

import pytest

import lvtime
from lvtime import LVTimestamp

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "real_labview"
MANIFEST: dict[str, Any] = json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))


def _bytes(file: str, offset: int, size: int = 16) -> bytes:
    return (FIXTURES / file).read_bytes()[offset : offset + size]


def _stamp(file: str, offset: int) -> LVTimestamp:
    record = next(r for r in MANIFEST["records"] if (r["file"], r["offset"]) == (file, offset))
    return lvtime.read_timestamp(_bytes(file, offset), record["byteorder"])


def test_the_captures_match_the_manifest() -> None:
    for entry in MANIFEST["files"]:
        body = (FIXTURES / entry["file"]).read_bytes()
        assert (len(body), hashlib.sha256(body).hexdigest()) == (entry["size"], entry["sha256"])
    for record in MANIFEST["records"]:
        size = len(record["hex"]) // 2
        assert _bytes(record["file"], record["offset"], size).hex() == record["hex"]


def test_tdms_little_endian_and_datalog_big_endian_hold_the_same_instants() -> None:
    pairs = [(407, 4890), (838, 9242)]
    for tdms_offset, datalog_offset in pairs:
        little = _stamp("tdms_write_events.tdms", tdms_offset)
        big = _stamp("tdms_write_events.datalog", datalog_offset)
        assert little == big
        assert little.to_bytes("little") == big.to_bytes("big")[::-1]
        assert _bytes("tdms_write_events.tdms", tdms_offset - 4, 4) == b"\x44\x00\x00\x00"


def test_tdms_timestamps_decode_to_the_capture_run() -> None:
    first = _stamp("tdms_write_events.tdms", 407)
    assert (first.seconds, first.frac) == (3874687546, 0x4C7B280000000000)
    assert first.to_datetime().isoformat() == "2026-10-12T22:05:46.298754+00:00"
    channel = lvtime.read_timestamps(_bytes("tdms_write_events.tdms", 9071), "little")
    assert channel == [_stamp("tdms_write_events.tdms", 838)]


def test_labview_converts_a_timestamp_to_exactly_our_double() -> None:
    x = _stamp("timestamp_to_double.datalog", 754)
    (labview_double,) = struct.unpack(">d", _bytes("timestamp_to_double.datalog", 718, 8))
    assert labview_double == x.to_float() == lvtime.to_float(x.seconds, x.frac)
    assert x.to_unix() == labview_double - lvtime.LABVIEW_UNIX_EPOCH_OFFSET


def test_a_millisecond_input_lands_on_the_double_fraction_labview_stored() -> None:
    x = _stamp("timestamp_to_double.datalog", 754)
    assert x.to_datetime().isoformat() == "2026-10-12T22:05:46.797000+00:00"
    assert lvtime.from_float(0.797) == (0, x.frac)


@pytest.mark.parametrize(
    ("file", "operation"),
    [
        ("timestamp_add.datalog", "add"),
        ("timestamp_subtract.datalog", "subtract"),
        ("timestamp_add_2026_plus_0p1.datalog", "add"),
    ],
)
def test_exact_decimals_reproduce_labview_128_bit_arithmetic(file: str, operation: str) -> None:
    with localcontext(Context(prec=100)):
        if operation == "add":
            x, y, result = (_stamp(file, o) for o in (114, 130, 98))
            expected = x.to_decimal() + y.to_decimal()
        else:
            x, y, result = (_stamp(file, o) for o in (98, 114, 130))
            expected = x.to_decimal() - y.to_decimal()
    assert result.to_decimal() == expected
    assert LVTimestamp.from_decimal(expected) == result


def test_local_inputs_decode_to_the_right_utc_instants() -> None:
    summer = _stamp("timestamp_add_2026_plus_0p1.datalog", 114)
    assert summer.to_datetime().isoformat() == "2026-07-01T10:00:00.123000+00:00"
    old = _stamp("timestamp_add_1900.datalog", 114)
    assert old.seconds < 0
    assert old.to_datetime().isoformat() == "1899-12-31T23:00:00+00:00"
    assert old.to_decimal() == Decimal(-126147600)


def test_nptdms_reads_the_labview_file_like_we_do() -> None:
    nptdms = pytest.importorskip("nptdms")
    with nptdms.TdmsFile.open(
        io.BytesIO((FIXTURES / "tdms_write_events.tdms").read_bytes()), raw_timestamps=True
    ) as tdms:
        prop = tdms["Measured Data"]["Phase sweep"].properties["NI_ExpStartTimeStamp"]
    ours = _stamp("tdms_write_events.tdms", 838)
    assert (prop.seconds, prop.second_fractions) == (ours.seconds, ours.frac)
