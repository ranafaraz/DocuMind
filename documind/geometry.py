"""Geometry utilities: turn a bag of placed tokens back into lines, columns, and
neighbour relations.

This module is the whole reason a layout-aware extractor can beat a reading-order
one. ``reading_order`` is what a layout-*blind* extractor is stuck with -- it
flattens the page into one stream, which is exactly where two-column and
value-below-label layouts mislead it. The neighbour helpers (``right_of``,
``below_in_column``) are what the layout extractor uses instead.
"""

from __future__ import annotations

from documind.types import BBox, Token


def group_lines(tokens: list[Token]) -> list[list[Token]]:
    """Cluster tokens into text lines by vertical overlap; sort each line left
    to right and the lines top to bottom."""
    lines: list[list[Token]] = []
    for t in sorted(tokens, key=lambda tk: (tk.bbox.y0, tk.bbox.x0)):
        for line in lines:
            if line[0].bbox.same_row(t.bbox):
                line.append(t)
                break
        else:
            lines.append([t])
    for line in lines:
        line.sort(key=lambda tk: tk.bbox.x0)
    lines.sort(key=lambda ln: min(tk.bbox.y0 for tk in ln))
    return lines


def reading_order(tokens: list[Token]) -> list[Token]:
    """Flatten the page top-to-bottom, left-to-right -- the layout-blind view."""
    return [t for line in group_lines(tokens) for t in line]


def right_of(label: Token, tokens: list[Token], max_gap: float = 90.0) -> list[Token]:
    """Tokens on the same row as ``label`` and to its right, taken left to right
    while consecutive horizontal gaps stay under ``max_gap`` (so the run stops at
    a column break)."""
    same = [
        t for t in tokens
        if t is not label and t.bbox.same_row(label.bbox) and t.bbox.x0 >= label.bbox.x1 - 1.0
    ]
    same.sort(key=lambda t: t.bbox.x0)
    out: list[Token] = []
    prev_x1 = label.bbox.x1
    for t in same:
        if t.bbox.x0 - prev_x1 > max_gap:
            break
        out.append(t)
        prev_x1 = t.bbox.x1
    return out


def below_in_column(
    label: Token, tokens: list[Token], x_tol: float = 25.0, max_gap: float = 90.0
) -> list[Token]:
    """The value on the nearest line *below* ``label`` that left-aligns with it.

    Find the closest line below whose first token starts in the label's column
    (``|x0 - label.x0| <= x_tol``), then return that line's contiguous run of
    tokens (stopping at a gap wider than ``max_gap``, i.e. a neighbouring
    column). This is the geometric read of a value placed under its label.
    """
    below = [t for t in tokens if t is not label and t.bbox.y0 >= label.bbox.y1 - 1.0]
    starters = [t for t in below if abs(t.bbox.x0 - label.bbox.x0) <= x_tol]
    if not starters:
        return []
    top_y = min(t.bbox.y0 for t in starters)
    line = sorted(
        (t for t in below if abs(t.bbox.y0 - top_y) <= 6.0 and t.bbox.x0 >= label.bbox.x0 - x_tol),
        key=lambda t: t.bbox.x0,
    )
    out: list[Token] = []
    prev_x1 = line[0].bbox.x0
    for t in line:
        if out and t.bbox.x0 - prev_x1 > max_gap:
            break
        out.append(t)
        prev_x1 = t.bbox.x1
    return out


def nearest_column(cx: float, anchors: list[tuple[str, float]]) -> str:
    """Name of the column anchor closest in x to ``cx``."""
    return min(anchors, key=lambda a: abs(a[1] - cx))[0]


def join_text(tokens: list[Token]) -> str:
    return " ".join(t.text for t in tokens)


def bbox_of(tokens: list[Token]) -> BBox | None:
    if not tokens:
        return None
    return BBox(
        min(t.bbox.x0 for t in tokens),
        min(t.bbox.y0 for t in tokens),
        max(t.bbox.x1 for t in tokens),
        max(t.bbox.y1 for t in tokens),
    )
