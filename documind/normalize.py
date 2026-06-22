"""Value canonicalisation shared by the generator, extractors, and verifier.

Extraction is only fair if prediction and ground truth are compared in the same
normalised form: ``$1,234.50`` and ``1234.5`` are the same money value, and a
field is "correct" iff its canonical string matches. Keeping these helpers in one
place means every component (truth, layout reader, text reader, verifier) speaks
the same dialect.
"""

from __future__ import annotations

import re

_MONEY_RE = re.compile(r"-?\d[\d,]*\.?\d*")
_INT_RE = re.compile(r"-?\d+")


def money_str(value: float | int) -> str:
    """Canonical money string: two decimals, no thousands separators."""
    return f"{float(value):.2f}"


def add_money(*values: float) -> float:
    """Sum money amounts in integer cents to avoid binary-float drift.

    The generator and the verifier both reconcile totals through this helper, so
    a recomputed total is bit-for-bit identical to the ground truth -- no spurious
    one-cent disagreements from two different float representations of the same
    2-decimal value."""
    return sum(round(v * 100) for v in values) / 100.0


def parse_money(text: str) -> float | None:
    """Parse a money-like token (``$1,234.50``, ``1234.5``) into a float."""
    m = _MONEY_RE.search(text.replace(" ", ""))
    if not m:
        return None
    cleaned = m.group(0).replace(",", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_int(text: str) -> int | None:
    m = _INT_RE.search(text)
    return int(m.group(0)) if m else None


def norm_money_field(text: str) -> str | None:
    """Canonicalise a money field string, or ``None`` if it is not money-like."""
    v = parse_money(text)
    return None if v is None else money_str(v)


def norm_text(text: str) -> str:
    """Collapse whitespace and trim -- the canonical form for free-text fields."""
    return re.sub(r"\s+", " ", text).strip()
