"""The ``lvtime`` command line: decode and encode the 16-byte on-disk form."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone

from . import __version__
from ._codec import ByteOrder
from ._timestamp import LVTimestamp, read_timestamp, write_timestamp

_DESCRIPTION = "Decode and encode LabVIEW 128-bit timestamps (1904 epoch)."
_EPILOG = """\
examples:
  lvtime decode 00000000e32589408000000000000000
  echo 00000000e32589408000000000000000 | lvtime decode
  lvtime decode --format fields 00000000e32589408000000000000000
  lvtime decode --format decimal 00000000e32589408000000000000000
  lvtime encode 2024-10-04T12:00:00.5+00:00
  lvtime encode --byteorder little 2024-10-04T12:00:00Z
"""


def _read_arg(value: str | None) -> str:
    text = sys.stdin.read() if value is None else value
    text = text.strip()
    if not text:
        raise ValueError("no input given (pass an argument or pipe it on stdin)")
    return text


def _parse_iso(text: str) -> datetime:
    dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _decode(hex_text: str, byteorder: ByteOrder, fmt: str) -> str:
    ts = read_timestamp(bytes.fromhex(hex_text), byteorder)
    if fmt == "iso":
        return ts.to_datetime().isoformat()
    if fmt == "fields":
        dt = ts.to_datetime()
        return f"seconds={ts.seconds} frac={ts.frac} iso={dt.isoformat()} unix={ts.to_unix()!r}"
    if fmt == "decimal":
        return f"epoch1904={ts.to_decimal()} unix={ts.to_unix_decimal()}"
    payload = {
        "seconds": ts.seconds,
        "frac": ts.frac,
        "iso": ts.to_datetime().isoformat(),
        "unix": ts.to_unix(),
    }
    return json.dumps(payload)


def _encode(iso_text: str, byteorder: ByteOrder) -> str:
    return write_timestamp(LVTimestamp.from_datetime(_parse_iso(iso_text)), byteorder).hex()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lvtime",
        description=_DESCRIPTION,
        epilog=_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"lvtime {__version__}")
    subs = parser.add_subparsers(dest="command", required=True)

    decode = subs.add_parser("decode", help="16-byte hex timestamp to an ISO datetime")
    decode.add_argument("hex", nargs="?", help="32 hex chars; read from stdin if omitted")
    decode.add_argument("--byteorder", choices=["big", "little"], default="big")
    decode.add_argument("--format", choices=["iso", "fields", "json", "decimal"], default="iso")

    encode = subs.add_parser("encode", help="ISO datetime to a 16-byte hex timestamp")
    encode.add_argument("iso", nargs="?", help="ISO datetime (UTC if naive); stdin if omitted")
    encode.add_argument("--byteorder", choices=["big", "little"], default="big")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point for the ``lvtime`` console script. Returns a process exit code."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "decode":
            line = _decode(_read_arg(args.hex), args.byteorder, args.format)
        else:
            line = _encode(_read_arg(args.iso), args.byteorder)
    except ValueError as error:
        print(f"lvtime: {error}", file=sys.stderr)
        return 1
    print(line)
    return 0
