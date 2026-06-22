"""Extractor base class and the helpers both offline extractors share.

The shared helpers (canonicalisation, label finding, table-region detection)
guarantee the *only* difference between the layout and text extractors is how
they associate values with fields -- not how they clean strings or find the
table. That is what keeps the head-to-head honest: one independent variable.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod

from documind.geometry import group_lines, join_text, reading_order
from documind.normalize import norm_money_field, norm_text
from documind.schema import MONEY, DocSchema, FieldSpec, TableSpec, label_key
from documind.types import Document, Record, Token

_NUM_RE = re.compile(r"\d+(\.\d+)?$")


def is_number(text: str) -> bool:
    return bool(_NUM_RE.fullmatch(text.strip()))


def canon_value(kind: str, text: str) -> str:
    if not text:
        return ""
    if kind == MONEY:
        return norm_money_field(text) or ""
    return norm_text(text)


class Extractor(ABC):
    name: str = "base"

    @abstractmethod
    def extract(self, doc: Document, schema: DocSchema) -> Record:
        ...


def find_label(tokens: list[Token], field: FieldSpec) -> Token | None:
    """First token (in reading order) whose text is a label for ``field``."""
    for t in reading_order(tokens):
        if field.matches_label(t.text):
            return t
    return None


def _match_headers(line: list[Token], table: TableSpec) -> list[tuple[str, float]]:
    out: list[tuple[str, float]] = []
    for t in line:
        k = label_key(t.text)
        if k in table.header:
            out.append((table.columns[table.header.index(k)], t.bbox.cx))
    out.sort(key=lambda a: a[1])
    return out


def table_region(
    doc: Document, schema: DocSchema
) -> tuple[list[tuple[str, float]], list[list[Token]]]:
    """Locate the line-item table: its column anchors and its body lines.

    Both extractors agree on *where* the table is (header line down to the first
    totals/field label); they differ only in how each body line becomes a row.
    """
    if schema.table is None:
        return [], []
    lines = group_lines(doc.tokens)
    anchors: list[tuple[str, float]] = []
    header_y = None
    for line in lines:
        matched = _match_headers(line, schema.table)
        if len(matched) >= 2:
            anchors = matched
            header_y = min(t.bbox.y0 for t in line)
            break
    if header_y is None:
        return [], []
    field_keys = set().union(*(set(f.aliases) for f in schema.fields))
    totals_ys = [
        t.bbox.y0 for t in doc.tokens
        if label_key(t.text) in field_keys and t.bbox.y0 > header_y + 5
    ]
    totals_y = min(totals_ys) if totals_ys else float("inf")
    body = [
        ln for ln in lines
        if header_y + 5 < min(t.bbox.y0 for t in ln) < totals_y
    ]
    return anchors, body


def cell_text(tokens: list[Token]) -> str:
    return norm_text(join_text(tokens))
