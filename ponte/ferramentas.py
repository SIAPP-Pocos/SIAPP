"""Ponte: esquemas de ferramentas (o que é cada arquivo de perfil do poço)."""

from __future__ import annotations

import os

from motor import documentos as md
from motor import ferramentas as mf
from motor import reate

from .base import PASTA_RECURSOS, PASTA_TESSDATA, ErroUsuario, resposta_segura
from .comunidade import _abrir_no_sistema

CAMINHO_FERRAMENTAS = os.path.join(PASTA_RECURSOS, "ferramentas.json")


class FerramentasAPI:
    _dic_ferramentas = None

    def _dic(self) -> dict:
        if self._dic_ferramentas is None:
            self._dic_ferramentas = mf.ler_dicionario(CAMINHO_FERRAMENTAS)
        return self._dic_ferramentas

    def _esquemas(self, poco_id: str) -> dict:
        """Esquemas do poço e rótulo de cada arquivo de perfil (para a ficha e a aba Perfis)."""
        return mf.do_poco(self._banco, poco_id, self._dic())

    def _corrida_do_arquivo(self, poco_id: str, nome: str, cache: dict | None = None) -> dict | None:
        if not poco_id:
            return None
        if cache is not None:
            if poco_id not in cache:
                cache[poco_id] = self._esquemas(poco_id)["perfis"]
            perfis = cache[poco_id]
        else:
            perfis = self._esquemas(poco_id)["perfis"]
        return perfis.get(nome)

    def _garantir_ocr_ingles(self) -> bool:
        """Baixa o modelo de OCR em inglês (~4 MB, uma vez). Sem internet, segue
        sem OCR: os esquemas com texto embutido ainda são lidos."""
        if mf.idioma_disponivel(PASTA_TESSDATA):
            return True
        self._status("Baixando o modelo de OCR em inglês (uma vez só, ~4 MB)…")
        try:
            md.baixar_idioma(PASTA_TESSDATA, idioma=mf.IDIOMA_OCR, modelos=mf.MODELOS_OCR)
        except md.ErroDocumento:
            return False
        return mf.idioma_disponivel(PASTA_TESSDATA)

    @resposta_segura
    def ler_esquemas_poco(self, poco: str):
        """Baixa e lê os esquemas de ferramentas do poço (só os ainda não lidos)."""
        self._exigir_projeto()
        pid = self._id_poco(poco)
        with self._banco.conexao() as c:
            bacias = [r[0] for r in c.execute(
                "SELECT DISTINCT bacia FROM acervo_pocos WHERE poco_id = ?", (pid,))]
        itens = [(b, it) for b in bacias for it in mf.pendentes(self._banco, b, poco_id=pid)]
        if not bacias:
            raise ErroUsuario(f"{pid} ainda não está no levantamento do acervo (aba Mapa → Levantamento).")
        ocr = self._garantir_ocr_ingles() if itens else True
        lidos = 0
        for bacia in bacias:
            fila = [it for b, it in itens if b == bacia]
            if not fila:
                continue
            lidos += mf.ler_do_portal(
                self._banco, reate.ClienteREATE.da_bacia(bacia), bacia, fila, self._dic(),
                pasta_projeto=self._projeto.pasta, tessdata=PASTA_TESSDATA if ocr else None,
                progresso=lambda k, n, nome: self._status(f"Lendo o esquema {k} de {n}: {nome}"))
        self._projeto.registrar("leu_esquemas", poco=pid, esquemas=lidos, ocr=ocr)
        return {"poco": pid, "lidos": lidos, "ocr": ocr, **self._esquemas(pid)}

    @resposta_segura
    def abrir_esquema(self, caminho: str):
        """Abre a cópia local de um esquema (ambiente_teste/esquemas/…)."""
        self._exigir_projeto()
        pasta = os.path.realpath(os.path.join(self._projeto.pasta, "esquemas"))
        alvo = os.path.realpath(os.path.join(self._projeto.pasta, caminho))
        if os.path.commonpath([alvo, pasta]) != pasta or not os.path.isfile(alvo):
            raise ErroUsuario("Esquema não encontrado na pasta do projeto.")
        _abrir_no_sistema(alvo)
        return {}
