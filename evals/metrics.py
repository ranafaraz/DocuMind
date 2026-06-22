"""Reduce per-document :class:`ExtractionResult` objects to portfolio metrics.

* **field accuracy** -- micro fraction of scalar fields read correctly (the
  layout axis).
* **cell P/R/F1** -- micro precision/recall over line-item table cells (the
  table-structure axis).
* **doc exact** -- fraction of documents extracted perfectly (every field and
  every cell).
* **validity** -- fraction whose final record satisfies the schema arithmetic
  (the verifier axis).
"""

from __future__ import annotations

from collections.abc import Iterable

from documind.types import ExtractionResult


def _f1(precision: float, recall: float) -> float:
    return 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0


def aggregate(results: Iterable[ExtractionResult]) -> dict:
    results = list(results)
    n = len(results)
    if not n:
        return {"n": 0}

    ft = sum(r.field_total for r in results)
    fc = sum(r.field_correct for r in results)
    cc = sum(r.cell_correct for r in results)
    ct = sum(r.cell_total for r in results)
    cp = sum(r.cell_pred for r in results)

    precision = cc / cp if cp else 0.0
    recall = cc / ct if ct else 0.0
    return {
        "n": n,
        "field_accuracy": round(fc / ft, 3) if ft else 0.0,
        "cells": ct,
        "cell_precision": round(precision, 3),
        "cell_recall": round(recall, 3),
        "cell_f1": round(_f1(precision, recall), 3),
        "doc_exact": round(sum(1 for r in results if r.doc_exact) / n, 3),
        "validity": round(sum(1 for r in results if r.valid) / n, 3),
        "total_field_acc": round(
            sum(1 for r in results if _total_correct(r)) / n, 3
        ),
        "repairs": round(sum(r.repairs for r in results) / n, 2),
    }


def _total_correct(r: ExtractionResult) -> bool:
    """Was the (often OCR-corrupted) `total` field correct? Only meaningful for
    doc types with a totals block; True elsewhere so it never drags a pool down."""
    if "total" not in r.truth.fields:
        return True
    return r.predicted.fields.get("total", "") == r.truth.fields.get("total", "")
