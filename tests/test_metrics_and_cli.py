"""Metrics, the eval gate shape, normalisation, and the CLI."""

from __future__ import annotations

from documind.cli import main as cli_main
from documind.config import Settings
from documind.normalize import money_str, norm_money_field, parse_money
from documind.pipeline import run_document
from evals.gate import _checks
from evals.harness import run_eval
from evals.metrics import aggregate


def test_normalize_money():
    assert money_str(1234.5) == "1234.50"
    assert parse_money("$1,234.50") == 1234.50
    assert norm_money_field("  32.4 ") == "32.40"
    assert norm_money_field("n/a") is None


def test_aggregate_basic():
    cfg = Settings()
    results = [run_document("invoice", s, cfg, "layout", True) for s in range(5)]
    m = aggregate(results)
    assert m["n"] == 5
    assert 0.0 <= m["field_accuracy"] <= 1.0
    assert m["cell_f1"] == 1.0  # layout reads the table perfectly


def test_run_eval_shape_and_gate_passes():
    res = run_eval()
    checks = _checks(res)
    assert all(ok for _, ok, _ in checks), [d for d, ok, _ in checks if not ok]
    # The two effects are real and large.
    assert res["layout_field_acc"] - res["text_field_acc"] >= 0.25
    assert res["validity_verify"] - res["validity_noverify"] >= 0.05
    assert res["ablation_field_acc"] <= 0.30


def test_cli_compare_runs(capsys):
    rc = cli_main(["compare", "--doctype", "invoice", "--seed", "1"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "layout+verify" in out


def test_cli_render_scramble_runs(capsys):
    rc = cli_main(["render", "--doctype", "form", "--seed", "0", "--scramble"])
    assert rc == 0
    assert "scrambled" in capsys.readouterr().out


def test_cli_extract_runs(capsys):
    rc = cli_main(["extract", "--doctype", "receipt", "--seed", "2", "--backend", "layout"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "valid" in out
