"""Ponte: documentos (texto/OCR), busca e visualização de página."""

from __future__ import annotations

import os
import subprocess
import sys

from motor import documentos as md
from motor import formatos
from motor import projeto as mp

from .base import PASTA_TESSDATA, ErroUsuario, resposta_segura


class DocumentosAPI:
    _indice = None

    def _bacia_poco_de(self, rel: str) -> tuple[str, str]:
        return self._projeto.bacia_poco_de(rel)

    def _exigir_documento(self, rel: str, caminho: str):
        if not os.path.isfile(caminho):
            raise ErroUsuario(f"Arquivo não encontrado: {rel}")
        if mp.tipo_arquivo(caminho) == "perfil":
            raise ErroUsuario(f"{os.path.basename(caminho)} tem nome de imagem, mas o conteúdo é um perfil "
                              f"({formatos.formato(caminho).upper()}). Abra na aba Perfis.")

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
        for rel in map(mp.rel_padrao, rels):
            caminho = self._projeto.caminho_seguro(rel)
            bacia, poco = self._bacia_poco_de(rel)
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
        """Imagem da página e, se o documento já foi processado, o texto com as
        correções. Documento ainda não processado também abre: só a imagem."""
        self._exigir_projeto()
        rel = mp.rel_padrao(rel)
        caminho = self._projeto.caminho_seguro(rel)
        self._exigir_documento(rel, caminho)
        texto = self._projeto.ler_texto(rel)
        total = texto["n_paginas"] if texto else md.n_paginas(caminho)
        pagina = max(1, min(int(pagina), total))
        bacia, poco = self._bacia_poco_de(rel)
        base = {"rel": rel, "nome": os.path.basename(caminho), "pagina": pagina,
                "n_paginas": total, "bacia": bacia, "poco": poco, "processado": texto is not None,
                "poco_id": self._id_poco(poco) if poco else "",
                "fatos": self._banco.fatos(fonte_rel=rel, pagina=pagina)}
        if texto is None:
            return {**base, "metodo": "imagem", "titulo": "", "segmentos": [], "palavras": [],
                    "n_corrigidas": 0, "imagem": md.imagem_pagina(caminho, pagina, [])}
        p = texto["paginas"][pagina - 1]
        variacoes = [v for e in self._indice.expandir(termo) for v in e["variacoes"]] if termo else []
        # destaque: casa com o que o OCR leu OU com a forma corrigida
        palavras = [[*w[:4], f"{w[4]} {self._corretor.corrigir(w[4])}"] for w in p["palavras"]]
        segmentos = self._corretor.segmentos(p["texto"])
        return {**base, "metodo": p["metodo"],
                "titulo": self._indice.titulos(rel).get(pagina, ""),
                "segmentos": segmentos,
                "palavras": p["palavras"],
                "n_corrigidas": sum(isinstance(x, dict) for x in segmentos),
                "imagem": md.imagem_pagina(caminho, pagina, palavras, termo, variacoes=variacoes)}

    @resposta_segura
    def visor_pagina(self, rel: str, pagina: int):
        """Medidas da página no visor ampliado (as faixas vêm por visor_faixa)."""
        self._exigir_projeto()
        rel = mp.rel_padrao(rel)
        caminho = self._projeto.caminho_seguro(rel)
        self._exigir_documento(rel, caminho)
        return {"rel": rel, "nome": os.path.basename(caminho), "pagina": int(pagina),
                **md.visor_info(caminho, int(pagina))}

    @resposta_segura
    def visor_faixa(self, rel: str, pagina: int, indice: int):
        self._exigir_projeto()
        caminho = self._projeto.caminho_seguro(mp.rel_padrao(rel))
        return {"indice": int(indice), "imagem": md.visor_faixa(caminho, int(pagina), int(indice))}

    @resposta_segura
    def abrir_arquivo(self, rel: str):
        """Abre o arquivo no programa padrão do sistema (leitor de PDF etc.)."""
        self._exigir_projeto()
        caminho = self._projeto.caminho_seguro(mp.rel_padrao(rel))
        if not os.path.isfile(caminho):
            raise ErroUsuario(f"Arquivo não encontrado: {rel}")
        if sys.platform.startswith("win"):
            os.startfile(caminho)   # noqa: S606 — caminho validado dentro de bruto/
        elif sys.platform == "darwin":
            subprocess.Popen(["open", caminho])
        else:
            subprocess.Popen(["xdg-open", caminho])
        return {}

    def _emitir_documento(self, evento: dict):
        self._js("eventoDocumento", evento)
