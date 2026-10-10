# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
