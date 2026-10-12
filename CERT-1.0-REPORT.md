# lvtime 1.0.0 certification report

Progress:
- [x] Branch `release/1.0.0` created from `main` (0.3.0)
- [x] Baseline gates run on 0.3.0
- [x] Ground-truth sources fetched (NI timestamp and TDMS pages, npTDMS), manifest tracked
- [x] API review and 1.0.0 API changes (item 1)
- [ ] Real LabVIEW 2026 captures (item 7)
- [ ] Errors, typing, docstrings and doctests (items 2 to 5)
- [ ] Contract, fuzz and mutation round (items 6, 9, 18)
- [ ] Docs: README, GUIDE, CHANGELOG (items 11, 12)
- [ ] Packaging, e2e and upgrade from PyPI 0.3.0 (items 8, 10, 13, 14)
- [ ] Independent reviewer and five QA lenses report PASS (items 16, 19)
- [ ] Gates (item 15)
- [ ] PR and trace guard (item 17); merge and publish left to the maintainer

## Baseline on 0.3.0 (before any change)

| Command | Result |
| --- | --- |
| `ruff format --check .`, `ruff check .`, `mypy --strict src tests` | exit 0 |
| `pytest` | 89 passed |
| `pytest --doctest-modules src` | no doctests at all |

Defects found in 0.3.0 at the start of this round:

- `"little"` wrote the seconds then the fraction, each little-endian. NI describes the
  timestamp as one 128-bit fixed-point number with the seconds in the upper 64 bits, and
  little-endian TDMS files (and npTDMS) store the fraction first: the whole 16 bytes
  reversed. The module's own docstring promised that byte-reversed form.
- `from_float` and `from_unix` lost the fraction of small negative values: `from_float(-2**-60)`
  returned `(0, 0)` instead of `(-1, 2**64 - 16)`, and `from_unix` added the epoch offset in
  float arithmetic.
- `from_decimal` rounded through a 96-digit context (double rounding for long inputs),
  raised `decimal.InvalidOperation` for bad text, `OverflowError` for infinity, and could
  try to build a billion-digit integer from `"1e999999999"`.
- `LVTimestamp(1.5, 0)` and `LVTimestamp(True, 0)` were accepted; a float second count then
  failed later inside `struct`.
- `to_datetime`, `to_float` and `to_decimal` did not check the second count; the CLI printed
  a traceback for a timestamp outside the `datetime` range.
- Error messages echoed whole inputs (a 10 MB string, a 100000-bit integer).
