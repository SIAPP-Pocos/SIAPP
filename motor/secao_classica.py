"""Seção estratigráfica no estilo clássico das seções de correlação da indústria.

Convenções usadas (as usuais em boletins técnicos e relatórios de poço):

- cada poço: trilha de GR à esquerda, escala de profundidade medida, coluna litológica
  com **padrões de rocha** (arenito pontilhado, folhelho tracejado, calcário em tijolo,
  evaporito em grade, embasamento em cruzes, ígnea em "v"…, no espírito dos padrões
  FGDC/USGS), faixa da formação e indícios de hidrocarboneto;
- entre poços: corpos das formações em tons pastel com o nome dentro, linhas de topo,
  discordâncias em linha ondulada, datum destacado;
- símbolo do poço pela classificação, pontas A–A′, mapa de localização da linha, escala
  gráfica e carimbo (título, datum, exagero, fontes, autor, data).

Os padrões são desenhados como geometria (não ``<pattern>``) e tudo é recortado no
Python: o PyMuPDF, que gera o PNG e o PDF, não entende ``<pattern>`` nem ``clipPath``.
A litologia vem das amostras de calha do AGP — é descrição, não interpretação de perfil.

Desde a 0.68, as cores e os padrões de rocha são os da legenda "Código das litologias" dos
perfis compostos da Petrobras (``recursos/litologias.json``, copiados do vetor do PDF do
1-BRSA-1041D-AL): cada quadradinho da legenda vira um ladrilho repetido na coluna. Rocha que
não está na legenda usa os padrões simples de antes (``LITOLOGIAS``).
"""

from __future__ import annotations

import json
import math
import os
import re
import unicodedata
from functools import lru_cache
from html import escape

from . import __version__
from .secao import _data, _fmt, _passo_grade, _plano

# Helvetica primeiro: é a que o PyMuPDF (PNG/PDF) conhece; no Windows vira Arial
FONTE = "Helvetica, Arial, Liberation Sans, sans-serif"
TINTA = "#1a1a1a"
TINTA_2 = "#4d4d4d"
TINTA_FRACA = "#8a8a8a"
GRADE = "#e6e6e6"
COR_GR = "#2f7d4f"

# (regex na descrição da rocha, chave, nome, cor de fundo, padrão) — a ordem importa:
# "CALCARENITO" é carbonato, não arenito.
LITOLOGIAS = [
    (r"CARVAO|CARVÃO|LINHITO", "carvao", "Carvão", "#2b2b2b", "solido"),
    (r"HALITA|\bSAL\b|ANIDRITA|GIPSITA|EVAPORIT|SILVINITA|CARNALITA", "evaporito", "Evaporito", "#f2c9e6", "grade"),
    (r"GRANITO|GNAISSE|EMBASAMENTO|METAMORF|XISTO|MIGMATITO|QUARTZITO|FILITO", "embasamento",
     "Embasamento cristalino", "#f3b9b0", "cruzes"),
    (r"BASALTO|DIABASIO|DIABÁSIO|IGNEA|ÍGNEA|VULCAN|GABRO|TUFO", "ignea", "Rocha ígnea", "#d8bfe8", "vees"),
    (r"CONGLOMERADO|BRECHA", "conglomerado", "Conglomerado", "#ffe39a", "seixos"),
    (r"CALC|COQUINA|CALCARIO|CALCÁRIO", "calcario", "Calcário", "#a9cff2", "tijolo"),
    (r"DOLOMIT", "dolomito", "Dolomito", "#c3cff5", "tijolo_obliquo"),
    (r"MARGA", "marga", "Marga", "#bcdccf", "marga"),
    (r"SILTITO", "siltito", "Siltito", "#dcd7a8", "silte"),
    (r"FOLHELHO|ARGILITO|LAMITO|ARGILA", "folhelho", "Folhelho / argilito", "#bccbb0", "tracos"),
    (r"ARENITO|AREIA", "arenito", "Arenito", "#fff27a", "pontos"),
]
OUTRA = ("outra", "Outra / não identificada", "#e4e1d8", "nenhum")
SEM_CALHA = ("sem", "Sem descrição de calha", "#ffffff", "sem")
ABREV = {"Formação": "Fm.", "Membro": "Mb.", "Grupo": "Gr.", "Camadas": "Cam.", "Supergrupo": "Sgr."}


CAMINHO_LITOLOGIAS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "recursos",
                                  "litologias.json")
LADO_LADRILHO = 13.0          # px de um ladrilho da legenda Petrobras (2 na largura da coluna)


def _sem_acento(t: str) -> str:
    return unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode("ascii").upper()


@lru_cache(maxsize=4)
def legenda_petrobras(caminho: str = CAMINHO_LITOLOGIAS) -> dict:
    """{codigo: {codigo, nome, termos, fundo, desenho}} da legenda Petrobras; {} se o arquivo faltar."""
    try:
        with open(caminho, encoding="utf-8") as f:
            dados = json.load(f)
    except (OSError, ValueError):
        return {}
    return {d["codigo"]: d for d in dados.get("litologias", [])}


@lru_cache(maxsize=1024)
def _termo_petrobras(rocha: str) -> str | None:
    """Código da legenda Petrobras para a rocha da calha: o termo mais longo que casa."""
    r = " ".join(_sem_acento(rocha).replace("-", " - ").split()).replace(" - ", "-")
    melhor, tam = None, 0
    for cod, d in legenda_petrobras().items():
        for termo in d["termos"]:
            if len(termo) > tam and re.search(r"(^|\s)" + re.escape(termo), r):
                melhor, tam = cod, len(termo)
    return melhor


def litologia(rocha: str) -> tuple[str, str, str, str]:
    """(chave, nome, cor de fundo, padrão). Padrão "pb:<código>" = ladrilho da legenda Petrobras."""
    cod = _termo_petrobras(rocha or "")
    if cod:
        d = legenda_petrobras()[cod]
        return cod, d["nome"][:1].upper() + d["nome"][1:], d["fundo"], "pb:" + cod
    r = (rocha or "").upper()
    for padrao, chave, nome, cor, pat in LITOLOGIAS:
        if re.search(padrao, r):
            return chave, nome, cor, pat
    return OUTRA


def pastel(cor: str, f: float = 0.62) -> str:
    """Mistura com branco (f = fração de branco)."""
    c = cor.lstrip("#")
    rgb = [int(c[i:i + 2], 16) for i in (0, 2, 4)]
    return "#" + "".join(f"{round(v + (255 - v) * f):02x}" for v in rgb)


def abreviar(nome: str) -> str:
    for longo, curto in ABREV.items():
        if nome.startswith(longo + " "):
            return curto + nome[len(longo):]
    return nome


def _t(x, y, texto, tam=10, cor=TINTA, ancora="middle", peso="normal", rot=None, estilo=None):
    tr = f' transform="rotate({rot} {x:.1f} {y:.1f})"' if rot is not None else ""
    it = f' font-style="{estilo}"' if estilo else ""
    # a fonte vai em cada texto: o PyMuPDF não herda font-family do <svg>
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{FONTE}" font-size="{tam}" fill="{cor}" '
            f'text-anchor="{ancora}" font-weight="{peso}"{it}{tr}>{escape(str(texto))}</text>')


# ================================================================ padrões
def marcas(pat: str, x: float, y: float, w: float, h: float) -> tuple[str, str]:
    """(traços, pontos) em SVG path 'd', dentro do retângulo. A grade é absoluta, para o
    padrão continuar entre camadas vizinhas."""
    if h < 1.6 or w < 2 or pat in ("nenhum", "solido"):
        return "", ""
    x1, y1 = x + w, y + h
    tr, pt = [], []

    def linhas_h(passo, desloc=0.0):
        k = math.ceil((y - desloc) / passo)
        v = desloc + k * passo
        while v <= y1:
            yield v
            v += passo

    if pat == "pontos":
        for row, yy in enumerate(linhas_h(4.0, 1.5)):
            off = 1.5 if row % 2 else 4.0
            xx = math.floor((x - off) / 5.0) * 5.0 + off
            while xx < x1 - 0.8:
                if xx >= x + 0.4 and yy <= y1 - 0.8:
                    pt.append(f"M{xx:.1f} {yy:.1f}h.9v.9h-.9z")
                xx += 5.0
    elif pat in ("tracos", "silte"):
        for row, yy in enumerate(linhas_h(3.5, 1.0)):
            if pat == "silte" and row % 2:
                xx = math.floor(x / 5.0) * 5.0 + 2.5
                while xx < x1 - 0.8:
                    if xx >= x + 0.4:
                        pt.append(f"M{xx:.1f} {yy - .4:.1f}h.9v.9h-.9z")
                    xx += 5.0
                continue
            off = 0.0 if row % 2 else 3.0
            xx = math.floor((x - off) / 6.0) * 6.0 + off
            while xx < x1:
                a, b = max(xx, x), min(xx + 3.6, x1)
                if b - a > 0.6:
                    tr.append(f"M{a:.1f} {yy:.1f}H{b:.1f}")
                xx += 6.0
    elif pat in ("tijolo", "tijolo_obliquo", "marga"):
        filas = list(linhas_h(5.0))
        for yy in filas:
            if pat == "marga":
                xx = math.floor(x / 6.0) * 6.0
                while xx < x1:
                    a, b = max(xx, x), min(xx + 3.6, x1)
                    if b - a > 0.6:
                        tr.append(f"M{a:.1f} {yy:.1f}H{b:.1f}")
                    xx += 6.0
            else:
                tr.append(f"M{x:.1f} {yy:.1f}H{x1:.1f}")
        bordas = [y] + filas + [y1]
        for k in range(len(bordas) - 1):
            a, b = bordas[k], bordas[k + 1]
            if b - a < 1.2:
                continue
            fila = round(a / 5.0)
            off = 0.0 if fila % 2 else 4.0
            xx = math.floor((x - off) / 8.0) * 8.0 + off
            while xx < x1 - 0.5:
                if xx > x + 0.5:
                    if pat == "tijolo_obliquo":
                        tr.append(f"M{xx:.1f} {a:.1f}L{min(xx + 1.6, x1):.1f} {b:.1f}")
                    else:
                        tr.append(f"M{xx:.1f} {a:.1f}V{b:.1f}")
                xx += 8.0
    elif pat == "grade":
        for yy in linhas_h(5.0):
            tr.append(f"M{x:.1f} {yy:.1f}H{x1:.1f}")
        xx = math.ceil(x / 5.0) * 5.0
        while xx < x1:
            tr.append(f"M{xx:.1f} {y:.1f}V{y1:.1f}")
            xx += 5.0
    elif pat in ("cruzes", "vees", "seixos"):
        for row, yy in enumerate(linhas_h(6.0, 3.0)):
            off = 2.5 if row % 2 else 6.5
            xx = math.floor((x - off) / 8.0) * 8.0 + off
            while xx < x1:
                if xx - 1.7 >= x and xx + 1.7 <= x1 and yy - 1.7 >= y and yy + 1.7 <= y1:
                    if pat == "cruzes":
                        tr.append(f"M{xx - 1.6:.1f} {yy:.1f}H{xx + 1.6:.1f}M{xx:.1f} {yy - 1.6:.1f}V{yy + 1.6:.1f}")
                    elif pat == "vees":
                        tr.append(f"M{xx - 1.6:.1f} {yy - 1.2:.1f}L{xx:.1f} {yy + 1.4:.1f}L{xx + 1.6:.1f} {yy - 1.2:.1f}")
                    else:
                        tr.append(f"M{xx - 1.5:.1f} {yy:.1f}a1.5 1.2 0 1 0 3 0a1.5 1.2 0 1 0 -3 0")
                xx += 8.0
    elif pat == "sem":
        k = math.floor((x + y) / 6.0) * 6.0
        while k < x1 + y1:
            # diagonal x + y = k, recortada no retângulo
            pa = (max(x, k - y1), min(y1, k - x))
            pb = (min(x1, k - y), max(y, k - x1))
            if pa[0] < pb[0]:
                tr.append(f"M{pa[0]:.1f} {pa[1]:.1f}L{pb[0]:.1f} {pb[1]:.1f}")
            k += 6.0
    return "".join(tr), "".join(pt)


_RE_CMD = re.compile(r"([MLCHVhvz])([^MLCHVhvz]*)")


@lru_cache(maxsize=256)
def _subcaminhos(d: str) -> tuple:
    """Path compacto da legenda (M, L, C, h, v, z em coordenadas 0–1) → subcaminhos, cada um uma
    lista de segmentos ("l", x1, y1, x2, y2) ou ("c", x1, y1, ..., x4, y4), e se é fechado."""
    subs, atual, ini, pos = [], [], None, (0.0, 0.0)
    for cmd, args in _RE_CMD.findall(d):
        v = [float(a) for a in args.replace(",", " ").split()]
        if cmd == "M":
            if atual:
                subs.append((tuple(atual), False))
            atual, pos = [], (v[0], v[1])
            ini = pos
        elif cmd == "L":
            for k in range(0, len(v), 2):
                atual.append(("l", *pos, v[k], v[k + 1]))
                pos = (v[k], v[k + 1])
        elif cmd == "C":
            for k in range(0, len(v), 6):
                atual.append(("c", *pos, *v[k:k + 6]))
                pos = (v[k + 4], v[k + 5])
        elif cmd in "hH":
            novo = (pos[0] + v[0], pos[1]) if cmd == "h" else (v[0], pos[1])
            atual.append(("l", *pos, *novo))
            pos = novo
        elif cmd in "vV":
            novo = (pos[0], pos[1] + v[0]) if cmd == "v" else (pos[0], v[0])
            atual.append(("l", *pos, *novo))
            pos = novo
        elif cmd == "z":
            if ini and pos != ini:
                atual.append(("l", *pos, *ini))
            subs.append((tuple(atual), True))
            atual, pos = [], ini or pos
    if atual:
        subs.append((tuple(atual), False))
    return tuple(subs)


def _corta_segmento(x1, y1, x2, y2, rx0, ry0, rx1, ry1):
    """Liang–Barsky: o pedaço do segmento dentro do retângulo, ou None."""
    dx, dy = x2 - x1, y2 - y1
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, x1 - rx0), (dx, rx1 - x1), (-dy, y1 - ry0), (dy, ry1 - y1)):
        if p == 0:
            if q < 0:
                return None
            continue
        t = q / p
        if p < 0:
            t0 = max(t0, t)
        else:
            t1 = min(t1, t)
        if t0 > t1:
            return None
    return x1 + t0 * dx, y1 + t0 * dy, x1 + t1 * dx, y1 + t1 * dy


def ladrilhos_petrobras(cod: str, x: float, y: float, w: float, h: float, lado: float = LADO_LADRILHO) -> list[str]:
    """SVG do desenho da legenda Petrobras repetido em ladrilhos (grade absoluta, para o padrão
    continuar entre camadas vizinhas), recortado no retângulo à mão: linhas são cortadas na borda;
    curvas e formas preenchidas só entram inteiras."""
    d = legenda_petrobras().get(cod)
    if not d or w < 2 or h < 1.6:
        return []
    x1, y1 = x + w, y + h
    eps = 0.15
    saida = []
    i0, i1 = math.floor(x / lado), math.ceil(x1 / lado)
    j0, j1 = math.floor(y / lado), math.ceil(y1 / lado)
    for parte in d["desenho"]:
        subs = _subcaminhos(parte["d"])
        preenche = parte.get("f")
        caminho = []
        for i in range(i0, i1):
            for j in range(j0, j1):
                ox, oy = i * lado, j * lado
                for cx, cy, r in parte.get("o", ()):
                    px, py, rr = ox + cx * lado, oy + cy * lado, max(r * lado, 0.35)
                    if x <= px - rr and px + rr <= x1 and y <= py - rr and py + rr <= y1:
                        caminho.append(f"M{px - rr:.1f} {py:.1f}a{rr:.2f} {rr:.2f} 0 1 0 {2 * rr:.2f} 0"
                                       f"a{rr:.2f} {rr:.2f} 0 1 0 {-2 * rr:.2f} 0")
                for segs, fechado in subs:
                    pts = [(ox + s[k] * lado, oy + s[k + 1] * lado) for s in segs for k in range(1, len(s), 2)]
                    dentro = all(x - eps <= px <= x1 + eps and y - eps <= py <= y1 + eps for px, py in pts)
                    if dentro:
                        p0 = pts[0]
                        caminho.append(f"M{p0[0]:.1f} {p0[1]:.1f}")
                        for s in segs:
                            q = [(ox + s[k] * lado, oy + s[k + 1] * lado) for k in range(1, len(s), 2)]
                            if s[0] == "l":
                                caminho.append(f"L{q[1][0]:.1f} {q[1][1]:.1f}")
                            else:
                                caminho.append("C" + " ".join(f"{a:.1f} {b:.1f}" for a, b in q[1:]))
                        if fechado:
                            caminho.append("z")
                    elif not preenche:
                        for s in segs:
                            if s[0] != "l":
                                continue
                            c = _corta_segmento(ox + s[1] * lado, oy + s[2] * lado, ox + s[3] * lado, oy + s[4] * lado,
                                                x, y, x1, y1)
                            if c and (abs(c[2] - c[0]) + abs(c[3] - c[1])) > 0.3:
                                caminho.append(f"M{c[0]:.1f} {c[1]:.1f}L{c[2]:.1f} {c[3]:.1f}")
        if not caminho:
            continue
        if preenche:
            traco = (f' stroke="{parte["s"]}" stroke-width="{max(0.25, parte.get("w", 0) * lado):.2f}"'
                     if parte.get("s") else "")
            saida.append(f'<path d="{"".join(caminho)}" fill="{preenche}"{traco}/>')
        else:
            saida.append(f'<path d="{"".join(caminho)}" fill="none" stroke="{parte.get("s") or TINTA}" '
                         f'stroke-width="{max(0.3, parte.get("w", 0) * lado):.2f}"/>')
    return saida


def bloco_litologico(x, y, w, h, cor, pat, dica="") -> str:
    if pat.startswith("pb:"):
        s = [f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{max(h, 0.5):.1f}" fill="{cor}"/>']
        s += ladrilhos_petrobras(pat[3:], x, y, w, h)
        corpo = "".join(s)
        return f"<g><title>{escape(dica)}</title>{corpo}</g>" if dica else corpo
    tr, pt = marcas(pat, x, y, w, h)
    s = [f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{max(h, 0.5):.1f}" fill="{cor}"/>']
    if tr:
        larg = "0.35" if pat != "sem" else "0.3"
        cor_tr = TINTA if pat != "sem" else "#c4c4c4"
        s.append(f'<path d="{tr}" stroke="{cor_tr}" stroke-width="{larg}" fill="none"/>')
    if pt:
        s.append(f'<path d="{pt}" fill="{TINTA}"/>')
    corpo = "".join(s)
    return f"<g><title>{escape(dica)}</title>{corpo}</g>" if dica else corpo


def simbolo_poco(cx, cy, classe, r=5.0) -> str:
    preto = classe in ("oleo", "oleo_gas")
    s = [f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r}" fill="{TINTA if preto else "#ffffff"}" stroke="{TINTA}" stroke-width="1"/>']
    if classe in ("gas", "oleo_gas"):
        for k in range(8):
            a = k * math.pi / 4
            s.append(f'<line x1="{cx + r * math.cos(a):.1f}" y1="{cy + r * math.sin(a):.1f}" '
                     f'x2="{cx + (r + 3.2) * math.cos(a):.1f}" y2="{cy + (r + 3.2) * math.sin(a):.1f}" '
                     f'stroke="{TINTA}" stroke-width="1"/>')
    elif classe == "seco":
        for k in range(4):
            a = math.pi / 4 + k * math.pi / 2
            s.append(f'<line x1="{cx + r * math.cos(a):.1f}" y1="{cy + r * math.sin(a):.1f}" '
                     f'x2="{cx + (r + 3.5) * math.cos(a):.1f}" y2="{cy + (r + 3.5) * math.sin(a):.1f}" '
                     f'stroke="{TINTA}" stroke-width="1"/>')
    return "".join(s)


ROTULO_CLASSE = {"oleo": "Poço com óleo", "gas": "Poço com gás", "oleo_gas": "Poço com óleo e gás",
                 "seco": "Poço seco", "outro": "Outro / sem classificação"}


def _onda(x1, y1, x2, y2, amp=1.6, comp=7.0) -> str:
    n = max(2, int(math.hypot(x2 - x1, y2 - y1) / (comp / 4)))
    pts = []
    for k in range(n + 1):
        t = k / n
        xx, yy = x1 + t * (x2 - x1), y1 + t * (y2 - y1)
        pts.append(f"{xx:.1f},{yy + amp * math.sin(2 * math.pi * t * math.hypot(x2 - x1, y2 - y1) / comp):.1f}")
    return " ".join(pts)


# ================================================================== desenho
def desenhar_classico(modelo: dict, titulo: str = "", autor: str = "", data: str = "") -> str:
    pocos = modelo["pocos"]
    par = modelo["parametros"]
    n = len(pocos)
    tem_gr = any(p["gr"] for p in pocos)
    W_GR, w_md, w_lit, w_fm, w_ind = 54, 24, 26, 8, 9
    w_base = w_md + w_lit + w_fm + w_ind
    larg = [w_base + (W_GR if p["gr"] else 0) for p in pocos]      # GR só ocupa espaço onde existe
    gap_min = 58
    esq, dir_, topo_area, alt = 70, 70, 132, 760
    margem = 16

    if par["espacamento"] == "igual" or modelo["comprimento_km"] <= 0:
        xs_km = [float(i) for i in range(n)]
    else:
        xs_km = [p["x_km"] for p in pocos]
    largura_util = max(1008, sum(larg) + (n - 1) * gap_min)       # painel de baixo cabe embaixo
    esc = (largura_util - larg[-1]) / ((xs_km[-1] - xs_km[0]) or 1)
    xs = [esq + margem + (v - xs_km[0]) * esc for v in xs_km]
    ajustado = False
    for i in range(1, n):
        if xs[i] - xs[i - 1] < larg[i - 1] + gap_min:
            xs[i] = xs[i - 1] + larg[i - 1] + gap_min
            ajustado = True
    largura_plot = xs[-1] + larg[-1] + margem - esq
    largura_painel = max(largura_plot, 1040)
    W = esq + largura_painel + dir_
    x_dir = esq + largura_plot

    y_max, y_min = modelo["y_max"], modelo["y_min"]
    folga = 0.03 * (y_max - y_min or 1)
    y_max, y_min = y_max + folga, y_min - folga
    y_cima, y_baixo = topo_area, topo_area + alt

    def Yl(v):
        return topo_area + (y_max - v) / (y_max - y_min) * alt

    def Y(v):
        return min(max(Yl(v), y_cima), y_baixo)

    def dentro(v):
        return y_min <= v <= y_max

    def recortar(pts):
        for borda, fora in ((y_cima, lambda yy: yy < y_cima), (y_baixo, lambda yy: yy > y_baixo)):
            novo = []
            for k in range(len(pts)):
                p1, p2 = pts[k - 1], pts[k]
                f1, f2 = fora(p1[1]), fora(p2[1])
                if f1 != f2:
                    t = (borda - p1[1]) / (p2[1] - p1[1])
                    novo.append((p1[0] + t * (p2[0] - p1[0]), borda))
                if not f2:
                    novo.append(p2)
            pts = novo
            if not pts:
                break
        return pts

    def linha(x1, y1, x2, y2):
        """Segmento recortado nas bordas de cima e de baixo (None se fica fora)."""
        t0, t1, dy = 0.0, 1.0, y2 - y1
        for borda, sinal in ((y_cima, 1), (y_baixo, -1)):
            ini, d = sinal * (y1 - borda), sinal * dy
            if abs(d) < 1e-12:
                if ini < 0:
                    return None
                continue
            t = -ini / d
            if d > 0:
                t0 = max(t0, t)
            else:
                t1 = min(t1, t)
        if t0 > t1:
            return None
        return x1 + t0 * (x2 - x1), y1 + t0 * dy, x1 + t1 * (x2 - x1), y1 + t1 * dy

    # partes de cada bloco
    def partes(i):
        x0 = xs[i]
        w_gr = W_GR if pocos[i]["gr"] else 0
        return {"gr": x0, "md": x0 + w_gr, "lit": x0 + w_gr + w_md, "fm": x0 + w_gr + w_md + w_lit,
                "ind": x0 + w_gr + w_md + w_lit + w_fm, "fim": x0 + larg[i]}

    leg = modelo["legenda"]
    cor_fm = {u["chave"]: u["cor"] for u in leg}
    lit_usadas: dict[str, tuple] = {}
    classes_usadas, fluidos_usados, tem_disc = set(), set(), False

    o = []
    # ---------------------------------------------------- grade e eixos
    passo = _passo_grade(y_max - y_min)
    v = math.ceil(y_min / passo) * passo
    while v <= y_max:
        y = Yl(v)
        o.append(f'<line x1="{esq}" y1="{y:.1f}" x2="{x_dir:.1f}" y2="{y:.1f}" stroke="{GRADE}" stroke-width="0.5"/>')
        o.append(f'<line x1="{esq - 5}" y1="{y:.1f}" x2="{esq}" y2="{y:.1f}" stroke="{TINTA}" stroke-width="0.8"/>')
        o.append(f'<line x1="{x_dir:.1f}" y1="{y:.1f}" x2="{x_dir + 5:.1f}" y2="{y:.1f}" stroke="{TINTA}" stroke-width="0.8"/>')
        rot = _fmt(v, 0 if passo >= 1 else 1)
        o.append(_t(esq - 8, y + 3.5, rot, 9, ancora="end"))
        o.append(_t(x_dir + 8, y + 3.5, rot, 9, ancora="start"))
        v += passo
    nivelado = par["eixo"] == "nivelado"
    nome_datum = modelo.get("datum_nome") or par.get("datum") or ""
    rotulo_y = "Distância ao datum (m)" if nivelado else "Cota (m)"
    meio = topo_area + alt / 2
    o.append(_t(22, meio, rotulo_y, 10.5, rot=-90))
    o.append(_t(W - 18, meio, rotulo_y, 10.5, rot=90))

    # ---------------------------------------------------- corpos e topos entre poços
    rotulos_corpo: dict[str, tuple] = {}
    for i in range(n - 1):
        a, b = pocos[i], pocos[i + 1]
        xa, xb = partes(i)["fim"], partes(i + 1)["md"]
        ub = {u["chave"]: u for u in b["unidades"]}
        for u in a["unidades"]:
            v2 = ub.get(u["chave"])
            if not v2:
                continue
            poli = recortar([(xa, Yl(u["y_topo"])), (xb, Yl(v2["y_topo"])), (xb, Yl(v2["y_base"])),
                             (xa, Yl(u["y_base"]))])
            if len(poli) >= 3:
                pts = " ".join(f"{px:.1f},{py:.1f}" for px, py in poli)
                o.append(f'<polygon points="{pts}" fill="{pastel(u["cor"])}" stroke="none">'
                         f'<title>{escape(u["nome"])}: {escape(a["id"])} → {escape(b["id"])}</title></polygon>')
            # onde o corpo é mais espesso na seção, vai o nome
            ys = [py for _, py in poli] if len(poli) >= 3 else []
            if ys:
                esp = min(Y(u["y_base"]) - Y(u["y_topo"]), Y(v2["y_base"]) - Y(v2["y_topo"]))
                if esp >= 13 and (u["chave"] not in rotulos_corpo or esp > rotulos_corpo[u["chave"]][0]):
                    yc = (Y(u["y_topo"]) + Y(u["y_base"]) + Y(v2["y_topo"]) + Y(v2["y_base"])) / 4
                    xv = partes(i + 1)["gr"]          # trecho visível, antes da trilha GR do vizinho
                    rotulos_corpo[u["chave"]] = (esp, (xa + xv) / 2, yc, abreviar(u["nome"]), xv - xa)
        for u in a["unidades"]:
            v2 = ub.get(u["chave"])
            if v2:
                seg = linha(xa, Yl(u["y_topo"]), xb, Yl(v2["y_topo"]))
                if seg:
                    o.append(f'<line x1="{seg[0]:.1f}" y1="{seg[1]:.1f}" x2="{seg[2]:.1f}" y2="{seg[3]:.1f}" '
                             f'stroke="{TINTA}" stroke-width="0.8"/>')
        # discordâncias com a mesma sigla nos dois poços: linha ondulada
        db = {d["sigla"]: d for d in b["discordancias"]}
        for d in a["discordancias"]:
            d2 = db.get(d["sigla"])
            if d2 and dentro(d["y_topo"]) and dentro(d2["y_topo"]):
                tem_disc = True
                o.append(f'<polyline points="{_onda(xa, Y(d["y_topo"]), xb, Y(d2["y_topo"]))}" fill="none" '
                         f'stroke="{TINTA}" stroke-width="1"><title>Discordância {escape(d["sigla"])} (AGP)</title></polyline>')
    for esp, xc, yc, nome, largura in rotulos_corpo.values():
        tam = 10 if largura > 70 else 8.5
        o.append(_t(xc, yc + 3.5, nome, tam, TINTA, estilo="italic"))

    # ---------------------------------------------------- poços
    for i, p in enumerate(pocos):
        pt = partes(i)
        ya = Y(p["y_mesa"]) if p["y_mesa"] is not None else y_cima
        yb = Y(p["y_fundo"]) if p["y_fundo"] is not None else y_baixo
        # coluna litológica (camadas vizinhas da mesma rocha viram uma)
        camadas = []
        for c in sorted(p["litologia"], key=lambda c: -c["y_topo"]):
            lt = litologia(c["rocha"])
            if camadas and camadas[-1][0] == lt[0] and abs(camadas[-1][2] - c["y_topo"]) < 0.6:
                camadas[-1][2] = c["y_base"]
                camadas[-1][4].append(c)
            else:
                camadas.append([lt[0], c["y_topo"], c["y_base"], lt, [c]])
        if camadas:
            # trecho sem descrição de calha entre a mesa e a primeira amostra
            if p["y_mesa"] is not None and camadas[0][1] < p["y_mesa"] - 1:
                y0, y1 = Y(p["y_mesa"]), Y(camadas[0][1])
                if y1 - y0 > 0.5:
                    o.append(bloco_litologico(pt["lit"], y0, w_lit, y1 - y0, SEM_CALHA[2], SEM_CALHA[3],
                                              f"{p['id']}: sem descrição de calha"))
                    lit_usadas.setdefault("sem", SEM_CALHA[1:])
            for chave, yt, ybs, lt, lista in camadas:
                if not (dentro(yt) or dentro(ybs) or (yt > y_max and ybs < y_min)):
                    continue
                y0, y1 = Y(yt), Y(ybs)
                lit_usadas.setdefault(chave, lt[1:])
                c0, c1 = lista[0], lista[-1]
                dica = f"{p['id']} · {_fmt(c0['topo'])}–{_fmt(c1['base'])} m: {lt[1]} ({c0['rocha']}"
                dica += f" … {c1['rocha']})" if len(lista) > 1 else ")"
                o.append(bloco_litologico(pt["lit"], y0, w_lit, y1 - y0, lt[2], lt[3], dica))
        else:
            o.append(bloco_litologico(pt["lit"], ya, w_lit, yb - ya, SEM_CALHA[2], SEM_CALHA[3],
                                      f"{p['id']}: sem descrição de calha no AGP"))
            lit_usadas.setdefault("sem", SEM_CALHA[1:])
        o.append(f'<rect x="{pt["lit"]:.1f}" y="{ya:.1f}" width="{w_lit}" height="{max(0.0, yb - ya):.1f}" '
                 f'fill="none" stroke="{TINTA}" stroke-width="0.7"/>')
        # faixa da formação e marca de topo atravessando a coluna
        for u in p["unidades"]:
            y0, y1 = Y(u["y_topo"]), Y(u["y_base"])
            if y1 - y0 > 0.3:
                dica = (f'{p["id"]} · {u["nome"]}\nTopo {_fmt(u["topo"])} m (cota {_fmt(u["cota_topo"])}) · base '
                        f'{_fmt(u["base"])} m (cota {_fmt(u["cota_base"])})'
                        f'{"" if u["base_atingida"] else " — base não atingida"}\n'
                        f'Fonte: {u["fonte"]} {_data(u["data"])} · qualidade {u["qualidade"] or "—"} · {u["metodo"]}')
                o.append(f'<rect x="{pt["fm"]:.1f}" y="{y0:.1f}" width="{w_fm}" height="{y1 - y0:.1f}" '
                         f'fill="{pastel(u["cor"], 0.3)}" stroke="{TINTA}" stroke-width="0.4"><title>{escape(dica)}</title></rect>')
            if dentro(u["y_topo"]):
                o.append(f'<line x1="{pt["lit"]:.1f}" y1="{y0:.1f}" x2="{pt["ind"]:.1f}" y2="{y0:.1f}" '
                         f'stroke="{TINTA}" stroke-width="1.1"/>')
        for d in p["discordancias"]:
            if dentro(d["y_topo"]):
                tem_disc = True
                o.append(f'<polyline points="{_onda(pt["lit"], Y(d["y_topo"]), pt["ind"], Y(d["y_topo"]), 1.3, 5)}" '
                         f'fill="none" stroke="{TINTA}" stroke-width="0.9"/>')
        # indícios
        ultimo = {}
        for c in sorted(p["indicios"], key=lambda c: -c["y_topo"]):
            yc = Y((c["y_topo"] + c["y_base"]) / 2)
            if not dentro((c["y_topo"] + c["y_base"]) / 2):
                continue
            f = "oleo" if c["fluido"].startswith("ó") or c["fluido"].startswith("o") else \
                "gas" if c["fluido"].startswith("g") else None
            if not f or abs(ultimo.get(f, -99) - yc) < 4:
                continue
            ultimo[f] = yc
            fluidos_usados.add(f)
            cx = pt["ind"] + w_ind / 2
            tit = f"<title>{escape(p['id'])}: indício de {escape(c['fluido'])} {_fmt(c['topo'])} m</title>"
            if f == "oleo":
                o.append(f'<circle cx="{cx:.1f}" cy="{yc:.1f}" r="2.3" fill="{TINTA}">{tit}</circle>')
            else:
                o.append(f'<path d="M{cx - 2.6:.1f} {yc:.1f}H{cx + 2.6:.1f}M{cx - 1.3:.1f} {yc - 2.3:.1f}L{cx + 1.3:.1f} '
                         f'{yc + 2.3:.1f}M{cx + 1.3:.1f} {yc - 2.3:.1f}L{cx - 1.3:.1f} {yc + 2.3:.1f}" '
                         f'stroke="{TINTA}" stroke-width="0.9">{tit}</path>')
        # escala de profundidade medida
        if p.get("md_y"):
            px_100 = abs(Yl(0) - Yl(100))
            rot_passo = next((s for s in (50, 100, 250, 500, 1000) if px_100 * s / 100 >= 16), 1000)
            for md, yv in p["md_y"]:
                if not dentro(yv):
                    continue
                y = Y(yv)
                grande = md % rot_passo == 0
                o.append(f'<line x1="{pt["lit"] - (4 if grande else 2):.1f}" y1="{y:.1f}" x2="{pt["lit"]:.1f}" '
                         f'y2="{y:.1f}" stroke="{TINTA}" stroke-width="0.5"/>')
                if grande and md > 0:
                    o.append(_t(pt["lit"] - 5, y + 2.6, f"{md:.0f}", 7, TINTA_2, ancora="end"))
        # GR
        if p["gr"]:
            w_gr = W_GR
            o.append(f'<rect x="{pt["gr"]:.1f}" y="{ya:.1f}" width="{w_gr - 3}" height="{max(0.0, yb - ya):.1f}" '
                     f'fill="#ffffff" stroke="{TINTA_FRACA}" stroke-width="0.5"/>')
            for frac in (1 / 3, 2 / 3):
                xg = pt["gr"] + frac * (w_gr - 3)
                o.append(f'<line x1="{xg:.1f}" y1="{ya:.1f}" x2="{xg:.1f}" y2="{yb:.1f}" stroke="{GRADE}" stroke-width="0.4"/>')
            seg, cur = [], []
            for yv, gv in zip(p["gr"]["y"], p["gr"]["valores"]):
                fora_poco = (p["y_mesa"] is not None and yv > p["y_mesa"]) or \
                    (p["y_fundo"] is not None and yv < p["y_fundo"])
                if gv is None or not dentro(yv) or fora_poco:
                    if len(cur) > 1:
                        seg.append(cur)
                    cur = []
                    continue
                cur.append(f"{pt['gr'] + min(max(gv, 0), 150) / 150 * (w_gr - 3):.1f},{Y(yv):.1f}")
            if len(cur) > 1:
                seg.append(cur)
            for sgm in seg:
                o.append(f'<polyline points="{" ".join(sgm)}" fill="none" stroke="{COR_GR}" stroke-width="0.8"/>')
            o.append(_t(pt["gr"] + (w_gr - 3) / 2, y_cima - 4, "GR 0–150 API", 6.5, COR_GR))
        # fundo do poço
        if p["y_fundo"] is not None and dentro(p["y_fundo"]):
            yf = Y(p["y_fundo"])
            o.append(f'<line x1="{pt["lit"] - 4:.1f}" y1="{yf:.1f}" x2="{pt["fm"] + w_fm + 4:.1f}" y2="{yf:.1f}" '
                     f'stroke="{TINTA}" stroke-width="1.6"/>')
            o.append(_t(pt["lit"] + w_lit / 2, yf + 11, f'PF {_fmt(p["prof_final"], 0)}', 8, TINTA_2))
        # cabeçalho do poço
        cx = pt["lit"] + w_lit / 2
        classes_usadas.add(p.get("classe", "outro"))
        o.append(simbolo_poco(cx, topo_area - 66, p.get("classe", "outro")))
        o.append(_t(cx, topo_area - 44, p["id"], 9.5, peso="bold"))
        sub = []
        if p["mesa"] is not None:
            sub.append(f'MR {_fmt(p["mesa"], 0)} m')
        if p["prof_final"]:
            sub.append(f'PF {_fmt(p["prof_final"], 0)} m')
        o.append(_t(cx, topo_area - 32, " · ".join(sub), 7.5, TINTA_2))
        if i:
            d = p["x_km"] - pocos[i - 1]["x_km"]
            cxa = partes(i - 1)["lit"] + w_lit / 2
            o.append(f'<line x1="{cxa + 8:.1f}" y1="{topo_area - 86:.1f}" x2="{cx - 8:.1f}" y2="{topo_area - 86:.1f}" '
                     f'stroke="{TINTA_FRACA}" stroke-width="0.5"/>')
            o.append(_t((cxa + cx) / 2, topo_area - 90, f"{_fmt(d, 1)} km" if d >= 0.05 else "< 0,1 km", 7.5, TINTA_2))

    # datum
    if nivelado and y_min < 0 < y_max:
        o.append(f'<line x1="{esq}" y1="{Yl(0):.1f}" x2="{x_dir:.1f}" y2="{Yl(0):.1f}" stroke="#b3261e" '
                 f'stroke-width="1.4" stroke-dasharray="8,3"/>')
        rotulo_d = f"DATUM: topo da {nome_datum}"
        o.append(f'<rect x="{esq + 3}" y="{Yl(0) - 13:.1f}" width="{len(rotulo_d) * 4.9 + 6:.0f}" height="11" '
                 f'fill="#ffffff" fill-opacity="0.9"/>')
        o.append(_t(esq + 6, Yl(0) - 4, rotulo_d, 8, "#b3261e", ancora="start", peso="bold"))
    elif not nivelado and y_min < 0 < y_max:
        o.append(f'<line x1="{esq}" y1="{Yl(0):.1f}" x2="{x_dir:.1f}" y2="{Yl(0):.1f}" stroke="{TINTA_FRACA}" '
                 f'stroke-width="0.6" stroke-dasharray="3,3"/>')
        o.append(_t(x_dir - 4, Yl(0) - 3, "nível do mar", 7.5, TINTA_FRACA, ancora="end"))
    o.append(f'<rect x="{esq}" y="{y_cima}" width="{largura_plot:.1f}" height="{alt}" fill="none" '
             f'stroke="{TINTA}" stroke-width="1"/>')

    # pontas A – A'
    e, d = modelo["pontas"]
    o.append(_t(esq, 34, "A", 18, peso="bold", ancora="start"))
    o.append(_t(esq + 18, 34, f"({e})", 9, TINTA_2, ancora="start"))
    o.append(_t(x_dir, 34, "A′", 18, peso="bold", ancora="end"))
    o.append(_t(x_dir - 24, 34, f"({d})", 9, TINTA_2, ancora="end"))
    if titulo:
        o.append(_t((esq + x_dir) / 2, 30, titulo, 13, peso="bold"))

    # ---------------------------------------------------- painel inferior
    y_p = y_baixo + 30
    m_por_px_v = (y_max - y_min) / alt
    exag = None
    if par["espacamento"] != "igual" and modelo["comprimento_km"] > 0:
        m_por_px_h = modelo["comprimento_km"] * 1000 / ((xs[-1] - xs[0]) or 1)
        exag = m_por_px_h / m_por_px_v
        if not ajustado:     # escala gráfica horizontal sob a seção
            alvo = 160 * m_por_px_h / 1000
            km = next((k for k in (0.5, 1, 2, 5, 10, 20, 50) if k >= alvo), 50)
            L = km * 1000 / m_por_px_h
            xb0 = esq
            for k in range(4):
                o.append(f'<rect x="{xb0 + k * L / 4:.1f}" y="{y_baixo + 10}" width="{L / 4:.1f}" height="4" '
                         f'fill="{TINTA if k % 2 == 0 else "#ffffff"}" stroke="{TINTA}" stroke-width="0.5"/>')
            o.append(_t(xb0, y_baixo + 24, "0", 7.5, ancora="middle"))
            o.append(_t(xb0 + L, y_baixo + 24, f"{_fmt(km, 1 if km < 1 else 0)} km", 7.5))
    if ajustado:
        o.append(_t(esq, y_baixo + 18, "Espaçamento entre poços ajustado para leitura: use as distâncias "
                    "indicadas no topo.", 7.5, TINTA_2, ancora="start"))

    largura_mapa, largura_carimbo = 230, 300
    largura_leg = largura_painel - largura_mapa - largura_carimbo - 24
    # legenda
    itens_lit = [v for k, v in lit_usadas.items()]
    itens_fm = [(pastel(u["cor"]), abreviar(u["nome"])) for u in leg]
    itens_sim = [(c, ROTULO_CLASSE[c]) for c in ("oleo", "oleo_gas", "gas", "seco", "outro") if c in classes_usadas]
    linhas_sim = len(itens_sim) + len(fluidos_usados) + (1 if tem_disc else 0) + 1 + (1 if tem_gr else 0) + \
        (1 if nivelado else 0)
    linhas = max(len(itens_lit), len(itens_fm), linhas_sim)
    alt_painel = max(170, 34 + 15 * linhas)
    o.append(f'<rect x="{esq}" y="{y_p}" width="{largura_leg:.1f}" height="{alt_painel}" fill="#ffffff" '
             f'stroke="{TINTA}" stroke-width="0.8"/>')
    col = largura_leg / 3
    for k, cab in enumerate(("Litologia (calha)", "Unidades", "Símbolos")):
        o.append(_t(esq + 10 + k * col, y_p + 16, cab, 9, peso="bold", ancora="start"))
    for k, (nome, cor, pat) in enumerate(itens_lit):
        yy = y_p + 26 + k * 15
        o.append(bloco_litologico(esq + 10, yy, 22, 11, cor, pat))
        o.append(f'<rect x="{esq + 10}" y="{yy}" width="22" height="11" fill="none" stroke="{TINTA}" stroke-width="0.5"/>')
        o.append(_t(esq + 38, yy + 9, nome, 8, ancora="start"))
    for k, (cor, nome) in enumerate(itens_fm):
        yy = y_p + 26 + k * 15
        xx = esq + 10 + col
        o.append(f'<rect x="{xx:.1f}" y="{yy}" width="22" height="11" fill="{cor}" stroke="{TINTA}" stroke-width="0.5"/>')
        o.append(_t(xx + 28, yy + 9, nome, 8, ancora="start"))
    xx = esq + 10 + 2 * col
    yy = y_p + 26
    for c, nome in itens_sim:
        o.append(simbolo_poco(xx + 8, yy + 5, c, 4))
        o.append(_t(xx + 28, yy + 9, nome, 8, ancora="start"))
        yy += 15
    if "oleo" in fluidos_usados:
        o.append(f'<circle cx="{xx + 8:.1f}" cy="{yy + 5:.1f}" r="2.3" fill="{TINTA}"/>')
        o.append(_t(xx + 28, yy + 9, "Indício de óleo (AGP)", 8, ancora="start"))
        yy += 15
    if "gas" in fluidos_usados:
        cx = xx + 8
        o.append(f'<path d="M{cx - 2.6:.1f} {yy + 5:.1f}H{cx + 2.6:.1f}M{cx - 1.3:.1f} {yy + 2.7:.1f}L{cx + 1.3:.1f} '
                 f'{yy + 7.3:.1f}M{cx + 1.3:.1f} {yy + 2.7:.1f}L{cx - 1.3:.1f} {yy + 7.3:.1f}" stroke="{TINTA}" stroke-width="0.9"/>')
        o.append(_t(xx + 28, yy + 9, "Indício de gás (AGP)", 8, ancora="start"))
        yy += 15
    o.append(f'<line x1="{xx}" y1="{yy + 5}" x2="{xx + 18}" y2="{yy + 5}" stroke="{TINTA}" stroke-width="0.8"/>')
    o.append(_t(xx + 28, yy + 9, "Topo de unidade (AGP)", 8, ancora="start"))
    yy += 15
    if tem_disc:
        o.append(f'<polyline points="{_onda(xx, yy + 5, xx + 18, yy + 5)}" fill="none" stroke="{TINTA}" stroke-width="1"/>')
        o.append(_t(xx + 28, yy + 9, "Discordância (AGP)", 8, ancora="start"))
        yy += 15
    if nivelado:
        o.append(f'<line x1="{xx}" y1="{yy + 5}" x2="{xx + 18}" y2="{yy + 5}" stroke="#b3261e" stroke-width="1.4" '
                 f'stroke-dasharray="5,2"/>')
        o.append(_t(xx + 28, yy + 9, "Datum", 8, ancora="start"))
        yy += 15
    if tem_gr:
        o.append(f'<line x1="{xx}" y1="{yy + 5}" x2="{xx + 18}" y2="{yy + 5}" stroke="{COR_GR}" stroke-width="1"/>')
        o.append(_t(xx + 28, yy + 9, "Raios gama, 0–150 API", 8, ancora="start"))

    # mapa de localização
    xm = esq + largura_leg + 12
    o.append(f'<rect x="{xm:.1f}" y="{y_p}" width="{largura_mapa}" height="{alt_painel}" fill="#ffffff" '
             f'stroke="{TINTA}" stroke-width="0.8"/>')
    o.append(_t(xm + 10, y_p + 16, "Localização", 9, peso="bold", ancora="start"))
    px, py = _plano([p["lat"] for p in pocos], [p["lon"] for p in pocos])
    ext = max(float(px.max() - px.min()), float(py.max() - py.min()), 0.5)
    caixa = min(largura_mapa - 40, alt_painel - 56)
    cxm, cym = xm + largura_mapa / 2, y_p + 28 + (alt_painel - 40) / 2
    kx = caixa / ext

    def M(i):
        return cxm + (px[i] - (px.max() + px.min()) / 2) * kx, cym - (py[i] - (py.max() + py.min()) / 2) * kx
    pontos = [M(i) for i in range(n)]
    o.append(f'<polyline points="{" ".join(f"{a:.1f},{b:.1f}" for a, b in pontos)}" fill="none" '
             f'stroke="{TINTA_2}" stroke-width="0.8"/>')
    for (a, b) in pontos:
        o.append(f'<circle cx="{a:.1f}" cy="{b:.1f}" r="2" fill="{TINTA}"/>')
    o.append(_t(pontos[0][0] - 6, pontos[0][1] - 5, "A", 9, peso="bold"))
    o.append(_t(pontos[-1][0] + 7, pontos[-1][1] - 5, "A′", 9, peso="bold"))
    # norte e escala
    xn, yn = xm + largura_mapa - 18, y_p + 26
    o.append(f'<path d="M{xn} {yn}l-5 14l5 -4l5 4z" fill="{TINTA}"/>')
    o.append(_t(xn, yn + 24, "N", 8, peso="bold"))
    km_m = next((k for k in (0.5, 1, 2, 5, 10, 20, 50) if k * kx >= 30), 50)
    xs0, ys0 = xm + 12, y_p + alt_painel - 12
    o.append(f'<line x1="{xs0}" y1="{ys0}" x2="{xs0 + km_m * kx:.1f}" y2="{ys0}" stroke="{TINTA}" stroke-width="1.4"/>')
    o.append(_t(xs0 + km_m * kx / 2, ys0 - 4, f"{_fmt(km_m, 1 if km_m < 1 else 0)} km", 7.5))

    # carimbo
    xc = xm + largura_mapa + 12
    o.append(f'<rect x="{xc:.1f}" y="{y_p}" width="{largura_carimbo}" height="{alt_painel}" fill="#ffffff" '
             f'stroke="{TINTA}" stroke-width="0.8"/>')
    campos = sorted({p["campo"] for p in pocos if p["campo"]})
    bacias = sorted({re.sub(r"\s*\(.*\)", "", p.get("bacia") or "").title() for p in pocos if p.get("bacia")})
    linhas_c = [
        ("SEÇÃO ESTRATIGRÁFICA A–A′", 11, "bold"),
        (titulo or ", ".join(c.title() for c in campos[:3]) or "", 9, "normal"),
        (("Bacia " + ", ".join(bacias)) if bacias else "", 8.5, "normal"),
        (f"Datum: topo da {nome_datum}" if nivelado else "Referência vertical: nível do mar (cota do AGP)", 8.5, "normal"),
        (f"{n} poços · {_fmt(modelo['comprimento_km'], 1)} km" +
         (f" · exagero vertical ≈ {exag:,.0f}×".replace(",", ".") if exag else ""), 8.5, "normal"),
        ("Topos e litologia: AGP (ANP, portal REATE)" + (" · GR: perfis do poço" if tem_gr else ""), 7.5, "normal"),
        ("Topos interpretados pela operadora; litologia de amostras de calha", 7.5, "normal"),
        ("Cores e padrões de rocha: legenda dos perfis compostos da Petrobras", 7.5, "normal"),
        (f"Elaboração: {autor or '—'} · {data or ''}", 7.5, "normal"),
        (f"SIAPP {__version__}", 7.5, "normal"),
    ]
    yy = y_p + 18
    for k, (txt, tam, peso) in enumerate(linhas_c):
        if not txt:
            continue
        o.append(_t(xc + 10, yy, txt, tam, ancora="start", peso=peso, cor=TINTA if k < 5 else TINTA_2))
        if k == 0:
            o.append(f'<line x1="{xc:.1f}" y1="{yy + 7}" x2="{xc + largura_carimbo:.1f}" y2="{yy + 7}" '
                     f'stroke="{TINTA}" stroke-width="0.6"/>')
            yy += 8
        yy += tam + 7

    H = y_p + alt_painel + 16
    cab = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}" '
           f'viewBox="0 0 {W:.0f} {H:.0f}" font-family="{FONTE}">',
           f'<rect width="{W:.0f}" height="{H:.0f}" fill="#ffffff"/>']
    return "\n".join(cab + o + ["</svg>"])
