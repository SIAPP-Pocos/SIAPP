"""Ponte: procurar poços por tipo de dado (a partir do levantamento do acervo, sem baixar nada)."""

from __future__ import annotations

import os

from motor import tipos_dado as mtd

from .base import ErroUsuario, resposta_segura

PASTA_EXPORTACAO = os.path.join("exportacoes", "tipos_de_dado")


class TiposAPI:
    @resposta_segura
    def tipos_de_dado(self, bacia: str = ""):
        """Os tipos de dado do acervo e quantos poços têm cada um (pelo levantamento já feito)."""
        self._exigir_projeto()
        return mtd.contar(self._banco, bacia or None)

    @resposta_segura
    def buscar_por_tipo(self, tipos: list, bacia: str = "", modo: str = "todos"):
        """Poços com todos (ou algum) dos tipos de dado escolhidos, com os arquivos desses tipos."""
        self._exigir_projeto()
        try:
            return mtd.buscar(self._banco, list(tipos or []), bacia or None, modo)
        except ValueError as e:
            raise ErroUsuario(str(e)) from e

    @resposta_segura
    def exportar_busca_por_tipo(self, tipos: list, bacia: str = "", modo: str = "todos"):
        """Grava a busca em CSV (um arquivo do portal por linha) em exportacoes/tipos_de_dado/."""
        self._exigir_projeto()
        try:
            r = mtd.buscar(self._banco, list(tipos or []), bacia or None, modo)
        except ValueError as e:
            raise ErroUsuario(str(e)) from e
        caminho = mtd.exportar(r, os.path.join(self._projeto.pasta, PASTA_EXPORTACAO))
        self._projeto.registrar("exportou_busca_por_tipo", tipos=r["tipos"], bacia=bacia, pocos=r["n_pocos"])
        return {"arquivo": os.path.relpath(caminho, self._projeto.pasta).replace(os.sep, "/"), "n_pocos": r["n_pocos"],
                "n_arquivos": r["n_arquivos"]}
