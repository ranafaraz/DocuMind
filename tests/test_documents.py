"""The synthetic generator must produce internally consistent ground truth."""

from __future__ import annotations

import pytest

from documind.documents import make_document, scramble_layout
from documind.normalize import parse_money
from documind.schema import DOCTYPES, get_schema
from documind.verify import is_valid


@pytest.mark.parametrize("doc_type", DOCTYPES)
def test_generator_is_deterministic(doc_type):
    d1, r1 = make_document(doc_type, 5, 0.15)
    d2, r2 = make_document(doc_type, 5, 0.15)
    assert [t.text for t in d1.tokens] == [t.text for t in d2.tokens]
    assert r1.as_dict() == r2.as_dict()


@pytest.mark.parametrize("doc_type", DOCTYPES)
def test_ground_truth_is_arithmetically_valid(doc_type):
    # The *truth* record must always satisfy its own schema constraints, even
    # when the printed page total is OCR-corrupted.
    schema = get_schema(doc_type)
    for seed in range(20):
        _, truth = make_document(doc_type, seed, 0.5)
        assert is_valid(truth, schema)


def test_invoice_totals_reconcile():
    _, truth = make_document("invoice", 1, 0.0)
    sub = parse_money(truth.fields["subtotal"])
    tax = parse_money(truth.fields["tax"])
    tot = parse_money(truth.fields["total"])
    assert abs((sub + tax) - tot) < 0.011
    assert abs(sum(li.amount for li in truth.line_items) - sub) < 0.011


def test_ocr_noise_can_corrupt_printed_total():
    # With high noise some printed totals differ from the (correct) truth total.
    from documind.documents import make_document as mk
    from documind.geometry import group_lines

    corrupted = 0
    for seed in range(40):
        doc, truth = mk("invoice", seed, 0.9)
        printed = None
        for line in group_lines(doc.tokens):
            texts = [t.text for t in line]
            if any(t.startswith("Total") for t in texts):
                printed = texts[-1]
        if printed is not None and printed != truth.fields["total"]:
            corrupted += 1
    assert corrupted > 0


def test_scramble_preserves_tokens_changes_geometry():
    doc, _ = make_document("form", 2, 0.15)
    scr = scramble_layout(doc, 2)
    assert sorted(t.text for t in doc.tokens) == sorted(t.text for t in scr.tokens)
    assert [t.bbox for t in doc.tokens] != [t.bbox for t in scr.tokens]
