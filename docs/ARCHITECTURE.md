# Architecture

DocuMind is a small, dependency-free document-extraction library built around one
idea: **an extractor turns tokens-with-boxes into a structured record, and the
only thing that should vary between extractors is how they use the geometry.**
Keeping that boundary sharp is what makes the layout extractor's contribution
measurable against a reading-order baseline.

## Layers

```
documind/
  types.py          BBox, Token, Document, LineItem, Record, ExtractionResult
  config.py         env-driven Settings (offline defaults)
  normalize.py      money/text canonicalisation + cent-exact add_money
  schema.py         per-doc-type field specs + table spec (data, not code)
  geometry.py       group_lines, reading_order, right_of, below_in_column, columns
  documents.py      synthetic generator: (Document, ground-truth Record); scramble
  io_pdf.py         optional: a real PDF -> the same tokens-with-boxes
  extract/
    base.py         Extractor ABC + shared canonicalisation, label & table-region finding
    layout.py       LayoutExtractor: geometry-driven key/value + column table parse
    text.py         TextExtractor: reading-order ablation (line-based, layout-blind)
    ollama.py / openai_extractor.py   optional, lazy, graceful fallback to layout
  verify.py         SchemaVerifier + is_valid (arithmetic reconciliation/repair)
  pipeline.py       document -> extractor -> (verify) -> score vs. ground truth
  cli.py            extract | compare | render | extract-pdf | eval
evals/              metrics, harness (-> RESULTS.md), gate (CI shape checks)
```

## The shared spine

Both offline extractors call into `extract/base.py` for everything *except* value
association: canonicalising a field by kind (`money`/`text`/`date`/`id`), finding a
field's label token, and locating the line-item table's column anchors and body
lines. So when the results table shows the layout extractor ahead, that difference
is the geometry — not a second, subtly different table finder or string cleaner.

| Extractor | Key/value association | Table rows |
|---|---|---|
| `layout` | value **right of** the label, else **below** it in its column | tokens assigned to columns by x-position; number-free lines merge as wrapped cells |
| `text` | tokens **after the label on the same line**, up to the next label | "the last three tokens are qty/price/amount"; no columns |

The text extractor is a faithful stand-in for a layout-blind pipeline (feed the OCR
text dump to a regex or an LLM). It still respects line breaks — that is reading
order — but it has no 2-D model, so it cannot look in a second column or on the
line below a label. That is precisely where it breaks.

## Geometry primitives

`geometry.py` reconstructs structure from the bag of placed tokens:

- `group_lines` / `reading_order` — cluster tokens into text lines by vertical
  overlap; flatten top-to-bottom, left-to-right. This *is* the layout-blind view.
- `right_of` — same-row tokens to the right, stopping at a wide column gap.
- `below_in_column` — the nearest line below that left-aligns with a label
  (how a value placed under its label is read).
- `nearest_column` — assign a table token to the closest header anchor by x.

## The verifier

`SchemaVerifier` is the second, orthogonal lever. It checks the schema's arithmetic
— line `amount = qty × unit_price`, `subtotal = Σ amounts`, `total = subtotal +
tax` — and recomputes any field that violates it. All money math runs through
`add_money`, which sums in integer cents, so a recomputed total is bit-for-bit
identical to the ground truth (no spurious one-cent float disagreements). Crucially
the verifier is identical for both extractors and touches only arithmetic fields,
so its effect (validity, `total` accuracy) is independent of the layout effect
(field association). That independence is what lets the two be dissociated.

## Scoring

`pipeline.run_document` generates a document and its truth, runs the chosen
extractor, optionally verifies, then scores: micro field accuracy, line-item cell
F1 (a multiset of typed cells, so wrapped/extra rows are penalised), whole-document
exact match, and arithmetic validity. The harness pools 60 seeds × 3 doc types and
the gate enforces the **shape** of the result — the two effects, the single-column
control where the extractors must agree, and the scrambled-geometry null — not just
nice numbers.
