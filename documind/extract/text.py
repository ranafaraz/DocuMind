"""Reading-order extractor: the layout-blind ablation.

It reads the page as ordered lines of text (exactly what an OCR text dump or a
"throw the boxes away and feed the string to a regex/LLM" pipeline sees) and
takes each field's value as the tokens that *follow its label on the same line*,
up to the next label. It uses line breaks -- that is still reading order -- but no
2-D reasoning: it cannot look in a second column or on the line *below* a label.
So it matches the layout extractor on single-column horizontal layouts and breaks
where the value sits below the label (`Bill To`) or in a parallel column (the
two-column `form`). The table parser is column-blind in the same spirit: the last
three tokens of a row are assumed to be qty/price/amount.
"""

from __future__ import annotations

from documind.extract.base import (
    Extractor,
    canon_value,
    cell_text,
    is_number,
    table_region,
)
from documind.geometry import group_lines, join_text
from documind.normalize import norm_text, parse_int, parse_money
from documind.schema import DocSchema, FieldSpec, label_key
from documind.types import Document, LineItem, Record, Token


class TextExtractor(Extractor):
    name = "text"

    def extract(self, doc: Document, schema: DocSchema) -> Record:
        lines = group_lines(doc.tokens)
        all_label_keys: set[str] = set().union(*(set(f.aliases) for f in schema.fields))
        fields = {fs.name: self._field(lines, fs, all_label_keys) for fs in schema.fields}
        items = self._table(doc, schema) if schema.table else []
        return Record(schema.doc_type, fields, items)

    @staticmethod
    def _field(lines: list[list[Token]], fs: FieldSpec, all_label_keys: set[str]) -> str:
        for line in lines:
            idx = next((i for i, t in enumerate(line) if fs.matches_label(t.text)), None)
            if idx is None:
                continue
            value: list[Token] = []
            for t in line[idx + 1:]:
                if label_key(t.text) in all_label_keys:
                    break
                value.append(t)
            return canon_value(fs.kind, cell_text(value))
        return ""

    def _table(self, doc: Document, schema: DocSchema) -> list[LineItem]:
        _, body = table_region(doc, schema)
        items: list[LineItem] = []
        for line in body:
            # Layout-blind row parse: trailing 3 numerics are the numeric columns.
            if len(line) >= 4 and all(is_number(t.text) for t in line[-3:]):
                desc = norm_text(join_text(line[:-3]))
                qty = parse_int(line[-3].text) or 0
                unit = parse_money(line[-2].text) or 0.0
                amount = parse_money(line[-1].text) or 0.0
                items.append(LineItem(desc, qty, round(unit, 2), round(amount, 2)))
            # Number-free lines (wrapped descriptions) can't be placed without
            # column geometry and are dropped -- so wrapped cells lose their tail.
        return items
