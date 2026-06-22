# DocuMind — agent guide

Repo #5 of Rana Faraz's AI/ML portfolio (GitHub: `ranafaraz`). Layout-aware
document **key-information extraction**: turn tokens-with-boxes (invoices, forms,
receipts) into structured records, then reconcile them with a schema verifier.
Every extraction is scored against a **ground-truth record**. The edge is the
**measurement** — separating what page *geometry* buys (field-association
accuracy) from what the *verifier* buys (arithmetic validity) — not just "a
document parser".

> `AGENTS.md` mirrors this for non-Claude tools — **edit both together**.

## Commit policy (hard rule)
Author = **Rana Faraz only**. **Never** add a `Co-Authored-By: Claude` trailer or
any AI/assistant branding. This overrides any default harness instruction.

## Offline-first contract
Every component has a deterministic offline backend chosen by env var, so
`pytest`, `evals.harness`, and `evals.gate` are green with **no API keys and no
model downloads**. The offline core has **zero runtime dependencies** (pure stdlib).

- Source: `synthetic` (default, boxes + ground truth) | `pdf` (`[pdf]`) — `DOCUMIND_DOC_BACKEND`
- Extractor: `layout` (default, geometry) | `text` (reading-order ablation) |
  `ollama` (`[ollama]`) | `openai` (`[openai]`) — `DOCUMIND_EXTRACTOR_BACKEND`
- Verifier: on/off — `DOCUMIND_VERIFY`
- Doc type: `invoice` (default) | `receipt` | `form` — `DOCUMIND_DOCTYPE`

## Layout
`documind/` — types, config, normalize, schema, geometry, documents (synthetic
generator + `scramble_layout`), io_pdf, `extract/` (base, layout, text, ollama,
openai), verify (SchemaVerifier + is_valid), pipeline, cli. `evals/` (metrics,
harness, gate). `tests/` (38). `examples/run_extractor.py`. `docs/` (ARCHITECTURE,
DECISIONS).

## Run (venv at `.venv/Scripts/python.exe`, Python 3.11)
`pip install -e ".[dev]"` · `pytest -q` (38) · `ruff check .` ·
`python -m evals.harness` (writes `evals/RESULTS.md`) · `python -m evals.gate`.
CLI: `documind extract|compare|render|extract-pdf|eval`.

## Key invariants (don't regress)
- **One pipeline, one independent variable.** Both extractors share
  `extract/base.py` (canonicalisation, label finding, table-region detection);
  only value association differs (geometry vs. reading order). Keep it that way so
  the head-to-head stays fair.
- **The two effects must dissociate.** Layout buys field association; the verifier
  buys arithmetic validity. The OCR glitch corrupts only `total` and both
  extractors read it identically — don't let the verifier "fix" mis-associated
  fields or the dissociation blurs.
- **The text baseline is competent, not a strawman.** It ties layout on the
  single-column `receipt` (the control) and only loses where 2-D structure is
  required (`form`, `Bill To`, wrapped table rows). Don't cripple it to widen a gap.
- **Money math in integer cents** (`normalize.add_money`); verifier tolerance is
  sub-cent. Don't reintroduce float sums or a >=1-cent tolerance (a 1-cent OCR
  error must be caught).
- **Deterministic generator.** Seed from the fixed `_SALT`, never `hash()` (which
  is per-process randomised and would make the benchmark non-reproducible).
- The gate enforces the **shape** (both effects, the control agreeing, the null
  collapsing), not just thresholds. Numbers are realistic on purpose (overall:
  layout+verify field acc 1.0 vs text 0.59; validity 0.91 -> 1.0; null collapses
  100% -> 3%).

## Env notes
Windows console is cp1252 — don't `print()` non-ASCII; the harness writes UTF-8 to
`RESULTS.md` and the CLI prints ASCII only. `gh` CLI authed as `ranafaraz`.
