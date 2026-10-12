# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-10-13

The public API is now stable: the names in `lvtime.__all__`, their signatures and defaults,
the `LVTimestamp` fields `seconds` and `frac`, the rounding rules and error types documented
in the guide, and the command-line options, output formats and exit codes.

### Changed

- `byteorder="little"` is now the 16-byte value reversed byte for byte: the fraction first,
  then the seconds, each little-endian. This is how little-endian TDMS files (the TDMS
  default) and npTDMS store a timestamp, and what the 0.3.0 documentation described; 0.3.0
  wrote the seconds first. Bytes written by 0.3.0 in little-endian read correctly after
  swapping their two 8-byte halves (see the guide). Big-endian output is unchanged.
- `from_float` and `from_unix` convert the exact value of the float and round once to the
  nearest 2**-64 s, ties to even. 0.3.0 returned `(0, 0)` for `from_float(-2**-60)` (the
  answer is `(-1, 2**64 - 16)`) and added the epoch offset in float arithmetic.
- `to_float` and `to_unix` return the correctly rounded float of the exact instant (0.3.0
  could round twice).
- `from_decimal` and `from_unix_decimal` round exactly once whatever the input length (0.3.0
  rounded through a 96-digit context), raise `ValueError` for text that is not a finite
  number (was `decimal.InvalidOperation`, or `OverflowError` for infinity), refuse `bool`, and
  reject values far out of range at once (0.3.0 hung on `"1e999999999"`).
- `to_decimal` and `to_unix_decimal` return the same exact values without trailing zeros
  (`Decimal('10.5')`, not 64 decimal places).
- `LVTimestamp` and every function taking a `(seconds, frac)` pair refuse floats, strings and
  `bool` with `TypeError` (0.3.0 stored `LVTimestamp(1.5, 0)` and failed later) and accept any
  integer type with `__index__`, such as NumPy integers, stored as plain `int`. The constructor
  is typed `LVTimestamp(seconds: SupportsIndex, frac: SupportsIndex = 0)` to match.
- Conversions use a fully specified private decimal context: a customised
  `decimal.DefaultContext` or the caller's context no longer changes results or raises
  `decimal.Inexact`, and the caller's decimal flags are left untouched.
- A result outside the 64-bit second range raises `ValueError` with one message for every
  conversion.
- `to_datetime`, `to_float`, `to_unix`, `to_decimal` and `to_unix_decimal` raise `ValueError`
  when `seconds` does not fit a signed 64-bit integer (0.3.0 returned a value, for example
  `to_float(2**63, 0)`, or raised `OverflowError` from `to_datetime`). `to_datetime` raises `OverflowError` with its own
  short message outside the years 1 to 9999.
- `from_datetime` raises `TypeError` for anything that is not a `datetime` (was
  `AttributeError`).
- `from_float` and `from_unix` raise `ValueError` for NaN and infinities (infinity raised
  `OverflowError`) and `TypeError` for non-numbers.
- The byte readers accept `bytes`, `bytearray` and `memoryview` (any format) and raise
  `TypeError` for anything else; `write_timestamp` and `write_timestamps` raise `TypeError`
  for items that are not `LVTimestamp`.
- Error messages never repeat more than about 40 characters of the input.
- CLI: `encode` keeps every fractional digit of the ISO text (0.3.0 cut it to the
  microsecond) and accepts fractions of any length on Python 3.10, whose `fromisoformat`
  only takes 3 or 6 digits (`lvtime encode 2024-10-04T12:00:00.5Z` failed there), plus
  `+0200` style offsets and the basic form `20241004T120000.5Z` there. It refuses UTC offsets
  with seconds (Python reads `+00:00:00.5` as `+00:00`) and fractions of minutes or hours
  (Python reads `12:00.5` as half a second).
- CLI: a missing or unreadable stdin, a closed stderr and very long bad arguments no longer
  give a traceback, a wrong exit code or a huge message.
- CLI: a timestamp outside the `datetime` range exits 1 with a message instead of a
  traceback (`--format decimal` still works for it); bad hex or ISO text is not echoed back
  in full; a closed output pipe exits quietly; `--help` lists the exit codes.

### Added

- `LVTimestamp` instances are ordered (`<`, `sorted`) by instant.
- Docstrings with runnable examples for every public name, and a guide (GUIDE.md).

### Removed

- Nothing public. The private helpers moved between modules.

## [0.3.0]

- Exact conversions through integer and `Decimal` arithmetic, never a float:
  `to_decimal` / `from_decimal`, `to_unix_decimal` / `from_unix_decimal` and the matching
  `LVTimestamp` methods. These reproduce NI's exact documented bytes for values a double
  cannot hold, such as -5.2 s (`0xCCCCCCCCCCCCCCCD`), and keep the full 2**-64 s resolution.
  `from_decimal` accepts `Decimal`, `int` or `str` and refuses `float` so a lossy value
  cannot slip in.
- `LVTimestamp.hex` / `LVTimestamp.from_hex`: round trip the 16-byte on-disk form as a
  32-character hex string, byte-order aware.
- CLI: `--version`, a `decode --format decimal` output (exact seconds since 1904 and since
  the Unix epoch), and the console script entry point now resolves to `lvtime._cli:main`.
- CLI errors now exit with code 1 (was 2) and still print to stderr.
- Documented two NI caveats: the 0.8 fraction only survives in fixed point, and NI's own
  page mislabels `{3092601600, 0}` as 2002 when the byte value is 2001-12-31 UTC.

## [0.2.0]

- `to_unix` / `from_unix` and `LVTimestamp.to_unix` / `LVTimestamp.from_unix`: convert
  to and from Unix time (float seconds since 1970-01-01 UTC).
- `to_float` / `from_float` and the matching `LVTimestamp` methods: seconds since the
  1904 epoch as a float, the LabVIEW "coerce timestamp to double" view.
- Little-endian support: every byte function and `LVTimestamp.to_bytes` / `from_bytes`
  takes a `byteorder` argument (`"big"`, the default, or `"little"`).
- `read_timestamps` / `write_timestamps`: batch read and write of back-to-back 16-byte
  records.
- `ByteOrder`: the `Literal["big", "little"]` type alias used by the byte functions.
- `lvtime` command line (console script and `python -m lvtime`): `decode` a hex
  timestamp to an ISO datetime (or `fields` / `json`) and `encode` an ISO datetime back,
  reading from an argument or stdin.

## [0.1.0]

- First release.
- `LVTimestamp`: a lossless, immutable integer pair (signed 64-bit seconds, unsigned
  64-bit fraction of 2**-64 s) with range-checked construction.
- `to_datetime` and `from_datetime`: convert between the integer pair and a UTC-aware
  `datetime`, rounded to the microsecond, with the correct 1904 epoch and signedness.
- `read_timestamp` and `write_timestamp`: read and write the 16-byte big-endian on-disk
  form used by TDMS and "Flatten To String".
- `LABVIEW_UNIX_EPOCH_OFFSET`: the exact 2082844800 s epoch constant.
- Zero runtime dependencies; typed (`py.typed`), tested on the success and failure paths.
