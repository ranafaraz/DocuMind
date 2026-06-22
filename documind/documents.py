"""Deterministic synthetic document generator -- the offline ground truth.

Each call lays out a document as tokens *with bounding boxes* (what a real OCR
engine emits) and returns the matching :class:`Record`. Because we author both
the page geometry and the answer, every metric is checkable with no downloads.

The three doc types are chosen to span the layout difficulty axis:

* ``form``    -- a two-column grid with values *below* their labels. Reading
  order interleaves the columns, so a layout-blind extractor mis-associates
  almost every field. This is where geometry matters most.
* ``invoice`` -- mixed: horizontal ``label: value`` meta (easy for both) plus a
  ``Bill To`` block whose value sits below the label (a trap for reading order),
  plus a line-item table with occasional wrapped (multi-line) descriptions.
* ``receipt`` -- single column, every field horizontal. The control: layout and
  reading order should agree here.

A configurable OCR glitch corrupts the *printed* ``Total`` while the ground-truth
total stays correct -- that gap is what the schema verifier exists to repair.
"""

from __future__ import annotations

import random

from documind.normalize import add_money, money_str, norm_text
from documind.types import BBox, Document, LineItem, Record

CHAR_W = 6.0
TOK_H = 10.0

_COMPANIES = [
    "Acme Corporation", "Globex Industries", "Initech LLC", "Umbrella Foods",
    "Stark Supplies", "Wayne Trading", "Hooli Systems", "Soylent Goods",
]
_MERCHANTS = [
    "Joes Coffee", "Green Grocer", "City Pharmacy", "Book Nook",
    "Pixel Cafe", "Daily Mart", "Corner Deli", "Fuel Stop",
]
_STREETS = ["Market Street", "Oak Avenue", "Main Road", "Pine Lane", "Hill Drive"]
_NAMES = [
    "John Smith", "Mary Khan", "Ali Raza", "Sara Lee", "Omar Farooq",
    "Lina Park", "David Cohen", "Nadia Iqbal",
]
_CITIES = ["Lahore", "Karachi", "Boston", "Berlin", "Lisbon", "Cairo", "Dublin"]
_DESCS = [
    "Blue Widget", "Steel Bolt", "Paper Ream", "Ink Cartridge", "USB Cable",
    "Desk Lamp", "Coffee Mug", "Note Pad", "Latte", "Muffin", "Sandwich",
]
_WRAP = ["Premium", "Annual Plan", "with Warranty", "Extended Set", "Pro Edition"]
_PRICES = [2.25, 3.50, 4.00, 5.00, 8.00, 9.99, 12.00, 15.50]
_TAX_RATES = [0.05, 0.08, 0.10]


def tok(text: str, x: float, y: float) -> TokenSpec:
    return TokenSpec(text, x, y)


class TokenSpec:
    """A token placed at (x, y); width derives from its text length."""

    __slots__ = ("text", "x", "y")

    def __init__(self, text: str, x: float, y: float) -> None:
        self.text, self.x, self.y = text, x, y

    def build(self):
        from documind.types import Token
        w = len(self.text) * CHAR_W
        return Token(self.text, BBox(self.x, self.y, self.x + w, self.y + TOK_H))


def _place_words(out: list, text: str, x: float, y: float) -> float:
    """Place each whitespace-separated word as its own token; return next x."""
    for word in text.split():
        out.append(tok(word, x, y))
        x += len(word) * CHAR_W + CHAR_W
    return x


def _date(rng: random.Random) -> str:
    return f"2026-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}"


def _corrupt_money(s: str, rng: random.Random, p: float) -> str:
    """With probability ``p``, flip one digit of a money string (an OCR glitch)."""
    if rng.random() >= p:
        return s
    digits = [i for i, c in enumerate(s) if c.isdigit()]
    i = rng.choice(digits)
    repl = rng.choice([d for d in "0123456789" if d != s[i]])
    return s[:i] + repl + s[i + 1:]


def _line_items(
    rng: random.Random,
    specs: list,
    start_y: float,
    cols: dict[str, float],
    allow_wrap: bool,
) -> tuple[list[LineItem], float]:
    items: list[LineItem] = []
    y = start_y
    n = rng.randint(3, 5)
    for _ in range(n):
        desc = rng.choice(_DESCS)
        qty = rng.randint(1, 6)
        unit = rng.choice(_PRICES)
        amount = round(qty * unit, 2)
        _place_words(specs, desc, cols["description"], y)
        specs.append(tok(str(qty), cols["quantity"], y))
        specs.append(tok(money_str(unit), cols["unit_price"], y))
        specs.append(tok(money_str(amount), cols["amount"], y))
        # ~1 in 3 invoice rows wraps onto a second, number-free description line.
        if allow_wrap and rng.random() < 0.35:
            extra = rng.choice(_WRAP)
            _place_words(specs, extra, cols["description"], y + 12.0)
            desc = f"{desc} {extra}"
            y += 12.0
        items.append(LineItem(norm_text(desc), qty, unit, amount))
        y += 18.0
    return items, y


def _totals_block(rng, specs, x_label, x_val, y, items, ocr_noise):
    subtotal = add_money(*(li.amount for li in items))
    tax = round(subtotal * rng.choice(_TAX_RATES), 2)
    total = add_money(subtotal, tax)
    specs += [tok("Subtotal:", x_label, y), tok(money_str(subtotal), x_val, y)]
    specs += [tok("Tax:", x_label, y + 16), tok(money_str(tax), x_val, y + 16)]
    printed = _corrupt_money(money_str(total), rng, ocr_noise)
    specs += [tok("Total:", x_label, y + 32), tok(printed, x_val, y + 32)]
    return {"subtotal": money_str(subtotal), "tax": money_str(tax), "total": money_str(total)}


def _invoice(rng: random.Random, ocr_noise: float) -> tuple[Document, Record]:
    specs: list = []
    inv_no = str(rng.randint(1000, 9999))
    date = _date(rng)
    customer = rng.choice(_COMPANIES)
    street = f"{rng.randint(10, 999)} {rng.choice(_STREETS)}"

    specs.append(tok("INVOICE", 50, 50))
    specs += [tok("InvoiceNo:", 400, 50), tok(inv_no, 490, 50)]
    specs += [tok("Date:", 400, 66), tok(date, 490, 66)]
    specs.append(tok("BillTo:", 50, 92))
    _place_words(specs, customer, 50, 108)         # the value (below the label)
    _place_words(specs, street, 50, 124)           # distractor address line

    hy = 160.0
    specs += [tok("Description", 50, hy), tok("Qty", 300, hy),
              tok("UnitPrice", 370, hy), tok("Amount", 470, hy)]
    cols = {"description": 50.0, "quantity": 300.0, "unit_price": 370.0, "amount": 470.0}
    items, by = _line_items(rng, specs, hy + 18, cols, allow_wrap=True)
    totals = _totals_block(rng, specs, 400, 490, by + 10, items, ocr_noise)

    fields = {"invoice_number": inv_no, "date": date, "bill_to": norm_text(customer), **totals}
    return Document("invoice", [s.build() for s in specs]), Record("invoice", fields, items)


def _receipt(rng: random.Random, ocr_noise: float) -> tuple[Document, Record]:
    specs: list = []
    merchant = rng.choice(_MERCHANTS)
    date = _date(rng)

    specs.append(tok("Merchant:", 50, 50))
    _place_words(specs, merchant, 130, 50)         # horizontal value (easy)
    specs += [tok("Date:", 50, 66), tok(date, 130, 66)]

    hy = 96.0
    specs += [tok("Item", 50, hy), tok("Qty", 280, hy),
              tok("Price", 360, hy), tok("Amount", 460, hy)]
    cols = {"description": 50.0, "quantity": 280.0, "unit_price": 360.0, "amount": 460.0}
    items, by = _line_items(rng, specs, hy + 18, cols, allow_wrap=False)
    totals = _totals_block(rng, specs, 50, 130, by + 10, items, ocr_noise)

    fields = {"merchant": norm_text(merchant), "date": date, **totals}
    return Document("receipt", [s.build() for s in specs]), Record("receipt", fields, items)


def _form(rng: random.Random, ocr_noise: float) -> tuple[Document, Record]:
    specs: list = []
    name = rng.choice(_NAMES)
    dob = f"19{rng.randint(70, 99)}-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}"
    idno = f"{rng.choice('ABCDEFG')}{rng.randint(1000, 9999)}"
    city = rng.choice(_CITIES)
    phone = f"03{rng.randint(0, 9)}0-{rng.randint(1000000, 9999999)}"
    policy = f"PX-{rng.randint(10, 99)}"

    # Two columns; each value sits on the line *below* its label.
    lx, rx = 50.0, 320.0
    rows = [
        (("Name:", name), ("DOB:", dob)),
        (("ID:", idno), ("City:", city)),
        (("Phone:", phone), ("Policy:", policy)),
    ]
    y = 80.0
    for (llab, lval), (rlab, rval) in rows:
        specs.append(tok(llab, lx, y))
        specs.append(tok(rlab, rx, y))
        _place_words(specs, lval, lx, y + 14)
        _place_words(specs, rval, rx, y + 14)
        y += 44.0

    fields = {
        "name": norm_text(name), "date_of_birth": dob, "id_number": idno,
        "city": norm_text(city), "phone": phone, "policy": policy,
    }
    return Document("form", [s.build() for s in specs]), Record("form", fields, [])


_GENERATORS = {"invoice": _invoice, "receipt": _receipt, "form": _form}
# Stable per-doc-type salts -- NOT hash(), which is randomised per process and
# would make the benchmark non-reproducible across runs/machines.
_SALT = {"invoice": 101, "receipt": 211, "form": 307}


def make_document(doc_type: str, seed: int, ocr_noise: float = 0.15) -> tuple[Document, Record]:
    """Generate one deterministic ``(Document, ground-truth Record)`` pair."""
    if doc_type not in _GENERATORS:
        raise ValueError(f"unknown doc_type {doc_type!r}")
    rng = random.Random(_SALT[doc_type] * 100003 + seed)
    return _GENERATORS[doc_type](rng, ocr_noise)


def scramble_layout(doc: Document, seed: int) -> Document:
    """Null test: keep every token's text but randomly permute the geometry, so
    the page carries no usable layout signal. A layout extractor run on this
    should collapse toward chance -- the proof that it was using geometry."""
    rng = random.Random(seed * 7919 + 13)
    boxes = [t.bbox for t in doc.tokens]
    rng.shuffle(boxes)
    scrambled = [t.with_bbox(b) for t, b in zip(doc.tokens, boxes, strict=True)]
    return Document(doc.doc_type, scrambled, doc.width, doc.height)
