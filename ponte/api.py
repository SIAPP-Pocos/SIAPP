"""
A API exposta à janela: `window.pywebview.api.<função>()` no JavaScript.

Cada área fica num módulo próprio (catalogo, documentos, vocabulario…) e a
classe API apenas junta as partes. Atributos com "_" não são expostos.
"""

from __future__ import annotations

import os

import webview

from motor import documentos as md
from motor import projeto as mp
from motor import reate
from motor import registro
from motor.downloads import FilaDownloads

from . import base
from .base import BaseAPI, ErroUsuario, mesma_pasta, resposta_segura
from .catalogo import CatalogoAPI
from .documentos import DocumentosAPI
from .vocabulario import VocabularioAPI


class API(BaseAPI, CatalogoAPI, DocumentosAPI, VocabularioAPI):
    def __init__(self):
        self._janela = None
        self._projeto = None
        self._fila = FilaDownloads(self._emitir_download)
        self._fila_docs = md.FilaDocumentos(base.PASTA_TESSDATA, self._emitir_documento)

    @resposta_segura
    def info(self):
        return {"versao": mp.VERSAO_SIAPP, "bacias": sorted(reate.BACIAS),
                "nome_pasta_projeto": base.NOME_PASTA_PROJETO,
                "pasta_projeto": base.PASTA_PROJETO}

    @resposta_segura
    def escolher_pasta(self):
        pasta_projeto = base.PASTA_PROJETO
        os.makedirs(pasta_projeto, exist_ok=True)
        escolha = self._janela.create_file_dialog(webview.FileDialog.FOLDER,
                                                  directory=pasta_projeto)
        if not escolha:
            return {"cancelado": True}
        pasta = escolha[0] if isinstance(escolha, (list, tuple)) else escolha
        if not mesma_pasta(pasta, pasta_projeto):
            raise ErroUsuario(
                f"Pasta recusada: {pasta}. Por enquanto o projeto precisa ficar "
                f"exatamente na pasta '{base.NOME_PASTA_PROJETO}', ao lado do aplicativo. "
                f"Com o diálogo aberto nela, clique direto em 'Selecionar pasta' "
                f"sem entrar em nenhuma subpasta.")
        return self._abrir_projeto(pasta_projeto)

    def _abrir_projeto(self, pasta: str) -> dict:
        self._projeto = mp.Projeto.abrir_ou_criar(pasta)
        registro.configurar(self._projeto.pasta)
        registro.log.info("projeto aberto: %s (SIAPP %s)", self._projeto.pasta, mp.VERSAO_SIAPP)
        self._indice = md.Indice(os.path.join(self._projeto.pasta, "texto", "indice.sqlite"))
        self._carregar_corretor()
        if self._indice.recriado:   # estrutura do índice mudou de versão: refaz a partir dos textos
            self._indice.reconstruir(self._projeto.documentos_processados(), self._corretor)
        cfg = self._projeto.config
        return {"pasta": self._projeto.pasta, "bacia_anterior": cfg.get("bacia"),
                "criado": cfg.get("criado")}
