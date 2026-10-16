"""
Registro de erros e eventos do SIAPP (siapp.log).

O arquivo fica na pasta de projeto, ao lado de siapp.json. Quando algo dá
errado num computador que não é o do desenvolvedor, este arquivo é o que o
usuário envia: ele traz a mensagem completa do erro (o "traceback"), que a
barra de status da janela resume em uma linha.

Rotação: no máximo 3 arquivos de 1 MB (siapp.log, siapp.log.1, siapp.log.2).
"""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler

NOME = "siapp"
ARQUIVO = "siapp.log"
_FORMATO = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"

log = logging.getLogger(NOME)


def configurar(pasta: str | None = None, nivel: int = logging.INFO) -> str | None:
    """Liga o registro em <pasta>/siapp.log (e no terminal). Pode ser chamada de
    novo ao trocar de pasta: o arquivo anterior é fechado. Devolve o caminho."""
    log.setLevel(nivel)
    for h in list(log.handlers):
        log.removeHandler(h)
        h.close()
    terminal = logging.StreamHandler()
    terminal.setFormatter(logging.Formatter(_FORMATO))
    terminal.setLevel(logging.WARNING)
    log.addHandler(terminal)
    if not pasta:
        return None
    os.makedirs(pasta, exist_ok=True)
    caminho = os.path.join(pasta, ARQUIVO)
    arq = RotatingFileHandler(caminho, maxBytes=1_000_000, backupCount=2, encoding="utf-8")
    arq.setFormatter(logging.Formatter(_FORMATO))
    log.addHandler(arq)
    log.propagate = False
    return caminho


def filho(nome: str) -> logging.Logger:
    """Logger de um módulo: siapp.reate, siapp.perfis…"""
    return log.getChild(nome)
