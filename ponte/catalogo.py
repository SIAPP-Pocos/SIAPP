"""Ponte: catálogo do REATE (bacias, categorias, poços) e downloads."""

from __future__ import annotations

import os

from motor import reate

from .base import ErroUsuario, resposta_segura


class CatalogoAPI:
    _cliente = None
    _cliente_dl = None
    _bacia = None
    _base_remota = "/"

    @resposta_segura
    def conectar(self, bacia: str):
        self._exigir_projeto()
        cliente = reate.ClienteREATE.da_bacia(bacia)
        base, categorias = cliente.descobrir_categorias()

        self._cliente, self._bacia, self._base_remota = cliente, bacia, base
        # Downloads usam uma conexão própria: um arquivo grande baixando não
        # trava a listagem de pastas na janela.
        self._cliente_dl = reate.ClienteREATE.da_bacia(bacia)
        cats = [{"nome": c["nome"], "modificado": c["modificado"]} for c in categorias]
        arquivo = self._projeto.salvar_categorias(bacia, base, cats)
        self._projeto.registrar("conectou", bacia=bacia, categorias=len(cats))
        return {"bacia": bacia, "base": base, "categorias": cats,
                "salvo_em": self._projeto.rel(arquivo)}

    def _exigir_conexao(self):
        if self._cliente is None:
            raise ErroUsuario("Conecte-se a uma bacia primeiro.")

    @resposta_segura
    def listar_pocos(self, categoria: str):
        self._exigir_conexao()
        r = self._cliente.listar_pocos(self._base_remota + categoria, progresso=self._status)
        arquivo = self._projeto.salvar_pocos(self._bacia, categoria, r["pocos"],
                                             r["arquivos_soltos"], partes=r["partes"],
                                             duplicados=r["duplicados"])
        self._ao_listar_pocos(self._bacia, categoria, r["pocos"])
        self._projeto.registrar("listou_categoria", bacia=self._bacia, categoria=categoria,
                                pocos=len(r["pocos"]), partes=len(r["partes"]))
        return {"categoria": categoria, **r,
                "salvo_em": self._projeto.rel(arquivo)}

    def _ao_listar_pocos(self, bacia, categoria, pocos):
        """Gancho: outras partes da ponte registram os poços vistos no portal."""

    @resposta_segura
    def explorar_poco(self, nome: str, caminho: str, categoria: str = "", parte: str | None = None):
        self._exigir_conexao()
        if not caminho.startswith(self._base_remota):
            raise ErroUsuario(f"Caminho fora da bacia conectada: {caminho}")
        mapa = self._cliente.mapear_poco(caminho, nome, progresso=self._status)
        arquivo = self._projeto.salvar_arvore(self._bacia, nome, mapa,
                                              categoria=categoria, parte=parte)
        self._projeto.registrar("explorou_poco", bacia=self._bacia, poco=nome,
                                arquivos=mapa["resumo"]["n_arquivos"],
                                bytes=mapa["resumo"]["tamanho_total"])
        for a in mapa.pop("arquivos"):   # mesma referência dos nós da árvore
            destino = self._projeto.destino_bruto(self._bacia, nome, a["pasta_relativa"], a["nome"])
            a["baixado"] = (os.path.isfile(destino) and
                            (not a["tamanho"] or os.path.getsize(destino) == a["tamanho"]))
            a["parcial"] = not a["baixado"] and os.path.isfile(destino + ".part")
            if a["baixado"]:
                a["rel"] = self._projeto.rel(destino)
        return {**mapa, "categoria": categoria, "parte": parte,
                "salvo_em": self._projeto.rel(arquivo)}

    @resposta_segura
    def baixar(self, poco: str, arquivos: list):
        """Enfileira arquivos de um poço. Cada item: {caminho, nome, tamanho, pasta_relativa}."""
        if self._cliente_dl is None:
            raise ErroUsuario("Conecte-se a uma bacia primeiro.")
        if not arquivos:
            raise ErroUsuario("Nenhum arquivo selecionado.")
        tarefas = []
        for a in arquivos:
            if not str(a.get("caminho", "")).startswith(self._base_remota):
                raise ErroUsuario(f"Caminho fora da bacia conectada: {a.get('caminho')}")
            tarefas.append({
                "cliente": self._cliente_dl, "projeto": self._projeto,
                "bacia": self._bacia, "poco": poco,
                "caminho": a["caminho"], "nome": a["nome"], "tamanho": int(a.get("tamanho") or 0),
                "destino": self._projeto.destino_bruto(self._bacia, poco,
                                                       a.get("pasta_relativa", ""), a["nome"]),
            })
        r = self._fila.adicionar(tarefas)
        self._projeto.registrar("pediu_download", bacia=self._bacia, poco=poco,
                                arquivos=[a["nome"] for a in arquivos],
                                bytes=sum(t["tamanho"] for t in tarefas))
        return r

    @resposta_segura
    def cancelar_downloads(self):
        self._fila.cancelar()
        return {}

    def _emitir_download(self, evento: dict):
        if evento.get("arquivo_local") and self._projeto:
            self._ao_terminar_download(evento)
            evento["arquivo_local"] = self._projeto.rel(evento["arquivo_local"])
        self._js("eventoDownload", evento)

    def _ao_terminar_download(self, evento: dict):
        """Gancho: registrar o arquivo novo no banco do projeto."""
