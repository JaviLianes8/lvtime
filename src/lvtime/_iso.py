"""A strict ISO 8601 reader for the command line, the same on every Python version.

``datetime.fromisoformat`` accepts different forms on each Python release and stops at
the microsecond, so the CLI reads its own small grammar instead:

    YYYY-MM-DD[(T| )hh:mm[:ss[(.|,)fraction]][offset]]
    YYYYMMDD[(T| )hhmm[ss[(.|,)fraction]][offset]]

where ``offset`` is ``Z`` (or ``z``), ``+hh``, ``+hh:mm`` or ``+hhmm`` (or ``-``). A missing offset
means UTC. The fraction may have any number of digits and is kept exactly.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from decimal import Context, Decimal, localcontext

from ._timestamp import LVTimestamp
from ._validate import short

# Every repeat is fixed-width apart from the fraction, which only a fixed tail follows,
# so matching stays linear in the input length.
_GRAMMAR = re.compile(
    r"(?P<y>\d{4})(?P<ds>-?)(?P<mo>\d{2})(?P=ds)(?P<d>\d{2})"
    r"(?:[T ](?P<h>\d{2})(?P<ts>:?)(?P<mi>\d{2})"
    r"(?:(?P=ts)(?P<s>\d{2})(?:[.,](?P<frac>\d+))?)?"
    r"(?P<tz>[Zz]|(?P<sign>[+-])(?P<oh>\d{2})(?::?(?P<om>\d{2}))?)?)?",
    re.ASCII,
)


def _offset(match: re.Match[str]) -> timezone:
    if match["sign"] is None:
        return timezone.utc
    minutes = int(match["oh"]) * 60 + int(match["om"] or 0)
    if int(match["om"] or 0) > 59 or minutes >= 24 * 60:
        raise ValueError("offset out of range")
    return timezone(timedelta(minutes=-minutes if match["sign"] == "-" else minutes))


def parse_iso(text: str) -> LVTimestamp:
    """Return the instant ISO 8601 ``text`` names, keeping every fractional digit."""
    match = _GRAMMAR.fullmatch(text)
    try:
        if match is None:
            raise ValueError("no match")
        if match["h"] is not None and (match["ds"] == "") != (match["ts"] == ""):
            raise ValueError("basic and extended forms mixed")
        dt = datetime(
            int(match["y"]),
            int(match["mo"]),
            int(match["d"]),
            int(match["h"] or 0),
            int(match["mi"] or 0),
            int(match["s"] or 0),
            tzinfo=_offset(match),
        )
        whole = LVTimestamp.from_datetime(dt)
    except (ValueError, OverflowError):
        raise ValueError(f"not an ISO 8601 datetime: {short(text)}") from None
    digits = match["frac"]
    if digits is None:
        return whole
    with localcontext(Context(prec=len(digits) + 40)):
        return LVTimestamp.from_decimal(whole.to_decimal() + Decimal("0." + digits))
