# Contributing

Thanks for taking the time. This project keeps a small, predictable shape.

## Setup

```
pip install -r requirements-dev.txt
```

## Before you open a pull request

- Keep public API in `src/lvtime/__init__.py`; internals live in `_`-prefixed modules.
- Add a test for the behaviour you change. Tests inject time, disk and network; they
  never touch the real thing.
- Run `scripts/check.ps1` (format, lint, types, tests) and make sure it passes.
- One logical change per commit, imperative subject line.

## Ground-truth references

`tests/test_sources_truth.py` re-reads facts (byte values, field order, the epoch) from NI's
timestamp and TDMS pages and from npTDMS. Those copies are not in the repository; fetch them
with `python scripts/fetch_sources.py`, which also rewrites
`tests/fixtures/sources/MANIFEST.json` (URL, date, size, SHA-256). Without them the module
skips. With npTDMS installed, one more test cross-checks its reader.

Open an issue first if the change is large or shifts the public API.
