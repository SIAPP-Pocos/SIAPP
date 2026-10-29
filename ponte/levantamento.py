"""Ponte: levantamento do acervo de uma bacia (o que cada poço tem, pelo conteúdo)."""

from __future__ import annotations

import os

from motor import agp as magp
from motor import levantamento as mlv
from motor import operador as mop
from motor import reate

from .base import PASTA_RECURSOS, PASTA_TESSDATA, ErroUsuario, resposta_segura
from .comunidade import _abrir_no_sistema

PASTA_EXPORTACAO = os.path.join("exportacoes", "levantamento")
CAMINHO_ESTRATIGRAFIA = os.path.join(PASTA_RECURSOS, "estratigrafia.json")


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
    def perfis_processados(self, bacia: str | None = None):
        """Poços do levantamento com curvas interpretadas pela operadora (Vsh, φ, Sw, k), sem baixar nada."""
        self._exigir_projeto()
        return mop.pesquisar(self._banco, list(mlv.FAMILIAS_INTERP), bacia or None)

    @resposta_segura
    def levantar_acervo(self, bacia: str, categorias: list, curvas: bool = False,
                        conferir_todos: bool = False, agp: bool = True, esquemas: bool = False,
                        direcionais: bool = True):
        self._exigir_projeto()
        if self._levantamento and self._levantamento.ativo:
            raise ErroUsuario(f"Já há um levantamento em andamento ({self._levantamento.bacia}).")
        if bacia not in reate.BACIAS:
            raise ErroUsuario(f"Bacia desconhecida: {bacia}")
        cl = self._cl()
        self._levantamento = mlv.Levantamento(
            self._banco, bacia, list(categorias or []), emitir=self._emitir_levantamento,
            curvas=bool(curvas), conferir_todos=bool(conferir_todos), familia=cl.familia,
            agp=bool(agp), pasta_agp=os.path.join(self._projeto.pasta, "agp"),
            estratigrafia=magp.ler_estratigrafia(CAMINHO_ESTRATIGRAFIA),
            esquemas=bool(esquemas), pasta_projeto=self._projeto.pasta,
            tessdata=PASTA_TESSDATA if (esquemas and self._garantir_ocr_ingles()) else None,
            ferramentas=self._dic() if esquemas else None, direcionais=bool(direcionais))
        self._levantamento.iniciar()
        self._projeto.registrar("iniciou_levantamento", bacia=bacia, categorias=list(categorias or []),
                                curvas=bool(curvas), conferir_todos=bool(conferir_todos), agp=bool(agp),
                                esquemas=bool(esquemas), direcionais=bool(direcionais))
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

    @resposta_segura
    def abrir_agp(self, caminho: str):
        """Abre o texto do AGP guardado em ambiente_teste/agp/."""
        self._exigir_projeto()
        pasta = os.path.realpath(os.path.join(self._projeto.pasta, "agp"))
        alvo = os.path.realpath(os.path.join(self._projeto.pasta, caminho))
        if os.path.commonpath([alvo, pasta]) != pasta or not os.path.isfile(alvo):
            raise ErroUsuario("AGP não encontrado na pasta do projeto.")
        _abrir_no_sistema(alvo)
        return {}

    def _emitir_levantamento(self, ev: dict):
        if ev.get("tipo") in ("fim", "cancelado", "erro") and self._projeto:
            self._projeto.registrar("levantamento_" + ev["tipo"],
                                    bacia=self._levantamento.bacia if self._levantamento else "",
                                    pocos=ev.get("pocos"), arquivos_lidos=ev.get("arquivos_lidos"),
                                    agps_lidos=ev.get("agps_lidos"), esquemas_lidos=ev.get("esquemas_lidos"),
                                    direcionais_lidos=ev.get("direcionais_lidos"),
                                    erro=ev.get("erro"))
        self._js("eventoLevantamento", ev)
