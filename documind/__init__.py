"""DocuMind: offline-first layout-aware document key-information extraction."""

from __future__ import annotations

from documind.config import Settings
from documind.documents import make_document, scramble_layout
from documind.extract import make_extractor
from documind.pipeline import run_document, score
from documind.schema import DOCTYPES, get_schema
from documind.types import BBox, Document, ExtractionResult, LineItem, Record, Token
from documind.verify import SchemaVerifier, is_valid

__version__ = "0.1.0"

__all__ = [
    "Settings",
    "make_document",
    "scramble_layout",
    "make_extractor",
    "run_document",
    "score",
    "get_schema",
    "DOCTYPES",
    "BBox",
    "Token",
    "Document",
    "LineItem",
    "Record",
    "ExtractionResult",
    "SchemaVerifier",
    "is_valid",
]
