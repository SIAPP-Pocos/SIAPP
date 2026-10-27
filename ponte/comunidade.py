"""Ponte: autoria, exportar/importar contribuições e base comunitária."""

from __future__ import annotations

import os
import re
import subprocess
import sys

import webview

from motor import comunidade as mc
from motor import projeto as mp

from .base import ErroUsuario, resposta_segura

PASTA_CONTRIBUICOES = "contribuicoes"   # pacotes exportados por este computador
PASTA_COMUNIDADE = "comunidade"         # base comunitária baixada
_RE_ORCID = re.compile(r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$")


class ComunidadeAPI:
    # ----------------------------------------------------------------- autor
    @resposta_segura
    def definir_autor(self, nome: str, instituicao: str = "", orcid: str = ""):
        self._exigir_projeto()
        nome, instituicao, orcid = (" ".join(str(x or "").split()) for x in (nome, instituicao, orcid))
        if len(nome) < 3:
            raise ErroUsuario("Informe seu nome completo: ele assina as suas contribuições.")
        if orcid and not _RE_ORCID.match(orcid):
            raise ErroUsuario("ORCID no formato 0000-0000-0000-0000 (ou deixe em branco).")
        autor = {"nome": nome, "instituicao": instituicao, "orcid": orcid}
        self._projeto.definir_config(autor=autor)
        return {"autor": autor}

    # --------------------------------------------------------------- resumo
    @resposta_segura
    def comunidade(self):
        self._exigir_projeto()
        b = self._banco
        local = b.vocab_local()
        bases = b.pacotes("base")
        return {
            "autor": self._projeto.config.get("autor") or {},
            "local": {"correcoes": len(local["correcoes"]), "palavras": len(local["palavras"]),
                      "manter_original": len(local["ignorar"]),
                      "fatos": b.contar("fatos", "WHERE origem = 'local'"),
                      "fatos_nao_exportados": b.contar(
                          "fatos", "WHERE origem = 'local' AND exportado_em IS NULL")},
            "ultima_exportacao": b.meta("ultima_exportacao"),
            "exportados": b.pacotes("exportado")[:10],
            "importados": b.pacotes("importado"),
            "base": bases[0] if bases else None,
            "pasta_contribuicoes": os.path.join(mp.NOME_PASTA_PADRAO, PASTA_CONTRIBUICOES),
        }

    # -------------------------------------------------------------- exportar
    @resposta_segura
    def exportar_contribuicao(self, apenas_novos: bool = True):
        self._exigir_projeto()
        pacote = mc.montar_pacote(self._banco, self._projeto.config.get("autor") or {},
                                  mp.VERSAO_SIAPP, apenas_novos=bool(apenas_novos))
        if mc.pacote_vazio(pacote):
            raise ErroUsuario("Nada novo para exportar desde a última vez." if apenas_novos
                              else "Ainda não há correções nem fatos feitos neste computador.")
        caminho = mc.gravar_pacote(self._banco, pacote, self._projeto.pasta_de(PASTA_CONTRIBUICOES))
        self._projeto.registrar("exportou_contribuicao", pacote=pacote["id"],
                                arquivo=os.path.basename(caminho), **mc.contar_itens(pacote))
        return {"arquivo": self._projeto.rel(caminho), "itens": mc.contar_itens(pacote)}

    @resposta_segura
    def abrir_pasta_contribuicoes(self):
        self._exigir_projeto()
        _abrir_no_sistema(self._projeto.pasta_de(PASTA_CONTRIBUICOES))
        return {}

    # -------------------------------------------------------------- importar
    def _escolher_arquivo(self, tipos: tuple) -> str | None:
        escolha = self._janela.create_file_dialog(webview.FileDialog.OPEN,
                                                  directory=self._projeto.pasta,
                                                  file_types=tipos)
        if not escolha:
            return None
        return escolha[0] if isinstance(escolha, (list, tuple)) else escolha

    @resposta_segura
    def escolher_contribuicao(self):
        """Abre o diálogo e devolve a PRÉVIA da importação (nada é gravado)."""
        self._exigir_projeto()
        caminho = self._escolher_arquivo(("Contribuição SIAPP (*.json)", "Todos os arquivos (*.*)"))
        if not caminho:
            return {"cancelado": True}
        pacote = mc.ler_pacote(caminho)
        self._pacote_em_previa = (caminho, pacote)
        return {"arquivo": os.path.basename(caminho), "previa": mc.previa(self._banco, pacote)}

    @resposta_segura
    def confirmar_importacao(self, id_pacote: str):
        self._exigir_projeto()
        caminho, pacote = getattr(self, "_pacote_em_previa", (None, None))
        if not pacote or pacote["id"] != id_pacote:
            raise ErroUsuario("Escolha o arquivo de novo: a prévia expirou.")
        resumo = mc.importar(self._banco, pacote, os.path.basename(caminho))
        self._pacote_em_previa = (None, None)
        self._projeto.registrar("importou_contribuicao", pacote=pacote["id"],
                                autor=pacote["autor"].get("nome", ""), **resumo)
        return {"resumo": resumo, **self._aplicar_vocabulario_silencioso()}

    @resposta_segura
    def desfazer_pacote(self, id_pacote: str):
        self._exigir_projeto()
        n = self._banco.desfazer_pacote(id_pacote)
        self._projeto.registrar("desfez_pacote", pacote=id_pacote, **n)
        return {"removidos": n, **self._aplicar_vocabulario_silencioso()}

    # ----------------------------------------------------------------- base
    @resposta_segura
    def atualizar_base(self):
        """Baixa a base mais recente do SIAPP-dados (GitHub Releases) e aplica."""
        self._exigir_projeto()
        destino = os.path.join(self._projeto.pasta_de(PASTA_COMUNIDADE), mc.NOME_ARQUIVO_BASE)
        self._status("Baixando a base comunitária…")
        info = mc.baixar_base(destino)
        return self._aplicar_base(destino, info)

    @resposta_segura
    def importar_base_arquivo(self):
        self._exigir_projeto()
        caminho = self._escolher_arquivo(("Base SIAPP-dados (*.sqlite)", "Todos os arquivos (*.*)"))
        if not caminho:
            return {"cancelado": True}
        return self._aplicar_base(caminho, {})

    def _aplicar_base(self, caminho: str, info: dict) -> dict:
        resumo = mc.aplicar_base(self._banco, caminho)
        self._projeto.registrar("aplicou_base", **resumo)
        return {"resumo": {**resumo, **info}, **self._aplicar_vocabulario_silencioso()}

    def _aplicar_vocabulario_silencioso(self) -> dict:
        """Depois de mudar o que veio da comunidade: recarrega o corretor e o índice."""
        self._carregar_corretor()
        n = self._reindexar_tudo()
        return {"paginas_atualizadas": n}


def _abrir_no_sistema(caminho: str):
    if sys.platform.startswith("win"):
        os.startfile(caminho)   # noqa: S606 — pasta dentro do projeto
    elif sys.platform == "darwin":
        subprocess.Popen(["open", caminho])
    else:
        subprocess.Popen(["xdg-open", caminho])
