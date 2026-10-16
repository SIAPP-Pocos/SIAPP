"""Ponte: dicionário do projeto e correções de OCR (guardados no banco do projeto)."""

from __future__ import annotations

import re

from motor import vocabulario as mvoc

from .base import CAMINHO_VOCAB_BASE, ErroUsuario, resposta_segura


class VocabularioAPI:
    _corretor = None

    def _carregar_corretor(self):
        self._corretor = mvoc.Corretor(mvoc.ler_base(CAMINHO_VOCAB_BASE), self._banco.vocab_efetivo())

    def _aplicar_vocabulario(self, evento: str, **detalhe) -> dict:
        """Reaplica as correções em TODOS os documentos já processados (o OCR
        original não é refeito nem alterado) e anota o evento no histórico."""
        self._carregar_corretor()
        n = self._indice.reconstruir(self._projeto.documentos_processados(), self._corretor)
        self._projeto.registrar(evento, **detalhe)
        return {"paginas_atualizadas": n, **self._dicionario()}

    def _dicionario(self) -> dict:
        v = self._banco.vocab_local()
        comunidade = [{"de": r["de"], "para": r["para"], "origem": r["origem"]}
                      for r in self._banco.vocab_linhas()
                      if r["origem"] != "local" and r["tipo"] == "correcao"]
        return {"palavras": sorted(v["palavras"], key=str.lower),
                "correcoes": dict(sorted(v["correcoes"].items(), key=lambda kv: kv[0].lower())),
                "ignorar": sorted(v["ignorar"], key=str.lower),
                "correcoes_comunidade": sorted(comunidade, key=lambda x: x["de"].lower())}

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
            raise ErroUsuario("Palavra muito curta.")
        self._banco.vocab_definir("palavra", palavra, autor=self._autor())
        return self._aplicar_vocabulario("adicionou_palavra", palavra=palavra)

    @resposta_segura
    def remover_palavra(self, palavra: str):
        self._exigir_projeto()
        self._banco.vocab_remover("palavra", palavra)
        return self._aplicar_vocabulario("removeu_palavra", palavra=palavra)

    @resposta_segura
    def corrigir_palavra(self, de: str, para: str):
        """Correção explícita: vale para todos os documentos do projeto."""
        self._exigir_projeto()
        de, para = str(de).strip(), " ".join(str(para).split())
        if not de or not para:
            raise ErroUsuario("Informe a palavra lida e a correção.")
        if de == para:
            raise ErroUsuario("A correção é igual à palavra lida.")
        if not re.search(r"[A-Za-zÀ-ÿ]", de) or len(de) < 3:
            # "87"→"83" trocaria TODO 87 de TODAS as páginas. Números se corrigem
            # página a página, na transcrição assistida — nunca por regra global.
            raise ErroUsuario("Números e palavras de 1–2 letras não podem ser corrigidos em todos "
                              "os documentos de uma vez: a troca atingiria valores certos em outras "
                              "páginas. Use a transcrição assistida, página a página.")
        self._banco.vocab_definir("correcao", de, para, autor=self._autor())
        # quem corrige explicitamente também está dizendo que a regra automática não vale
        self._banco.vocab_remover("ignorar", de)
        return self._aplicar_vocabulario("corrigiu_palavra", de=de, para=para)

    @resposta_segura
    def remover_correcao(self, de: str):
        self._exigir_projeto()
        self._banco.vocab_remover("correcao", de)
        return self._aplicar_vocabulario("removeu_correcao", de=de)

    @resposta_segura
    def manter_original(self, palavra: str):
        """O OCR estava certo: desfaz, NESTE computador, uma correção automática
        (do dicionário) ou vinda da comunidade."""
        self._exigir_projeto()
        self._banco.vocab_definir("ignorar", palavra, autor=self._autor())
        return self._aplicar_vocabulario("manteve_original", palavra=palavra)

    @resposta_segura
    def remover_ignorar(self, palavra: str):
        self._exigir_projeto()
        self._banco.vocab_remover("ignorar", palavra)
        return self._aplicar_vocabulario("voltou_a_corrigir", palavra=palavra)
