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
from motor import reate, registro
from motor.downloads import FilaDownloads

from . import base
from .base import BaseAPI, ErroUsuario, mesma_pasta, resposta_segura
from .bloco import BlocoAPI
from .catalogo import CatalogoAPI
from .comunidade import ComunidadeAPI
from .documentos import DocumentosAPI
from .externos import ExternosAPI
from .fatos import FatosAPI
from .ferramentas import FerramentasAPI
from .janelas import JanelasAPI
from .levantamento import LevantamentoAPI
from .perfis import PerfisAPI
from .pocos import PocosAPI
from .secao import SecaoAPI
from .vocabulario import VocabularioAPI


class API(BaseAPI, JanelasAPI, PocosAPI, CatalogoAPI, DocumentosAPI, VocabularioAPI, ComunidadeAPI,
          FatosAPI, PerfisAPI, LevantamentoAPI, SecaoAPI, FerramentasAPI,
          BlocoAPI, ExternosAPI):
    def __init__(self):
        self._janela = None
        self._janelas = {}            # abas destacadas em janela própria: {aba: janela}
        self._salvar_depois = {}
        self._prefs = None
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
        # cada passo avisa a janela (tela "Abrindo o projeto", com o que falta)
        passos = 5
        self._progresso_abertura(1, passos, f"Abrindo a pasta {os.path.basename(pasta)}")
        self._projeto = mp.Projeto.abrir_ou_criar(pasta)
        registro.configurar(self._projeto.pasta)
        registro.log.info("projeto aberto: %s (SIAPP %s)", self._projeto.pasta, mp.VERSAO_SIAPP)
        tam = os.path.getsize(self._projeto.caminho_banco) if os.path.isfile(self._projeto.caminho_banco) else 0
        self._progresso_abertura(2, passos, "Lendo o banco do projeto" + (f" ({tam / 1e6:.0f} MB)" if tam > 2e6 else ""))
        self._banco = mb.Banco(self._projeto.caminho_banco)
        n = self._banco.migrar_vocab_json(self._projeto.caminho_vocabulario)
        if n:
            registro.log.info("vocabulário do SIAPP 0.6 migrado para o banco: %d itens", n)
        self._progresso_abertura(3, passos, "Conferindo os arquivos baixados (só os novos ganham hash)")
        self._migrar_downloads()
        self._progresso_abertura(4, passos, "Conferindo o catálogo do REATE")
        self._migrar_pocos()
        self._progresso_abertura(5, passos, "Carregando o índice de texto dos documentos")
        self._indice = md.Indice(os.path.join(self._projeto.pasta, "texto", "indice.sqlite"))
        self._carregar_corretor()
        if self._indice.recriado:   # estrutura do índice mudou de versão: refaz a partir dos textos
            self._progresso_abertura(5, passos, "Refazendo o índice de texto (estrutura nova)")
            self._indice.reconstruir(self._projeto.documentos_processados(), self._corretor)
        self._js("projetoAbertoEmOutraJanela", {"pasta": self._projeto.pasta})
        cfg = self._projeto.config
        return {"pasta": self._projeto.pasta, "bacia_anterior": cfg.get("bacia"),
                "criado": cfg.get("criado"), "autor": cfg.get("autor") or {}}

    @resposta_segura
    def panorama(self):
        """Números do projeto para a tela inicial."""
        self._exigir_projeto()
        b = self._banco
        arqs = b.arquivos()
        resumo = self._projeto.resumo_texto()
        return {
            "arquivos": {"total": len(arqs), "bytes": sum(a["bytes"] or 0 for a in arqs),
                         "por_tipo": {t: sum(1 for a in arqs if a["tipo"] == t)
                                      for t in ("documento", "perfil", "outro")}},
            "documentos": {"processados": len(resumo),
                           "paginas": sum(v.get("n_paginas", 0) for v in resumo.values())},
            "vocabulario": b.contar("vocab"),
            "fatos": b.contar("fatos"),
            "pocos": b.contar("pocos"),
            "curvas": b.contar("curvas"),
        }

    # ------------------------------------------------------ arquivos baixados
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
        conhecidos = {}
        for a in self._banco.arquivos():
            conhecidos[a["rel"]] = a
            caminho = os.path.join(self._projeto.pasta, a["rel"])
            # o tipo passou a vir do conteúdo (0.11.1): DLIS com extensão .tif vira perfil
            if os.path.isfile(caminho) and (t := mp.tipo_arquivo(caminho)) != a["tipo"]:
                self._banco.definir_tipo(a["rel"], t)
                registro.log.info("tipo de %s corrigido pelo conteúdo: %s -> %s", a["rel"], a["tipo"], t)
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
