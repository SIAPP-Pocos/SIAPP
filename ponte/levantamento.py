"""Ponte: levantamento do acervo de uma bacia (o que cada poço tem, pelo conteúdo)."""

from __future__ import annotations

import os

from motor import levantamento as mlv
from motor import reate

from .base import ErroUsuario, resposta_segura
from .comunidade import _abrir_no_sistema

PASTA_EXPORTACAO = os.path.join("exportacoes", "levantamento")


class LevantamentoAPI:
    _levantamento = None   # motor.levantamento.Levantamento em andamento

    @resposta_segura
    def levantamento_categorias(self, bacia: str):
        """Categorias da bacia no portal (precisa de internet)."""
        self._exigir_projeto()
        if bacia not in reate.BACIAS:
            raise ErroUsuario(f"Bacia desconhecida: {bacia}")
        _, cats = reate.ClienteREATE.da_bacia(bacia).descobrir_categorias()
        return {"bacia": bacia, "categorias": [c["nome"] for c in cats]}

    @resposta_segura
    def levantamento_resumo(self, bacia: str):
        self._exigir_projeto()
        lev = self._levantamento
        return {"resumo": mlv.resumo(self._banco, bacia), "situacoes": mlv.SITUACOES,
                "ativo": bool(lev and lev.ativo), "bacia_ativa": lev.bacia if lev and lev.ativo else ""}

    @resposta_segura
    def levantar_acervo(self, bacia: str, categorias: list, curvas: bool = False,
                        conferir_todos: bool = False):
        self._exigir_projeto()
        if self._levantamento and self._levantamento.ativo:
            raise ErroUsuario(f"Já há um levantamento em andamento ({self._levantamento.bacia}).")
        if bacia not in reate.BACIAS:
            raise ErroUsuario(f"Bacia desconhecida: {bacia}")
        cl = self._cl()
        self._levantamento = mlv.Levantamento(
            self._banco, bacia, list(categorias or []), emitir=self._emitir_levantamento,
            curvas=bool(curvas), conferir_todos=bool(conferir_todos), familia=cl.familia)
        self._levantamento.iniciar()
        self._projeto.registrar("iniciou_levantamento", bacia=bacia, categorias=list(categorias or []),
                                curvas=bool(curvas), conferir_todos=bool(conferir_todos))
        return {"iniciado": True}

    @resposta_segura
    def cancelar_levantamento(self):
        if self._levantamento:
            self._levantamento.cancelar.set()
        return {}

    @resposta_segura
    def exportar_levantamento(self, bacia: str):
        self._exigir_projeto()
        pasta = os.path.join(self._projeto.pasta, PASTA_EXPORTACAO)
        arquivos = mlv.exportar_csv(self._banco, bacia, pasta)
        self._projeto.registrar("exportou_levantamento", bacia=bacia,
                                arquivos=[os.path.basename(a) for a in arquivos])
        return {"arquivos": [os.path.relpath(a, self._projeto.pasta).replace(os.sep, "/") for a in arquivos]}

    @resposta_segura
    def abrir_pasta_levantamento(self):
        self._exigir_projeto()
        pasta = os.path.join(self._projeto.pasta, PASTA_EXPORTACAO)
        os.makedirs(pasta, exist_ok=True)
        _abrir_no_sistema(pasta)
        return {}

    def _emitir_levantamento(self, ev: dict):
        if ev.get("tipo") in ("fim", "cancelado", "erro") and self._projeto:
            self._projeto.registrar("levantamento_" + ev["tipo"],
                                    bacia=self._levantamento.bacia if self._levantamento else "",
                                    pocos=ev.get("pocos"), arquivos_lidos=ev.get("arquivos_lidos"),
                                    erro=ev.get("erro"))
        self._js("eventoLevantamento", ev)
