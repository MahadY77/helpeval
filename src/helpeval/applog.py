"""Record answers collected by hand in public chatbot apps.

Apps cannot be automated fairly, and they can behave differently from the
developer interface, so a person types each question into the app and pastes
the answer into a spreadsheet (templates/app_log_template.csv). This module
loads that spreadsheet and checks every row before analysis.
"""

from __future__ import annotations

import csv
from pathlib import Path

from .schema import Response

COLUMNS = [
    "response_id", "item_id", "product", "tier", "surface", "version_seen",
    "tested_on", "search_on", "run", "text", "screenshot",
]


def load_app_log(path: str | Path) -> list[Response]:
    """Load and validate a filled-in app log. Raises on the first bad row."""
    responses: list[Response] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing = set(COLUMNS) - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"app log is missing columns: {sorted(missing)}")
        for line, row in enumerate(reader, start=2):
            row = {k: (v.strip() if isinstance(v, str) else v) for k, v in row.items()}
            if row["search_on"] in ("", None):
                row["search_on"] = None
            for optional in ("version_seen", "screenshot"):
                if row[optional] == "":
                    row[optional] = None
            try:
                responses.append(Response(**row))
            except Exception as err:  # report which row is wrong
                raise ValueError(f"row {line}: {err}") from err
    ids = [r.response_id for r in responses]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate response_id values in app log")
    return responses
