"""Ponte: documentos (texto/OCR), busca e visualização de página."""

from __future__ import annotations

import os
import subprocess
import sys

from motor import dicionario as mdic
from motor import documentos as md
from motor import formatos
from motor import layout as ml
from motor import projeto as mp
from motor import vocabulario as mvoc

from .base import PASTA_TESSDATA, ErroUsuario, resposta_segura


class DocumentosAPI:
    _indice = None
    _conhecida_cache = None
    _corpus_cache = None

    # ------------------------------------------------ texto final da página
    # Ordem: texto revisado à mão (banco) > texto remontado das caixas do OCR (motor/layout)
    # > texto como o OCR devolveu. O índice de busca e a página usam o mesmo texto final;
    # a coluna "original" do índice continua com o que o OCR leu, para a busca achar as duas.
    def _conhecida(self):
        """Palavras conhecidas para juntar peças partidas: dicionário de português +
        vocabulário técnico + palavras do projeto. Não usa o acervo, para que o texto
        de um documento não mude quando outro é processado."""
        if self._conhecida_cache is None:
            c = self._corretor
            termos = list(c.vocab.values()) + list(c.projeto.get("palavras", [])) if c else []
            k = ml.conhecida_por(termos)
            dic = mdic.padrao()
            self._conhecida_cache = lambda w: k(w) or dic.conhece(w)
        return self._conhecida_cache

    def _vocab_corpus(self):
        """Palavras que o próprio acervo repete (5+ letras, 3+ vezes): não entram como
        possível erro. Calculado uma vez por abertura do projeto (e depois de processar)."""
        if self._corpus_cache is None:
            self._corpus_cache = ml.conhecida_por(ml.vocabulario_do_corpus(
                p["texto"] for *_, pags in self._projeto.documentos_processados() for p in pags))
        return self._corpus_cache

    def _esquecer_vocabulario(self):
        self._conhecida_cache = None
        self._corpus_cache = None

    def _remontado(self, p: dict) -> str:
        if not p.get("palavras"):
            return p["texto"]
        return ml.reconstruir(p["palavras"], self._conhecida()) or p["texto"]

    def _com_texto_final(self, rel: str, paginas: list, revisoes: dict | None = None) -> list:
        rev = self._banco.revisoes(rel) if revisoes is None else revisoes
        return [{**p, "final": rev[p["pagina"]]["texto"] if p["pagina"] in rev else self._remontado(p)}
                for p in paginas]

    def _docs_para_indice(self):
        todas = self._banco.revisoes()
        for rel, bacia, poco, nome, paginas in self._projeto.documentos_processados():
            yield rel, bacia, poco, nome, self._com_texto_final(rel, paginas, todas.get(rel, {}))

    def _reindexar_tudo(self) -> int:
        self._esquecer_vocabulario()
        return self._indice.reconstruir(self._docs_para_indice(), self._corretor)

    def _reindexar_documento(self, rel: str):
        texto = self._projeto.ler_texto(rel)
        if not texto:
            return
        bacia, poco = self._bacia_poco_de(rel)
        caminho = self._projeto.caminho_seguro(rel)
        self._indice.substituir_documento(rel, bacia, poco, os.path.basename(caminho),
                                          self._com_texto_final(rel, texto["paginas"]),
                                          corretor=self._corretor)

    def _bacia_poco_de(self, rel: str) -> tuple[str, str]:
        return self._projeto.bacia_poco_de(rel)

    def _exigir_documento(self, rel: str, caminho: str):
        if not os.path.isfile(caminho):
            raise ErroUsuario(f"Arquivo não encontrado: {rel}")
        if mp.tipo_arquivo(caminho) == "perfil":
            raise ErroUsuario(f"{os.path.basename(caminho)} tem nome de imagem, mas o conteúdo é um perfil "
                              f"({formatos.formato(caminho).upper()}). Abra na aba Perfis.")

    def _campos_dos_pocos(self, nomes) -> dict:
        """{nome da pasta do poço: campo} pelo cadastro da ANP (vazio se não estiver lá)."""
        ids = {n: self._id_poco(n) for n in nomes if n}
        if not ids:
            return {}
        with self._banco.conexao() as c:
            q = ",".join("?" * len(ids))
            campos = {r[0]: r[1] for r in c.execute(
                f"SELECT id, campo FROM pocos WHERE id IN ({q})", list(set(ids.values())))}
        return {n: (campos.get(i) or "") for n, i in ids.items()}

    @resposta_segura
    def documentos(self):
        self._exigir_projeto()
        docs = self._projeto.listar_documentos(md.EXTENSOES)
        campos = self._campos_dos_pocos({d["poco"] for d in docs})
        revisadas = {}
        for rel, pags in self._banco.revisoes().items():
            revisadas[rel] = len(pags)
        for d in docs:
            d["campo"] = campos.get(d["poco"], "")
            d["revisadas"] = revisadas.get(d["rel"], 0)
        return {"documentos": docs,
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
                self._corpus_cache = None
                self._indice.substituir_documento(rel, bacia, poco, nome,
                                                  self._com_texto_final(rel, resultado["paginas"]),
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
    def buscar_documentos(self, termo: str, tolerante: bool = True, docs: list | None = None):
        """`docs`: só nestes documentos (lista de rel) — o filtro da lista (bacia, campo,
        poço, pasta) ou só o documento aberto. None = em todos."""
        self._exigir_projeto()
        filtro = [mp.rel_padrao(d) for d in docs] if docs is not None else None
        r = self._indice.buscar(termo, tolerante=tolerante, docs=filtro)
        return {"termo": termo, **r, "documentos": len({x["doc"] for x in r["resultados"]}),
                "escopo": None if filtro is None else len(filtro)}

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
        revisao = self._banco.revisoes(rel).get(pagina)
        remontado = self._remontado(p)
        final = revisao["texto"] if revisao else remontado
        segmentos = self._corretor.segmentos(final)
        corrigido = "".join(x if isinstance(x, str) else x["t"] for x in segmentos)
        # palavras trocadas pelo corretor: contornadas na imagem com a cor da origem
        corrigidas = []
        for w in p["palavras"]:
            tipo = next((x["tipo"] for x in self._corretor.segmentos(w[4]) if isinstance(x, dict)), None)
            if tipo:
                corrigidas.append([*w[:4], tipo])
        corretor = self._corretor
        conhecida, corpus = self._conhecida(), self._vocab_corpus()
        erros = mdic.possiveis_erros(
            corrigido, lambda w: conhecida(w) or corpus(w), mdic.padrao(),
            ignorar=lambda w: mvoc.normalizar(w) in corretor.ignorar)
        return {**base, "metodo": p["metodo"],
                "titulo": self._indice.titulos(rel).get(pagina, ""),
                "segmentos": segmentos,
                "texto_ocr": p["texto"],
                "texto_editavel": corrigido,
                "modo_texto": "revisado" if revisao else ("remontado" if remontado != p["texto"] else "ocr"),
                "revisao": {"autor": revisao.get("autor") or "", "criado_em": revisao["criado_em"]}
                           if revisao else None,
                "possiveis_erros": erros,
                "legibilidade": mdic.legibilidade(corrigido, lambda w: conhecida(w) or corpus(w)),
                "palavras": p["palavras"],
                "n_corrigidas": sum(isinstance(x, dict) for x in segmentos),
                "n_corrigidas_imagem": len(corrigidas),
                "imagem": md.imagem_pagina(caminho, pagina, palavras, termo, variacoes=variacoes,
                                           corrigidas=corrigidas)}

    @resposta_segura
    def texto_caixa(self, rel: str, pagina: int, caixa: list):
        """Texto das palavras dentro de uma caixa desenhada na imagem, remontado em linhas
        e com as correções (para a transcrição de um trecho)."""
        self._exigir_projeto()
        texto = self._projeto.ler_texto(mp.rel_padrao(rel))
        if not texto or not 1 <= int(pagina) <= texto["n_paginas"]:
            return {"texto": ""}
        x0, y0, x1, y1 = (float(v) for v in caixa)
        dentro = [w for w in texto["paginas"][int(pagina) - 1]["palavras"]
                  if x0 <= (w[0] + w[2]) / 2 <= x1 and y0 <= (w[1] + w[3]) / 2 <= y1]
        return {"texto": self._corretor.corrigir(ml.reconstruir(dentro, self._conhecida()))}

    @resposta_segura
    def salvar_texto_pagina(self, rel: str, pagina: int, texto: str):
        """Texto da página revisado à mão: passa a valer na página e na busca (o que o OCR
        leu continua guardado e também é achado pela busca)."""
        self._exigir_projeto()
        rel = mp.rel_padrao(rel)
        info = self._projeto.ler_texto(rel)
        if not info:
            raise ErroUsuario("Processe o documento antes de revisar o texto.")
        pagina = int(pagina)
        if not 1 <= pagina <= info["n_paginas"]:
            raise ErroUsuario(f"Página {pagina} não existe neste documento.")
        texto = "\n".join(l.rstrip() for l in (texto or "").replace("\r\n", "\n").split("\n")).strip()
        if not texto:
            raise ErroUsuario("O texto ficou vazio. Para voltar ao texto automático, use "
                              "“Voltar ao texto automático”.")
        self._banco.salvar_revisao(rel, pagina, texto, self._autor())
        self._reindexar_documento(rel)
        self._projeto.registrar("revisou_pagina", documento=rel, pagina=pagina, caracteres=len(texto))
        return {"rel": rel, "pagina": pagina}

    @resposta_segura
    def descartar_texto_pagina(self, rel: str, pagina: int):
        """Apaga a revisão: a página volta ao texto remontado automaticamente."""
        self._exigir_projeto()
        rel = mp.rel_padrao(rel)
        n = self._banco.remover_revisao(rel, int(pagina))
        if n:
            self._reindexar_documento(rel)
        return {"rel": rel, "pagina": int(pagina), "removida": bool(n)}

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
