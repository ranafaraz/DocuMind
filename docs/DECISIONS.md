# Design decisions

What I chose, and why — the trade-offs behind DocuMind.

## 1. Synthetic documents that ship their own geometry *and* answer
Real document datasets (FUNSD, CORD, SROIE) need downloads, licences, and OCR, and
their labels are noisy. I generate documents as tokens-with-boxes plus the exact
ground-truth record.
- *Why:* it makes every metric — field accuracy, table-cell F1, arithmetic
  validity — checkable in CI with no keys and no downloads, and it lets me author
  *layouts that isolate a specific failure mode* (values below labels, second
  columns, wrapped table cells) instead of hoping a corpus contains them.
- *Cost:* the tokens are clean (no OCR character noise beyond the deliberate total
  glitch). The same extractors run on a real PDF via the optional `[pdf]` backend,
  which is where messy real-world geometry would show up.

## 2. A reading-order extractor as the ablation, not a strawman
The `text` baseline respects line breaks and reads `label: value` on a line — a
faithful model of "throw the boxes away and feed the OCR text to a regex/LLM."
- *Why:* the comparison is only honest if the baseline is competent where it should
  be. On the single-column `receipt` it ties the layout extractor exactly; it only
  loses where 2-D structure is genuinely required. A deliberately broken baseline
  would inflate the layout extractor's win and prove nothing.

## 3. One pipeline, one independent variable
Both extractors share canonicalisation, label finding, and table-region detection;
only value association differs.
- *Why:* if each extractor had its own table parser or string cleaner, a difference
  in the results could be an implementation artefact. Sharing the spine means the
  only thing that varies is geometry vs. reading order.

## 4. Two effects, deliberately orthogonal
Layout drives **field association**; the verifier drives **arithmetic validity**.
The OCR glitch corrupts only the printed `total`, which *both* extractors read
identically.
- *Why:* it produces a clean 2×2 (extractor × verify) where each lever moves a
  different metric. That dissociation — geometry buys field accuracy, verification
  buys validity — is the whole thesis, and it would blur if, say, the verifier also
  fixed mis-associated fields.

## 5. The scrambled-geometry null test
Mirroring a good empirical paper, DocuMind ships a null: permute every token's box
and re-run the *same* layout extractor.
- *Why:* high accuracy could in principle come from text-order regularities rather
  than geometry. Destroying the geometry while keeping the text collapses the
  layout extractor from 100% to ~3%, proving the geometry was load-bearing.

## 6. Money arithmetic in integer cents
`add_money` sums in cents; the verifier tolerance is sub-cent.
- *Why:* two different binary-float representations of the same two-decimal value
  can round differently when added, which once produced a phantom one-cent
  disagreement between the generated total and the recomputed one. Cents make the
  reconciliation exact, so "validity" measures real OCR errors, not float noise.

## 7. Zero runtime dependencies for the offline core
The core is pure standard library; `pdfplumber`/`requests`/`openai` are extras.
- *Why:* fast, reproducible CI with nothing to download, and the extraction logic
  stays legible. Real backends are opt-in and lazily imported.

## 8. Small, fixed-template documents on purpose
Three doc types, a handful of fields each, a few line items.
- *Why:* the point is the *measurement* — isolating what geometry buys — which
  needs exact ground truth and a fast, fully-offline benchmark. Scaling to messy
  real layouts is the job of the optional PDF backend and a stronger extractor; it
  is orthogonal to the thesis.

## 9. CI gate enforces the *shape*, not just thresholds
The gate checks both effects, the single-column control where the extractors must
**agree**, and the null collapse — not just "accuracy ≥ X".
- *Why:* a plain floor can pass while the story silently breaks (e.g. the verifier
  regresses but field accuracy stays high, or the layout extractor quietly starts
  reading in text order). Gating the *relationships* catches regressions a single
  threshold misses.
