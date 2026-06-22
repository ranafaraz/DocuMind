"""Layout-aware extractor: associate values with fields using page geometry.

For each scalar field it reads the value to the *right* of the label, falling
back to the value *below* it (the standard key/value heuristic). For the table it
assigns every body token to a column by x-position and merges number-free lines
into the previous row (wrapped multi-line cells). Geometry is the whole signal --
scramble it (the null test) and this extractor has nothing to stand on.
"""

from __future__ import annotations

from documind.extract.base import (
    Extractor,
    canon_value,
    cell_text,
    find_label,
    table_region,
)
from documind.geometry import below_in_column, nearest_column, right_of
from documind.normalize import parse_int, parse_money
from documind.schema import DocSchema
from documind.types import Document, LineItem, Record, Token


class LayoutExtractor(Extractor):
    name = "layout"

    def extract(self, doc: Document, schema: DocSchema) -> Record:
        fields: dict[str, str] = {}
        for fs in schema.fields:
            label = find_label(doc.tokens, fs)
            if label is None:
                fields[fs.name] = ""
                continue
            value_toks = right_of(label, doc.tokens) or below_in_column(label, doc.tokens)
            fields[fs.name] = canon_value(fs.kind, cell_text(value_toks))
        items = self._table(doc, schema) if schema.table else []
        return Record(schema.doc_type, fields, items)

    def _table(self, doc: Document, schema: DocSchema) -> list[LineItem]:
        anchors, body = table_region(doc, schema)
        if not anchors:
            return []
        rows: list[dict[str, list[Token]]] = []
        cols = [c for c, _ in anchors]
        for line in body:
            buckets: dict[str, list[Token]] = {c: [] for c in cols}
            for t in line:
                buckets[nearest_column(t.bbox.cx, anchors)].append(t)
            numeric_filled = any(buckets.get(c) for c in ("quantity", "unit_price", "amount"))
            if not numeric_filled and rows:
                # A number-free line is a wrapped continuation of the row above.
                rows[-1]["description"].extend(buckets.get("description", []))
            else:
                rows.append(buckets)
        return [self._row(b) for b in rows]

    @staticmethod
    def _row(buckets: dict[str, list[Token]]) -> LineItem:
        desc = cell_text(buckets.get("description", []))
        qty = parse_int(cell_text(buckets.get("quantity", []))) or 0
        unit = parse_money(cell_text(buckets.get("unit_price", []))) or 0.0
        amount = parse_money(cell_text(buckets.get("amount", []))) or 0.0
        return LineItem(desc, qty, round(unit, 2), round(amount, 2))
