# lvtime

Lossless LabVIEW 128-bit timestamp (1904 epoch) to and from datetime, UTC, sub-microsecond preserved.

## Install

```
pip install lvtime
```

## Usage

```python
from datetime import datetime, timezone
from lvtime import LVTimestamp, to_datetime, from_datetime, read_timestamp, write_timestamp

# A LabVIEW absolute time is a signed 64-bit second count since 1904-01-01 UTC
# plus an unsigned 64-bit fraction in units of 2**-64 s.
ts = LVTimestamp(seconds=3810888000, frac=1 << 63)  # 2024-10-04 12:00:00.5 UTC
ts.to_datetime()  # datetime(2024, 10, 4, 12, 0, 0, 500000, tzinfo=UTC)

# Build one from an aware datetime (naive input is rejected).
LVTimestamp.from_datetime(datetime(2024, 10, 4, tzinfo=timezone.utc))

# Read and write the 16-byte big-endian on-disk form (TDMS / "Flatten To String").
raw = write_timestamp(ts)  # 16 bytes: 8 signed seconds + 8 unsigned fraction
read_timestamp(raw) == ts  # True, every bit preserved

# The plain functions take and return the integer pair directly.
to_datetime(3810888000, 1 << 63)
seconds, frac = from_datetime(datetime(2024, 10, 4, tzinfo=timezone.utc))
```

`LVTimestamp` is the lossless carrier: it keeps the full 2**-64 s fraction, so two
instants a single fraction unit apart stay distinct even though they collapse to the
same microsecond when you ask for a `datetime`.

### Unix time and float seconds

```python
ts.to_unix()  # 1728043200.5, float seconds since 1970-01-01 UTC
LVTimestamp.from_unix(1728043200.5)
ts.to_float()  # 3810888000.5, seconds since 1904 (LabVIEW coerce-to-double)
LVTimestamp.from_float(3810888000.5)
```

Floats hold about 52 bits of mantissa, so these views are convenient but lossy below
the microsecond. The integer pair stays exact.

### Exact values with Decimal

When you need the real value and not a float, convert through `Decimal` (or plain `int`
or a `str`). This is the only way to reproduce NI's own documented bytes for a value
like -5.2 s, which a float cannot represent:

```python
from decimal import Decimal
from lvtime import LVTimestamp, to_decimal, from_decimal

from_decimal("-5.2")  # (-6, 14757395258967641293) == {0xFFFFFFFFFFFFFFFA, 0xCCCCCCCCCCCCCCCD}
LVTimestamp.from_decimal("-5.2").hex()  # 'fffffffffffffffacccccccccccccccd', the exact NI bytes

LVTimestamp(10, 1 << 63).to_decimal()  # Decimal('10.5'), exact seconds since 1904
to_decimal(0, 1)  # Decimal('5.42...E-20'), one 2**-64 fraction unit, held exactly
```

`from_decimal` refuses a `float` on purpose, so a lossy value cannot slip in unnoticed;
reach for `from_float` when a float is really what you have. There are `to_unix_decimal`
and `from_unix_decimal` for the Unix-epoch view, and `LVTimestamp.hex()` /
`LVTimestamp.from_hex()` for the hex string you usually hold the flattened form as.

### Endianness and batches

```python
ts.to_bytes("little")  # byte-reversed 16-byte form
LVTimestamp.from_bytes(raw, "little")

from lvtime import read_timestamps, write_timestamps

blob = write_timestamps([ts, LVTimestamp(0, 0)])  # back-to-back 16-byte records
read_timestamps(blob)  # [LVTimestamp(...), LVTimestamp(0, 0)]
```

## Command line

Installing the package puts an `lvtime` command on the path (also runnable as
`python -m lvtime`):

```
$ lvtime decode 00000000e32589408000000000000000
2024-10-04T12:00:00.500000+00:00

$ lvtime decode --format fields 00000000e32589408000000000000000
seconds=3810888000 frac=9223372036854775808 iso=2024-10-04T12:00:00.500000+00:00 unix=1728043200.5

$ lvtime encode 2024-10-04T12:00:00.5+00:00
00000000e32589408000000000000000

$ lvtime decode --format decimal 00000000e32589408000000000000000
epoch1904=3810888000.5000... unix=1728043200.5000...

$ echo 00000000e32589408000000000000000 | lvtime decode
2024-10-04T12:00:00.500000+00:00
```

`decode` also takes `--format json`, `--format decimal` (exact seconds, no float) and
`--byteorder little`; `encode` reads the ISO datetime from an argument or stdin and treats
a naive datetime as UTC. `lvtime --version` prints the version, and a bad input goes to
stderr with exit code 1. See `lvtime --help`.

## How it works

A LabVIEW absolute time is 128 bits of fixed point: a **signed** 64-bit count of whole
seconds since **1904-01-01 00:00:00 UTC** followed by an **unsigned** 64-bit fraction in
units of 2**-64 s. On disk ("Flatten To String", TDMS timestamp channels) the two fields
are stored big-endian, most significant byte first, for 16 bytes total. Converting to a
`datetime` means scaling the fraction to microseconds and adding to the 1904 epoch;
converting back maps the microsecond field to the nearest fraction unit. The full integer
pair is the only representation that keeps every bit.

## Two caveats worth knowing

The [NI timestamp overview](https://www.ni.com/en/support/documentation/supplemental/08/labview-timestamp-overview.html)
lists example values. Two of them trip people up, and `lvtime` is built around the byte
values rather than the labels:

- **The 0.8 fraction only survives in fixed point.** 0.8 s is exactly
  `0xCCCCCCCCCCCCCCCD` in 2**-64 units (so -5.2 s is `{0xFFFFFFFFFFFFFFFA, 0xCCCCCCCCCCCCCCCD}`).
  Build that same fraction from a C `double` and it collapses to `0xCCCCCCCCCCCCC000`, losing
  the low bits, which NI's own page notes. `from_float(-5.2)` reproduces the lossy
  `0xCCCCCCCCCCCCC000`; `from_decimal("-5.2")` reproduces the exact `0xCCCCCCCCCCCCCCCD`. Use
  the Decimal path when the bytes have to match.
- **NI's page mislabels the 2002 row by a day.** It labels `{3092601600, 0}` (`0xB8555B00`)
  as "01/01/2002 00:00:00 UTC", but 3092601600 seconds after the 1904 epoch is
  2001-12-31 00:00:00 UTC, one day earlier. `lvtime` decodes the byte value, so it returns
  the correct 2001-12-31.

## Why

LabVIEW stores absolute time as a 128-bit fixed-point value: a **signed** 64-bit count
of whole seconds since **1904-01-01 00:00:00 UTC** and an **unsigned** 64-bit fraction in
units of 2**-64 s ([NI, LabVIEW Timestamp Overview](https://www.ni.com/en/support/documentation/supplemental/08/labview-timestamp-overview.html)).
Two things trip people up every time:

- **The 1904 epoch.** The Unix offset is exactly `2082844800` seconds. Hand-rolled code
  that re-derives or mistypes this constant lands "off by 300 years" or by a timezone, a
  recurring complaint on the NI and LAVA forums.
- **The precision.** The format resolves far below a nanosecond. Round-tripping through a
  C `double` or a `datetime` throws most of that away (about a 0.5 microsecond step through
  a double). npTDMS's default read path surfaces timestamps as NumPy `datetime64` truncated
  to microseconds, which loses the fraction; it does expose the lossless pair with
  `raw_timestamps=True`, but only for timestamps read from inside a TDMS file.

Inside a TDMS file, then, npTDMS already covers the lossless case. What is missing is a
standalone codec for the raw 16-byte form that is **not** part of a TDMS file: Flatten To
String blobs, protocol payloads, anything where you hold the bytes directly. The LabVIEW-side
toolkits (OpenG, VIPM/JKI) run inside LabVIEW and ship no Python reader. `lvtime` fills that
gap: a tiny, typed, zero-dependency (stdlib only) library that keeps the exact integer pair
with the correct signedness, reads and writes the 16-byte on-disk form (big- or little-endian)
independent of any file container, and converts to a UTC-aware `datetime` only when you ask
(rounded to the microsecond, which is all `datetime` can hold).

## Scope

`lvtime` handles the absolute-time value itself: the integer pair, the 16-byte record, the
`datetime` conversion, and the Unix and float-seconds views. It does not parse whole TDMS or
flattened-data files; it is the piece you reach for once you have the 16 raw bytes in hand, or
the seconds-and-fraction pair you need to turn into a real instant. LabVIEW follows the
Gregorian calendar and ignores leap seconds, and so does this library.

## License

MIT. See [LICENSE](LICENSE).

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/
