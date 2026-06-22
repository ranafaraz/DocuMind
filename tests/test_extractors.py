"""The two effects, at the unit level: layout reads what text cannot."""

from __future__ import annotations

import pytest

from documind.documents import make_document, scramble_layout
from documind.extract import EXTRACTORS, make_extractor
from documind.schema import DOCTYPES, get_schema


def _fields_correct(pred, truth, schema):
    return sum(
        1 for n in schema.field_names if pred.fields.get(n, "") == truth.fields.get(n, "")
    )


@pytest.mark.parametrize("backend", EXTRACTORS)
@pytest.mark.parametrize("doc_type", DOCTYPES)
def test_extractor_returns_all_fields(backend, doc_type):
    schema = get_schema(doc_type)
    doc, _ = make_document(doc_type, 0, 0.0)
    rec = make_extractor(backend).extract(doc, schema)
    assert set(rec.fields) == set(schema.field_names)


@pytest.mark.parametrize("doc_type", DOCTYPES)
def test_layout_extracts_every_field(doc_type):
    schema = get_schema(doc_type)
    for seed in range(15):
        doc, truth = make_document(doc_type, seed, 0.0)  # no OCR noise
        rec = make_extractor("layout").extract(doc, schema)
        assert _fields_correct(rec, truth, schema) == len(schema.field_names)


def test_text_collapses_on_two_column_form():
    # Values sit *below* labels in a two-column grid -> reading order gets ~nothing.
    schema = get_schema("form")
    doc, truth = make_document("form", 0, 0.0)
    text = make_extractor("text").extract(doc, schema)
    layout = make_extractor("layout").extract(doc, schema)
    assert _fields_correct(text, truth, schema) == 0
    assert _fields_correct(layout, truth, schema) == len(schema.field_names)


def test_text_matches_layout_on_single_column_receipt():
    # The control: a single-column horizontal layout -- both extractors agree.
    schema = get_schema("receipt")
    for seed in range(10):
        doc, truth = make_document("receipt", seed, 0.0)
        text = make_extractor("text").extract(doc, schema)
        layout = make_extractor("layout").extract(doc, schema)
        assert _fields_correct(text, truth, schema) == _fields_correct(layout, truth, schema)


def test_layout_recovers_wrapped_table_cells():
    # Layout merges number-free continuation lines; text drops them.
    schema = get_schema("invoice")
    # seed chosen so at least one row wraps; verified by description containing a space-joined tail
    found_wrap = False
    for seed in range(30):
        doc, truth = make_document("invoice", seed, 0.0)
        if any(len(li.description.split()) >= 3 for li in truth.line_items):
            layout = make_extractor("layout").extract(doc, schema)
            assert [li.as_tuple() for li in layout.line_items] == [
                li.as_tuple() for li in truth.line_items
            ]
            found_wrap = True
            break
    assert found_wrap


def test_layout_collapses_on_scrambled_geometry():
    schema = get_schema("form")
    doc, truth = make_document("form", 1, 0.0)
    scrambled = scramble_layout(doc, 1)
    rec = make_extractor("layout").extract(scrambled, schema)
    assert _fields_correct(rec, truth, schema) <= 1
