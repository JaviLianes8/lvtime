import json

import pytest

from lvtime import LVTimestamp
from lvtime._cli import main

# 1904-01-01 plus half a second: seconds 0, frac 2**63.
EPOCH_HALF_HEX = LVTimestamp(0, 1 << 63).to_bytes().hex()


def test_decode_prints_the_iso_datetime(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["decode", EPOCH_HALF_HEX])
    assert code == 0
    assert capsys.readouterr().out.strip() == "1904-01-01T00:00:00.500000+00:00"


def test_decode_fields_shows_the_integer_pair(capsys: pytest.CaptureFixture[str]) -> None:
    main(["decode", "--format", "fields", EPOCH_HALF_HEX])
    out = capsys.readouterr().out
    assert "seconds=0" in out
    assert f"frac={1 << 63}" in out


def test_decode_json_is_machine_readable(capsys: pytest.CaptureFixture[str]) -> None:
    main(["decode", "--format", "json", EPOCH_HALF_HEX])
    payload = json.loads(capsys.readouterr().out)
    assert payload["seconds"] == 0
    assert payload["frac"] == 1 << 63


def test_encode_then_decode_is_a_round_trip(capsys: pytest.CaptureFixture[str]) -> None:
    main(["encode", "2024-10-04T12:00:00.5+00:00"])
    hex_text = capsys.readouterr().out.strip()
    main(["decode", hex_text])
    assert capsys.readouterr().out.strip() == "2024-10-04T12:00:00.500000+00:00"


def test_encode_treats_a_naive_datetime_as_utc(capsys: pytest.CaptureFixture[str]) -> None:
    main(["encode", "1970-01-01T00:00:00"])
    naive = capsys.readouterr().out.strip()
    main(["encode", "1970-01-01T00:00:00Z"])
    aware = capsys.readouterr().out.strip()
    assert naive == aware


def test_decode_reads_hex_from_stdin(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    import io

    monkeypatch.setattr("sys.stdin", io.StringIO(EPOCH_HALF_HEX + "\n"))
    main(["decode"])
    assert capsys.readouterr().out.strip() == "1904-01-01T00:00:00.500000+00:00"


def test_little_endian_flag_changes_the_bytes(capsys: pytest.CaptureFixture[str]) -> None:
    main(["encode", "--byteorder", "little", "1904-01-01T00:00:01Z"])
    little = capsys.readouterr().out.strip()
    main(["encode", "1904-01-01T00:00:01Z"])
    big = capsys.readouterr().out.strip()
    assert little != big
    assert main(["decode", "--byteorder", "little", little]) == 0


def test_empty_input_reports_an_error(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["decode", ""])
    assert code == 1
    assert "lvtime:" in capsys.readouterr().err


def test_bad_hex_reports_an_error(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["decode", "nothex"])
    assert code == 1
    assert capsys.readouterr().err.startswith("lvtime:")


def test_version_flag_prints_the_version(capsys: pytest.CaptureFixture[str]) -> None:
    import lvtime

    with pytest.raises(SystemExit) as exit_info:
        main(["--version"])
    assert exit_info.value.code == 0
    assert capsys.readouterr().out.strip() == f"lvtime {lvtime.__version__}"


def test_decode_decimal_shows_the_exact_value(capsys: pytest.CaptureFixture[str]) -> None:
    main(["decode", "--format", "decimal", EPOCH_HALF_HEX])
    out = capsys.readouterr().out
    assert "epoch1904=0.5" in out
    assert "unix=" in out
