"""Phone-number parsing and normalization."""

from __future__ import annotations

import re


def extract_number_part(value: str | None) -> str:
    """Extract the number portion from a phone number or SIP/TEL URI."""
    if value is None:
        return ""

    raw = str(value).strip()
    if not raw:
        return ""

    lower = raw.lower()
    if lower.startswith("sips:"):
        raw = raw[5:]
    elif lower.startswith("sip:"):
        raw = raw[4:]
    elif lower.startswith("tel:"):
        raw = raw[4:]

    raw = raw.split("@", 1)[0]
    raw = raw.split(";", 1)[0]
    raw = raw.split("?", 1)[0]
    return raw.strip()


def normalize_phone(value: str | None, country_code: str = "49") -> str:
    """Normalize to international digits without a leading plus.

    Germany examples with country_code="49":
      +49 1520 1234567     -> 4915201234567
      0049 1520 1234567    -> 4915201234567
      01520 1234567        -> 4915201234567
      sip:4915...@host     -> 4915...
    """
    raw = extract_number_part(value)
    if not raw:
        return ""

    number = re.sub(r"\D", "", raw)
    if not number:
        return ""

    if number.startswith("00"):
        number = number[2:]

    cc = re.sub(r"\D", "", country_code)
    if number.startswith("0") and cc:
        number = cc + number[1:]

    return number


def to_e164(value: str | None, country_code: str = "49") -> str:
    """Return an E.164-style number, e.g. +4915201234567."""
    number = normalize_phone(value, country_code=country_code)
    return f"+{number}" if number else ""
