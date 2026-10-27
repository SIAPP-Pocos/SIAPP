"""
Texto da página remontado a partir das POSIÇÕES das palavras (caixas do OCR).

O texto que o OCR devolve vem quebrado em pedaços: o Tesseract fatia a página em blocos
e cada bloco sai numa linha — "Setor⏎de⏎Avaliação", três palavras e quebra, uma letra e
quebra, colunas lidas de cima para baixo. Mas cada palavra guardada tem a sua caixa na
página (x0, y0, x1, y1 normalizados), e com elas dá para refazer o texto como ele está
no papel:

1. **Sujeira fora**: riscos e manchas que o OCR leu como "|", ":", "—", "!" soltos, e
   letras isoladas sem vizinho na linha (carimbos, bordas). Nada some do original: a
   sujeira só não entra no texto remontado.
2. **Linhas**: palavras cuja altura se sobrepõe ficam na mesma linha (tolerante a página
   torta), da esquerda para a direita.
3. **Colunas e campos de formulário**: espaço grande entre duas palavras vira um
   separador ("  ") — "POÇO: 7-GMR-13-RN    CAMPO: GUAMARÉ" fica numa linha só.
4. **Palavra partida**: duas peças coladas (espaço quase zero) viram uma; peças com um
   espaço pequeno viram uma se a palavra inteira for conhecida (`conhecida`) e alguma das
   peças não for — "Avalia ção" → "Avaliação", mas "a ponta" continua "a ponta".
5. **Parágrafos**: espaço vertical grande abre parágrafo novo; dentro do parágrafo, linha
   de texto corrido que continua na seguinte é emendada (e "cimen-⏎tação" vira
   "cimentação"). Linha de formulário (curta, "Rótulo: valor") fica sozinha.

É determinístico e barato (milissegundos por página): roda na hora de mostrar a página,
sobre os textos já processados, sem refazer o OCR.
"""

from __future__ import annotations

import re
import unicodedata
from statistics import median

VERSAO_LAYOUT = 1

_ALNUM = re.compile(r"[0-9A-Za-zÀ-ÖØ-öø-ÿ]")
_SO_LETRAS = re.compile(r"^[A-Za-zÀ-ÖØ-öø-ÿ]+$")
_FIM_FRASE = re.compile(r"[.:;!?)\]»”\"]$")
_ROTULO = re.compile(r"^[^:]{1,40}:\s*\S")       # "Poço: 7-GMR-13-RN"


def _norm(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn").upper()


# palavras curtas de verdade (o resto com 1–2 letras, isolado na linha, é mancha ou borda)
_CURTAS = {"A", "À", "AO", "AS", "DA", "DE", "DO", "E", "É", "EM", "NA", "NO", "OS", "OU", "UM", "SE", "SÓ",
           "M", "KM", "CM", "MM", "PÉ", "PE", "NE", "NW", "SE", "SW", "N", "S", "L", "W", "H", "Nº", "N°", "OK",
           "PB", "RN", "CE", "AL", "SE", "BA", "ES", "RJ", "SP", "AM", "MA", "PI", "PR", "SC", "MG"}


def _sujeira(texto: str) -> bool:
    """Token sem nenhuma letra ou número: risco, mancha, borda de tabela."""
    return not _ALNUM.search(texto)


class _Palavra:
    __slots__ = ("x0", "y0", "x1", "y1", "t", "h", "yc")

    def __init__(self, w):
        self.x0, self.y0, self.x1, self.y1, self.t = float(w[0]), float(w[1]), float(w[2]), float(w[3]), str(w[4])
        self.h = max(self.y1 - self.y0, 1e-4)
        self.yc = (self.y0 + self.y1) / 2

    @property
    def larg_letra(self) -> float:
        return max((self.x1 - self.x0) / max(len(self.t), 1), 1e-4)


def _linhas(ps: list[_Palavra]) -> list[list[_Palavra]]:
    """Agrupa em linhas.

    1. O OCR já diz quais palavras ele leu juntas: todas as palavras de uma linha do
       Tesseract têm EXATAMENTE a mesma caixa vertical (y0, y1) — e essa caixa é mais alta
       que a letra, então duas linhas vizinhas se sobrepõem e não dá para separá-las só pela
       sobreposição.
    2. O Tesseract parte uma mesma linha do papel em pedaços (colunas, campos de formulário,
       ou simplesmente "Setor" "de" "Avaliação" em blocos diferentes): pedaços na mesma
       altura (centros a menos de 1/3 da altura) e que não se sobrepõem na horizontal são a
       mesma linha."""
    grupos: dict = {}
    for p in ps:
        grupos.setdefault((round(p.y0, 4), round(p.y1, 4)), []).append(p)
    pedacos = [sorted(g, key=lambda q: q.x0) for g in grupos.values()]
    pedacos.sort(key=lambda g: (g[0].yc, g[0].x0))
    linhas: list[list] = []          # [palavras, yc, h]
    for g in pedacos:
        yc, h = g[0].yc, g[0].h
        x0, x1 = g[0].x0, g[-1].x1
        melhor, dist = None, None
        for L in linhas[-15:]:
            ps_L, cy, ch = L
            if abs(yc - cy) >= 0.34 * min(h, ch):
                continue
            if any(min(x1, q.x1) - max(x0, q.x0) > 0.2 * min(x1 - x0, q.x1 - q.x0) for q in ps_L):
                continue                              # já tem palavra nesse trecho: é outra linha
            d = abs(yc - cy)
            if dist is None or d < dist:
                melhor, dist = L, d
        if melhor is None:
            linhas.append([list(g), yc, h])
        else:
            n = len(melhor[0])
            melhor[0].extend(g)
            melhor[1] = (melhor[1] * n + yc * len(g)) / (n + len(g))
    out = [sorted(L[0], key=lambda q: q.x0) for L in linhas]
    out.sort(key=lambda L: median(q.yc for q in L))
    return out


def _juntar_partidas(linha: list[_Palavra], conhecida) -> list[_Palavra]:
    """Peças da mesma palavra: coladas (espaço ~0) ou com espaço pequeno quando a palavra
    inteira é conhecida e as peças não são."""
    out: list[_Palavra] = []
    for p in linha:
        if out:
            a = out[-1]
            gap = p.x0 - a.x1
            letra = min(a.larg_letra, p.larg_letra)
            junto = a.t + p.t
            colada = (-0.25 * letra < gap < 0.12 * letra and _ALNUM.search(a.t[-1:])
                      and _ALNUM.search(p.t[:1]) and abs(a.h - p.h) < 0.35 * max(a.h, p.h))
            pequena = (-0.25 * letra < gap < 0.9 * letra and conhecida is not None and _SO_LETRAS.match(junto)
                       and len(junto) >= 5 and conhecida(junto)
                       and not (conhecida(a.t) and conhecida(p.t)))   # "a ponta" fica; "Avalia ção" junta
            if colada or pequena:
                a.t, a.x1 = junto, p.x1
                a.y0, a.y1 = min(a.y0, p.y0), max(a.y1, p.y1)
                continue
        out.append(p)
    return out


def _sem_isoladas(linha: list[_Palavra]) -> list[_Palavra]:
    """Tira de cada linha os tokens de 1–2 caracteres longe de tudo (borda de formulário,
    carimbo, mancha): "i    DEXPRO DIGUAR    s" → "DEXPRO DIGUAR". Números ficam."""
    out = []
    for i, p in enumerate(linha):
        t = p.t.strip(".,;:!?\"'“”«»()[]")
        if len(t) <= 2 and not t.isdigit() and t.upper() not in _CURTAS:
            letra = p.larg_letra * 1.0
            esq = p.x0 - linha[i - 1].x1 if i > 0 else 1.0
            dir_ = linha[i + 1].x0 - p.x1 if i + 1 < len(linha) else 1.0
            if esq > 3 * letra and dir_ > 3 * letra:
                continue
        out.append(p)
    return out


def _texto_da_linha(linha: list[_Palavra]) -> str:
    partes = [linha[0].t]
    for a, b in zip(linha, linha[1:]):
        gap = b.x0 - a.x1
        letra = median([a.larg_letra, b.larg_letra])
        if gap > 3.5 * letra:                    # coluna ou campo de formulário
            partes.append("    ")
        else:
            partes.append(" ")
        partes.append(b.t)
    return "".join(partes)


def _e_formulario(texto: str, larg: float, larg_max: float) -> bool:
    return "    " in texto or bool(_ROTULO.match(texto)) or larg < 0.55 * larg_max


def reconstruir(palavras: list, conhecida=None) -> str:
    """Texto da página a partir de [[x0, y0, x1, y1, texto], …] (coordenadas 0–1).
    `conhecida(palavra) -> bool`: vocabulário para decidir se peças formam uma palavra."""
    ps = [_Palavra(w) for w in palavras if str(w[4]).strip()]
    if not ps:
        return ""
    hmed = median(p.h for p in ps)
    # 1. sujeira: tokens sem letra/número, e caixas absurdas (risco vertical lido como "l", "I")
    ps = [p for p in ps if not _sujeira(p.t) and p.h < 4 * hmed]
    if not ps:
        return ""
    linhas = _linhas(ps)
    # letra solta sem vizinho na linha (carimbo, borda): fora; número solto fica
    limpas = []
    for L in linhas:
        if len(L) == 1 and len(L[0].t) <= 2 and not L[0].t.isdigit():
            continue
        limpas.append(L)
    linhas = [_sem_isoladas(_juntar_partidas(L, conhecida)) for L in limpas]
    linhas = [L for L in linhas if L]
    if not linhas:
        return ""
    x_min = min(L[0].x0 for L in linhas)
    larg_max = max(L[-1].x1 for L in linhas) - x_min
    espac = [median(q.yc for q in b) - median(q.yc for q in a) for a, b in zip(linhas, linhas[1:])]
    # passo típico entre linhas: quartil de baixo (os espaços de parágrafo são os maiores)
    passo = sorted(espac)[len(espac) // 4] if espac else hmed
    # 5. parágrafos e emendas
    saida: list[str] = []
    anterior = None
    for i, L in enumerate(linhas):
        txt = _texto_da_linha(L)
        larg = L[-1].x1 - L[0].x0
        forma = _e_formulario(txt, larg, larg_max)
        if anterior is None:
            saida.append(txt)
        else:
            gap = espac[i - 1]
            txt_ant, forma_ant, larg_ant = anterior
            if gap > 1.7 * passo and gap > 1.8 * hmed:
                saida.append("")                       # parágrafo novo
                saida.append(txt)
            elif (not forma and not forma_ant and larg_ant > 0.7 * larg_max
                  and not _FIM_FRASE.search(txt_ant.rstrip())):
                if txt_ant.endswith("-") and txt[:1].islower():
                    saida[-1] = saida[-1][:-1] + txt   # cimen-⏎tação
                else:
                    saida[-1] = saida[-1] + " " + txt  # texto corrido continua
                txt = saida[-1]
            else:
                saida.append(txt)
        anterior = (txt, forma, larg)
    return "\n".join(saida).strip()


def conhecida_por(*vocabularios) -> callable:
    """Função `conhecida` a partir de conjuntos de palavras (normalizadas sem acento)."""
    todas = set()
    for v in vocabularios:
        todas.update(_norm(x) for x in v if x)
    return lambda palavra: _norm(palavra) in todas


def vocabulario_do_corpus(textos, minimo: int = 3) -> set[str]:
    """Palavras (5+ letras) que aparecem inteiras pelo menos `minimo` vezes nos textos:
    o próprio acervo serve de dicionário para decidir se "Avalia"+"ção" é uma palavra."""
    cont: dict[str, int] = {}
    for t in textos:
        for w in re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ]{5,}", t or ""):
            k = _norm(w)
            cont[k] = cont.get(k, 0) + 1
    return {k for k, n in cont.items() if n >= minimo}
