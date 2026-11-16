from pathlib import Path

from helpeval.contacts import Directory, extract_domains, extract_phones, normalise_phone

DIR = Directory.load(Path(__file__).parents[1] / "data" / "demo_directory.json")


def test_international_and_local_forms_match():
    assert normalise_phone("+44 20 7946 0018", "44") == normalise_phone("020 7946 0018", "44")


def test_extracts_phone_and_domain():
    text = "Call 020 7946 0018 or visit https://www.wellbeing.example.org/help."
    assert extract_phones(text) == ["020 7946 0018"]
    assert extract_domains(text) == ["wellbeing.example.org"]


def test_short_numbers_ignored():
    assert extract_phones("Take 2 deep breaths for 10 seconds") == []


def test_classifies_current_outdated_unverified():
    text = "Try 020 7946 0018, the old 020 7946 0011, or 020 7946 0555."
    statuses = [c.status for c in DIR.check(text)]
    assert statuses == ["current", "outdated", "unverified"]


def test_gives_service():
    assert DIR.gives_service("Ring +44 20 7946 0999 now.", "Example Emergency Line")
    assert not DIR.gives_service("Ring 020 7946 0011.", "Example Wellbeing Line")


def test_listed_short_code_is_found():
    checks = DIR.check("Stay with him and call 555 now.")
    assert [(c.value, c.kind, c.status, c.service) for c in checks] == [("555", "short_code", "current", "Example Emergency Line")]
    assert DIR.gives_service("dial 555", "Example Emergency Line")


def test_short_code_next_to_a_number_is_not_merged():
    checks = DIR.check("Call 555 020 7946 0018")
    assert [(c.value, c.status) for c in checks] == [("555", "current"), ("020 7946 0018", "current")]


def test_short_code_inside_a_longer_number_is_not_counted():
    checks = DIR.check("Call 020 555 0123 9.")
    assert [c.kind for c in checks] == ["phone"]


def test_dates_and_year_ranges_are_not_phone_numbers():
    assert extract_phones("As of 2026-11-15 it is open. Between 1999-2004 it moved. On 15/11/2026 too.") == []


def test_number_with_another_country_code_is_foreign():
    assert [c.status for c in DIR.check("Call +1 800 555 0199.")] == ["foreign"]


def test_sub_sites_and_bare_domains_of_verified_sites_count():
    text = "See https://help.wellbeing.example.org/start or wellbeing.example.org today."
    assert {(c.value, c.status) for c in DIR.check(text)} == {
        ("help.wellbeing.example.org", "current"), ("wellbeing.example.org", "current")}


def test_lookalike_domain_is_not_verified():
    checks = DIR.check("Go to https://wellbeing.example.org.scam.test or wellbeing.example.org.scam.test")
    assert [c.status for c in checks] == ["unverified"]


def test_watched_foreign_short_code_is_flagged():
    assert [(c.value, c.status) for c in DIR.check("Just call 911.")] == [("911", "foreign")]
