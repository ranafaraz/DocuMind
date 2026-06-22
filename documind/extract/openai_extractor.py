"""Optional OpenAI extractor (lazy, offline-safe).

Same contract as the Ollama backend: prompt a hosted model for the record as
JSON and fall back to the layout extractor on any failure (missing ``openai``
package, no ``OPENAI_API_KEY``, malformed response).
"""

from __future__ import annotations

import json
import os

from documind.extract.base import Extractor
from documind.extract.layout import LayoutExtractor
from documind.extract.ollama import _build_prompt, _record_from_json
from documind.geometry import reading_order
from documind.schema import DocSchema
from documind.types import Document, Record


class OpenAIExtractor(Extractor):
    name = "openai"

    def __init__(self, model: str = "gpt-4o-mini") -> None:
        self.model = model
        self._fallback = LayoutExtractor()

    def extract(self, doc: Document, schema: DocSchema) -> Record:
        try:
            if not os.environ.get("OPENAI_API_KEY"):
                raise RuntimeError("OPENAI_API_KEY not set")
            from openai import OpenAI

            text = " ".join(t.text for t in reading_order(doc.tokens))
            client = OpenAI()
            resp = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": _build_prompt(schema, text)}],
                response_format={"type": "json_object"},
                temperature=0,
            )
            data = json.loads(resp.choices[0].message.content)
            return _record_from_json(schema, data)
        except Exception:
            return self._fallback.extract(doc, schema)
