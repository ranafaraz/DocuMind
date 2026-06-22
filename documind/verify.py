"""Schema verifier: reconcile an extracted record against its arithmetic.

Extraction can read every field off the page correctly and still be *internally
inconsistent* -- a smudged digit makes the printed total disagree with
subtotal + tax. The verifier is the second, orthogonal lever in DocuMind: it
checks the schema's constraints (line amounts = qty x price, subtotal = sum of
amounts, total = subtotal + tax) and recomputes a field that violates them. It
buys arithmetic *validity* (and repairs the total) regardless of which extractor
produced the record -- which is exactly why its effect dissociates cleanly from
the layout effect.
"""

from __future__ import annotations

from documind.normalize import add_money, money_str, parse_money
from documind.schema import DocSchema
from documind.types import LineItem, Record

# Sub-cent tolerance. All money arithmetic goes through `add_money` (integer
# cents), so legitimate values differ only by ~1e-14 float noise; a real
# one-cent OCR error (0.01) is comfortably above this and gets caught.
EPS = 0.005


def is_valid(record: Record, schema: DocSchema) -> bool:
    """True if the record satisfies the schema's arithmetic constraints."""
    if not schema.has_totals:
        return True
    for li in record.line_items:
        if abs(round(li.quantity * li.unit_price, 2) - li.amount) > EPS:
            return False
    sub = parse_money(record.fields.get("subtotal", "") or "")
    tax = parse_money(record.fields.get("tax", "") or "")
    tot = parse_money(record.fields.get("total", "") or "")
    if sub is None or tax is None or tot is None:
        return False
    items_sum = add_money(*(li.amount for li in record.line_items))
    if record.line_items and abs(items_sum - sub) > EPS:
        return False
    return abs(add_money(sub, tax) - tot) <= EPS


class SchemaVerifier:
    name = "schema"

    def verify(self, record: Record, schema: DocSchema) -> tuple[Record, int]:
        if not schema.has_totals:
            return record, 0
        repairs = 0
        fields = dict(record.fields)

        items: list[LineItem] = []
        for li in record.line_items:
            expected = round(li.quantity * li.unit_price, 2)
            if abs(expected - li.amount) > EPS:
                li = LineItem(li.description, li.quantity, li.unit_price, expected)
                repairs += 1
            items.append(li)

        sub = parse_money(fields.get("subtotal", "") or "")
        tax = parse_money(fields.get("tax", "") or "")
        tot = parse_money(fields.get("total", "") or "")
        items_sum = add_money(*(li.amount for li in items))

        if items and (sub is None or abs(sub - items_sum) > EPS):
            fields["subtotal"] = money_str(items_sum)
            sub = items_sum
            repairs += 1

        if sub is not None and tax is not None:
            expected_total = add_money(sub, tax)
            if tot is None or abs(tot - expected_total) > EPS:
                fields["total"] = money_str(expected_total)
                repairs += 1

        return Record(record.doc_type, fields, items), repairs
