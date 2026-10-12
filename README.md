# lvtime

Lossless LabVIEW 128-bit timestamp (1904 epoch) to and from datetime, UTC, sub-microsecond preserved.

A LabVIEW timestamp is a signed 64-bit count of whole seconds since 1904-01-01 00:00:00 UTC
plus an unsigned 64-bit fraction in units of 2**-64 s. `lvtime` reads and writes its 16-byte
form, keeps the exact integer pair, and converts to `datetime`, Unix time, floats and exact
`Decimal` values only when you ask. Pure Python, typed, no dependencies.

- [Guide](https://github.com/JaviLianes8/lvtime/blob/main/GUIDE.md): every function, the
  rounding rules, the byte layouts, errors and the command line.
- [Changelog](https://github.com/JaviLianes8/lvtime/blob/main/CHANGELOG.md)

## Install

```
pip install lvtime
```

Python 3.10 or newer.

## Quick start

```pycon
>>> from datetime import datetime, timezone
>>> from lvtime import LVTimestamp, read_timestamp
>>> ts = read_timestamp(bytes.fromhex("00000000e32589408000000000000000"))
>>> ts
LVTimestamp(seconds=3810888000, frac=9223372036854775808)
>>> ts.to_datetime()
datetime.datetime(2024, 10, 4, 12, 0, 0, 500000, tzinfo=datetime.timezone.utc)
>>> ts.to_unix()
1728043200.5
>>> LVTimestamp.from_datetime(datetime(2024, 10, 4, 12, 0, 0, 500000, tzinfo=timezone.utc)) == ts
True
>>> ts.to_bytes("little").hex()
'0000000000000080408925e300000000'

```

`LVTimestamp` is the lossless carrier: two instants one 2**-64 s unit apart stay distinct
even though they collapse to the same microsecond as a `datetime`. Instances are immutable,
hashable and sort in time order.

## Exact values

A float cannot hold most decimal fractions, and a `datetime` stops at the microsecond. The
`Decimal` path never touches a float, so it reproduces the exact bytes for a value like
-5.2 s from NI's timestamp overview:

```pycon
>>> from lvtime import LVTimestamp, from_decimal, from_float
>>> LVTimestamp.from_decimal("-5.2").hex()
'fffffffffffffffacccccccccccccccd'
>>> hex(from_float(-5.2)[1])
'0xccccccccccccc000'
>>> LVTimestamp(10, 1 << 63).to_decimal()
Decimal('10.5')

```

`from_decimal` takes a `Decimal`, `int` or `str` and refuses a `float`, so a lossy value
cannot slip in. Every conversion into a timestamp rounds once to the nearest 2**-64 s.

## Command line

```
$ lvtime decode 00000000e32589408000000000000000
2024-10-04T12:00:00.500000+00:00
$ lvtime decode --format fields 00000000e32589408000000000000000
seconds=3810888000 frac=9223372036854775808 iso=2024-10-04T12:00:00.500000+00:00 unix=1728043200.5
$ lvtime decode --format decimal fffffffffffffffacccccccccccccccd
epoch1904=-5.1999999999999999999891579782751449556599254719913005828857421875 unix=-2082844805.1999999999999999999891579782751449556599254719913005828857421875
$ lvtime encode 2024-10-04T12:00:00.5Z
00000000e32589408000000000000000
$ lvtime encode --byteorder little 2024-10-04T12:00:00.5Z
0000000000000080408925e300000000
```

Input can also come on stdin. Exit codes: 0 success, 1 bad input, 2 bad usage. See the
[Guide](https://github.com/JaviLianes8/lvtime/blob/main/GUIDE.md#command-line).

## Why

LabVIEW documents its timestamp as a signed 128-bit fixed-point number: the upper 64 bits
are whole seconds since 1904-01-01 UTC, the lower 64 bits the fraction
([NI, LabVIEW Timestamp Overview](https://www.ni.com/en/support/documentation/supplemental/08/labview-timestamp-overview.html)).
Two details make hand-written conversions go wrong:

- **Precision.** The fraction resolves 2**-64 s. A double near today's second counts steps
  in about 0.48 microseconds, and a `datetime` in whole microseconds, so both views round.
- **Layout.** Flatten To String and datalog files write the 16 bytes big-endian, seconds
  first. Little-endian TDMS files, the default
  ([NI, TDMS File Format Internal Structure](https://www.ni.com/en/support/documentation/supplemental/07/tdms-file-format-internal-structure.html)),
  write the same 128-bit number reversed, fraction first. The tests pin both layouts to
  files written by LabVIEW 2026.

[npTDMS](https://github.com/adamreeve/npTDMS) reads timestamps inside TDMS files; by default
it returns NumPy `datetime64` values, and its `raw_timestamps=True` option keeps the seconds
and fraction. `lvtime` is for the timestamp on its own, wherever the 16 bytes come from
(Flatten To String output, protocol payloads, logs, hex dumps), with exact conversions in
both directions and no dependencies.

## Scope

`lvtime` handles the timestamp value itself: the integer pair, the 16-byte record, and the
`datetime`, Unix, float and `Decimal` views. It does not parse TDMS or flattened-data files.
Like LabVIEW, it uses the Gregorian calendar and ignores leap seconds.

## License

MIT. See [LICENSE](https://github.com/JaviLianes8/lvtime/blob/main/LICENSE).

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/
