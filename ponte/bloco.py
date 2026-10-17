"""Ponte: bloco 3D dos poços e das superfícies de topo (aba Bloco 3D)."""

from __future__ import annotations

import base64
import os

from motor import agp as magp
from motor import bloco as mbl
from motor import secao as msc

from .base import PASTA_RECURSOS, ErroUsuario, resposta_segura
from .comunidade import _abrir_no_sistema

CAMINHO_ESTRATIGRAFIA = os.path.join(PASTA_RECURSOS, "estratigrafia.json")
PASTA_EXPORTACAO = os.path.join("exportacoes", "blocos")
MAX_PNG = 40 * 1024 * 1024


class BlocoAPI:
    def _num(self, v, padrao=None):
        if v in (None, ""):
            return padrao
        try:
            return float(str(v).replace(",", "."))
        except ValueError as e:
            raise ErroUsuario(f"Valor inválido: {v}") from e

    def _ident_bloco(self, ident: str) -> str:
        if not ident or not ident.startswith("bloco_") or "/" in ident or "\\" in ident or ".." in ident:
            raise ErroUsuario("Bloco inválido.")
        return ident

    @resposta_segura
    def bloco_opcoes(self):
        """Bacias, campos e poços com topos no AGP (para escolher os poços do bloco)."""
        self._exigir_projeto()
        pocos = mbl.pocos_disponiveis(self._banco)
        with self._banco.conexao() as c:
            bacias = [r[0] for r in c.execute(
                "SELECT bacia, count(DISTINCT poco_id) FROM agp_unidades WHERE tip = 'L' AND topo IS NOT NULL "
                "GROUP BY bacia ORDER BY 2 DESC")]
        return {"bacias": bacias, "campos": mbl.campos(self._banco),
                "pocos": [{"id": p["id"], "campo": p["campo"], "n_unidades": p["n_unidades"]} for p in pocos],
                "total": len(pocos)}

    @resposta_segura
    def bloco_selecionar(self, modo: str, campo: str = "", poco: str = "", raio_km=5.0, bacia: str = ""):
        self._exigir_projeto()
        try:
            ids = mbl.selecionar(self._banco, modo=modo, campo=campo or "",
                                 poco=self._id_poco(poco) if poco else "",
                                 raio_km=self._num(raio_km, 5.0), bacia=bacia or None)
        except mbl.ErroBloco as e:
            raise ErroUsuario(str(e)) from e
        return {"pocos": ids, "isolado": modo == "campo"}

    @resposta_segura
    def bloco_montar(self, pocos: list, opcoes: dict | None = None):
        self._exigir_projeto()
        op = opcoes or {}
        ids = [self._id_poco(p) for p in pocos if str(p).strip()]
        try:
            modelo = mbl.montar(
                self._banco, ids, nivel=op.get("nivel", "formacoes"), margem_km=self._num(op.get("margem"), 0.0),
                celulas=int(self._num(op.get("celulas"), mbl.CELULAS_PADRAO)),
                dist_max_km=self._num(op.get("dist_max")),
                nomes=magp.ler_estratigrafia(CAMINHO_ESTRATIGRAFIA), slots=msc.ler_slots(CAMINHO_ESTRATIGRAFIA))
        except mbl.ErroBloco as e:
            raise ErroUsuario(str(e)) from e
        modelo["titulo"] = (op.get("titulo") or "").strip()
        ident, _ = mbl.registrar(self._projeto.pasta_de("execucoes"), modelo, autor=self._autor())
        self._projeto.registrar("montou_bloco", execucao=ident, pocos=len(modelo["pocos"]),
                                area_km2=modelo["area_km2"], parametros=modelo["parametros"])
        return {"id": ident, "modelo": modelo, "autor": self._autor()}

    @resposta_segura
    def bloco_execucoes(self):
        self._exigir_projeto()
        return {"execucoes": mbl.execucoes(self._projeto.pasta_de("execucoes"))[:20]}

    @resposta_segura
    def bloco_abrir(self, ident: str):
        """Um bloco já montado (do histórico), sem recalcular."""
        self._exigir_projeto()
        try:
            reg = mbl.abrir(self._projeto.pasta_de("execucoes"), self._ident_bloco(ident))
        except mbl.ErroBloco as e:
            raise ErroUsuario(str(e)) from e
        return {"id": ident, "modelo": reg, "autor": reg.get("autor", "")}

    @resposta_segura
    def bloco_exportar_csv(self, ident: str):
        self._exigir_projeto()
        try:
            reg = mbl.abrir(self._projeto.pasta_de("execucoes"), self._ident_bloco(ident))
        except mbl.ErroBloco as e:
            raise ErroUsuario(str(e)) from e
        arquivos = mbl.exportar_csv(reg, os.path.join(self._projeto.pasta, PASTA_EXPORTACAO), ident)
        self._projeto.registrar("exportou_bloco", execucao=ident, formato="csv")
        return {"arquivos": [os.path.relpath(a, self._projeto.pasta).replace(os.sep, "/") for a in arquivos]}

    @resposta_segura
    def bloco_salvar_png(self, ident: str, dados_url: str):
        """Grava a imagem que a janela desenhou (data:image/png;base64,…)."""
        self._exigir_projeto()
        ident = self._ident_bloco(ident)
        prefixo = "data:image/png;base64,"
        if not isinstance(dados_url, str) or not dados_url.startswith(prefixo) or len(dados_url) > MAX_PNG:
            raise ErroUsuario("Imagem inválida.")
        dados = base64.b64decode(dados_url[len(prefixo):])
        if not dados.startswith(b"\x89PNG"):
            raise ErroUsuario("Imagem inválida.")
        pasta = os.path.join(self._projeto.pasta, PASTA_EXPORTACAO)
        os.makedirs(pasta, exist_ok=True)
        saida = os.path.join(pasta, f"{ident}.png")
        with open(saida + ".tmp", "wb") as f:
            f.write(dados)
        os.replace(saida + ".tmp", saida)
        self._projeto.registrar("exportou_bloco", execucao=ident, formato="png")
        return {"arquivo": os.path.relpath(saida, self._projeto.pasta).replace(os.sep, "/")}

    @resposta_segura
    def abrir_pasta_blocos(self):
        self._exigir_projeto()
        pasta = os.path.join(self._projeto.pasta, PASTA_EXPORTACAO)
        os.makedirs(pasta, exist_ok=True)
        _abrir_no_sistema(pasta)
        return {}
