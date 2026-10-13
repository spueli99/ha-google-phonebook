from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

MODULE = (
    Path(__file__).parents[1]
    / "custom_components"
    / "google_phonebook"
    / "phone.py"
)
spec = spec_from_file_location("google_phonebook_phone", MODULE)
phone = module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(phone)


def test_german_formats():
    assert phone.normalize_phone("+49 1520 1234567", "49") == "4915201234567"
    assert phone.normalize_phone("0049 1520 1234567", "49") == "4915201234567"
    assert phone.normalize_phone("01520 1234567", "49") == "4915201234567"
    assert phone.to_e164("01520 1234567", "49") == "+4915201234567"


def test_sip_uri():
    value = "sip:4915201234567@provider.example"
    assert phone.normalize_phone(value, "49") == "4915201234567"
    assert phone.to_e164(value, "49") == "+4915201234567"


def test_tel_uri():
    assert phone.to_e164("tel:+492159814669", "49") == "+492159814669"


def test_empty():
    assert phone.normalize_phone("", "49") == ""
    assert phone.to_e164(None, "49") == ""


def test_other_country_default():
    assert phone.to_e164("020 1234567", "31") == "+31201234567"
