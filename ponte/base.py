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

import collections
import functools
import json
import os
import time
from datetime import datetime

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


# Últimas chamadas da janela (nome, duração, resultado), para a tela de Diagnóstico.
CHAMADAS: collections.deque = collections.deque(maxlen=300)


def _anotar(nome: str, inicio: float, ok: bool, erro: str = ""):
    CHAMADAS.append({"quando": datetime.now().isoformat(timespec="seconds"), "funcao": nome,
                     "ms": round((time.perf_counter() - inicio) * 1000), "ok": ok, "erro": erro[:300]})


def resposta_segura(func):
    """Toda chamada vinda da interface devolve {"ok": True, ...} ou
    {"ok": False, "erro": "..."} — nunca deixa uma exceção estourar no JS.
    Erros inesperados vão completos para o siapp.log."""
    @functools.wraps(func)
    def envelope(*args, **kwargs):
        inicio = time.perf_counter()
        try:
            r = {"ok": True, **(func(*args, **kwargs) or {})}
            _anotar(func.__name__, inicio, True)
            return r
        except ERROS_ESPERADOS as e:
            log.info("%s recusado: %s", func.__name__, e)
            _anotar(func.__name__, inicio, False, str(e))
            return {"ok": False, "erro": str(e)}
        except Exception as e:  # erro inesperado: mensagem curta na tela, detalhe no log
            log.exception("erro inesperado em %s", func.__name__)
            _anotar(func.__name__, inicio, False, f"{type(e).__name__}: {e}")
            return {"ok": False, "erro": f"Erro inesperado ({type(e).__name__}): {e}. "
                                         f"Detalhes em ambiente_teste\\siapp.log."}
    return envelope


def _carregada(janela) -> bool:
    eventos = getattr(janela, "events", None)
    carregou = getattr(eventos, "loaded", None)
    return carregou is None or not hasattr(carregou, "is_set") or carregou.is_set()


class BaseAPI:
    """Estado compartilhado por todas as partes da ponte."""

    _janela = None
    _projeto = None

    def _janelas_abertas(self) -> list:
        """A principal e as abas destacadas que já carregaram (evaluate_js numa janela que
        ainda carrega esperaria até 15 s e travaria quem chamou)."""
        extras = [j for j in (getattr(self, "_janelas", None) or {}).values() if _carregada(j)]
        return [j for j in [self._janela, *extras] if j is not None]

    def _js(self, funcao: str, dados) -> None:
        """Chama uma função global em TODAS as janelas (a principal e as abas destacadas):
        cada uma mostra o que lhe cabe. Janela que já fechou é ignorada — o trabalho em
        segundo plano nunca quebra por causa da interface."""
        codigo = f"{funcao}({json.dumps(dados)})"
        for janela in self._janelas_abertas():
            try:
                janela.evaluate_js(codigo)
            except Exception:
                pass

    def _status(self, texto: str):
        """Atualiza a barra de status das janelas durante operações longas."""
        self._js_status(texto, "trab")

    def _js_status(self, texto: str, tipo: str):
        codigo = f"status({json.dumps(texto)}, {json.dumps(tipo)})"
        for janela in self._janelas_abertas():
            try:
                janela.evaluate_js(codigo)
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
            raise ErroUsuario("Abra primeiro o projeto (aba Projeto, “Abrir o projeto”).")
