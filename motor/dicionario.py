"""
Dicionário de português para o texto dos documentos.

Lista de ~400 mil palavras (com flexões) em `recursos/palavras_pt.txt.gz`, da mais para a
menos frequente. Origem: lista de português do pyspellchecker (licença MIT,
Tyler Barrus), derivada de legendas abertas (OpenSubtitles / FrequencyWords).

Serve para três coisas:
- decidir se duas peças que o OCR separou formam uma palavra ("Avalia ção" → "Avaliação");
- apontar as **possíveis palavras erradas** de uma página (fora do dicionário, do
  vocabulário técnico e das palavras que o próprio acervo repete);
- sugerir a forma certa (1 letra trocada, faltando ou sobrando, e as confusões típicas
  do OCR: rn↔m, cl↔d, li↔h, 0↔o, 1↔l, 5↔s).

Carrega na primeira vez que é usado (cerca de 1 s) e fica na memória.
"""

from __future__ import annotations

import gzip
import os
import re
import threading
import unicodedata

CAMINHO_PADRAO = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                              "recursos", "palavras_pt.txt.gz")
_LETRAS = "abcdefghijklmnopqrstuvwxyz"
_CONFUSOES = [("rn", "m"), ("m", "rn"), ("cl", "d"), ("li", "h"), ("ii", "u"), ("vv", "w"),
              ("0", "o"), ("1", "l"), ("1", "i"), ("5", "s"), ("8", "b"), ("l", "i"), ("i", "l"),
              ("c", "e"), ("e", "c"), ("n", "u"), ("u", "n")]
_RE_PALAVRA = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9]+")


def chave(palavra: str) -> str:
    """minúscula e sem acento: "Avaliação" → "avaliacao"."""
    return "".join(c for c in unicodedata.normalize("NFD", palavra.lower())
                   if unicodedata.category(c) != "Mn")


class Dicionario:
    def __init__(self, caminho: str = CAMINHO_PADRAO):
        self.caminho = caminho
        self._trava = threading.Lock()
        self._chaves: dict[str, int] | None = None   # chave -> posição (0 = mais frequente)
        self._formas: list[str] = []                  # posição -> forma com acento

    @property
    def carregado(self) -> bool:
        return self._chaves is not None

    def _carregar(self) -> dict:
        if self._chaves is None:
            with self._trava:
                if self._chaves is None:
                    d: dict[str, int] = {}
                    formas: list[str] = []
                    try:
                        with gzip.open(self.caminho, "rt", encoding="utf-8") as f:
                            for linha in f:
                                w = linha.rstrip("\n")
                                k = chave(w)
                                if w and k not in d:
                                    d[k] = len(formas)
                                    formas.append(k if k == w else w)
                    except OSError:
                        pass                         # sem o arquivo: dicionário vazio, nada quebra
                    self._formas = formas
                    self._chaves = d
        return self._chaves

    def __len__(self) -> int:
        return len(self._carregar())

    def conhece(self, palavra: str) -> bool:
        return chave(palavra) in self._carregar()

    def forma(self, palavra: str) -> str | None:
        """Forma com acento, no estilo (maiúsculas) de quem pediu: "AVALIACAO" → "AVALIAÇÃO"."""
        i = self._carregar().get(chave(palavra))
        return _no_estilo(palavra, self._formas[i]) if i is not None else None

    def sugerir(self, palavra: str, n: int = 3) -> list[str]:
        """Palavras do dicionário a uma edição de distância (e confusões típicas do OCR),
        da mais para a menos frequente."""
        d = self._carregar()
        k = chave(palavra)
        if not k or k in d:
            return []
        cands: list[str] = []
        vistos = set()

        def tentar(c):
            if c and c not in vistos:
                vistos.add(c)
                if c in d:
                    cands.append(c)
        for a, b in _CONFUSOES:
            i = k.find(a)
            while i >= 0:
                tentar(k[:i] + b + k[i + len(a):])
                i = k.find(a, i + 1)
        for i in range(len(k) + 1):
            for L in _LETRAS:
                tentar(k[:i] + L + k[i:])                    # faltou uma letra
                if i < len(k):
                    tentar(k[:i] + L + k[i + 1:])            # letra trocada
            if i < len(k):
                tentar(k[:i] + k[i + 1:])                    # letra sobrando
            if i < len(k) - 1:
                tentar(k[:i] + k[i + 1] + k[i] + k[i + 2:])  # duas letras invertidas
        cands.sort(key=lambda c: d[c])                       # a mais frequente primeiro
        return [_no_estilo(palavra, self._formas[d[c]]) for c in cands[:n]]


def _no_estilo(modelo: str, palavra: str) -> str:
    if modelo.isupper() and len(modelo) > 1:
        return palavra.upper()
    if modelo[:1].isupper():
        return palavra[:1].upper() + palavra[1:]
    return palavra


_PADRAO: Dicionario | None = None


def padrao() -> Dicionario:
    global _PADRAO
    if _PADRAO is None:
        _PADRAO = Dicionario()
    return _PADRAO


def possiveis_erros(texto: str, conhecida, dicionario: Dicionario, ignorar=lambda w: False,
                    limite: int = 60) -> list[dict]:
    """Palavras do texto que não estão no dicionário nem no vocabulário (`conhecida`):
    [{"palavra", "vezes", "sugestoes"}] na ordem em que aparecem. Fica de fora o que quase
    certamente não é erro: siglas curtas em maiúsculas (GMR, RN), palavras com menos de 4
    letras e códigos com número (7-GMR-13-RN) — a não ser que o número esteja no meio de
    letras, que é erro típico de OCR ("perfura1ção")."""
    vistas: dict[str, dict] = {}
    for m in _RE_PALAVRA.finditer(texto or ""):
        w = m.group(0)
        tem_num = any(c.isdigit() for c in w)
        if tem_num:
            letras = sum(c.isalpha() for c in w)
            if letras < 4 or not (w[0].isalpha() and w[-1].isalpha()):
                continue
        if len(w) < 4 or (w.isupper() and len(w) <= 5 and not tem_num):
            continue
        k = chave(w)
        if k in vistas:
            vistas[k]["vezes"] += 1
            continue
        if not tem_num and (dicionario.conhece(w) or conhecida(w)):
            continue
        if ignorar(w):
            continue
        vistas[k] = {"palavra": w, "vezes": 1, "sugestoes": dicionario.sugerir(w)}
        if len(vistas) >= limite:
            break
    return list(vistas.values())


def legibilidade(texto: str, conhecida) -> int | None:
    """% das palavras (5+ letras) do texto que são palavras de verdade — dicionário,
    vocabulário técnico ou o acervo (`conhecida`). Página manuscrita, gráfico ou carimbo
    lidos pelo OCR dão números baixos: aí o texto só serve de pista e vale a imagem.
    None quando há poucas palavras para julgar."""
    ws = [w for w in re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ]{5,}", texto or "")]
    if len(ws) < 12:
        return None
    return round(100 * sum(1 for w in ws if conhecida(w)) / len(ws))
