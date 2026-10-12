# lvtime guide

Everything `lvtime` 1.0 promises, in one page. Every example here runs as part of the test
suite.

1. [The value](#the-value)
2. [LVTimestamp](#lvtimestamp)
3. [Bytes and byte order](#bytes-and-byte-order)
4. [datetime](#datetime)
5. [Unix time and float seconds](#unix-time-and-float-seconds)
6. [Exact Decimal values](#exact-decimal-values)
7. [Rounding rules](#rounding-rules)
8. [Errors](#errors)
9. [Command line](#command-line)
10. [Upgrading from 0.3](#upgrading-from-03)

## The value

LabVIEW absolute time is a signed 128-bit fixed-point number with 64 fractional bits:

- `seconds`: signed 64-bit whole seconds since 1904-01-01 00:00:00 UTC, the upper half;
- `frac`: unsigned 64-bit fraction in units of 2**-64 s (about 0.054 attoseconds), the lower
  half.

The instant is `seconds + frac / 2**64`, so half a second before the epoch is
`(-1, 2**63)`. The calendar is Gregorian and leap seconds do not exist, as in LabVIEW and
Unix time. `LABVIEW_UNIX_EPOCH_OFFSET` is the 2082844800 s between the two epochs.

```pycon
>>> import lvtime
>>> lvtime.LABVIEW_UNIX_EPOCH_OFFSET
2082844800
>>> lvtime.to_datetime(lvtime.LABVIEW_UNIX_EPOCH_OFFSET).isoformat()
'1970-01-01T00:00:00+00:00'

```

Every conversion exists twice: as a plain function on the integer pair (`to_datetime(seconds,
frac)`, `from_datetime(dt) -> (seconds, frac)`) and as a method of `LVTimestamp`. The two
always agree.

## LVTimestamp

`LVTimestamp(seconds, frac=0)` is a frozen dataclass. Construction checks both fields:
`TypeError` for anything that is not an integer (floats, strings and `bool` included),
`ValueError` when a field is out of range. Integer types other than `int` that implement
`__index__`, such as NumPy integers from `npTDMS` raw timestamps, are accepted and stored as
plain `int`.

```pycon
>>> from lvtime import LVTimestamp
>>> LVTimestamp(-1, 1 << 63).to_float()
-0.5
>>> sorted([LVTimestamp(0, 1), LVTimestamp(-1), LVTimestamp(0)])
[LVTimestamp(seconds=-1, frac=0), LVTimestamp(seconds=0, frac=0), LVTimestamp(seconds=0, frac=1)]
>>> len({LVTimestamp(5), LVTimestamp(5, 0)})
1

```

Comparison and ordering follow the instant. The stable attributes are `seconds` and `frac`.
Methods: `to_datetime`, `from_datetime`, `to_unix`, `from_unix`, `to_float`, `from_float`,
`to_decimal`, `from_decimal`, `to_unix_decimal`, `from_unix_decimal`, `to_bytes`,
`from_bytes`, `hex` and `from_hex`. The `from_*` ones are class methods.

## Bytes and byte order

The 16-byte form comes in two byte orders, chosen with `byteorder` (type `ByteOrder`,
`"big"` or `"little"`; the default is `"big"`):

| `byteorder` | bytes 0 to 7 | bytes 8 to 15 | written by |
| --- | --- | --- | --- |
| `"big"` | seconds, big-endian | fraction, big-endian | Flatten To String, datalog files, big-endian TDMS |
| `"little"` | fraction, little-endian | seconds, little-endian | little-endian TDMS (the TDMS default) |

The little-endian form is the big-endian one reversed byte for byte, because both store the
same 128-bit number. The test suite checks both against files LabVIEW 2026 wrote in one run: a
TDMS file and a datalog file that hold the same instants.

```pycon
>>> from lvtime import LVTimestamp, read_timestamp, write_timestamp, read_timestamps, write_timestamps
>>> ts = LVTimestamp(1, 2)
>>> write_timestamp(ts).hex()
'00000000000000010000000000000002'
>>> write_timestamp(ts, "little").hex()
'02000000000000000100000000000000'
>>> read_timestamp(write_timestamp(ts, "little"), "little") == ts
True
>>> blob = write_timestamps([ts, LVTimestamp(0)])
>>> read_timestamps(blob)
[LVTimestamp(seconds=1, frac=2), LVTimestamp(seconds=0, frac=0)]
>>> LVTimestamp.from_hex("00000000 b8555b00 00000000 00000000").to_datetime().isoformat()
'2001-12-31T00:00:00+00:00'

```

The readers (`read_timestamp`, `read_timestamps`, `LVTimestamp.from_bytes`) take `bytes`,
`bytearray` or `memoryview`. `read_timestamp` needs exactly 16 bytes; `read_timestamps`
needs a multiple of 16 and returns a list (empty for an empty buffer). `write_timestamps`
takes any iterable of `LVTimestamp`. `hex()` gives 32 lower-case hex digits and `from_hex`
accepts spaces between bytes.

NI's timestamp overview labels the value `{3092601600, 0}` as 01/01/2002; 3092601600 s after
the epoch is 2001-12-31 00:00:00 UTC, which is what `lvtime` returns.

## datetime

`to_datetime` returns an aware `datetime` in UTC, rounded to the nearest microsecond.
`from_datetime` takes an aware `datetime` in any time zone; a naive one raises `ValueError`,
because it does not name an instant. The microsecond maps to the nearest 2**-64 s, so
`to_datetime(*from_datetime(dt)) == dt` for every aware `dt`.

```pycon
>>> from datetime import datetime, timedelta, timezone
>>> from lvtime import from_datetime, to_datetime
>>> from_datetime(datetime(2024, 10, 4, 14, tzinfo=timezone(timedelta(hours=2))))
(3810888000, 0)
>>> to_datetime(0, 2**64 - 1).isoformat()
'1904-01-01T00:00:01+00:00'

```

`datetime` covers the years 1 to 9999. Outside them `to_datetime` raises `OverflowError`;
the other views still work.

## Unix time and float seconds

`to_unix` and `to_float` return the nearest float to the exact instant, counted from 1970 or
from 1904. `to_float` is the same quantity LabVIEW gives when a timestamp is converted to a
double. A double keeps 53 significant bits, so for present-day dates it steps in about
0.48 microseconds.

`from_unix` and `from_float` take a float or an integer and convert its exact value. NaN and
infinities raise `ValueError`; so does anything beyond the 64-bit second range.

```pycon
>>> from lvtime import from_float, from_unix, to_float, to_unix
>>> to_unix(3810888000, 1 << 63)
1728043200.5
>>> from_unix(1728043200.5)
(3810888000, 9223372036854775808)
>>> from_float(-0.5)
(-1, 9223372036854775808)
>>> to_float(-1, 1 << 63)
-0.5

```

## Exact Decimal values

`to_decimal` and `to_unix_decimal` return the exact instant as a `Decimal`: every multiple
of 2**-64 has a finite decimal expansion, so nothing is rounded. The result is written with
no trailing zeros. `from_decimal` and `from_unix_decimal` take a `Decimal`, an `int` or a
`str` and round once to the nearest 2**-64 s. A `float` raises `TypeError` (use
`from_float`), and text that is not a finite decimal number raises `ValueError`.

```pycon
>>> from decimal import Decimal
>>> from lvtime import from_decimal, from_unix_decimal, to_decimal, to_unix_decimal
>>> from_decimal("-5.2") == (-6, 0xCCCCCCCCCCCCCCCD)
True
>>> to_decimal(0, 1)
Decimal('5.42101086242752217003726400434970855712890625E-20')
>>> to_unix_decimal(3810888000, 1 << 63)
Decimal('1728043200.5')
>>> from_unix_decimal(Decimal("1728043200.5"))
(3810888000, 9223372036854775808)

```

Arithmetic on the returned `Decimal` follows your decimal context, which keeps 28 digits by
default. A present-day instant needs up to 84, so raise the precision before adding or
subtracting timestamps exactly:

```pycon
>>> from decimal import Context, localcontext
>>> from lvtime import from_decimal, to_decimal
>>> with localcontext(Context(prec=100)):
...     total = to_decimal(3810888000, 1 << 63) + to_decimal(0, 1)
>>> from_decimal(total)
(3810888000, 9223372036854775809)

```

## Rounding rules

| Conversion | Rounding |
| --- | --- |
| `to_datetime` | nearest microsecond; an exact half goes to the later microsecond |
| `from_datetime` | nearest 2**-64 s (a microsecond never falls on a tie) |
| `to_float`, `to_unix` | nearest float (ties to even), one rounding of the exact value |
| `from_float`, `from_unix` | nearest 2**-64 s, ties to even, from the exact float value |
| `to_decimal`, `to_unix_decimal` | exact |
| `from_decimal`, `from_unix_decimal` | nearest 2**-64 s, ties to even, from the exact decimal value |

A fraction that rounds up to a whole second carries into `seconds`. A result whose second
count leaves the signed 64-bit range raises `ValueError`.

## Errors

| Error | When |
| --- | --- |
| `TypeError` | a field or argument of the wrong type: a float or `bool` second count, a `str` for bytes, a `float` for `from_decimal`, anything but a `datetime` for `from_datetime`, anything but an `LVTimestamp` in the writers |
| `ValueError` | a value out of range or malformed: fields outside 64 bits, the wrong byte count, a `byteorder` other than `"big"` or `"little"`, a naive `datetime`, NaN or infinity, text that is not a number or not hex |
| `OverflowError` | `to_datetime` for an instant outside the years 1 to 9999 |

Messages are short: they never repeat more than about 40 characters of what you passed, and
huge integers are described by their size.

## Command line

The `lvtime` command (also `python -m lvtime`) has two subcommands:

- `lvtime decode [HEX] [--byteorder big|little] [--format iso|fields|json|decimal]` turns 32
  hex digits (spaces allowed) into an ISO 8601 instant, the pair and Unix time (`fields`,
  `json`), or the exact seconds since 1904 and since 1970 (`decimal`).
- `lvtime encode [ISO] [--byteorder big|little]` turns an ISO 8601 datetime into 32 hex
  digits. A trailing `Z` means UTC, and a datetime without an offset is taken as UTC.

Without the positional argument both read standard input. Exit codes: 0 success, 1 bad input
(a one-line message on stderr), 2 bad usage. `iso`, `fields` and `json` need an instant
inside the years 1 to 9999; `decimal` works for every value.

```
$ lvtime decode --format json 00000000b8555b000000000000000000
{"seconds": 3092601600, "frac": 0, "iso": "2001-12-31T00:00:00+00:00", "unix": 1009756800.0}
$ lvtime decode --format decimal 7fffffffffffffff0000000000000000
epoch1904=9223372036854775807 unix=9223372034771931007
$ lvtime encode 1903-12-31T23:59:59.5Z
ffffffffffffffff8000000000000000
```

## Upgrading from 0.3

- `byteorder="little"` now means the 128-bit value reversed byte for byte (fraction first),
  the layout of little-endian TDMS files. 0.3 wrote the seconds first. To read bytes written
  by 0.3 in little-endian, swap the two 8-byte halves first:
  `read_timestamp(old[8:] + old[:8], "little")`.
- Fields and arguments are type-checked: floats, strings and `bool` raise `TypeError`
  instead of being accepted.
- `from_float` and `from_unix` are exact (0.3 lost the fraction of small negative values and
  added the epoch offset in float arithmetic); `to_float` and `to_unix` round once.
- `from_decimal` raises `ValueError` (not `decimal.InvalidOperation` or `OverflowError`) for
  bad text, NaN and infinities.
- `to_decimal` and `to_unix_decimal` return the same values without trailing zeros, for
  example `Decimal('10.5')` where 0.3 printed 64 decimal places.
- `LVTimestamp` instances can be ordered with `<`.
