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
ts = LVTimestamp(seconds=3813177600, frac=1 << 63)  # 2024-10-04 12:00:00.5 UTC
ts.to_datetime()                 # datetime(2024, 10, 4, 12, 0, 0, 500000, tzinfo=UTC)

# Build one from an aware datetime (naive input is rejected).
LVTimestamp.from_datetime(datetime(2024, 10, 4, tzinfo=timezone.utc))

# Read and write the 16-byte big-endian on-disk form (TDMS / "Flatten To String").
raw = write_timestamp(ts)        # 16 bytes: 8 signed seconds + 8 unsigned fraction
read_timestamp(raw) == ts        # True, every bit preserved

# The plain functions take and return the integer pair directly.
to_datetime(3813177600, 1 << 63)
seconds, frac = from_datetime(datetime(2024, 10, 4, tzinfo=timezone.utc))
```

`LVTimestamp` is the lossless carrier: it keeps the full 2**-64 s fraction, so two
instants a single fraction unit apart stay distinct even though they collapse to the
same microsecond when you ask for a `datetime`.

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
  a double), and existing readers inherit the loss: npTDMS surfaces timestamps as NumPy
  `datetime64`, truncated to microseconds, with no way back to the original fraction.

At the time of writing there is no PyPI package that converts a LabVIEW timestamp both ways
with the full 128-bit precision and the correct signedness. The toolkits that exist are
LabVIEW-side (VIPM/JKI), not Python. `lvtime` fills that gap: a tiny, typed, zero-dependency
(stdlib only) library that keeps the exact integer pair, reads and writes the 16-byte
big-endian on-disk form, and converts to a UTC-aware `datetime` only when you ask (rounded
to the microsecond, which is all `datetime` can hold).

## Scope

`lvtime` handles the absolute-time value itself: the integer pair, the 16-byte big-endian
record, and the `datetime` conversion. It does not parse whole TDMS or flattened-data
files; it is the piece you reach for once you have the 16 raw bytes in hand, or the
seconds-and-fraction pair you need to turn into a real instant. LabVIEW follows the
Gregorian calendar and ignores leap seconds, and so does this library.

## License

MIT. See [LICENSE](LICENSE).

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/
