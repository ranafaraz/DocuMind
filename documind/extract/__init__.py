"""Extractor backends and their factory.

``EXTRACTORS`` lists the two offline configurations the benchmark sweeps; the
optional ``ollama``/``openai`` backends are constructible but not part of CI.
"""

from __future__ import annotations

from documind.config import Settings
from documind.extract.base import Extractor
from documind.extract.layout import LayoutExtractor
from documind.extract.text import TextExtractor

# Offline extractors compared head-to-head in the eval.
EXTRACTORS: tuple[str, ...] = ("layout", "text")


def make_extractor(name: str, cfg: Settings | None = None) -> Extractor:
    cfg = cfg or Settings.from_env()
    if name == "layout":
        return LayoutExtractor()
    if name == "text":
        return TextExtractor()
    if name == "ollama":
        from documind.extract.ollama import OllamaExtractor

        return OllamaExtractor(cfg.ollama_model)
    if name == "openai":
        from documind.extract.openai_extractor import OpenAIExtractor

        return OpenAIExtractor(cfg.openai_model)
    raise ValueError(f"unknown extractor backend {name!r}")


__all__ = ["Extractor", "EXTRACTORS", "make_extractor", "LayoutExtractor", "TextExtractor"]
