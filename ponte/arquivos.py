"""Ponte: Dados › Arquivos baixados (lista, abrir, mostrar na pasta, apagar para a Lixeira)."""

from __future__ import annotations

import os
import subprocess
import sys

from motor import arquivos_baixados as mab

from .base import ErroUsuario, resposta_segura
from .comunidade import _abrir_no_sistema


class ArquivosAPI:
    def _arquivo_do_projeto(self, rel: str) -> str:
        self._exigir_projeto()
        try:
            caminho = self._projeto.caminho_seguro(str(rel or ""))
        except ValueError as e:
            raise ErroUsuario("Este arquivo não está na pasta de downloads do projeto.") from e
        return caminho

    @resposta_segura
    def arquivos_baixados(self):
        """Tudo o que está em bruto/, com tipo, formato, tamanho, data e o que o SIAPP fez com cada arquivo."""
        self._exigir_projeto()
        return mab.listar(self._projeto, self._banco)

    @resposta_segura
    def abrir_arquivo_baixado(self, rel: str):
        """Abre o arquivo no programa padrão do Windows. Programas e scripts não abrem por aqui."""
        caminho = self._arquivo_do_projeto(rel)
        if not os.path.isfile(caminho):
            raise ErroUsuario("O arquivo não está mais no disco (apagado ou movido).")
        if not mab.pode_abrir(caminho):
            raise ErroUsuario("Por segurança o SIAPP não abre programas nem scripts. Use \u201cMostrar na pasta\u201d.")
        _abrir_no_sistema(caminho)
        self._projeto.registrar("abriu_arquivo_baixado", rel=self._projeto.rel(caminho))
        return {}

    @resposta_segura
    def mostrar_arquivo_na_pasta(self, rel: str):
        """Abre o Explorer com o arquivo selecionado (fora do Windows, abre a pasta)."""
        caminho = self._arquivo_do_projeto(rel)
        alvo = caminho if os.path.exists(caminho) else os.path.dirname(caminho)
        if not os.path.exists(alvo):
            raise ErroUsuario("A pasta do arquivo não existe mais.")
        if sys.platform == "win32" and os.path.isfile(alvo):
            subprocess.Popen(f'explorer /select,"{alvo}"')              # noqa: S603 — caminho dentro do projeto
        else:
            _abrir_no_sistema(alvo if os.path.isdir(alvo) else os.path.dirname(alvo))
        return {}

    @resposta_segura
    def impacto_apagar_arquivo(self, rel: str):
        """O que sai do banco e o que fica (trabalho seu) se o arquivo for apagado."""
        caminho = self._arquivo_do_projeto(rel)
        return {"rel": self._projeto.rel(caminho), "nome": os.path.basename(caminho),
                "bytes": os.path.getsize(caminho) if os.path.isfile(caminho) else 0,
                **mab.impacto(self._projeto, self._banco, self._projeto.rel(caminho))}

    @resposta_segura
    def apagar_arquivo_baixado(self, rel: str):
        """Manda o arquivo para a Lixeira e limpa o que o SIAPP derivou dele. Transcrições e correções suas ficam."""
        caminho = self._arquivo_do_projeto(rel)
        try:
            r = mab.apagar(self._projeto, self._banco, self._projeto.rel(caminho), self._indice)
        except ValueError as e:
            raise ErroUsuario(str(e)) from e
        except OSError as e:
            raise ErroUsuario(f"Não consegui apagar: {e}") from e
        self._corpus_cache = None
        self._projeto.registrar("apagou_arquivo_baixado", rel=r["rel"], destino=r["destino"])
        return r
