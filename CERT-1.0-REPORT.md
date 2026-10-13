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

## Later QA rounds (item 19)

| Lens | Round | Head | Verdict | Findings and outcome |
| --- | --- | --- | --- | --- |
| a + d | 2 (fresh agent) | 6132529 | a PASS, d PASS | all nine earlier findings fixed; doctests, every README and GUIDE example and transcript, strict consumer with NumPy integers, `get_type_hints` on 3.10 and 3.14; wheel suite from the sdist on 3.10.19 (372 passed, 4 skipped), 3.11 to 3.14 and 3.14t (374 passed, 2 skipped); sabotaged installed CLI caught three ways; sdist install; 0.3.0 upgrade matches CHANGELOG |
| b + c | 2 (fresh agent) | 11467f3 | b PASS, c FAIL | 770,935 oracle checks, 180 checks on the LabVIEW captures, 168,000 fuzz calls, 18,000 CLI runs; all twelve earlier findings fixed. New: quadratic regex in `encode`, fractions cut with other separators, version-dependent reading of partial fractions, unbounded int-subclass repr, float and datetime subclass tricks, invalid ISO forms accepted. Fixed in 6132529 by a strict ISO grammar of its own (`_iso.py`), the same on every Python version |
| c | 3 | 6132529 | FAIL | 900,053 grammar strings against its own parser, identical digests on 3.10 to 3.14t, 900,000 fuzz calls; all seven earlier findings fixed. New: datetime subclass with a junk `tzinfo` property, bytes subclass with a lying `__len__`, int subclass hiding its size, lower-case `z` undocumented, released memoryview in `write_timestamps` on 3.10. Fixed in 09edd48 |
| c | 4 | 09edd48 | FAIL | 600,000 fuzz calls, 1.65 million grammar strings, 2,400 CLI runs; earlier five fixed. New: a `__bytes__` returning a lying bytes subclass, a `__repr__` returning a lying str subclass, decimal constants computed in the import-time context (wrong results near ties after `getcontext().Emin = -30`), CLI context taken from `DefaultContext`. Fixed in 11ff43d |
| c | 5 | 11ff43d | pending | |
| e | blind, fresh agent | 11ff43d | PASS with its contracts | 104 mutations, 100 killed, 4 equivalent; 14 needed new contracts (`tests/test_contract_edges.py`, `tests/test_cli_contract_edges.py`, added in 6d6b649) |

Lens e (contract strength) was cut by a usage limit once and relaunched fresh; its final round
was designed from the source alone without the author's table.

### Blind mutation round by lens e (items 18 and 19e)

| Id | Mutation | File | Result | Caught by |
| --- | --- | --- | --- | --- |
| M01 | big layout reads seconds unsigned | _codec.py | killed | test_cli_e2e.py::test_decimal_format_prints_the_exact_ni_value |
| M02 | little layout reads seconds unsigned | _codec.py | killed | test_oracle.py::test_byte_layouts_match_struct_and_the_reversed_128_bit_number |
| M03 | big layout uses little-endian fields | _codec.py | killed | test_cli_contract_edges.py::test_every_offset_form_names_the_same_instant[2024-10-04T05:00:00-07:00] |
| M04 | unpack little: fields not swapped | _codec.py | killed | test_cli_contract_edges.py::test_every_offset_form_names_the_same_instant[2024-10-04T05:00:00-07:00] |
| M05 | unpack: longer buffer not refused with ValueError | _codec.py | killed | test_robustness.py::test_a_bytes_subclass_cannot_lie_about_its_length |
| M06 | unpack_many: ragged length check dropped | _codec.py | killed | test_robustness.py::test_a_bytes_subclass_cannot_lie_about_its_length |
| M07 | unpack_many little: field order swapped | _codec.py | killed | test_contract.py::test_byte_promises |
| M08 | any non-big string accepted as little | _codec.py | killed | test_hostile.py::test_error_messages_stay_short[<lambda>6] |
| M09 | memoryview refused | _codec.py | killed | test_validation.py::test_byte_readers_accept_every_bytes_like_buffer |
| M10 | signed min off by one | _validate.py | killed | test_contract_edges.py::test_whole_seconds_print_as_plain_integers[-9223372036854775808] |
| M11 | signed max off by one | _validate.py | killed | test_contract_edges.py::test_from_unix_decimal_reaches_both_ends_of_the_range |
| M12 | frac max off by one | _validate.py | killed | test_convert.py::test_to_datetime_rejects_fraction_above_the_range |
| M13 | frac -1 accepted | _validate.py | killed | test_convert.py::test_to_datetime_rejects_negative_fraction |
| M14 | bools accepted as integers | _validate.py | killed | test_validation.py::test_pair_functions_refuse_non_integers[True-to_datetime] |
| M15 | non-integer gives ValueError | _validate.py | killed | test_validation.py::test_pair_functions_refuse_non_integers[1.0-to_datetime] |
| M16 | ties to odd | _validate.py | killed | test_oracle.py::test_from_float_and_from_unix_round_the_exact_float_once |
| M17 | ties always up | _validate.py | killed | test_oracle.py::test_from_float_and_from_unix_round_the_exact_float_once |
| M18 | message echo bound lifted | _validate.py | killed | test_cli_e2e.py::test_huge_bad_input_is_not_echoed_back |
| M19 | huge ints echoed in messages | _validate.py | killed | test_hostile.py::test_error_messages_stay_short[<lambda>1] |
| M20 | seconds range gives OverflowError | _validate.py | killed | test_hostile.py::test_error_messages_stay_short[<lambda>0] |
| M21 | epoch offset off by one | _convert.py | killed | test_cli_e2e.py::test_decimal_format_prints_the_exact_ni_value |
| M22 | to_datetime truncates | _convert.py | killed | test_convert.py::test_datetime_round_trip_is_microsecond_exact |
| M23 | to_datetime exact half rounds down | _convert.py | killed | test_oracle.py::test_to_datetime_rounds_to_the_nearest_microsecond_half_up |
| M24 | to_datetime out of range gives ValueError | _convert.py | killed | test_convert.py::test_to_datetime_overflows_outside_the_datetime_range |
| M25 | tzinfo with None offset not refused | _convert.py | killed (new test) | test_contract_edges.py::test_a_tzinfo_without_an_offset_counts_as_naive |
| M26 | from_datetime truncates microsecond | _convert.py | killed | test_oracle.py::test_from_datetime_inverts_to_datetime_for_every_microsecond |
| M27 | from_datetime float division, truncation | _convert.py | killed | test_oracle.py::test_from_datetime_inverts_to_datetime_for_every_microsecond |
| M28 | nonfinite float check dropped | _convert.py | killed | test_validation.py::test_float_inputs_must_be_finite_and_in_range[inf-from_float] |
| M29 | float API accepts bool | _convert.py | killed | test_validation.py::test_float_inputs_refuse_other_types[True-from_float] |
| M30 | split_units refuses the minimum | _convert.py | killed | test_contract_edges.py::test_from_unix_decimal_reaches_both_ends_of_the_range |
| M31 | split_units gives OverflowError | _convert.py | killed | test_hostile.py::test_out_of_range_values_share_one_message[<lambda>0] |
| M32 | to_float double rounding | _convert.py | killed | test_oracle.py::test_to_float_and_to_unix_are_correctly_rounded |
| M33 | to_unix offset sign | _convert.py | killed | test_cli_e2e.py::test_fields_and_json_formats_carry_the_pair |
| M34 | to_unix offset subtracted in float | _convert.py | killed | test_oracle.py::test_to_float_and_to_unix_are_correctly_rounded |
| M35 | from_float floors | _convert.py | killed | test_oracle.py::test_from_float_and_from_unix_round_the_exact_float_once |
| M36 | from_unix ties up | _convert.py | killed | test_oracle.py::test_from_float_and_from_unix_round_the_exact_float_once |
| M37 | from_unix offset sign | _convert.py | killed | test_contract.py::test_conversion_promises_on_one_instant |
| M38 | pre-cut to 60 places loses ties | _exact.py | killed | test_oracle.py::test_from_decimal_ties_go_to_even_and_near_ties_go_the_right_way |
| M39 | pre-cut double rounding | _exact.py | killed | test_oracle.py::test_from_decimal_ties_go_to_even_and_near_ties_go_the_right_way |
| M40 | exact lower bound off by one | _exact.py | killed | test_contract_edges.py::test_from_unix_decimal_reaches_both_ends_of_the_range |
| M41 | exact upper bound off by one | _exact.py | killed | test_contract_edges.py::test_from_unix_decimal_reaches_both_ends_of_the_range |
| M42 | huge int guard dropped | _exact.py | killed (new test) | test_contract_edges.py::test_huge_integers_are_refused_at_once[int-from_decimal] |
| M43 | str parse uses caller context | _exact.py | killed | test_robustness.py::test_rejected_text_leaves_the_callers_flags_clean |
| M44 | nonfinite Decimal check dropped | _exact.py | killed | test_validation.py::test_exact_inputs_refuse_bad_values[nan-from_decimal] |
| M45 | to_decimal not normalised | _exact.py | killed | test_docs.py::test_module_doctests_pass[lvtime._exact] |
| M46 | zero-frac shortcut dropped | _exact.py | killed (new test) | test_contract_edges.py::test_whole_seconds_print_as_plain_integers[0] |
| M47 | private context precision 28 | _exact.py | killed | test_cli.py::test_encode_then_decode_is_a_round_trip |
| M48 | to_unix_decimal offset sign | _exact.py | killed | test_cli_e2e.py::test_decimal_format_prints_the_exact_ni_value |
| M49 | from_unix_decimal range check without offset | _exact.py | killed (new test) | test_contract_edges.py::test_from_unix_decimal_reaches_both_ends_of_the_range |
| M50 | not ordered | _timestamp.py | killed | test_docs.py::test_module_doctests_pass[lvtime._timestamp] |
| M51 | not frozen / unhashable | _timestamp.py | killed | test_contract.py::test_timestamp_promise |
| M52 | from_bytes default little | _timestamp.py | killed | test_docs.py::test_module_doctests_pass[lvtime._timestamp] |
| M53 | hex ignores byteorder | _timestamp.py | killed | test_exact.py::test_hex_honours_byte_order |
| M54 | from_hex ignores byteorder | _timestamp.py | killed | test_exact.py::test_hex_honours_byte_order |
| M55 | from_hex type check dropped | _timestamp.py | equivalent | equivalent: bytes.fromhex already raises TypeError for every non-str; a str subclass passes both versions |
| M56 | write_timestamps byteorder check dropped | _io.py | killed | test_validation.py::test_byte_order_must_be_big_or_little[middle] |
| M57 | write_timestamp duck typed | _io.py | killed | test_validation.py::test_writers_refuse_things_that_are_not_timestamps |
| M58 | read_timestamps ignores byteorder | _io.py | killed | test_contract.py::test_byte_promises |
| M59 | single timestamp / buffer check dropped | _io.py | killed | test_robustness.py::test_write_timestamps_refuses_buffers_and_text[] |
| M60 | write_timestamps duck typed | _io.py | killed | test_validation.py::test_writers_refuse_things_that_are_not_timestamps |
| M69 | bad input exit 2 | _cli.py | killed | test_cli.py::test_empty_input_reports_an_error |
| M70 | interrupt exit 1 | _cli.py | killed (new test) | test_cli_contract_edges.py::test_an_interrupt_while_reading_stdin_exits_130 |
| M71 | closed stdout exit 0 | _cli.py | killed (new test) | test_cli_contract_edges.py::test_a_reader_that_went_away_gives_exit_1 |
| M72 | usage error unbounded | _cli.py | killed | test_robustness.py::test_usage_errors_do_not_echo_huge_arguments |
| M73 | fields format swapped | _cli.py | killed | test_cli.py::test_decode_fields_shows_the_integer_pair |
| M74 | json frac as string | _cli.py | killed | test_cli.py::test_decode_json_is_machine_readable |
| M75 | decimal format unix wrong | _cli.py | killed | test_cli_e2e.py::test_decimal_format_prints_the_exact_ni_value |
| M76 | input not stripped | _cli.py | killed | test_cli_e2e.py::test_encode_reads_stdin_and_treats_naive_input_as_utc |
| M77 | OverflowError escapes | _cli.py | killed | test_cli_e2e.py::test_bad_input_exits_one_with_a_short_message[args3] |
| M78 | decode default format json | _cli.py | killed | test_cli.py::test_decode_prints_the_iso_datetime |
| M79 | encode ignores byteorder | _cli.py | killed | test_cli.py::test_little_endian_flag_changes_the_bytes |
| M80 | decode ignores byteorder | _cli.py | killed | test_cli_e2e.py::test_little_endian_is_the_reversed_big_endian_form |
| M81 | missing stdin not handled | _cli.py | killed | test_robustness.py::test_missing_stdin_is_bad_input |
| M82 | bad hex echoed in full | _cli.py | killed | test_cli_e2e.py::test_huge_bad_input_is_not_echoed_back |
| M85 | stdin OSError escapes | _cli.py | killed | test_robustness.py::test_a_failing_stdin_is_bad_input |
| I01 | mixed date separators accepted | _iso.py | killed | test_cli_contract_edges.py::test_mixed_separators_and_bad_offsets_are_bad_input[2024-1004T12:00:00Z] |
| I02 | basic and extended forms may mix | _iso.py | killed | test_cli_encode_e2e.py::test_encode_refuses_everything_outside_its_grammar[2024-10-04T120000.5Z] |
| I03 | offset minute 60 accepted | _iso.py | killed | test_cli_encode_e2e.py::test_encode_refuses_everything_outside_its_grammar[2024-10-04T12:00:00.5+05:60] |
| I04 | offset +24:00 accepted | _iso.py | equivalent | equivalent: timezone() itself refuses |offset| >= 24 h with ValueError, mapped to the same message |
| I05 | negative offset sign lost | _iso.py | killed (new test) | test_cli_contract_edges.py::test_every_offset_form_names_the_same_instant[2024-10-04T05:00:00-07:00] |
| I06 | lower-case z refused | _iso.py | killed (new test) | test_cli_contract_edges.py::test_every_offset_form_names_the_same_instant[2024-10-04T12:00:00z] |
| I07 | comma fraction refused | _iso.py | killed | test_cli_contract_edges.py::test_every_fraction_digit_is_kept[1234567890] |
| I08 | fraction sum at 28 digits | _iso.py | killed (new test) | test_cli_contract_edges.py::test_every_fraction_digit_is_kept[1234567890123456789012345] |
| I09 | OverflowError not mapped | _iso.py | equivalent | equivalent: nothing in the try block can raise OverflowError (4-digit fields, timedelta arithmetic in range) |
| I10 | bad ISO echoed in full | _iso.py | killed | test_cli_encode_e2e.py::test_encode_errors_quote_what_the_user_typed |
| I11 | fraction cut to nanoseconds | _iso.py | killed (new test) | test_cli_contract_edges.py::test_every_fraction_digit_is_kept[1234567890123456789012345] |
| I12 | space separator refused | _iso.py | killed | test_cli_contract_edges.py::test_every_offset_form_names_the_same_instant[2024-10-04 |
| I13 | missing offset not UTC | _iso.py | killed | test_cli.py::test_little_endian_flag_changes_the_bytes |
| I14 | basic offset +hhmm refused | _iso.py | killed | test_cli_contract_edges.py::test_every_offset_form_names_the_same_instant[2024-10-04T05:00-0700] |
| I15 | trailing junk accepted | _iso.py | killed | test_cli_contract_edges.py::test_mixed_separators_and_bad_offsets_are_bad_input[2024-10-04T12:0000Z] |
| I16 | mixed time separators accepted | _iso.py | killed (new test) | test_cli_contract_edges.py::test_mixed_separators_and_bad_offsets_are_bad_input[2024-10-04T12:0000Z] |
| I17 | +hh offset refused | _iso.py | killed | test_cli_contract_edges.py::test_every_offset_form_names_the_same_instant[20241004T050000-07] |
| I18 | offset hours and minutes swapped | _iso.py | killed | test_cli_contract_edges.py::test_every_offset_form_names_the_same_instant[2024-10-04T05:00:00-07:00] |
| H01 | short trusts int subclass | _validate.py | killed | test_robustness.py::test_integer_subclasses_cannot_blow_up_messages |
| H02 | from_datetime trusts subclass __sub__ | _convert.py | killed | test_robustness.py::test_a_datetime_subclass_cannot_change_the_subtraction |
| H03 | _ratio trusts float subclass | _convert.py | killed | test_robustness.py::test_float_subclasses_cannot_lie_about_themselves |
| H04 | bytes subclass passed through | _codec.py | killed | test_robustness.py::test_a_bytes_subclass_cannot_lie_about_its_length |
| H05 | naive check trusts subclass utcoffset | _convert.py | killed (new test) | test_contract_edges.py::test_a_datetime_subclass_cannot_claim_an_offset_it_does_not_have |
| H06 | huge int guard trusts subclass | _exact.py | killed | test_contract_edges.py::test_huge_integers_are_refused_at_once[_ShortInt-from_decimal] |
| H07 | buffers accepted as iterables | _io.py | killed | test_robustness.py::test_write_timestamps_refuses_buffers_and_text[] |
| H08 | buffer copy trusts subclass __bytes__ | _codec.py | killed | test_robustness_more.py::test_a_buffer_cannot_swap_itself_for_another |
| H09 | short trusts repr return type | _validate.py | killed | test_robustness_more.py::test_a_lying_repr_cannot_blow_up_messages |
| H10 | private context does not trap invalid operations | _exact.py | killed (new test) | test_contract_edges.py::test_text_that_is_not_a_number_is_named_as_such[abc-from_decimal] |
| H11 | private context rounds down | _exact.py | equivalent | equivalent: every operation under the private context is exact (precision covers all digits; quantize names its own rounding) |

Equivalent: M55 (`bytes.fromhex` already refuses non-text with `TypeError`), I04 (`timezone()`
refuses a 24-hour offset with the same message), I09 (nothing in that block raises
`OverflowError`), H11 (every operation under the private context is exact, so its rounding mode
never applies).
