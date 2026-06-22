"""``documind`` command-line interface.

Console output is ASCII-only on purpose (the Windows console is cp1252). The eval
harness writes its richer, Unicode-friendly tables to a file instead.
"""

from __future__ import annotations

import argparse
import json
import sys

from documind.config import Settings
from documind.documents import make_document, scramble_layout
from documind.extract import EXTRACTORS, make_extractor
from documind.geometry import group_lines
from documind.pipeline import run_document
from documind.schema import DOCTYPES, get_schema
from documind.verify import SchemaVerifier, is_valid


def _cfg(args: argparse.Namespace) -> Settings:
    cfg = Settings.from_env()
    if getattr(args, "doctype", None):
        cfg.doctype = args.doctype
    if getattr(args, "seed", None) is not None:
        cfg.seed = args.seed
    if getattr(args, "backend", None):
        cfg.extractor_backend = args.backend
    return cfg


def _print_record(rec) -> None:
    for name, value in rec.fields.items():
        print(f"    {name:<16}: {value}")
    if rec.line_items:
        print("    line_items:")
        for li in rec.line_items:
            d, q, u, a = li.as_tuple()
            print(f"      - {d:<24} qty={q} unit={u:.2f} amount={a:.2f}")


def _cmd_extract(args: argparse.Namespace) -> int:
    cfg = _cfg(args)
    verify = not args.no_verify
    res = run_document(cfg.doctype, cfg.seed, cfg, cfg.extractor_backend, verify)
    print(f"DocuMind :: {cfg.doctype} (seed {cfg.seed}) :: "
          f"extractor={cfg.extractor_backend} verify={verify}")
    print("-" * 60)
    print("  predicted:")
    _print_record(res.predicted)
    print("-" * 60)
    print(f"  field accuracy : {res.field_correct}/{res.field_total}")
    print(f"  doc exact      : {'yes' if res.doc_exact else 'no'}")
    print(f"  valid          : {'yes' if res.valid else 'no'}")
    print(f"  repairs        : {res.repairs}")
    return 0


def _cmd_compare(args: argparse.Namespace) -> int:
    cfg = _cfg(args)
    print(f"DocuMind :: {cfg.doctype} (seed {cfg.seed}) :: ocr_noise={cfg.ocr_noise}")
    print(f"{'config':<18} {'field':>7} {'cellF1':>7} {'exact':>6} {'valid':>6}")
    for backend in EXTRACTORS:
        for verify in (False, True):
            res = run_document(cfg.doctype, cfg.seed, cfg, backend, verify)
            from evals.metrics import aggregate

            m = aggregate([res])
            label = f"{backend}{'+verify' if verify else ''}"
            cell = f"{m['cell_f1']:.2f}" if m.get("cells") else "n/a"
            print(f"{label:<18} {res.field_correct}/{res.field_total:<5} {cell:>7} "
                  f"{'yes' if res.doc_exact else 'no':>6} {'yes' if res.valid else 'no':>6}")
    return 0


def _cmd_render(args: argparse.Namespace) -> int:
    cfg = _cfg(args)
    doc, truth = make_document(cfg.doctype, cfg.seed, cfg.ocr_noise)
    if args.scramble:
        doc = scramble_layout(doc, cfg.seed)
    print(f"DocuMind :: {cfg.doctype} (seed {cfg.seed})"
          f"{' [scrambled]' if args.scramble else ''}")
    print("-" * 60)
    for line in group_lines(doc.tokens):
        y = int(min(t.bbox.y0 for t in line))
        print(f"  y={y:>3}: " + "  ".join(t.text for t in line))
    print("-" * 60)
    print("  ground truth:")
    _print_record(truth)
    return 0


def _cmd_extract_pdf(args: argparse.Namespace) -> int:
    cfg = _cfg(args)
    try:
        from documind.io_pdf import load_pdf
    except Exception as exc:  # pragma: no cover - optional dependency path
        print(f"PDF backend unavailable: {exc}")
        return 2
    doc = load_pdf(args.path, cfg.doctype)
    schema = get_schema(cfg.doctype)
    rec = make_extractor(cfg.extractor_backend, cfg).extract(doc, schema)
    if not args.no_verify:
        rec, _ = SchemaVerifier().verify(rec, schema)
    print(json.dumps({"valid": is_valid(rec, schema), **rec.as_dict()}, indent=2))
    return 0


def _cmd_eval(args: argparse.Namespace) -> int:
    from evals.harness import main as eval_main

    return eval_main()


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="documind",
        description="Layout-aware document key-information extraction vs. ground truth.",
    )
    sub = p.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--doctype", choices=DOCTYPES, help="document type")
    common.add_argument("--seed", type=int, help="instance seed")
    common.add_argument("--backend", choices=["layout", "text", "ollama", "openai"],
                        help="extractor backend")
    common.add_argument("--no-verify", action="store_true", help="skip the schema verifier")

    e = sub.add_parser("extract", parents=[common], help="extract one synthetic document")
    e.set_defaults(func=_cmd_extract)

    c = sub.add_parser("compare", parents=[common], help="all configs head-to-head")
    c.set_defaults(func=_cmd_compare)

    r = sub.add_parser("render", parents=[common], help="print a document's tokens + ground truth")
    r.add_argument("--scramble", action="store_true", help="scramble geometry (the null test)")
    r.set_defaults(func=_cmd_render)

    pf = sub.add_parser("extract-pdf", parents=[common], help="extract a real PDF ([pdf] extra)")
    pf.add_argument("path", help="path to a PDF file")
    pf.set_defaults(func=_cmd_extract_pdf)

    ev = sub.add_parser("eval", help="run the full offline eval harness")
    ev.set_defaults(func=_cmd_eval)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
