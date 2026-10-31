"""Ponte: procurar poços por tipo de dado (a partir do levantamento do acervo, sem baixar nada)."""

from __future__ import annotations

import os

from motor import tipos_dado as mtd

from .base import ErroUsuario, resposta_segura

PASTA_EXPORTACAO = os.path.join("exportacoes", "tipos_de_dado")


class TiposAPI:
    def _restricao(self, restricao) -> list | None:
        """Lista de poços a que a busca fica restrita: {"campo": "..."} (cadastro da ANP) ou {"pocos": [...]}."""
        if not restricao:
            return None
        if restricao.get("campo"):
            ids = mtd.pocos_do_campo(self._banco, str(restricao["campo"]))
            if not ids:
                raise ErroUsuario(f"O cadastro da ANP não tem poços do campo {restricao['campo']}. Baixe o cadastro em "
                                  "Dados › Cadastro da ANP ou confira o nome do campo.")
            return ids
        if restricao.get("pocos") is not None:
            return list(restricao["pocos"])
        return None

    @resposta_segura
    def tipos_de_dado(self, bacia: str = "", restricao: dict | None = None):
        """Os tipos de dado do acervo e quantos poços têm cada um (pelo levantamento já feito)."""
        self._exigir_projeto()
        r = mtd.contar(self._banco, bacia or None, self._restricao(restricao))
        r["campos"] = mtd.campos_do_cadastro(self._banco)
        return r

    @resposta_segura
    def buscar_por_tipo(self, tipos: list, bacia: str = "", modo: str = "todos", restricao: dict | None = None):
        """Poços com todos (ou algum) dos tipos de dado escolhidos, com os arquivos desses tipos."""
        self._exigir_projeto()
        try:
            return mtd.buscar(self._banco, list(tipos or []), bacia or None, modo, self._restricao(restricao))
        except ValueError as e:
            raise ErroUsuario(str(e)) from e

    @resposta_segura
    def exportar_busca_por_tipo(self, tipos: list, bacia: str = "", modo: str = "todos", restricao: dict | None = None):
        """Grava a busca em CSV (um arquivo do portal por linha) em exportacoes/tipos_de_dado/."""
        self._exigir_projeto()
        try:
            r = mtd.buscar(self._banco, list(tipos or []), bacia or None, modo, self._restricao(restricao))
        except ValueError as e:
            raise ErroUsuario(str(e)) from e
        caminho = mtd.exportar(r, os.path.join(self._projeto.pasta, PASTA_EXPORTACAO))
        self._projeto.registrar("exportou_busca_por_tipo", tipos=r["tipos"], bacia=bacia, pocos=r["n_pocos"])
        return {"arquivo": os.path.relpath(caminho, self._projeto.pasta).replace(os.sep, "/"), "n_pocos": r["n_pocos"],
                "n_arquivos": r["n_arquivos"]}
