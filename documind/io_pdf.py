"""Optional real-PDF loader (the ``[pdf]`` extra).

Turns the first page of a real PDF into the same ``Document`` of tokens-with-boxes
that the synthetic generator emits, so the *exact same* layout and text extractors
run on real documents with no other changes. Imported lazily; the offline
benchmark never touches this path.
"""

from __future__ import annotations

from documind.types import BBox, Document, Token


def load_pdf(path: str, doc_type: str, page: int = 0) -> Document:
    import pdfplumber  # lazy: only needed for the [pdf] extra

    with pdfplumber.open(path) as pdf:
        pg = pdf.pages[page]
        tokens = [
            Token(w["text"], BBox(w["x0"], w["top"], w["x1"], w["bottom"]))
            for w in pg.extract_words(use_text_flow=False)
        ]
        return Document(doc_type, tokens, float(pg.width), float(pg.height))
