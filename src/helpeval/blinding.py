"""Hide which chatbot wrote each answer before a human scores it.

If a rater knows an answer came from a famous product, they may judge it more
kindly or more harshly. Blinding replaces product names with neutral codes
("System A", "System B"...) and removes the names from the answer text where
the chatbot mentions itself. The key that links codes back to products is
written to a separate file that raters must not see.
"""

from __future__ import annotations

import json
import random
import re
from pathlib import Path

from .schema import Response


def make_codes(products: list[str], seed: int) -> dict[str, str]:
    """Assign each product a random letter code. The seed makes it repeatable."""
    unique = sorted(set(products))
    rng = random.Random(seed)
    rng.shuffle(unique)
    return {product: f"System {chr(65 + i)}" for i, product in enumerate(unique)}


def scrub(text: str, names: list[str], replacement: str = "[the assistant]") -> str:
    """Remove self-mentions such as 'As ExampleChat, I...' from an answer."""
    for name in sorted(names, key=len, reverse=True):
        if name:
            text = re.sub(re.escape(name), replacement, text, flags=re.IGNORECASE)
    return text


def blind(
    responses: list[Response],
    self_names: dict[str, list[str]],
    seed: int,
    key_path: str | Path,
) -> list[dict]:
    """Return blinded records for raters and save the unblinding key separately.

    ``self_names`` maps each product to the words it might use to name itself,
    e.g. {"ExampleChat app": ["ExampleChat", "Example AI"]}.
    The output is shuffled so raters cannot guess the product from the order.
    """
    codes = make_codes([r.product for r in responses], seed)
    all_names = [n for names in self_names.values() for n in names] + list(codes)
    blinded = [
        {
            "response_id": r.response_id,
            "item_id": r.item_id,
            "system": codes[r.product],
            "text": scrub(r.text, all_names),
        }
        for r in responses
    ]
    random.Random(seed + 1).shuffle(blinded)
    Path(key_path).write_text(json.dumps(codes, indent=2), encoding="utf-8")
    return blinded
