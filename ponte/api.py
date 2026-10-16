"""
A API exposta à janela: `window.pywebview.api.<função>()` no JavaScript.

Cada área fica num módulo próprio (catalogo, documentos, vocabulario…) e a
classe API apenas junta as partes. Atributos com "_" não são expostos.
"""

from __future__ import annotations

import os

import webview

from motor import banco as mb
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
        self._banco = mb.Banco(self._projeto.caminho_banco)
        n = self._banco.migrar_vocab_json(self._projeto.caminho_vocabulario)
        if n:
            registro.log.info("vocabulário do SIAPP 0.6 migrado para o banco: %d itens", n)
        self._migrar_downloads()
        self._indice = md.Indice(os.path.join(self._projeto.pasta, "texto", "indice.sqlite"))
        self._carregar_corretor()
        if self._indice.recriado:   # estrutura do índice mudou de versão: refaz a partir dos textos
            self._indice.reconstruir(self._projeto.documentos_processados(), self._corretor)
        cfg = self._projeto.config
        return {"pasta": self._projeto.pasta, "bacia_anterior": cfg.get("bacia"),
                "criado": cfg.get("criado"), "autor": cfg.get("autor") or {}}

    # ------------------------------------------------------ arquivos baixados
    def _id_poco(self, nome_pasta: str) -> str:
        """Id do poço no banco a partir do nome da pasta no REATE."""
        return nome_pasta

    def _registrar_arquivo_local(self, caminho: str, *, bacia: str, poco: str,
                                 caminho_remoto: str = "", baixado_em: str | None = None):
        rel = self._projeto.rel(caminho)
        self._banco.registrar_arquivo(
            rel, bacia=bacia, poco_id=self._id_poco(poco), caminho_remoto=caminho_remoto,
            bytes_=os.path.getsize(caminho), sha256=mp.sha256_arquivo(caminho),
            tipo=mp.tipo_arquivo(caminho), baixado_em=baixado_em)

    def _ao_terminar_download(self, evento: dict):
        try:
            self._registrar_arquivo_local(evento["arquivo_local"], bacia=evento.get("bacia", ""),
                                          poco=evento.get("poco", ""),
                                          caminho_remoto=evento.get("caminho", ""))
        except OSError:
            registro.log.exception("não consegui registrar %s", evento.get("arquivo_local"))

    def _migrar_downloads(self):
        """Arquivos baixados antes do banco existir (ou copiados à mão para
        bruto/) entram na tabela arquivos, com hash. Roda a cada abertura, mas só
        calcula o hash do que ainda não está no banco."""
        conhecidos = {a["rel"] for a in self._banco.arquivos()}
        origem = {mp.rel_padrao(v["arquivo_local"]): v
                  for v in self._projeto.registro_downloads().values()}
        for raiz, _, nomes in os.walk(self._projeto.pasta_bruto):
            for nome in nomes:
                if nome.endswith((".part", ".tmp")) or nome == "registro_downloads.json":
                    continue
                caminho = os.path.join(raiz, nome)
                rel = self._projeto.rel(caminho)
                if rel in conhecidos:
                    continue
                bacia, poco = self._projeto.bacia_poco_de(rel)
                info = origem.get(rel, {})
                try:
                    self._registrar_arquivo_local(caminho, bacia=bacia, poco=poco,
                                                  caminho_remoto=info.get("caminho_remoto", ""),
                                                  baixado_em=info.get("baixado_em"))
                except OSError:
                    registro.log.exception("não consegui registrar %s", rel)
