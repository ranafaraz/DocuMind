"""Optional Ollama extractor (lazy, offline-safe).

Prompts a locally running model to return the structured record as JSON. Any
failure -- missing ``requests``, no server, bad JSON -- degrades silently to the
layout extractor, so selecting this backend can never crash the pipeline.
"""

from __future__ import annotations

import json

from documind.extract.base import Extractor
from documind.extract.layout import LayoutExtractor
from documind.geometry import reading_order
from documind.schema import DocSchema
from documind.types import Document, LineItem, Record


class OllamaExtractor(Extractor):
    name = "ollama"

    def __init__(self, model: str = "llama3.1:8b", url: str = "http://localhost:11434") -> None:
        self.model = model
        self.url = url
        self._fallback = LayoutExtractor()

    def extract(self, doc: Document, schema: DocSchema) -> Record:
        try:
            import requests  # noqa: F401  (lazy: only needed for this backend)

            text = " ".join(t.text for t in reading_order(doc.tokens))
            prompt = _build_prompt(schema, text)
            resp = requests.post(
                f"{self.url}/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": False, "format": "json"},
                timeout=60,
            )
            resp.raise_for_status()
            data = json.loads(resp.json()["response"])
            return _record_from_json(schema, data)
        except Exception:
            return self._fallback.extract(doc, schema)


def _build_prompt(schema: DocSchema, text: str) -> str:
    names = ", ".join(schema.field_names)
    table = (
        " Include a 'line_items' list of {description, quantity, unit_price, amount}."
        if schema.table else ""
    )
    return (
        f"Extract these fields from the document as a JSON object: {names}.{table}\n"
        f"Return only JSON.\n\nDOCUMENT:\n{text}"
    )


def _record_from_json(schema: DocSchema, data: dict) -> Record:
    from documind.extract.base import canon_value

    fields = {
        fs.name: canon_value(fs.kind, str(data.get(fs.name, "")))
        for fs in schema.fields
    }
    items: list[LineItem] = []
    for row in data.get("line_items", []) or []:
        try:
            items.append(LineItem(
                str(row.get("description", "")),
                int(row.get("quantity", 0)),
                round(float(row.get("unit_price", 0.0)), 2),
                round(float(row.get("amount", 0.0)), 2),
            ))
        except (TypeError, ValueError):
            continue
    return Record(schema.doc_type, fields, items)
