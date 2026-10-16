"""Ponte: cadastro de poços da ANP, catálogo do REATE no banco, mapa e ficha."""

from __future__ import annotations

import os

import webview

from motor import agp as magp
from motor import levantamento as mlv
from motor import pocos as mpo

from .base import ErroUsuario, resposta_segura


class PocosAPI:
    # ------------------------------------------------------- id dos poços
    def _id_poco(self, nome_pasta: str) -> str:
        return mpo.resolver(self._banco, nome_pasta) if nome_pasta else ""

    def _ao_listar_pocos(self, bacia, categoria, pocos):
        mpo.registrar_reate(self._banco, bacia, categoria, pocos)

    def _migrar_pocos(self):
        """Listas de poços salvas antes do banco (catalogo/*.json) entram na
        tabela reate; arquivos ganham o id canônico do poço."""
        if not self._banco.meta("migrou_catalogo_json"):
            n = mpo.importar_catalogo_json(self._banco, os.path.join(self._projeto.pasta, "catalogo"))
            self._banco.definir_meta("migrou_catalogo_json", str(n))
        with self._banco.conexao() as c:
            for rel, poco in c.execute("SELECT rel, poco_id FROM arquivos").fetchall():
                novo = mpo.chave(poco or "")
                if novo and novo != poco:
                    c.execute("UPDATE arquivos SET poco_id = ? WHERE rel = ?", (novo, rel))

    # ------------------------------------------------------------ cadastro
    @resposta_segura
    def cadastro_info(self):
        self._exigir_projeto()
        import json
        info = self._banco.meta("cadastro_anp")
        return {"cadastro": json.loads(info) if info else None,
                "bacias": mpo.bacias(self._banco),
                "pagina_anp": mpo.PAGINA_CADASTRO}

    @resposta_segura
    def atualizar_cadastro_anp(self):
        """Baixa a Tabela de Poços dos dados abertos da ANP (~12 MB) e importa."""
        self._exigir_projeto()
        self._status("Baixando a Tabela de Poços da ANP (~12 MB)…")
        dados = mpo.baixar_cadastro()
        destino = os.path.join(self._projeto.pasta_de("cadastro"), "tabela-pocos.csv")
        with open(destino, "wb") as f:
            f.write(dados)
        return self._importar_cadastro(dados, "anp:dados-abertos")

    @resposta_segura
    def importar_cadastro_arquivo(self):
        self._exigir_projeto()
        escolha = self._janela.create_file_dialog(
            webview.FileDialog.OPEN, directory=self._projeto.pasta,
            file_types=("Tabela de Poços (*.csv)", "Todos os arquivos (*.*)"))
        if not escolha:
            return {"cancelado": True}
        caminho = escolha[0] if isinstance(escolha, (list, tuple)) else escolha
        with open(caminho, "rb") as f:
            return self._importar_cadastro(f.read(), "anp:arquivo:" + os.path.basename(caminho))

    def _importar_cadastro(self, dados: bytes, fonte: str) -> dict:
        self._status("Lendo o cadastro…")
        linhas = mpo.ler_cadastro(dados)
        r = mpo.importar_cadastro(self._banco, linhas, fonte)
        self._migrar_pocos()
        self._projeto.registrar("importou_cadastro_anp", fonte=fonte, **r)
        return {"resumo": r, "bacias": mpo.bacias(self._banco)}

    # --------------------------------------------------------- mapa e ficha
    @resposta_segura
    def pocos_mapa(self, filtros: dict | None = None):
        self._exigir_projeto()
        f = filtros or {}
        return mpo.pocos_mapa(self._banco, bacia=f.get("bacia", ""), texto=f.get("texto", ""),
                              terra_mar=f.get("terra_mar", ""), tipo=f.get("tipo") or None,
                              so_reate=bool(f.get("so_reate")), so_baixados=bool(f.get("so_baixados")),
                              acervo=f.get("acervo", ""), familia=f.get("familia", ""))

    @resposta_segura
    def ficha_poco(self, poco: str):
        self._exigir_projeto()
        pid = mpo.resolver(self._banco, poco)
        d = mpo.ficha(self._banco, pid)
        if d is None:
            raise ErroUsuario(f"Poço {poco} não está no cadastro nem no catálogo deste projeto.")
        d["acervo"] = mlv.arquivos_do_poco(self._banco, pid)
        d["agp"] = [{"caminho": g["caminho"], "poco_pasta": g["poco_pasta"], "confere": g["confere"],
                     "arquivo_local": g["arquivo_local"], "lido_em": g["lido_em"], **g["dados"]}
                    for g in magp.do_poco(self._banco, pid)]
        return d

    @resposta_segura
    def catalogar_bacia(self):
        """Lista TODAS as categorias da bacia conectada e registra cada pasta de
        poço no banco (sem baixar nada). Permite marcar no mapa o que tem dado."""
        self._exigir_conexao()
        _, categorias = self._cliente.descobrir_categorias()
        total = 0
        for i, cat in enumerate(categorias, 1):
            self._status(f"Catalogando {self._bacia}: {cat['nome']} ({i} de {len(categorias)})…")
            r = self._cliente.listar_pocos(self._base_remota + cat["nome"], progresso=self._status)
            self._projeto.salvar_pocos(self._bacia, cat["nome"], r["pocos"], r["arquivos_soltos"],
                                       partes=r["partes"], duplicados=r["duplicados"])
            total += mpo.registrar_reate(self._banco, self._bacia, cat["nome"], r["pocos"])
        self._projeto.registrar("catalogou_bacia", bacia=self._bacia, pocos=total)
        return {"bacia": self._bacia, "categorias": len(categorias), "pocos": total}
