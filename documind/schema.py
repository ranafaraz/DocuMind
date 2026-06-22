"""Document schemas: what to extract from each document type, and the arithmetic
constraints the verifier enforces.

A schema is *data, not code* -- a list of scalar fields (each with the label
aliases that mark it on the page and a value ``kind``) plus an optional
line-item table. The same schema drives three things so they can never drift
apart: the generator (what to print), the extractors (what to look for), and the
verifier/metrics (how to check it).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Value kinds an extractor must canonicalise.
MONEY = "money"
TEXT = "text"
DATE = "date"
IDNUM = "id"


def label_key(text: str) -> str:
    """Normalise a label token for matching: lowercase, drop non-alphanumerics.

    ``"Bill To:"`` -> ``"billto"``; ``"Invoice #"`` -> ``"invoice"``. Labels are
    rendered as single tokens, so this is all the matching a label needs.
    """
    return re.sub(r"[^a-z0-9]", "", text.lower())


@dataclass(frozen=True)
class FieldSpec:
    name: str
    aliases: tuple[str, ...]   # label_key() forms that mark this field
    kind: str

    def matches_label(self, token_text: str) -> bool:
        return label_key(token_text) in self.aliases


@dataclass(frozen=True)
class TableSpec:
    # Column order matters: it is the left-to-right geometry of the table.
    columns: tuple[str, ...] = ("description", "quantity", "unit_price", "amount")
    # Header label per column (label_key form).
    header: tuple[str, ...] = ("description", "qty", "unitprice", "amount")


@dataclass(frozen=True)
class DocSchema:
    doc_type: str
    fields: tuple[FieldSpec, ...]
    table: TableSpec | None = None
    # Arithmetic constraints (only where a totals block exists).
    has_totals: bool = False

    def field(self, name: str) -> FieldSpec:
        for f in self.fields:
            if f.name == name:
                return f
        raise KeyError(name)

    @property
    def field_names(self) -> tuple[str, ...]:
        return tuple(f.name for f in self.fields)


# --- Invoice: header (2-column meta + bill-to), line-item table, totals block.
INVOICE = DocSchema(
    doc_type="invoice",
    fields=(
        FieldSpec("invoice_number", ("invoiceno", "invoicenum"), IDNUM),
        FieldSpec("date", ("date", "invoicedate"), DATE),
        FieldSpec("bill_to", ("billto", "customer"), TEXT),
        FieldSpec("subtotal", ("subtotal",), MONEY),
        FieldSpec("tax", ("tax",), MONEY),
        FieldSpec("total", ("total", "amountdue"), MONEY),
    ),
    table=TableSpec(),
    has_totals=True,
)

# --- Receipt: single-column merchant + items + totals (the layout 'control').
RECEIPT = DocSchema(
    doc_type="receipt",
    fields=(
        FieldSpec("merchant", ("merchant", "store"), TEXT),
        FieldSpec("date", ("date",), DATE),
        FieldSpec("subtotal", ("subtotal",), MONEY),
        FieldSpec("tax", ("tax",), MONEY),
        FieldSpec("total", ("total",), MONEY),
    ),
    table=TableSpec(columns=("description", "quantity", "unit_price", "amount"),
                    header=("item", "qty", "price", "amount")),
    has_totals=True,
)

# --- Form: pure key/value pairs in a 2-column grid, values *below* labels.
# No table, no arithmetic -- this is where reading order breaks worst.
FORM = DocSchema(
    doc_type="form",
    fields=(
        FieldSpec("name", ("name", "fullname"), TEXT),
        FieldSpec("date_of_birth", ("dob", "dateofbirth"), DATE),
        FieldSpec("id_number", ("id", "idno", "idnumber"), IDNUM),
        FieldSpec("city", ("city",), TEXT),
        FieldSpec("phone", ("phone", "tel"), IDNUM),
        FieldSpec("policy", ("policy", "policyno"), IDNUM),
    ),
)

SCHEMAS: dict[str, DocSchema] = {s.doc_type: s for s in (INVOICE, RECEIPT, FORM)}
DOCTYPES: tuple[str, ...] = tuple(SCHEMAS)


def get_schema(doc_type: str) -> DocSchema:
    if doc_type not in SCHEMAS:
        raise ValueError(f"unknown doc_type {doc_type!r}; choose from {DOCTYPES}")
    return SCHEMAS[doc_type]
