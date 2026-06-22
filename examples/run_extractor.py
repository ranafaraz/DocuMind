"""Minimal end-to-end example: extract one document and inspect the result.

Run: ``python examples/run_extractor.py``  (fully offline, no keys/downloads).
"""

from __future__ import annotations

from documind.config import Settings
from documind.pipeline import run_document


def main() -> None:
    cfg = Settings()
    for doc_type in ("invoice", "receipt", "form"):
        # The hero config: layout-aware extractor + schema verifier.
        layout = run_document(doc_type, seed=3, cfg=cfg, extractor_name="layout", verify=True)
        # The ablation: reading-order extractor, same document.
        text = run_document(doc_type, seed=3, cfg=cfg, extractor_name="text", verify=True)
        print(
            f"[{doc_type:<8}] layout fields {layout.field_correct}/{layout.field_total} "
            f"(exact={layout.doc_exact})  vs  text fields "
            f"{text.field_correct}/{text.field_total} (exact={text.doc_exact})"
        )


if __name__ == "__main__":
    main()
