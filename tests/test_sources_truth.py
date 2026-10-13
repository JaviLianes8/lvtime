"""Ground truth re-read from the public references, as fetched (see ``fixtures/sources``).

The copies are kept on the maintainer's machine only (``scripts/fetch_sources.py`` fetches
them and ``MANIFEST.json`` records URL, size and SHA-256). Without them this module skips.
Only facts are taken from them: byte values, field order and the epoch.
"""

from __future__ import annotations

import hashlib
import html
import io
import json
import re
from pathlib import Path

import pytest

import lvtime
from lvtime import LVTimestamp

SOURCES = Path(__file__).resolve().parent / "fixtures" / "sources"
_MANIFEST_PATH = SOURCES / "MANIFEST.json"
MANIFEST = (
    json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
    if _MANIFEST_PATH.is_file()
    else {"files": [{"file": "MANIFEST.json"}]}
)

if not all((SOURCES / entry["file"]).is_file() for entry in MANIFEST["files"]):
    pytest.skip(
        "source copies not present (scripts/fetch_sources.py in the repository fetches them)",
        allow_module_level=True,
    )


def _text(name: str) -> str:
    raw = (SOURCES / name).read_text(encoding="utf-8", errors="replace")
    raw = re.sub(r"(?s)<script.*?</script>|<style.*?</style>", " ", raw)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", raw)))


def test_the_copies_match_the_manifest() -> None:
    for entry in MANIFEST["files"]:
        body = (SOURCES / entry["file"]).read_bytes()
        assert len(body) == entry["size"], entry["file"]
        assert hashlib.sha256(body).hexdigest() == entry["sha256"], entry["file"]


def _ni_rows() -> list[tuple[int, int, int, int]]:
    """Return every (decimal seconds, decimal frac, hex seconds, hex frac) row of NI's table."""
    text = _text("ni-labview-timestamp-overview.html")
    table = text[text.index("Timestamp Interpretation Examples") :]
    table = table[: table.index("The second example")]
    hex_pairs = re.findall(r"\{ (0x[0-9A-Fa-f]+), (0x[0-9A-Fa-f]+) \}", table)
    seconds = re.findall(r"\{ (-?\d+), ", table)
    fractions = re.findall(r"\{ -?\d+, (?:\(.*?\) == )?(\d+) \}", table)
    assert len(hex_pairs) == len(seconds) == len(fractions) == 4
    return [
        (int(s), int(f), int(hs, 16), int(hf, 16))
        for s, f, (hs, hf) in zip(seconds, fractions, hex_pairs, strict=True)
    ]


def _signed(value: int) -> int:
    return value - 2**64 if value >= 2**63 else value


def test_every_ni_row_flattens_to_its_documented_bytes() -> None:
    for seconds, frac, hex_seconds, hex_frac in _ni_rows():
        assert (_signed(hex_seconds), hex_frac) == (seconds, frac)
        ts = LVTimestamp(seconds, frac)
        assert ts.to_bytes() == hex_seconds.to_bytes(8, "big") + hex_frac.to_bytes(8, "big")
        assert lvtime.read_timestamp(ts.to_bytes()) == ts


def test_ni_values_with_a_decimal_meaning_come_back_exactly() -> None:
    rows = {(s, f) for s, f, _, _ in _ni_rows()}
    assert lvtime.from_decimal("0") in rows
    assert lvtime.from_decimal("-0.5") in rows
    assert lvtime.from_decimal("-5.2") in rows
    assert (lvtime.from_float(-5.2)[1]) == 0xCCCCCCCCCCCCC000
    assert "0xccccccccccccc000" in _text("ni-labview-timestamp-overview.html")


def test_ni_describes_one_128_bit_number_with_the_seconds_on_top() -> None:
    text = _text("ni-labview-timestamp-overview.html")
    assert "01/01/1904 00:00:00.00 UTC" in text
    assert "most significant 64 bits" in text
    assert "least significant 64 bits" in text
    assert LVTimestamp(0, 0).to_datetime().isoformat() == "1904-01-01T00:00:00+00:00"


def test_tdms_stores_seconds_and_fraction_with_the_1904_epoch() -> None:
    text = _text("ni-tdms-file-format-internal-structure.html")
    seconds_at = text.index("(i64) seconds")
    fraction_at = text.index("(u64) positive fractions")
    assert seconds_at < fraction_at
    assert "01/01/1904 00:00:00.00 UTC" in text[seconds_at:fraction_at]
    assert "(2^-64)" in text[fraction_at : fraction_at + 80]
    assert "tdsTypeTimeStamp=0x44" in text


def test_nptdms_reads_little_endian_timestamps_fraction_first() -> None:
    source = (SOURCES / "nptdms-types.py.txt").read_text(encoding="utf-8")
    assert "dtype([('second_fractions', '<u8'), ('seconds', '<i8')])" in source
    assert "dtype([('seconds', '>i8'), ('second_fractions', '>u8')])" in source


def test_nptdms_itself_agrees_when_it_is_installed() -> None:
    types = pytest.importorskip("nptdms.types")
    for seconds, frac in [(0, 1), (-6, 0xCCCCCCCCCCCCCCCD), (3810888000, 1 << 63)]:
        ts = LVTimestamp(seconds, frac)
        little = types.TimeStamp.read(io.BytesIO(ts.to_bytes("little")), "<")
        big = types.TimeStamp.read(io.BytesIO(ts.to_bytes("big")), ">")
        assert (little.seconds, little.second_fractions) == (seconds, frac)
        assert (big.seconds, big.second_fractions) == (seconds, frac)
