"""CI quality gate: fail the build if the extraction story regresses.

Like the rest of the portfolio, the gate enforces the *shape* of the result, not
just that numbers are high. It checks the two dissociated effects (layout buys
field association; the verifier buys arithmetic validity), the single-column
control where the two extractors must *agree*, and the null test where scrambling
geometry must collapse the layout extractor. Floors sit well below the observed
offline numbers so ordinary variation never flakes CI, while a real regression --
a broken verifier, a layout extractor that secretly reads in text order -- trips
it. No API keys, no downloads.
"""

from __future__ import annotations

import sys

from evals.harness import run_eval


def _checks(r: dict) -> list[tuple[str, bool, str]]:
    field_gap = r["layout_field_acc"] - r["text_field_acc"]
    form_gap = r["form_layout_field_acc"] - r["form_text_field_acc"]
    control_gap = abs(r["receipt_layout_field_acc"] - r["receipt_text_field_acc"])
    cell_gap = r["layout_cell_f1"] - r["text_cell_f1"]
    null_drop = r["layout_field_acc"] - r["ablation_field_acc"]
    return [
        (
            "layout+verify extracts fields near-perfectly",
            r["layout_field_acc"] >= 0.95,
            f"field_acc={r['layout_field_acc']} >= 0.95",
        ),
        (
            "layout buys field association (beats text)",
            field_gap >= 0.25,
            f"field gap={field_gap:.3f} >= 0.25 "
            f"(layout {r['layout_field_acc']} vs text {r['text_field_acc']})",
        ),
        (
            "two-column form is where layout wins biggest",
            form_gap >= 0.60,
            f"form gap={form_gap:.3f} >= 0.60 "
            f"(layout {r['form_layout_field_acc']} vs text {r['form_text_field_acc']})",
        ),
        (
            "single-column control: extractors agree",
            control_gap <= 0.05,
            f"receipt |layout-text|={control_gap:.3f} <= 0.05",
        ),
        (
            "layout buys table-structure (cell F1)",
            cell_gap >= 0.02,
            f"cell F1 gap={cell_gap:.3f} >= 0.02 "
            f"(layout {r['layout_cell_f1']} vs text {r['text_cell_f1']})",
        ),
        (
            "verifier buys arithmetic validity",
            r["validity_verify"] >= 0.99 and r["validity_noverify"] <= 0.95,
            f"validity {r['validity_noverify']} -> {r['validity_verify']} (off<=0.95, on>=0.99)",
        ),
        (
            "verifier repairs the OCR-corrupted total",
            r["total_acc_verify"] >= 0.99 and r["total_acc_noverify"] <= 0.95,
            f"total acc {r['total_acc_noverify']} -> {r['total_acc_verify']} (off<=0.95, on>=0.99)",
        ),
        (
            "null test: scrambled geometry collapses layout",
            r["ablation_field_acc"] <= 0.30 and null_drop >= 0.50,
            f"scrambled field_acc={r['ablation_field_acc']} <= 0.30, drop={null_drop:.3f} >= 0.50",
        ),
    ]


def main() -> int:
    res = run_eval()
    checks = _checks(res)
    print("DocuMind eval gate")
    failures = []
    for desc, ok, detail in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {desc}: {detail}")
        if not ok:
            failures.append(desc)
    if failures:
        print("\nGATE FAILED:")
        for f in failures:
            print("  -", f)
        return 1
    print("\nGATE PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
