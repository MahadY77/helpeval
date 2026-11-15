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
