"""
Peças comuns da ponte entre a janela (JavaScript) e o motor (Python).

Regras da ponte:
  - toda função pública devolve um dicionário simples, nunca levanta exceção
    para o JavaScript (decorador `resposta_segura`);
  - nada de lógica de negócio aqui: validar a entrada, chamar o motor,
    devolver o resultado;
  - atributos e métodos que começam com "_" não são expostos à janela.
"""

from __future__ import annotations

import functools
import json
import os

from motor import documentos as md
from motor import reate
from motor.registro import filho

log = filho("ponte")

PASTA_APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Por enquanto o projeto mora SEMPRE nesta pasta, ao lado do aplicativo.
# Assim, ao compactar a pasta do SIAPP para outra pessoa, os dados vão junto e
# ficam no mesmo lugar em todos os computadores. Para liberar outras pastas no
# futuro, basta remover a checagem em API.escolher_pasta.
NOME_PASTA_PROJETO = "ambiente_teste"
PASTA_PROJETO = os.path.join(PASTA_APP, NOME_PASTA_PROJETO)
# Modelo de idioma do OCR: baixado uma vez e guardado junto do aplicativo.
PASTA_TESSDATA = os.path.join(PASTA_APP, "recursos", "tessdata")
PASTA_RECURSOS = os.path.join(PASTA_APP, "recursos")
# Dicionário de domínio que vem com o SIAPP (editável; ver motor/vocabulario.py).
CAMINHO_VOCAB_BASE = os.path.join(PASTA_RECURSOS, "vocabulario_base.json")


class ErroUsuario(ValueError):
    """Pedido inválido vindo da janela: a mensagem vai direto para a tela."""


def mesma_pasta(a: str, b: str) -> bool:
    """Compara caminhos ignorando maiúsculas/minúsculas e barras (Windows)."""
    def norm(p):
        return os.path.normcase(os.path.normpath(os.path.abspath(p)))
    return norm(a) == norm(b)


# Erros esperados: a mensagem já foi escrita para o usuário.
ERROS_ESPERADOS = (reate.ErroREATE, md.ErroDocumento, NotADirectoryError, ValueError)


def resposta_segura(func):
    """Toda chamada vinda da interface devolve {"ok": True, ...} ou
    {"ok": False, "erro": "..."} — nunca deixa uma exceção estourar no JS.
    Erros inesperados vão completos para o siapp.log."""
    @functools.wraps(func)
    def envelope(*args, **kwargs):
        try:
            return {"ok": True, **(func(*args, **kwargs) or {})}
        except ERROS_ESPERADOS as e:
            log.info("%s recusado: %s", func.__name__, e)
            return {"ok": False, "erro": str(e)}
        except Exception as e:  # erro inesperado: mensagem curta na tela, detalhe no log
            log.exception("erro inesperado em %s", func.__name__)
            return {"ok": False, "erro": f"Erro inesperado ({type(e).__name__}): {e}. "
                                         f"Detalhes em ambiente_teste\\siapp.log."}
    return envelope


class BaseAPI:
    """Estado compartilhado por todas as partes da ponte."""

    _janela = None
    _projeto = None

    def _js(self, funcao: str, dados) -> None:
        """Chama uma função global da janela. Se a janela já fechou, ignora:
        o trabalho em segundo plano nunca quebra por causa da interface."""
        try:
            self._janela.evaluate_js(f"{funcao}({json.dumps(dados)})")
        except Exception:
            pass

    def _status(self, texto: str):
        """Atualiza a barra de status da janela durante operações longas."""
        try:
            self._janela.evaluate_js(f"status({json.dumps(texto)}, 'trab')")
        except Exception:
            pass

    def _autor(self) -> str:
        """Nome de quem usa este computador (aba Comunidade), para a autoria
        de correções e fatos. Vazio se não preenchido."""
        if self._projeto is None:
            return ""
        return (self._projeto.config.get("autor") or {}).get("nome", "")

    def _exigir_projeto(self):
        if self._projeto is None:
            raise ErroUsuario("Escolha primeiro a pasta do projeto (aba Catálogo, passo 1).")
