"""The ``lvtime`` command line: decode and encode the 16-byte on-disk form."""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from decimal import Context, Decimal, localcontext
from typing import NoReturn, TextIO

from . import __version__
from ._codec import ByteOrder
from ._io import read_timestamp, write_timestamp
from ._timestamp import LVTimestamp
from ._validate import short

_DESCRIPTION = "Decode and encode LabVIEW 128-bit timestamps (1904 epoch)."
_EPILOG = """\
examples:
  lvtime decode 00000000e32589408000000000000000
  echo 00000000e32589408000000000000000 | lvtime decode
  lvtime decode --format fields 00000000e32589408000000000000000
  lvtime decode --format decimal 00000000e32589408000000000000000
  lvtime encode 2024-10-04T12:00:00.5+00:00
  lvtime encode --byteorder little 2024-10-04T12:00:00Z

exit codes: 0 success, 1 bad input, 2 bad usage
"""


def _read_arg(value: str | None) -> str:
    if value is None:
        if sys.stdin is None:
            raise ValueError("no input given (pass an argument or pipe it on stdin)")
        try:
            value = sys.stdin.read()
        except OSError as error:
            raise ValueError(f"cannot read stdin: {error.strerror or error}") from None
    text = value
    text = text.strip()
    if not text:
        raise ValueError("no input given (pass an argument or pipe it on stdin)")
    return text


# A date and a time of day with a fraction of any length; the rest is the UTC offset.
_ISO_FRACTION = re.compile(
    r"(?P<y>\d{4})-?(?P<mo>\d{2})-?(?P<d>\d{2})[T ](?P<h>\d{2}):?(?P<mi>\d{2}):?(?P<s>\d{2})"
    r"[.,](?P<frac>\d+)(?P<tail>.*)",
    re.ASCII,
)
# A fraction of an hour or a minute, which fromisoformat would read as seconds.
_PARTIAL_FRACTION = re.compile(r"[T ]\d{2}(?::?\d{2})?[.,]\d", re.ASCII)
# A UTC offset that carries seconds, such as +05:30:15 or +00:00:00.5.
_SECONDS_OFFSET = re.compile(r"[+-]\d{2}:?\d{2}:?\d{2}(?:[.,]\d+)?$", re.ASCII)
# A basic-format offset such as +0200, which fromisoformat on Python 3.10 refuses.
_BASIC_OFFSET = re.compile(
    r"(?P<head>.*\d)(?P<sign>[+-])(?P<hours>\d{2})(?P<minutes>\d{2})", re.ASCII
)


def _parse_iso(text: str, shown: str) -> datetime:
    if text[-1:] in ("Z", "z"):
        text = text[:-1] + "+00:00"
    basic = _BASIC_OFFSET.fullmatch(text)
    if basic is not None and ":" in basic["head"]:
        text = f"{basic['head']}{basic['sign']}{basic['hours']}:{basic['minutes']}"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        raise ValueError(f"not an ISO 8601 datetime: {short(shown)}") from None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _parse_iso_exact(text: str) -> LVTimestamp:
    """Parse ISO 8601 text, keeping every fractional digit (datetime stops at 6)."""
    if _SECONDS_OFFSET.search(text):
        # fromisoformat drops some of these (+00:00:00.5 reads as +00:00), so refuse them all.
        raise ValueError(f"UTC offsets with seconds are not supported: {short(text)}")
    match = _ISO_FRACTION.fullmatch(text)
    if match is None:
        if _PARTIAL_FRACTION.search(text):
            raise ValueError(f"a fraction must follow whole seconds: {short(text)}")
        return LVTimestamp.from_datetime(_parse_iso(text, text))
    head = "{y}-{mo}-{d}T{h}:{mi}:{s}".format(**match.groupdict())
    whole = LVTimestamp.from_datetime(_parse_iso(head + match["tail"], text))
    digits = match["frac"]
    with localcontext(Context(prec=len(digits) + 100)):
        return LVTimestamp.from_decimal(whole.to_decimal() + Decimal("0." + digits))


def _decode(hex_text: str, byteorder: ByteOrder, fmt: str) -> str:
    try:
        raw = bytes.fromhex(hex_text)
    except ValueError:
        raise ValueError(f"not a hex string: {short(hex_text)}") from None
    ts = read_timestamp(raw, byteorder)
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
    return write_timestamp(_parse_iso_exact(iso_text), byteorder).hex()


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        # argparse repeats a bad argument in full; keep usage errors one short line.
        super().error(message if len(message) <= 200 else message[:200] + "...")


def _build_parser() -> argparse.ArgumentParser:
    parser = _Parser(
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
    except (ValueError, OverflowError) as error:
        _report(f"lvtime: {error}")
        return 1
    except KeyboardInterrupt:
        return 130
    return _emit(line)


def _report(message: str) -> None:
    try:
        print(message, file=sys.stderr, flush=True)
    except (OSError, ValueError, AttributeError):
        _silence(sys.stderr)


def _silence(stream: TextIO | None) -> None:
    """Point a dead stream at the null device so the exit flush cannot fail."""
    with contextlib.suppress(OSError, ValueError, AttributeError):
        os.dup2(os.open(os.devnull, os.O_WRONLY), stream.fileno())  # type: ignore[union-attr]


def _emit(line: str) -> int:
    try:
        print(line, flush=True)
    except OSError:
        # The reader went away (a closed pipe is EPIPE on POSIX, EINVAL on Windows): exit quietly.
        _silence(sys.stdout)
        return 1
    return 0
