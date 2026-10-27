"""Ponte: catálogo do REATE (bacias, categorias, poços) e downloads."""

from __future__ import annotations

import os
import threading

from motor import projeto as mp
from motor import reate

from .base import ErroUsuario, resposta_segura


class CatalogoAPI:
    _cliente = None
    _cliente_dl = None
    _bacia = None
    _base_remota = "/"
    # Listar uma categoria grande leva segundos; se o usuário conecta em outra bacia
    # nesse meio-tempo, a resposta tem de ser gravada na bacia que foi LISTADA, não na
    # que está conectada agora (até a 0.29, a Categoria-7 da Potiguar foi gravada como
    # Alagoas assim). Cada ação pega um retrato da conexão no começo e usa só ele.
    _trava_conexao = threading.Lock()

    @resposta_segura
    def conectar(self, bacia: str):
        self._exigir_projeto()
        cliente = reate.ClienteREATE.da_bacia(bacia)
        base, categorias = cliente.descobrir_categorias()

        # Downloads usam uma conexão própria: um arquivo grande baixando não
        # trava a listagem de pastas na janela.
        cliente_dl = reate.ClienteREATE.da_bacia(bacia)
        with self._trava_conexao:
            self._cliente, self._bacia, self._base_remota = cliente, bacia, base
            self._cliente_dl = cliente_dl
        cats = [{"nome": c["nome"], "modificado": c["modificado"]} for c in categorias]
        arquivo = self._projeto.salvar_categorias(bacia, base, cats)
        self._projeto.registrar("conectou", bacia=bacia, categorias=len(cats))
        return {"bacia": bacia, "base": base, "categorias": cats,
                "salvo_em": self._projeto.rel(arquivo)}

    def _exigir_conexao(self):
        if self._cliente is None:
            raise ErroUsuario("Conecte-se a uma bacia primeiro.")

    def _conexao_reate(self, bacia: str | None = None):
        """(cliente, cliente de download, bacia, base remota) de agora, juntos.
        `bacia`: a bacia que a janela pensa estar usando; se a conexão mudou, recusa."""
        self._exigir_conexao()
        with self._trava_conexao:
            atual = (self._cliente, self._cliente_dl, self._bacia, self._base_remota)
        if bacia and bacia != atual[2]:
            raise ErroUsuario(f"A bacia conectada agora é {atual[2]}, e este pedido era da bacia {bacia}. "
                              f"Conecte-se de novo a {bacia} para continuar.")
        return atual

    @resposta_segura
    def listar_pocos(self, categoria: str, bacia: str | None = None):
        cliente, _, bacia, base = self._conexao_reate(bacia)
        r = cliente.listar_pocos(base + categoria, progresso=self._status)
        arquivo = self._projeto.salvar_pocos(bacia, categoria, r["pocos"],
                                             r["arquivos_soltos"], partes=r["partes"],
                                             duplicados=r["duplicados"])
        self._ao_listar_pocos(bacia, categoria, r["pocos"])
        self._projeto.registrar("listou_categoria", bacia=bacia, categoria=categoria,
                                pocos=len(r["pocos"]), partes=len(r["partes"]))
        return {"categoria": categoria, "bacia": bacia, **r,
                "salvo_em": self._projeto.rel(arquivo)}

    def _ao_listar_pocos(self, bacia, categoria, pocos):
        """Gancho: outras partes da ponte registram os poços vistos no portal."""

    @resposta_segura
    def explorar_poco(self, nome: str, caminho: str, categoria: str = "", parte: str | None = None,
                      bacia: str | None = None):
        cliente, _, bacia, base = self._conexao_reate(bacia)
        if not caminho.startswith(base):
            raise ErroUsuario(f"Caminho fora da bacia conectada: {caminho}")
        mapa = cliente.mapear_poco(caminho, nome, progresso=self._status)
        arquivo = self._projeto.salvar_arvore(bacia, nome, mapa,
                                              categoria=categoria, parte=parte)
        self._projeto.registrar("explorou_poco", bacia=bacia, poco=nome,
                                arquivos=mapa["resumo"]["n_arquivos"],
                                bytes=mapa["resumo"]["tamanho_total"])
        for a in mapa.pop("arquivos"):   # mesma referência dos nós da árvore
            destino = self._projeto.destino_bruto(bacia, nome, a["pasta_relativa"], a["nome"])
            a["baixado"] = (os.path.isfile(destino) and
                            (not a["tamanho"] or os.path.getsize(destino) == a["tamanho"]))
            a["parcial"] = not a["baixado"] and os.path.isfile(destino + ".part")
            if a["baixado"]:
                a["rel"] = self._projeto.rel(destino)
                a["tipo"] = mp.tipo_arquivo(destino)
        return {**mapa, "categoria": categoria, "parte": parte, "bacia": bacia,
                "salvo_em": self._projeto.rel(arquivo)}

    @resposta_segura
    def baixar(self, poco: str, arquivos: list, bacia: str | None = None):
        """Enfileira arquivos de um poço. Cada item: {caminho, nome, tamanho, pasta_relativa}."""
        _, cliente_dl, bacia, base = self._conexao_reate(bacia)
        if not arquivos:
            raise ErroUsuario("Nenhum arquivo selecionado.")
        tarefas = []
        for a in arquivos:
            if not str(a.get("caminho", "")).startswith(base):
                raise ErroUsuario(f"Caminho fora da bacia conectada: {a.get('caminho')}")
            tarefas.append({
                "cliente": cliente_dl, "projeto": self._projeto,
                "bacia": bacia, "poco": poco,
                "caminho": a["caminho"], "nome": a["nome"], "tamanho": int(a.get("tamanho") or 0),
                "destino": self._projeto.destino_bruto(bacia, poco,
                                                       a.get("pasta_relativa", ""), a["nome"]),
            })
        r = self._fila.adicionar(tarefas)
        self._projeto.registrar("pediu_download", bacia=bacia, poco=poco,
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
            evento["tipo"] = mp.tipo_arquivo(evento["arquivo_local"])
            evento["arquivo_local"] = self._projeto.rel(evento["arquivo_local"])
        self._js("eventoDownload", evento)

    def _ao_terminar_download(self, evento: dict):
        """Gancho: registrar o arquivo novo no banco do projeto."""
