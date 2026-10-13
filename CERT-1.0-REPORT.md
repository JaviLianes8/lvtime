# lvtime 1.0.0 certification report

Progress:
- [x] Branch `release/1.0.0` created from `main` (0.3.0)
- [x] Baseline gates run on 0.3.0
- [x] Ground-truth sources fetched (NI timestamp and TDMS pages, npTDMS), manifest tracked
- [x] API review and 1.0.0 API changes (item 1)
- [x] Real LabVIEW 2026 captures (item 7)
- [x] Errors, typing, docstrings and doctests (items 2 to 5)
- [x] Contract, fuzz and author mutation round (items 6, 9, 18)
- [x] Docs: README, GUIDE, CHANGELOG (items 11, 12)
- [x] Packaging, e2e and upgrade from PyPI 0.3.0 (items 8, 10, 13, 14), author run
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
- `lvtime encode 2024-10-04T12:00:00.5Z` failed on Python 3.10 (its `fromisoformat` takes only
  3 or 6 fractional digits), and `encode` cut every fraction to the microsecond.

## Ground truth (item 7)

- `tests/fixtures/real_labview/`: seven files written by LabVIEW 2026 Community 26.3.1f1 on
  this PC on 2026-10-12, driven headless through LabVIEW's ActiveX server, copied unchanged,
  with `manifest.json` (how each was made, size, SHA-256, offset of every timestamp). One run
  of the shipped example "TDMS Write Events Data.vi" produced a little-endian TDMS file and a
  big-endian front-panel datalog that hold the same two instants: the TDMS bytes are the
  datalog bytes reversed, fraction first. vi.lib timestamp VIs produced LabVIEW's own double
  for a timestamp (bit-identical to `to_float`) and three 128-bit additions and subtractions
  (reproduced exactly through `to_decimal`). `tests/test_real_labview.py` pins all of it;
  npTDMS 1.12.1, installed in a throwaway venv, reads the same TDMS property identically.
- Not capturable: a little-endian Flatten To String of a timestamp (no shipped VI exposes the
  byte-order input with a timestamp), and a TDMS timestamp of a chosen instant (the examples
  write clock readings; they are tied to the big-endian values by the same-instant pairs).
- `tests/fixtures/sources/`: NI's timestamp overview and TDMS format pages and npTDMS's
  `types.py`, `timestamp.py` and `tdms.py`, fetched 2026-10-12; only `MANIFEST.json` (URL, date,
  size, SHA-256) is tracked, the copies are git-ignored and excluded from the sdist, and
  `scripts/fetch_sources.py` re-creates them. `tests/test_sources_truth.py` re-reads every row
  of NI's example table and checks the 0.8 fraction both ways, the field order and epoch of
  the TDMS page, and npTDMS's field order; it skips when the copies are absent.
- Independent oracle: `tests/test_oracle.py` checks every conversion against exact
  `fractions.Fraction` arithmetic on seeded random inputs (floats over the whole range,
  decimal strings up to 140 digits, exact ties and values 1e-120 either side of them).

## Author mutation round (item 18)

Each mutation was applied alone to a clean clone on the laptop, the full suite run with
`-x`, and the clone restored. 45 mutations: 43 killed at once, 1 survived and was killed by a
new contract, 1 equivalent (the redundant code was removed).

| Id | Mutation | File | Result | Caught by |
| --- | --- | --- | --- | --- |
| M01 | signed 64-bit maximum off by one | `_validate.py` | killed | `test_exact.py::test_from_decimal_rejects_out_of_range_seconds` |
| M02 | signed 64-bit minimum excluded | `_validate.py` | killed | `test_timestamp.py::test_min_and_max_seconds_survive_the_byte_round_trip` |
| M03 | fraction maximum off by one | `_validate.py` | killed | `test_convert.py::test_to_datetime_rejects_fraction_above_the_range` |
| M04 | bool accepted as an integer | `_validate.py` | killed | `test_validation.py::test_pair_functions_refuse_non_integers[True-to_datetime]` |
| M05 | messages echo huge integers | `_validate.py` | survived, then killed | new `test_hostile::test_error_messages_stay_short` cases (a 4000-digit integer: Python refuses to print 30000 digits, which hid the bug) |
| M06 | messages echo long input | `_validate.py` | killed | `test_cli_e2e.py::test_huge_bad_input_is_not_echoed_back` |
| M07 | ties round up instead of to even | `_validate.py` | killed | `test_oracle.py::test_from_float_and_from_unix_round_the_exact_float_once` |
| M08 | ties round down instead of to even | `_validate.py` | killed | `test_oracle.py::test_from_float_and_from_unix_round_the_exact_float_once` |
| M09 | to_datetime truncates instead of rounding | `_convert.py` | killed | `test_convert.py::test_datetime_round_trip_is_microsecond_exact` |
| M10 | epoch offset off by one day | `_convert.py` | killed | `test_cli_e2e.py::test_decimal_format_prints_the_exact_ni_value` |
| M11 | from_datetime truncates the fraction | `_convert.py` | killed | `test_oracle.py::test_from_datetime_inverts_to_datetime_for_every_microsecond` |
| M12 | naive datetimes accepted | `_convert.py` | killed | `test_convert.py::test_from_datetime_rejects_naive_datetime` |
| M13 | to_float rounds twice (0.3.0 formula) | `_convert.py` | killed | `test_oracle.py::test_to_float_and_to_unix_are_correctly_rounded` |
| M14 | to_unix subtracts the offset in float (0.3.0 formula) | `_convert.py` | killed | `test_oracle.py::test_to_float_and_to_unix_are_correctly_rounded` |
| M15 | non-finite floats not checked | `_convert.py` | killed | `test_validation.py::test_float_inputs_must_be_finite_and_in_range[inf-from_float]` |
| M16 | bool accepted by from_float | `_convert.py` | equivalent, code removed | `as_int` already refuses `bool`; the redundant check in `_ratio` was deleted |
| M17 | split_units skips the range check | `_convert.py` | killed | `test_validation.py::test_float_inputs_must_be_finite_and_in_range[1e+300-from_float]` |
| M18 | from_unix applies the offset with the wrong sign | `_convert.py` | killed | `test_contract.py::test_conversion_promises_on_one_instant` |
| M19 | from_datetime does not type-check | `_convert.py` | killed | `test_validation.py::test_from_datetime_refuses_non_datetimes[None]` |
| M20 | pre-rounding to 100 places is half-even (double rounding) | `_exact.py` | killed | `test_oracle.py::test_from_decimal_ties_go_to_even_and_near_ties_go_the_right_way` |
| M21 | pre-rounding keeps fewer places than a tie needs | `_exact.py` | killed | `test_oracle.py::test_from_decimal_ties_go_to_even_and_near_ties_go_the_right_way` |
| M22 | no early range check (huge exponents) | `_exact.py` | killed | `test_validation.py::test_exact_inputs_refuse_bad_values[1e999999999-from_decimal]` |
| M23 | to_decimal keeps trailing zeros | `_exact.py` | killed | `test_docs.py::test_module_doctests_pass[lvtime._exact]` |
| M24 | to_unix_decimal offset sign | `_exact.py` | killed | `test_cli_e2e.py::test_decimal_format_prints_the_exact_ni_value` |
| M25 | from_unix_decimal forgets the offset | `_exact.py` | killed | `test_contract.py::test_conversion_promises_on_one_instant` |
| M26 | float accepted by from_decimal | `_exact.py` | killed | `test_exact.py::test_from_decimal_refuses_float` |
| M27 | bad text leaks decimal.InvalidOperation | `_exact.py` | killed | `test_validation.py::test_exact_inputs_refuse_bad_values[abc-from_decimal]` |
| M28 | NaN and infinity not checked | `_exact.py` | killed | `test_validation.py::test_exact_inputs_refuse_bad_values[nan-from_decimal]` |
| M29 | whole-second to_decimal off by one | `_exact.py` | killed | `test_cli_e2e.py::test_out_of_datetime_range_still_decodes_as_decimal` |
| M30 | little-endian back to the 0.3.0 field order | `_codec.py` | killed | `test_cli_e2e.py::test_little_endian_is_the_reversed_big_endian_form` |
| M31 | seconds read unsigned | `_codec.py` | killed | `test_cli_e2e.py::test_decimal_format_prints_the_exact_ni_value` |
| M32 | over-long buffer accepted by unpack | `_codec.py` | killed | `test_validation.py::test_read_timestamp_needs_exactly_16_bytes[17]` |
| M33 | batch length not checked | `_codec.py` | killed | `test_timestamp.py::test_read_timestamps_rejects_a_partial_record` |
| M34 | memoryview not flattened to bytes | `_codec.py` | killed | `test_validation.py::test_byte_readers_accept_every_bytes_like_buffer` |
| M35 | batch little-endian fields swapped | `_codec.py` | killed | `test_contract.py::test_byte_promises` |
| M36 | timestamps not ordered | `_timestamp.py` | killed | `test_docs.py::test_module_doctests_pass[lvtime._timestamp]` |
| M37 | seconds not normalised to int | `_timestamp.py` | killed | `test_validation.py::test_integer_like_values_are_accepted_and_stored_as_int` |
| M38 | empty batch skips the byteorder check | `_io.py` | killed | `test_validation.py::test_byte_order_must_be_big_or_little[middle]` |
| M39 | write_timestamp does not type-check | `_io.py` | killed | `test_validation.py::test_writers_refuse_things_that_are_not_timestamps` |
| M40 | CLI lets OverflowError through | `_cli.py` | killed | `test_cli_e2e.py::test_bad_input_exits_one_with_a_short_message[args3]` |
| M41 | CLI treats naive input as local time | `_cli.py` | killed | `test_cli.py::test_encode_treats_a_naive_datetime_as_utc` |
| M42 | CLI decode defaults to little-endian | `_cli.py` | killed | `test_cli.py::test_decode_prints_the_iso_datetime` |
| M43 | CLI decimal format prints a float | `_cli.py` | killed | `test_cli_e2e.py::test_decimal_format_prints_the_exact_ni_value` |
| M44 | CLI echoes the whole bad input | `_cli.py` | killed | `test_cli_e2e.py::test_huge_bad_input_is_not_echoed_back` |
| M45 | closed pipe on Windows raises a traceback | `_cli.py` | killed | `test_cli_e2e.py::test_a_closed_stdout_pipe_exits_quietly` |

## Packaging and end-to-end (items 8, 10, 14), author run

- `python -m build` and `twine check --strict`: both artifacts PASSED.
- Wheel: the nine modules, `py.typed`, LICENSE and metadata. Sdist: `src`, `tests` with the
  LabVIEW captures and the sources manifest, README, GUIDE, CHANGELOG, LICENSE, pyproject and
  the `.gitignore` hatchling always adds; no fetched NI or npTDMS copies, no scripts, no
  report or process notes.
- The wheel in a fresh venv on 3.10.19, 3.11.5, 3.12.12, 3.13.2 and 3.14.2, with the suite
  run from the extracted sdist with `src` removed (so it imports the installed wheel and drives
  its console script): 316 passed and 2 skipped on 3.11 to 3.14 (the sources module and the
  npTDMS cross-check), 314 passed and 4 skipped on 3.10 (plus the two `tomllib` checks).
  The first run found the Python 3.10 `encode` defect above.
- PyPI 0.3.0 installed, then upgraded in place to the 1.0.0 wheel: little-endian bytes,
  `from_float(-2**-60)`, `to_decimal` trailing zeros, `LVTimestamp(1.5, 0)`,
  `from_decimal("abc")`, `from_float(inf)` and `encode` of nine fractional digits change as
  CHANGELOG 1.0.0 lists.

## Independent QA lenses (item 19), first round at 8d11c9a

Every lens was a fresh agent that read the factory rules and CERT-1.0.md first, worked in its
own clone, ran things rather than reading, and reported back privately.

| Lens | First verdict | Findings | Fixed in |
| --- | --- | --- | --- |
| a. API and docs | FAIL (2 medium, 5 low, info) | CLI `encode` took an offset's fraction for the time's; `LVTimestamp` constructor typed `int` so NumPy integers failed `mypy --strict`; a test file over 200 lines; Flatten To String claimed as captured; four methods without examples; `_exact` docstring 0.8 wording; inconsistent out-of-range messages | 433bdf2, 97aa846 |
| b. Correctness and ground truth | FAIL (1 medium, 2 low, 2 info) | 6,986,448 library cases and 180,600 CLI cases against its own Fraction oracle, NI rows, npTDMS and the LabVIEW captures: 0 library mismatches. CLI `encode` cut basic-form fractions to the microsecond, misread offsets with seconds, and read fractions of minutes or hours as seconds | 73aaf4b |
| c. Adversarial and robustness | FAIL (1 medium-low, 6 low, info) | 152,963 fuzz cases, 26 scaling shapes (all linear), 366 CLI runs: a customised `decimal.DefaultContext` leaked in; an unbounded repr in one message; lying float and Decimal subclasses; caller decimal flags set; stdin `None` or failing, closed stderr (exit 120), 30 KB argparse echo, unicode digits as a fraction | 433bdf2 |
| d. Packaging and real e2e | PASS (6 low) | all five interpreters and 3.14t green from the installed wheel, sabotaged CLI caught, 0.3.0 upgrade matches; CHANGELOG claimed one change 0.3.0 already had and omitted two error-type changes; basic ISO form and offsets with seconds in `encode`; error text rewritten; skip message pointed at a script the sdist lacks | 73aaf4b |

Decision on CLI offsets: CPython's `fromisoformat` reads `+00:00:00.5` as `+00:00` while it
keeps `+05:30:00.5`, so `encode` now refuses every UTC offset with seconds instead of
trusting it. Offsets are `Z`, `+HH`, `+HH:MM` or `+HHMM`.
