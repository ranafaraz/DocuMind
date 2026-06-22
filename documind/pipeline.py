"""End-to-end extraction: document -> extractor -> (optional) verifier -> score.

One function, :func:`run_document`, ties the pieces together and scores the
result against ground truth so every caller (CLI, examples, harness) measures the
same way.
"""

from __future__ import annotations

from collections import Counter

from documind.config import Settings
from documind.documents import make_document, scramble_layout
from documind.extract import make_extractor
from documind.schema import get_schema
from documind.types import ExtractionResult, LineItem, Record
from documind.verify import SchemaVerifier, is_valid

_VERIFIER = SchemaVerifier()


def _cells(items: list[LineItem]) -> Counter:
    bag: Counter = Counter()
    for li in items:
        d, q, u, a = li.as_tuple()
        bag.update([f"d={d}", f"q={q}", f"u={u}", f"a={a}"])
    return bag


def score(predicted: Record, truth: Record, schema, extractor: str, verified: bool,
          repairs: int) -> ExtractionResult:
    field_total = len(schema.field_names)
    field_correct = sum(
        1 for n in schema.field_names if predicted.fields.get(n, "") == truth.fields.get(n, "")
    )
    truth_cells, pred_cells = _cells(truth.line_items), _cells(predicted.line_items)
    cell_correct = sum((truth_cells & pred_cells).values())
    fields_exact = field_correct == field_total
    items_exact = [li.as_tuple() for li in predicted.line_items] == [
        li.as_tuple() for li in truth.line_items
    ]
    return ExtractionResult(
        doc_type=truth.doc_type,
        extractor=extractor,
        verified=verified,
        predicted=predicted,
        truth=truth,
        field_total=field_total,
        field_correct=field_correct,
        cell_total=sum(truth_cells.values()),
        cell_correct=cell_correct,
        cell_pred=sum(pred_cells.values()),
        doc_exact=fields_exact and items_exact,
        valid=is_valid(predicted, schema),
        repairs=repairs,
    )


def run_document(
    doc_type: str,
    seed: int,
    cfg: Settings,
    extractor_name: str | None = None,
    verify: bool | None = None,
) -> ExtractionResult:
    schema = get_schema(doc_type)
    document, truth = make_document(doc_type, seed, cfg.ocr_noise)
    if cfg.ablate_layout:
        document = scramble_layout(document, seed)

    extractor_name = extractor_name or cfg.extractor_backend
    verify = cfg.verify if verify is None else verify

    predicted = make_extractor(extractor_name, cfg).extract(document, schema)
    repairs = 0
    if verify:
        predicted, repairs = _VERIFIER.verify(predicted, schema)
    return score(predicted, truth, schema, extractor_name, verify, repairs)
