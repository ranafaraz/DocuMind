"""Geometry primitives: lines, reading order, and neighbour relations."""

from __future__ import annotations

from documind.geometry import (
    below_in_column,
    group_lines,
    nearest_column,
    reading_order,
    right_of,
)
from documind.types import BBox, Token


def _tok(text, x, y, w=None):
    w = w if w is not None else len(text) * 6.0
    return Token(text, BBox(x, y, x + w, y + 10))


def test_group_lines_clusters_by_row():
    toks = [_tok("a", 0, 0), _tok("b", 50, 2), _tok("c", 0, 40)]
    lines = group_lines(toks)
    assert [[t.text for t in ln] for ln in lines] == [["a", "b"], ["c"]]


def test_reading_order_is_top_to_bottom_left_to_right():
    # Two-column layout: reading order interleaves the columns by row.
    toks = [_tok("L1", 0, 0), _tok("R1", 300, 0), _tok("L2", 0, 40), _tok("R2", 300, 40)]
    assert [t.text for t in reading_order(toks)] == ["L1", "R1", "L2", "R2"]


def test_right_of_stops_at_column_gap():
    label = _tok("Total:", 400, 0)
    near = _tok("32.40", 490, 0)
    far = _tok("X", 50, 0)  # far left, not to the right
    assert [t.text for t in right_of(label, [label, near, far])] == ["32.40"]


def test_right_of_breaks_across_wide_gap():
    label = _tok("Name:", 50, 0)
    other_col = _tok("DOB:", 320, 0)
    assert right_of(label, [label, other_col]) == []


def test_below_in_column_reads_value_under_label():
    label = _tok("BillTo:", 50, 90)
    v1 = _tok("Acme", 50, 108)
    v2 = _tok("Corp", 80, 108)
    distractor = _tok("Date:", 400, 90)
    got = below_in_column(label, [label, v1, v2, distractor])
    assert [t.text for t in got] == ["Acme", "Corp"]


def test_nearest_column():
    anchors = [("description", 80.0), ("qty", 300.0), ("amount", 480.0)]
    assert nearest_column(305.0, anchors) == "qty"
    assert nearest_column(70.0, anchors) == "description"
