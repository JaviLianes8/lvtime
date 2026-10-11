# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
