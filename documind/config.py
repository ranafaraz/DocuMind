"""Environment-driven configuration.

Every component has a deterministic *offline* default so tests and CI run green
with no API keys and no model downloads. The extractor defaults to ``layout``
(geometry-aware); the ``text`` backend is the layout-blind ablation. Real
backends (Ollama, OpenAI, a PDF reader) are opt-in via env vars and pip extras
and degrade gracefully back to the offline path if unavailable.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


def _get(name: str, default: str) -> str:
    val = os.environ.get(name)
    return default if val is None or val == "" else val


def _get_int(name: str, default: int) -> int:
    try:
        return int(os.environ[name])
    except (KeyError, ValueError):
        return default


def _get_float(name: str, default: float) -> float:
    try:
        return float(os.environ[name])
    except (KeyError, ValueError):
        return default


def _get_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class Settings:
    """Resolved runtime settings.

    Backends
    --------
    extractor_backend : ``layout`` (offline default, geometry-aware) |
        ``text`` (layout-blind ablation) | ``ollama`` (``[ollama]``) |
        ``openai`` (``[openai]``)
    """

    extractor_backend: str = "layout"
    doc_backend: str = "synthetic"
    doctype: str = "invoice"
    verify: bool = True
    seed: int = 7

    # Synthetic-document realism knobs (deterministic per seed).
    ocr_noise: float = 0.15      # P(a digit of the printed total is corrupted)
    ablate_layout: bool = False  # scramble geometry -> the null test

    # Optional real-LLM backend knobs.
    ollama_model: str = "llama3.1:8b"
    openai_model: str = "gpt-4o-mini"

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            extractor_backend=_get("DOCUMIND_EXTRACTOR_BACKEND", cls.extractor_backend),
            doc_backend=_get("DOCUMIND_DOC_BACKEND", cls.doc_backend),
            doctype=_get("DOCUMIND_DOCTYPE", cls.doctype),
            verify=_get_bool("DOCUMIND_VERIFY", cls.verify),
            seed=_get_int("DOCUMIND_SEED", cls.seed),
            ocr_noise=_get_float("DOCUMIND_OCR_NOISE", cls.ocr_noise),
            ablate_layout=_get_bool("DOCUMIND_ABLATE_LAYOUT", cls.ablate_layout),
            ollama_model=_get("DOCUMIND_OLLAMA_MODEL", cls.ollama_model),
            openai_model=_get("DOCUMIND_OPENAI_MODEL", cls.openai_model),
        )
