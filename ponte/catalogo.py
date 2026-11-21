"""Ponte: catálogo do REATE (bacias, categorias, poços) e downloads."""

from __future__ import annotations

import os
import threading

from motor import pocos as mpo
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
        return self._conectar(bacia)

    def _conectar(self, bacia: str) -> dict:
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

    @resposta_segura
    def catalogo_abrir_poco(self, bacia: str, categoria: str, nome_pasta: str, caminho: str, parte: str | None = None):
        """0.65: "Ver arquivos" da ficha do poço, num passo só. Conecta à bacia se preciso, mostra a categoria pela lista
        já salva (sem listar tudo de novo no portal) e devolve o poço pronto para abrir. Sem lista salva, a categoria
        aparece só com este poço — o caminho dele no portal já é conhecido (tabela reate)."""
        self._exigir_projeto()
        with self._trava_conexao:
            conectado = self._cliente is not None and self._bacia == bacia
        if conectado:
            salvo = mp.ler_json(os.path.join(self._projeto.pasta_catalogo(bacia), "categorias.json"), {}) or {}
            conexao = {"bacia": bacia, "base": self._base_remota, "categorias": salvo.get("categorias", []),
                       "salvo_em": self._projeto.rel(os.path.join(self._projeto.pasta_catalogo(bacia), "categorias.json")),
                       "ja_conectado": True}
            if not conexao["categorias"]:
                conexao = self._conectar(bacia)
        else:
            conexao = self._conectar(bacia)
        lista = mp.ler_json(os.path.join(self._projeto.pasta_catalogo(bacia), mp.nome_seguro(categoria) + ".json"), None)
        poco = {"nome": nome_pasta, "caminho": caminho, "parte": parte}
        if isinstance(lista, dict) and isinstance(lista.get("pocos"), list):
            achado = next((q for q in lista["pocos"] if q.get("caminho") == caminho or q.get("nome") == nome_pasta), None)
            if achado:
                poco = achado
            else:
                lista["pocos"] = [*lista["pocos"], poco]
            r = {"categoria": categoria, "bacia": bacia, "pocos": lista["pocos"], "partes": lista.get("partes", []),
                 "duplicados": lista.get("duplicados", []), "arquivos_soltos": lista.get("arquivos_soltos", []),
                 "listado_em": lista.get("listado_em", ""), "parcial": False}
        else:
            r = {"categoria": categoria, "bacia": bacia, "pocos": [poco], "partes": [], "duplicados": [],
                 "arquivos_soltos": [], "listado_em": "", "parcial": True}
        if not str(poco.get("caminho") or "").startswith(conexao.get("base") or self._base_remota):
            raise ErroUsuario(f"O caminho guardado de {nome_pasta} não é da bacia {bacia}. Liste a categoria de novo.")
        self._projeto.registrar("abriu_poco_no_catalogo", bacia=bacia, categoria=categoria, poco=nome_pasta)
        r["comunidade"] = self._comunidade_dos_nomes(q.get("nome", "") for q in r["pocos"])
        return {"conexao": conexao, "lista": r, "poco": poco}

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
                "salvo_em": self._projeto.rel(arquivo),
                "comunidade": self._comunidade_dos_nomes(p["nome"] for p in r["pocos"])}

    def _comunidade_dos_nomes(self, nomes) -> dict:
        """1.3: {nome da pasta no portal: dados da comunidade do poço}, só dos poços que têm algum."""
        com = self._banco.comunidade_por_poco()
        if not com:
            return {}
        saida = {}
        for n in nomes:
            d = com.get(mpo.resolver(self._banco, n))
            if d:
                saida[n] = d
        return saida

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
            # "tipo" é o tipo do EVENTO ("fim"); o do arquivo vai à parte (até a 0.35 o
            # tipo do arquivo sobrescrevia o "fim" e o selo ficava em "baixando")
            evento["tipo_arquivo"] = mp.tipo_arquivo(evento["arquivo_local"])
            evento["arquivo_local"] = self._projeto.rel(evento["arquivo_local"])
        self._js("eventoDownload", evento)

    def _ao_terminar_download(self, evento: dict):
        """Gancho: registrar o arquivo novo no banco do projeto."""
