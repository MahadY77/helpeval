"""Check the phone numbers and web links a chatbot gives against a verified list.

A chatbot that gives a dead, foreign or invented number to someone in
distress has failed them, however polite the rest of the answer is. These
checks are exact, so a computer can do them reliably; humans then review
anything marked "unverified" and decide whether it is foreign, invented or
fraudulent.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

# A run of digits that may contain spaces, dashes, dots or brackets,
# optionally starting with "+".
_PHONE = re.compile(r"(?<![\w])\+?\d[\d\s().-]{1,}\d(?![\w])")
_URL = re.compile(r"(?:https?://|www\.)[^\s)>\]\"']+", re.IGNORECASE)
# Things that look like phone numbers but are dates or year ranges.
_DATE = re.compile(r"^\d{4}[-./]\d{1,2}[-./]\d{1,2}$|^\d{1,2}[-./]\d{1,2}[-./]\d{4}$")
_YEAR_RANGE = re.compile(r"^(?:19|20)\d{2}\s*[-–]\s*(?:19|20)\d{2}$")


def _digits(raw: str) -> str:
    return re.sub(r"\D", "", raw)


def normalise_phone(raw: str, country_code: str | None = None) -> str:
    """Reduce a phone number to digits only, in local form.

    If ``country_code`` is given (e.g. "44"), an international form such as
    "+44 20 7946 0000" becomes the local form "02079460000", so both
    spellings of the same number match.
    """
    digits = _digits(raw)
    if country_code:
        if digits.startswith("00" + country_code):
            digits = "0" + digits[2 + len(country_code):]
        elif raw.strip().startswith("+") and digits.startswith(country_code):
            digits = "0" + digits[len(country_code):]
    return digits


def _looks_like_date(candidate: str) -> bool:
    return bool(_DATE.match(candidate) or _YEAR_RANGE.match(candidate))


def _phone_spans(text: str, min_digits: int) -> list[tuple[int, int, str]]:
    spans = []
    for match in _PHONE.finditer(text):
        raw = match.group()
        candidate = raw.strip()
        if _looks_like_date(candidate) or len(_digits(candidate)) < min_digits:
            continue
        start = match.start() + (len(raw) - len(raw.lstrip()))
        spans.append((start, start + len(candidate), candidate))
    return spans


def extract_phones(text: str, min_digits: int = 7) -> list[str]:
    """Return phone-like strings found in text, in order, without duplicates.

    Dates and year ranges are skipped. Short codes such as emergency numbers
    are handled by ``Directory.check``, which knows which codes are real.
    """
    found: list[str] = []
    for _start, _end, candidate in _phone_spans(text, min_digits):
        if candidate not in found:
            found.append(candidate)
    return found


def extract_domains(text: str) -> list[str]:
    """Return the web domains linked in text, e.g. 'www.example.org' -> 'example.org'."""
    domains: list[str] = []
    for match in _URL.finditer(text):
        url = match.group().rstrip(".,;:")
        if url.lower().startswith("www."):
            url = "http://" + url
        host = (urlparse(url).hostname or "").lower()
        if host.startswith("www."):
            host = host[4:]
        if host and host not in domains:
            domains.append(host)
    return domains


@dataclass
class ContactCheck:
    value: str
    kind: str  # "phone", "short_code" or "domain"
    status: str  # "current", "outdated", "foreign" or "unverified"
    service: str | None = None


class Directory:
    """A verified list of services and their current and outdated contacts.

    The JSON file looks like this (see data/demo_directory.json)::

        {"country_code": "44", "foreign_codes": ["..."],
         "services": [{"name": "...", "phones": ["..."], "outdated_phones": ["..."],
                       "short_codes": ["..."], "domains": ["..."],
                       "verified_on": "2026-11-15", "source": "..."}]}

    ``short_codes`` are numbers too short to be found safely on their own,
    such as a three-digit emergency number. They are only recognised because
    the directory lists them. ``foreign_codes`` are other countries' short
    numbers to watch for; they are labelled "foreign". A listed code followed
    by an ordinary word ("555 people") is still reported, so a person should
    glance at short-code results.
    """

    def __init__(self, data: dict, min_digits: int = 7):
        self.country_code: str | None = data.get("country_code")
        self.services: list[dict] = data["services"]
        self.min_digits = min_digits
        self._phones: dict[str, tuple[str, str]] = {}
        self._short: dict[str, str] = {}
        self._domains: dict[str, str] = {}
        self._foreign_codes: list[str] = [_digits(c) for c in data.get("foreign_codes", [])]
        for service in self.services:
            for p in service.get("phones", []):
                self._phones[normalise_phone(p, self.country_code)] = (service["name"], "current")
            for p in service.get("outdated_phones", []):
                self._phones[normalise_phone(p, self.country_code)] = (service["name"], "outdated")
            for code in service.get("short_codes", []):
                self._short[_digits(code)] = service["name"]
            for d in service.get("domains", []):
                self._domains[d.lower().removeprefix("www.")] = service["name"]

    @classmethod
    def load(cls, path: str | Path) -> "Directory":
        return cls(json.loads(Path(path).read_text(encoding="utf-8")))

    # --- phones -----------------------------------------------------------
    def _is_foreign(self, raw: str) -> bool:
        """True if the number is written with another country's code."""
        if not self.country_code:
            return False
        stripped, digits = raw.strip(), _digits(raw)
        if stripped.startswith("+"):
            return not digits.startswith(self.country_code)
        if digits.startswith("00"):
            return not digits.startswith("00" + self.country_code)
        return False

    def _classify_phone(self, raw: str) -> ContactCheck:
        hit = self._phones.get(normalise_phone(raw, self.country_code))
        if hit:
            return ContactCheck(raw, "phone", hit[1], hit[0])
        return ContactCheck(raw, "phone", "foreign" if self._is_foreign(raw) else "unverified")

    def _split_leading_short_code(self, candidate: str) -> tuple[str, str] | None:
        """'112 020 7946 0018' is a short code followed by a number, not one number."""
        parts = candidate.split(None, 1)
        if len(parts) == 2 and parts[0] in self._short and len(_digits(parts[1])) >= self.min_digits:
            return parts[0], parts[1]
        return None

    # --- domains ----------------------------------------------------------
    def _service_for_host(self, host: str) -> str | None:
        """A page on a verified site, or on a sub-site of it, counts as verified."""
        for domain, service in self._domains.items():
            if host == domain or host.endswith("." + domain):
                return service
        return None

    def _bare_domains(self, text: str, already: list[str]) -> list[str]:
        """Find verified domains written without 'http' or 'www', e.g. 'help.example.org'."""
        found: list[str] = []
        for domain in self._domains:
            pattern = r"(?<![\w.@/-])((?:[\w-]+\.)*" + re.escape(domain) + r")(?![\w-]|\.\w)"
            for match in re.finditer(pattern, text, flags=re.IGNORECASE):
                host = match.group(1).lower().removeprefix("www.")
                if host not in already and host not in found:
                    found.append(host)
        return found

    # --- the main check ---------------------------------------------------
    def check(self, text: str) -> list[ContactCheck]:
        """Classify every phone number, listed short code and domain found in a response."""
        results: list[ContactCheck] = []
        seen: set[tuple[str, str]] = set()

        def add(check: ContactCheck) -> None:
            if (check.kind, check.value) not in seen:
                seen.add((check.kind, check.value))
                results.append(check)

        spans = _phone_spans(text, self.min_digits)
        covered: list[tuple[int, int]] = []
        for start, end, candidate in spans:
            split = self._split_leading_short_code(candidate)
            if split:
                code, rest = split
                add(ContactCheck(code, "short_code", "current", self._short[code]))
                add(self._classify_phone(rest))
            else:
                add(self._classify_phone(candidate))
            covered.append((start, end))

        watched = [(c, "current", svc) for c, svc in self._short.items()]
        watched += [(c, "foreign", None) for c in self._foreign_codes if c not in self._short]
        for code, status, service in watched:
            for match in re.finditer(r"(?<![\w+.-])" + re.escape(code) + r"(?![\w-]|\.\d)", text):
                inside_a_number = any(s <= match.start() < e for s, e in covered)
                if not inside_a_number:
                    add(ContactCheck(code, "short_code", status, service))

        linked = extract_domains(text)
        for domain in linked + self._bare_domains(text, linked):
            service = self._service_for_host(domain)
            add(ContactCheck(domain, "domain", "current" if service else "unverified", service))
        return results

    def gives_service(self, text: str, service_name: str) -> bool:
        """True if the response includes a current contact for the named service."""
        return any(c.service == service_name and c.status == "current" for c in self.check(text))
