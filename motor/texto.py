"""Funções de texto usadas em vários leitores (0.60): um lugar só, para que o casamento de nomes seja igual em todos."""

from __future__ import annotations

import unicodedata


def sem_acento(texto) -> str:
    """O texto sem acentos nem cedilha (decomposição NFD sem as marcas). None vira ""."""
    return "".join(c for c in unicodedata.normalize("NFD", str(texto or "")) if unicodedata.category(c) != "Mn")
