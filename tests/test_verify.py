"""The verifier repairs arithmetic without touching layout-driven fields."""

from __future__ import annotations

from documind.documents import make_document
from documind.extract import make_extractor
from documind.normalize import money_str, parse_money
from documind.schema import get_schema
from documind.types import LineItem, Record
from documind.verify import SchemaVerifier, is_valid


def test_repairs_corrupted_total():
    schema = get_schema("invoice")
    rec = Record(
        "invoice",
        {"invoice_number": "1", "date": "2026-01-01", "bill_to": "Acme",
         "subtotal": "30.00", "tax": "2.40", "total": "99.99"},  # wrong total
        [LineItem("Widget", 3, 10.00, 30.00)],
    )
    assert not is_valid(rec, schema)
    fixed, repairs = SchemaVerifier().verify(rec, schema)
    assert repairs >= 1
    assert fixed.fields["total"] == "32.40"
    assert is_valid(fixed, schema)


def test_recomputes_missing_subtotal():
    schema = get_schema("receipt")
    rec = Record(
        "receipt",
        {"merchant": "Joe", "date": "2026-01-01", "subtotal": "", "tax": "1.00", "total": ""},
        [LineItem("Latte", 2, 3.50, 7.00), LineItem("Muffin", 1, 2.00, 2.00)],
    )
    fixed, _ = SchemaVerifier().verify(rec, schema)
    assert fixed.fields["subtotal"] == money_str(9.00)
    assert fixed.fields["total"] == money_str(10.00)
    assert is_valid(fixed, schema)


def test_no_constraints_for_form_is_a_noop():
    schema = get_schema("form")
    rec = Record("form", {"name": "X", "date_of_birth": "1990-01-01", "id_number": "A1",
                          "city": "Y", "phone": "1", "policy": "P"}, [])
    fixed, repairs = SchemaVerifier().verify(rec, schema)
    assert repairs == 0
    assert fixed.fields == rec.fields
    assert is_valid(rec, schema)


def test_verify_fixes_total_on_real_extraction():
    # End to end: where OCR corrupts the printed total, the verifier restores it.
    schema = get_schema("invoice")
    fixed_any = False
    for seed in range(30):
        doc, truth = make_document("invoice", seed, 0.9)  # high corruption
        raw = make_extractor("layout").extract(doc, schema)
        if raw.fields["total"] != truth.fields["total"]:
            fixed, _ = SchemaVerifier().verify(raw, schema)
            assert fixed.fields["total"] == truth.fields["total"]
            assert parse_money(fixed.fields["total"]) is not None
            fixed_any = True
    assert fixed_any
