"""Every conversion checked against an independent exact oracle built on ``fractions.Fraction``.

The oracle shares no code with the library: values are exact rationals, ``round`` on a
Fraction rounds half to even, and ``float(Fraction)`` is correctly rounded. Inputs come
from a seeded generator, so a failure always reproduces.
"""

from __future__ import annotations

import random
import struct
from datetime import datetime, timedelta, timezone
from decimal import Context, Decimal, localcontext
from fractions import Fraction

import lvtime
from lvtime import LVTimestamp

SEED = 20261013
UNIT = 2**64
OFFSET = 2082844800
EPOCH = datetime(1904, 1, 1, tzinfo=timezone.utc)


def _pair_of(value: Fraction) -> tuple[int, int]:
    return divmod(round(value * UNIT), UNIT)


def _value_of(seconds: int, frac: int) -> Fraction:
    return seconds + Fraction(frac, UNIT)


def _random_pairs(rng: random.Random, count: int) -> list[tuple[int, int]]:
    pairs = []
    for _ in range(count):
        bits = rng.choice([8, 32, 35, 40, 63])
        seconds = (
            rng.randrange(-(2**bits), 2**bits) if bits < 63 else rng.randrange(-(2**63), 2**63)
        )
        frac = rng.choice([0, 1, UNIT - 1, 1 << 63, rng.randrange(UNIT)])
        pairs.append((seconds, frac))
    return pairs


def _random_floats(rng: random.Random, count: int) -> list[float]:
    values = [0.0, -0.0, 5e-324, -5e-324, -(2.0**-60), 1 - 2.0**-53, -(2.0**62)]
    for _ in range(count):
        values.append(struct.unpack("<d", rng.getrandbits(64).to_bytes(8, "little"))[0])
        values.append(rng.uniform(-4e9, 4e9))
        values.append(rng.choice([-1.0, 1.0]) * rng.random() * 2.0 ** rng.randrange(-80, 62))
    return [v for v in values if v == v and abs(v) < 2.0**62]


def test_from_float_and_from_unix_round_the_exact_float_once() -> None:
    rng = random.Random(SEED)
    for value in _random_floats(rng, 3000):
        assert lvtime.from_float(value) == _pair_of(Fraction(value)), value
        assert lvtime.from_unix(value) == _pair_of(Fraction(value) + OFFSET), value


def test_to_float_and_to_unix_are_correctly_rounded() -> None:
    rng = random.Random(SEED + 1)
    for seconds, frac in _random_pairs(rng, 3000):
        exact = _value_of(seconds, frac)
        assert lvtime.to_float(seconds, frac) == float(exact)
        assert lvtime.to_unix(seconds, frac) == float(exact - OFFSET)


def test_to_decimal_is_exact_and_from_decimal_inverts_it() -> None:
    rng = random.Random(SEED + 2)
    for seconds, frac in _random_pairs(rng, 3000):
        exact = lvtime.to_decimal(seconds, frac)
        assert Fraction(exact) == _value_of(seconds, frac)
        assert Fraction(lvtime.to_unix_decimal(seconds, frac)) == _value_of(seconds, frac) - OFFSET
        assert lvtime.from_decimal(exact) == (seconds, frac)
        assert lvtime.from_decimal(str(exact)) == (seconds, frac)


def test_from_decimal_rounds_long_inputs_exactly_once() -> None:
    rng = random.Random(SEED + 3)
    for _ in range(3000):
        whole = rng.randrange(-(10**12), 10**12)
        digits = "".join(rng.choice("0123456789") for _ in range(rng.randrange(1, 140)))
        text = f"{whole}.{digits}"
        assert lvtime.from_decimal(text) == _pair_of(Fraction(text)), text
        assert lvtime.from_unix_decimal(text) == _pair_of(Fraction(text) + OFFSET), text


def test_from_decimal_ties_go_to_even_and_near_ties_go_the_right_way() -> None:
    rng = random.Random(SEED + 4)
    nudge = Decimal("1e-120")
    for _ in range(500):
        units = rng.randrange(-(2**80), 2**80)
        tie_exact = Fraction(2 * units + 1, 2 * UNIT)
        with localcontext(Context(prec=300)):
            tie = Decimal((2 * units + 1) * 5**65).scaleb(-65)
            above, below = tie + nudge, tie - nudge
        assert Fraction(tie) == tie_exact
        assert lvtime.from_decimal(format(tie, "f")) == _pair_of(tie_exact)
        assert lvtime.from_decimal(above) == divmod(units + 1, UNIT)
        assert lvtime.from_decimal(below) == divmod(units, UNIT)


def test_to_datetime_rounds_to_the_nearest_microsecond_half_up() -> None:
    rng = random.Random(SEED + 5)
    for _ in range(3000):
        seconds = rng.randrange(-60_000_000_000, 250_000_000_000)
        frac = rng.choice([rng.randrange(UNIT), 1 << 57, UNIT - 1])
        micros = (Fraction(frac * 10**6, UNIT) + Fraction(1, 2)).__floor__()
        expected = EPOCH + timedelta(seconds=seconds, microseconds=micros)
        assert lvtime.to_datetime(seconds, frac) == expected


def test_from_datetime_inverts_to_datetime_for_every_microsecond() -> None:
    rng = random.Random(SEED + 6)
    span = datetime.max.replace(tzinfo=timezone.utc) - datetime.min.replace(tzinfo=timezone.utc)
    for _ in range(3000):
        offset = timedelta(microseconds=rng.randrange(int(span / timedelta(microseconds=1))))
        dt = datetime.min.replace(tzinfo=timezone.utc) + offset
        seconds, frac = lvtime.from_datetime(dt)
        assert (seconds, frac) == _pair_of(
            Fraction((dt - EPOCH) // timedelta(microseconds=1), 10**6)
        )
        assert lvtime.to_datetime(seconds, frac) == dt


def test_byte_layouts_match_struct_and_the_reversed_128_bit_number() -> None:
    rng = random.Random(SEED + 7)
    for seconds, frac in _random_pairs(rng, 3000):
        big = (seconds * UNIT + frac).to_bytes(16, "big", signed=True)
        ts = LVTimestamp(seconds, frac)
        assert ts.to_bytes("big") == big == struct.pack(">qQ", seconds, frac)
        assert ts.to_bytes("little") == big[::-1] == struct.pack("<Qq", frac, seconds)
        assert LVTimestamp.from_bytes(big[::-1], "little") == ts


def test_ordering_follows_the_exact_instant() -> None:
    rng = random.Random(SEED + 8)
    stamps = [LVTimestamp(s, f) for s, f in _random_pairs(rng, 2000)]
    by_value = sorted(stamps, key=lambda ts: _value_of(ts.seconds, ts.frac))
    assert sorted(stamps) == by_value
