from scraper_and_import_embedding.detailed_scrapers.kawasaki_all_models import clean, price_to_int


def test_clean_none_or_empty():
    assert clean(None) == ""
    assert clean("") == ""


def test_clean_whitespace():
    assert clean("  Hello   world\n\t ") == "Hello world"


def test_price_to_int_simple():
    assert price_to_int("1,234,567") == 1234567
    assert price_to_int("123456") == 123456


def test_price_to_int_with_text():
    assert price_to_int("Price: 299,000 THB") == 299000
    assert price_to_int("N/A") is None
