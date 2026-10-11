# lvtime round 2: ranked improvements

A ranked plan for the second substantial round on top of 0.2.0, driving the
library toward a perfect, lossless LabVIEW timestamp codec. Every claim below was
checked in a real Python REPL against the byte values published by NI before it
was written down.

## Ground truth

The authoritative reference is NI's own documented value table (decimal and hex
byte pairs), not the human-readable labels next to them:

| Instant (value) | seconds | fraction (hex) |
| --- | --- | --- |
| epoch, 1904-01-01 00:00:00 UTC | 0 | 0x0 |
| 0xB8555B00, 0x0 | 3092601600 | 0x0 |
| -0.5 s | -1 (0xFFFFFFFFFFFFFFFF) | 0x8000000000000000 |
| -5.2 s | -6 (0xFFFFFFFFFFFFFFFA) | 0xCCCCCCCCCCCCCCCD |

Two caveats that fall straight out of this table drive the work:

1. **NI's doc has an off-by-one-day label error.** The page labels
   {3092601600, 0} as "01/01/2002 00:00:00.000 UTC", but 3092601600 seconds
   after 1904-01-01 UTC is 2001-12-31 00:00:00 UTC, one day earlier. The byte
   value is the truth; the label is wrong. `lvtime` already decodes this value to
   2001-12-31, which is correct, and the contract test pins the byte value, not
   NI's mislabel.
2. **The 0.8 fraction only survives in fixed point.** 0.8 s is exactly
   0xCCCCCCCCCCCCCCCD in 2**-64 units. Build that same fraction through a C
   double and it collapses to 0xCCCCCCCCCCCCC000, losing the low bits. NI's page
   says as much. So a float round trip cannot reproduce the real NI bytes; only
   an exact integer or Decimal path can.

## Ranked improvements

1. **Exact Decimal path (no float in the round trip).** New `to_decimal`,
   `from_decimal`, `to_unix_decimal`, `from_unix_decimal` and the matching
   `LVTimestamp` methods. These convert through integer and `Decimal` arithmetic
   only, so `from_decimal("-5.2")` returns the exact NI pair
   (-6, 0xCCCCCCCCCCCCCCCD) that `from_float(-5.2)` cannot. This is the headline
   feature: it is the only way to reproduce NI's published bytes for a value like
   -5.2, and it keeps the full 2**-64 s resolution end to end. `from_decimal`
   accepts `Decimal`, `int` or `str` on purpose and refuses `float`, so a lossy
   float can never sneak in unnoticed.
2. **Hex convenience on the type: `LVTimestamp.hex()` and `from_hex()`.** People
   hold the flattened timestamp as a hex string far more often than as raw bytes
   (logs, protocol dumps, the clipboard). A one-call round trip from and to hex,
   byte-order aware, removes the `bytes.fromhex` / `.hex()` dance and backs the
   CLI.
3. **The NI rounding caveat, documented and tested.** A README section and a
   contract test that assert both facts above: the exact-vs-double fraction for
   0.8 and the real instant behind the mislabelled 2002 row. This turns a
   footgun that bites LabVIEW users into a guarantee.
4. **CLI polish.** Move the entry point to `lvtime._cli:main`, add `--version`,
   and add a `--format decimal` output to `decode` that prints the exact Decimal
   seconds since 1904 and since the Unix epoch. The console script already
   decodes and encodes the raw 16-byte hex form; this rounds it out.
5. **Golden contract and real end-to-end tests.** A contract test that asserts
   the complete promise against the NI byte vectors, and an end-to-end test that
   pip-installs the package editable and drives the real `lvtime` console script
   through `subprocess`, asserting stdout and exit codes and that the NI values
   round-trip exactly.

## Already covered in 0.2.0 (kept, not re-done)

- **Flatten / unflatten of the 16-byte big-endian form.** `read_timestamp` /
  `write_timestamp` and `LVTimestamp.to_bytes` / `from_bytes` already do exactly
  this, big-endian by default, matching "Flatten To String" and TDMS.
- **Little-endian option, batch helpers, datetime and Unix and float views,
  honest range errors, immutable typed dataclass.** All present since 0.2.0.
