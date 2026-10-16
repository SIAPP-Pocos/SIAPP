"""
SIAPP — janela principal.

Abre uma janela nativa que exibe a interface HTML (pasta ui/) e expõe ao
JavaScript as funções da classe API. O JS chama, por exemplo:

    await window.pywebview.api.conectar("Sergipe")

Esta camada é fina de propósito: só traduz chamadas da interface para o
motor e devolve dicionários simples. Toda lógica fica em motor/.

Uso:  python siapp.py
"""

from __future__ import annotations

import functools
import json
import os
import re
import subprocess
import sys
import traceback

import webview

from motor import projeto as mp
from motor import reate
from motor import documentos as md
from motor import vocabulario as mvoc
from motor.downloads import FilaDownloads

PASTA_APP = os.path.dirname(os.path.abspath(__file__))

# Por enquanto o projeto mora SEMPRE nesta pasta, ao lado do aplicativo.
# Assim, ao compactar a siapp.vf para outra pessoa, os dados vão junto e
# ficam no mesmo lugar em todos os computadores. Para liberar outras
# pastas no futuro, basta remover a checagem em API.escolher_pasta.
NOME_PASTA_PROJETO = "ambiente_teste"
PASTA_PROJETO = os.path.join(PASTA_APP, NOME_PASTA_PROJETO)
# Modelo de idioma do OCR: baixado uma vez e guardado junto do aplicativo.
PASTA_TESSDATA = os.path.join(PASTA_APP, "recursos", "tessdata")
# Dicionário de domínio que vem com o SIAPP (editável; ver motor/vocabulario.py).
CAMINHO_VOCAB_BASE = os.path.join(PASTA_APP, "recursos", "vocabulario_base.json")


def mesma_pasta(a: str, b: str) -> bool:
    """Compara caminhos ignorando maiúsculas/minúsculas e barras (Windows)."""
    norm = lambda p: os.path.normcase(os.path.normpath(os.path.abspath(p)))
    return norm(a) == norm(b)


def resposta_segura(func):
    """Toda chamada vinda da interface devolve {"ok": True, ...} ou
    {"ok": False, "erro": "..."} — nunca deixa uma exceção estourar no JS."""
    @functools.wraps(func)
    def envelope(*args, **kwargs):
        try:
            return {"ok": True, **(func(*args, **kwargs) or {})}
        except (reate.ErroREATE, md.ErroDocumento, NotADirectoryError, ValueError) as e:
            return {"ok": False, "erro": str(e)}
        except Exception as e:  # erro inesperado: mensagem curta na tela, detalhe no terminal
            traceback.print_exc()
            return {"ok": False, "erro": f"Erro inesperado ({type(e).__name__}): {e}"}
    return envelope


class API:
    # Atributos com "_" não são expostos ao JavaScript pelo pywebview.
    def __init__(self):
        self._janela = None
        self._projeto: mp.Projeto | None = None
        self._cliente: reate.ClienteREATE | None = None
        self._bacia: str | None = None
        self._base_remota = "/"
        # Downloads usam uma conexão própria: um arquivo grande baixando não
        # trava a listagem de pastas na janela.
        self._cliente_dl: reate.ClienteREATE | None = None
        self._fila = FilaDownloads(self._emitir_download)
        self._fila_docs = md.FilaDocumentos(PASTA_TESSDATA, self._emitir_documento)
        self._indice: md.Indice | None = None
        self._corretor: mvoc.Corretor | None = None

    @resposta_segura
    def info(self):
        return {"versao": mp.VERSAO_SIAPP, "bacias": sorted(reate.BACIAS),
                "nome_pasta_projeto": NOME_PASTA_PROJETO, "pasta_projeto": PASTA_PROJETO}

    @resposta_segura
    def escolher_pasta(self):
        os.makedirs(PASTA_PROJETO, exist_ok=True)
        escolha = self._janela.create_file_dialog(webview.FileDialog.FOLDER,
                                                  directory=PASTA_PROJETO)
        if not escolha:
            return {"cancelado": True}
        pasta = escolha[0] if isinstance(escolha, (list, tuple)) else escolha
        if not mesma_pasta(pasta, PASTA_PROJETO):
            raise ValueError(
                f"Pasta recusada: {pasta}. Por enquanto o projeto precisa ficar "
                f"exatamente na pasta '{NOME_PASTA_PROJETO}', ao lado do aplicativo. "
                f"Com o diálogo aberto nela, clique direto em 'Selecionar pasta' "
                f"sem entrar em nenhuma subpasta.")
        self._projeto = mp.Projeto.abrir_ou_criar(PASTA_PROJETO)
        self._indice = md.Indice(os.path.join(self._projeto.pasta, "texto", "indice.sqlite"))
        self._carregar_corretor()
        if self._indice.recriado:   # estrutura do índice mudou de versão: refaz a partir dos textos
            self._indice.reconstruir(self._projeto.documentos_processados(), self._corretor)
        cfg = self._projeto.config
        return {"pasta": self._projeto.pasta, "bacia_anterior": cfg.get("bacia"),
                "criado": cfg.get("criado")}

    @resposta_segura
    def conectar(self, bacia: str):
        if self._projeto is None:
            raise ValueError("Escolha primeiro a pasta do projeto.")
        cliente = reate.ClienteREATE.da_bacia(bacia)
        base, categorias = cliente.descobrir_categorias()

        self._cliente, self._bacia, self._base_remota = cliente, bacia, base
        self._cliente_dl = reate.ClienteREATE.da_bacia(bacia)
        cats = [{"nome": c["nome"], "modificado": c["modificado"]} for c in categorias]
        arquivo = self._projeto.salvar_categorias(bacia, base, cats)
        self._projeto.registrar("conectou", bacia=bacia, categorias=len(cats))
        return {"bacia": bacia, "base": base, "categorias": cats,
                "salvo_em": os.path.relpath(arquivo, self._projeto.pasta)}

    @resposta_segura
    def listar_pocos(self, categoria: str):
        if self._cliente is None:
            raise ValueError("Conecte-se a uma bacia primeiro.")
        r = self._cliente.listar_pocos(self._base_remota + categoria, progresso=self._status)
        arquivo = self._projeto.salvar_pocos(self._bacia, categoria, r["pocos"],
                                             r["arquivos_soltos"], partes=r["partes"],
                                             duplicados=r["duplicados"])
        self._projeto.registrar("listou_categoria", bacia=self._bacia, categoria=categoria,
                                pocos=len(r["pocos"]), partes=len(r["partes"]))
        return {"categoria": categoria, **r,
                "salvo_em": os.path.relpath(arquivo, self._projeto.pasta)}

    @resposta_segura
    def explorar_poco(self, nome: str, caminho: str, categoria: str = "", parte: str | None = None):
        if self._cliente is None:
            raise ValueError("Conecte-se a uma bacia primeiro.")
        if not caminho.startswith(self._base_remota):
            raise ValueError(f"Caminho fora da bacia conectada: {caminho}")
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
        return {**mapa, "categoria": categoria, "parte": parte,
                "salvo_em": os.path.relpath(arquivo, self._projeto.pasta)}

    @resposta_segura
    def baixar(self, poco: str, arquivos: list):
        """Enfileira arquivos de um poço. Cada item: {caminho, nome, tamanho, pasta_relativa}."""
        if self._cliente_dl is None:
            raise ValueError("Conecte-se a uma bacia primeiro.")
        if not arquivos:
            raise ValueError("Nenhum arquivo selecionado.")
        tarefas = []
        for a in arquivos:
            if not str(a.get("caminho", "")).startswith(self._base_remota):
                raise ValueError(f"Caminho fora da bacia conectada: {a.get('caminho')}")
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
            evento["arquivo_local"] = os.path.relpath(evento["arquivo_local"], self._projeto.pasta)
        try:
            self._janela.evaluate_js(f"eventoDownload({json.dumps(evento)})")
        except Exception:
            pass   # janela fechada: o download continua/para sem quebrar nada

    # ---------------------------------------------------------- documentos
    def _exigir_projeto(self):
        if self._projeto is None:
            raise ValueError("Escolha primeiro a pasta do projeto (aba Catálogo, passo 1).")

    @resposta_segura
    def documentos(self):
        self._exigir_projeto()
        return {"documentos": self._projeto.listar_documentos(md.EXTENSOES),
                "idioma_ok": md.idioma_disponivel(PASTA_TESSDATA),
                "busca_fts": self._indice.fts}

    @resposta_segura
    def processar_documentos(self, rels: list):
        self._exigir_projeto()
        tarefas = []
        for rel in rels:
            caminho = self._projeto.caminho_seguro(rel)
            partes = os.path.relpath(caminho, self._projeto.pasta_bruto).split(os.sep)
            bacia, poco = (partes[0], partes[1]) if len(partes) > 2 else ("", "")
            nome = os.path.basename(caminho)

            def salvar(resultado, rel=rel, bacia=bacia, poco=poco, nome=nome):
                self._projeto.salvar_texto(rel, resultado)
                self._indice.substituir_documento(rel, bacia, poco, nome, resultado["paginas"],
                                                  corretor=self._corretor)

            tarefas.append({"doc": rel, "caminho": caminho, "nome": nome,
                            "bacia": bacia, "poco": poco, "salvar": salvar})
        n = self._fila_docs.adicionar(tarefas)
        self._projeto.registrar("pediu_processamento", documentos=len(tarefas))
        return {"enfileirados": n}

    @resposta_segura
    def cancelar_processamento(self):
        self._fila_docs.cancelar()
        return {}

    @resposta_segura
    def buscar_documentos(self, termo: str, tolerante: bool = True):
        self._exigir_projeto()
        r = self._indice.buscar(termo, tolerante=tolerante)
        return {"termo": termo, **r, "documentos": len({x["doc"] for x in r["resultados"]})}

    @resposta_segura
    def ver_pagina(self, rel: str, pagina: int, termo: str = ""):
        self._exigir_projeto()
        caminho = self._projeto.caminho_seguro(rel)
        texto = self._projeto.ler_texto(rel)
        if texto is None:
            raise ValueError("Documento ainda não processado.")
        pagina = max(1, min(int(pagina), texto["n_paginas"]))
        p = texto["paginas"][pagina - 1]
        variacoes = [v for e in self._indice.expandir(termo) for v in e["variacoes"]] if termo else []
        # destaque: casa com o que o OCR leu OU com a forma corrigida
        palavras = [[*w[:4], f"{w[4]} {self._corretor.corrigir(w[4])}"] for w in p["palavras"]]
        segmentos = self._corretor.segmentos(p["texto"])
        return {"rel": rel, "nome": os.path.basename(caminho), "pagina": pagina,
                "n_paginas": texto["n_paginas"], "metodo": p["metodo"],
                "titulo": self._indice.titulos(rel).get(pagina, ""),
                "segmentos": segmentos,
                "n_corrigidas": sum(isinstance(x, dict) for x in segmentos),
                "imagem": md.imagem_pagina(caminho, pagina, palavras, termo, variacoes=variacoes)}

    @resposta_segura
    def abrir_arquivo(self, rel: str):
        """Abre o arquivo no programa padrão do sistema (leitor de PDF etc.)."""
        self._exigir_projeto()
        caminho = self._projeto.caminho_seguro(rel)
        if sys.platform.startswith("win"):
            os.startfile(caminho)   # noqa: S606 — caminho validado dentro de bruto/
        elif sys.platform == "darwin":
            subprocess.Popen(["open", caminho])
        else:
            subprocess.Popen(["xdg-open", caminho])
        return {}

    # ---------------------------------------------------------- vocabulário
    def _carregar_corretor(self):
        self._vocab_projeto = mvoc.ler_projeto(self._projeto.caminho_vocabulario)
        self._corretor = mvoc.Corretor(mvoc.ler_base(CAMINHO_VOCAB_BASE), self._vocab_projeto)

    def _aplicar_vocabulario(self, evento: str, **detalhe) -> dict:
        """Salva o vocabulário do projeto e reaplica as correções em TODOS os
        documentos já processados (o OCR original não é refeito nem alterado)."""
        self._projeto.salvar_vocabulario(self._vocab_projeto)
        self._carregar_corretor()
        n = self._indice.reconstruir(self._projeto.documentos_processados(), self._corretor)
        self._projeto.registrar(evento, **detalhe)
        return {"paginas_atualizadas": n, **self._dicionario()}

    def _dicionario(self) -> dict:
        v = self._vocab_projeto
        return {"palavras": sorted(v["palavras"], key=str.lower),
                "correcoes": dict(sorted(v["correcoes"].items(), key=lambda kv: kv[0].lower())),
                "ignorar": sorted(v["ignorar"], key=str.lower)}

    @resposta_segura
    def dicionario(self):
        self._exigir_projeto()
        return self._dicionario()

    @resposta_segura
    def palavras_chave(self):
        """Atalhos de busca por categoria, com nº de páginas encontradas."""
        self._exigir_projeto()
        cats = []
        for nome, termos in self._corretor.palavras_chave().items():
            itens = [{"termo": t, "paginas": self._indice.contar(t)} for t in termos]
            cats.append({"categoria": nome, "termos": itens})
        return {"categorias": cats}

    @resposta_segura
    def adicionar_palavra(self, palavra: str):
        self._exigir_projeto()
        palavra = " ".join(str(palavra).split())
        if len(palavra) < 2:
            raise ValueError("Palavra muito curta.")
        lista = self._vocab_projeto["palavras"]
        if mvoc.normalizar(palavra) not in {mvoc.normalizar(x) for x in lista}:
            lista.append(palavra)
        return self._aplicar_vocabulario("adicionou_palavra", palavra=palavra)

    @resposta_segura
    def remover_palavra(self, palavra: str):
        self._exigir_projeto()
        self._vocab_projeto["palavras"] = [x for x in self._vocab_projeto["palavras"]
                                           if mvoc.normalizar(x) != mvoc.normalizar(palavra)]
        return self._aplicar_vocabulario("removeu_palavra", palavra=palavra)

    @resposta_segura
    def corrigir_palavra(self, de: str, para: str):
        """Correção explícita: vale para todos os documentos do projeto."""
        self._exigir_projeto()
        de, para = str(de).strip(), " ".join(str(para).split())
        if not de or not para:
            raise ValueError("Informe a palavra lida e a correção.")
        if de == para:
            raise ValueError("A correção é igual à palavra lida.")
        if not re.search(r"[A-Za-zÀ-ÿ]", de) or len(de) < 3:
            # "87"→"83" trocaria TODO 87 de TODAS as páginas. Números se corrigem
            # página a página, na transcrição assistida — nunca por regra global.
            raise ValueError("Números e palavras de 1–2 letras não podem ser corrigidos em todos "
                             "os documentos de uma vez: a troca atingiria valores certos em outras "
                             "páginas. Esses ficam para a transcrição assistida, página a página.")
        corr = self._vocab_projeto["correcoes"]
        for k in [k for k in corr if mvoc.normalizar(k) == mvoc.normalizar(de)]:
            del corr[k]
        corr[de] = para
        # quem corrige explicitamente também está dizendo que a regra automática não vale
        self._vocab_projeto["ignorar"] = [x for x in self._vocab_projeto["ignorar"]
                                          if mvoc.normalizar(x) != mvoc.normalizar(de)]
        return self._aplicar_vocabulario("corrigiu_palavra", de=de, para=para)

    @resposta_segura
    def remover_correcao(self, de: str):
        self._exigir_projeto()
        corr = self._vocab_projeto["correcoes"]
        for k in [k for k in corr if mvoc.normalizar(k) == mvoc.normalizar(de)]:
            del corr[k]
        return self._aplicar_vocabulario("removeu_correcao", de=de)

    @resposta_segura
    def manter_original(self, palavra: str):
        """Desfaz uma correção AUTOMÁTICA: o OCR estava certo."""
        self._exigir_projeto()
        lista = self._vocab_projeto["ignorar"]
        if mvoc.normalizar(palavra) not in {mvoc.normalizar(x) for x in lista}:
            lista.append(palavra)
        return self._aplicar_vocabulario("manteve_original", palavra=palavra)

    @resposta_segura
    def remover_ignorar(self, palavra: str):
        self._exigir_projeto()
        self._vocab_projeto["ignorar"] = [x for x in self._vocab_projeto["ignorar"]
                                          if mvoc.normalizar(x) != mvoc.normalizar(palavra)]
        return self._aplicar_vocabulario("voltou_a_corrigir", palavra=palavra)

    def _emitir_documento(self, evento: dict):
        try:
            self._janela.evaluate_js(f"eventoDocumento({json.dumps(evento)})")
        except Exception:
            pass

    def _status(self, texto: str):
        """Atualiza a barra de status da janela durante operações longas."""
        try:
            self._janela.evaluate_js(f"status({json.dumps(texto)}, 'trab')")
        except Exception:
            pass   # status é só cosmético; nunca interrompe o trabalho


def main():
    os.makedirs(PASTA_PROJETO, exist_ok=True)
    api = API()
    janela = webview.create_window(
        f"SIAPP {mp.VERSAO_SIAPP}",
        url=os.path.join(PASTA_APP, "ui", "index.html"),
        js_api=api,
        width=1180, height=800, min_size=(900, 600),
    )
    api._janela = janela
    # http_server=True serve a pasta ui/ por um servidor local interno, o que
    # garante que index.html carregue estilo.css e app.js em qualquer sistema.
    webview.start(http_server=True, debug="--debug" in sys.argv)


if __name__ == "__main__":
    main()
