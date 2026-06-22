"""Core value types shared across documents, extractors, and the verifier.

A :class:`Document` is the *only* thing an extractor sees: an unordered bag of
:class:`Token` objects, each carrying the geometry (a :class:`BBox`) that a real
OCR engine would emit. The geometry is what separates a layout-aware extractor
from a reading-order one -- so it lives here, in the data, not in any one
extractor. A :class:`Record` is the structured output (scalar fields + a
line-item table) that gets scored against ground truth.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class BBox:
    """An axis-aligned bounding box in page coordinates (origin top-left).

    Units are abstract "points"; only relative geometry matters. Frozen so a
    token (and therefore a document) is cheap to copy and hash.
    """

    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def cx(self) -> float:
        return (self.x0 + self.x1) / 2.0

    @property
    def cy(self) -> float:
        return (self.y0 + self.y1) / 2.0

    @property
    def width(self) -> float:
        return self.x1 - self.x0

    @property
    def height(self) -> float:
        return self.y1 - self.y0

    def y_overlap(self, other: BBox) -> float:
        """Vertical overlap (in points) -- two tokens on the same text line
        share most of their height. Negative/zero means no overlap."""
        return min(self.y1, other.y1) - max(self.y0, other.y0)

    def same_row(self, other: BBox, frac: float = 0.5) -> bool:
        """True if the boxes overlap vertically by at least ``frac`` of the
        smaller height -- a geometric, font-size-tolerant 'same line' test."""
        h = min(self.height, other.height)
        return h > 0 and self.y_overlap(other) >= frac * h


@dataclass(frozen=True)
class Token:
    """A single recognised text token plus where it sits on the page."""

    text: str
    bbox: BBox

    def with_bbox(self, bbox: BBox) -> Token:
        return Token(self.text, bbox)


@dataclass
class Document:
    """A page of tokens. ``doc_type`` selects the schema used to score it.

    The token order is deliberately *not* meaningful -- generators may shuffle
    it. Any notion of "reading order" must be reconstructed from geometry, which
    is exactly the dependency a layout-blind extractor cannot escape.
    """

    doc_type: str
    tokens: list[Token] = field(default_factory=list)
    width: float = 612.0
    height: float = 792.0


@dataclass(frozen=True)
class LineItem:
    """One row of an invoice/receipt line-item table."""

    description: str
    quantity: int
    unit_price: float
    amount: float

    def as_tuple(self) -> tuple[str, int, float, float]:
        return (self.description, self.quantity, round(self.unit_price, 2), round(self.amount, 2))


@dataclass
class Record:
    """A structured extraction (or ground truth).

    ``fields`` holds scalar key fields as *normalised strings* (so prediction
    and truth compare exactly); ``line_items`` holds the table. Money fields are
    canonicalised to two decimals by :func:`documind.normalize.money_str`.
    """

    doc_type: str
    fields: dict[str, str] = field(default_factory=dict)
    line_items: list[LineItem] = field(default_factory=list)

    def get(self, name: str) -> str | None:
        return self.fields.get(name)

    def as_dict(self) -> dict[str, Any]:
        return {
            "doc_type": self.doc_type,
            "fields": dict(self.fields),
            "line_items": [li.as_tuple() for li in self.line_items],
        }


@dataclass
class ExtractionResult:
    """Outcome of running one (extractor, verify) configuration on one document.

    Carries the predicted record and the per-document scores the harness pools:
    field accuracy, table-cell F1, whole-document exact match, and arithmetic
    validity (does the final record satisfy the schema's constraints).
    """

    doc_type: str
    extractor: str
    verified: bool
    predicted: Record
    truth: Record
    field_total: int = 0
    field_correct: int = 0
    cell_total: int = 0
    cell_correct: int = 0
    cell_pred: int = 0
    doc_exact: bool = False
    valid: bool = False
    repairs: int = 0

    @property
    def field_accuracy(self) -> float:
        return self.field_correct / self.field_total if self.field_total else 0.0
