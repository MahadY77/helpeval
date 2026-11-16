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

# Columns every app log must have.
COLUMNS = [
    "response_id", "item_id", "product", "tier", "surface", "version_seen",
    "tested_on", "search_on", "run", "text", "screenshot",
]
# Columns added in v0.2; older logs without them still load.
OPTIONAL_COLUMNS = ["tested_at", "condition", "settings", "account", "turn", "notes"]
_BLANK_MEANS_NONE = ["version_seen", "screenshot", "search_on", "tested_at", "condition", "settings", "account", "notes"]


def load_app_log(path: str | Path) -> list[Response]:
    """Load and validate a filled-in app log. Raises on the first bad row."""
    responses: list[Response] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = set(reader.fieldnames or [])
        missing = set(COLUMNS) - fields
        if missing:
            raise ValueError(f"app log is missing columns: {sorted(missing)}")
        unknown = fields - set(COLUMNS) - set(OPTIONAL_COLUMNS)
        if unknown:
            raise ValueError(f"app log has unknown columns: {sorted(unknown)}")
        for line, row in enumerate(reader, start=2):
            row = {k: (v.strip() if isinstance(v, str) else v) for k, v in row.items()}
            for name in _BLANK_MEANS_NONE:
                if name in row and row[name] in ("", None):
                    row[name] = None
            if row.get("turn") in ("", None):
                row.pop("turn", None)
            try:
                responses.append(Response(**row))
            except Exception as err:  # report which row is wrong
                raise ValueError(f"row {line}: {err}") from err
    ids = [r.response_id for r in responses]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate response_id values in app log")
    return responses
