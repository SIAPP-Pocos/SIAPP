"""Mapa 2D do bloco com curvas de nível (0.56).

Um mapa de cima do terreno, do topo ou da espessura (isópaca) de cada camada ou zona produtora, no estilo dos mapas
estruturais de artigo: cor por faixa de valor, **curvas de nível rotuladas** a cada N metros, poços em círculos
brancos, eixos em **metros locais** (a partir do centro do bloco) e barra de cores. Sai em SVG (e, pelo mesmo caminho
das outras figuras do bloco, PDF e PNG), sem biblioteca de gráficos: as curvas vêm de um *marching squares* próprio.

Os valores são os mesmos dos mapas para SIG (motor/bloco_mapas.py): a grade UTM do bloco, recortada no contorno dos
poços (mais a margem pedida na montagem do bloco). Fora do contorno não há dado, não se desenha nada.
"""

from __future__ import annotations

import math
from collections import defaultdict

import numpy as np

from . import __version__
from . import bloco_figura as mbf
from . import bloco_mapas as mbm
from . import bloco_solido as mbs
from . import utm

PALETAS = {
    "viridis": ["#440154", "#472d7b", "#3b528b", "#2c728e", "#21918c", "#28ae80", "#5ec962", "#addc30", "#fde725"],
    "plasma": ["#0d0887", "#6a00a8", "#b12a90", "#e16462", "#fca636", "#f0f921"],
    "azuis": mbf.RAMPA,
    "terra": ["#2b5d34", "#6b9a45", "#c9c36a", "#d6a85c", "#a8703f", "#6b4a32", "#f1ece4"],
    "cinza": ["#f4f4f4", "#9a9a9a", "#202020"],
}
NOMES_PALETAS = {"viridis": "viridis", "plasma": "plasma", "azuis": "azuis (padrão do SIAPP)", "terra": "relevo",
                 "cinza": "tons de cinza"}
NIVEIS_COR = 48
MAX_LADO = 200                # células por lado na grade do desenho


class ErroMapa2D(Exception):
    pass


# ----------------------------------------------------------------------------- cores
def cor_da_paleta(paleta: str, t: float, inverter: bool = False) -> str:
    pts = PALETAS.get(paleta) or PALETAS["viridis"]
    t = min(1.0, max(0.0, t))
    if inverter:
        t = 1.0 - t
    f = t * (len(pts) - 1)
    k = min(len(pts) - 2, int(f))
    return mbf._cor(mbf._hex(pts[k]) + (f - k) * (mbf._hex(pts[k + 1]) - mbf._hex(pts[k])))


# ----------------------------------------------------------------------------- curvas de nível
# casos do marching squares: bits a (canto NO)=1, b (NE)=2, c (SE)=4, d (SO)=8; arestas T, R, B, L
_CASOS = {1: [("L", "T")], 2: [("T", "R")], 3: [("L", "R")], 4: [("R", "B")], 6: [("T", "B")], 7: [("L", "B")],
          8: [("L", "B")], 9: [("T", "B")], 11: [("R", "B")], 12: [("L", "R")], 13: [("T", "R")], 14: [("L", "T")]}


def curvas(z: np.ndarray, xs: np.ndarray, ys: np.ndarray, nivel: float) -> list[tuple[bool, np.ndarray]]:
    """Linhas do `nivel`: [(fechada, pontos (n × 2) em x, y)]. Células com algum canto sem dado ficam de fora."""
    ny, nx = z.shape
    ok = np.isfinite(z)
    alto = np.where(ok, z > nivel, False)
    celula_ok = ok[:-1, :-1] & ok[:-1, 1:] & ok[1:, 1:] & ok[1:, :-1]
    caso = (alto[:-1, :-1] * 1 + alto[:-1, 1:] * 2 + alto[1:, 1:] * 4 + alto[1:, :-1] * 8)
    caso = np.where(celula_ok, caso, 0)

    def chave(borda, i, j):
        return {"T": ("h", i, j), "B": ("h", i + 1, j), "L": ("v", i, j), "R": ("v", i, j + 1)}[borda]

    segs = []
    for i, j in zip(*np.nonzero((caso > 0) & (caso < 15))):
        i, j, c = int(i), int(j), int(caso[i, j])
        if c in (5, 10):                           # sela: decide pelo centro da célula
            centro = (z[i, j] + z[i, j + 1] + z[i + 1, j + 1] + z[i + 1, j]) / 4.0 > nivel
            if c == 5:
                pares = [("L", "B"), ("T", "R")] if centro else [("L", "T"), ("R", "B")]
            else:
                pares = [("L", "T"), ("R", "B")] if centro else [("T", "R"), ("L", "B")]
        else:
            pares = _CASOS[c]
        for a, b in pares:
            segs.append((chave(a, i, j), chave(b, i, j)))
    if not segs:
        return []

    def ponto(k):
        t, i, j = k
        if t == "h":
            z1, z2 = z[i, j], z[i, j + 1]
            f = (nivel - z1) / (z2 - z1) if z2 != z1 else 0.5
            return xs[j] + f * (xs[j + 1] - xs[j]), ys[i]
        z1, z2 = z[i, j], z[i + 1, j]
        f = (nivel - z1) / (z2 - z1) if z2 != z1 else 0.5
        return xs[j], ys[i] + f * (ys[i + 1] - ys[i])

    viz = defaultdict(list)
    for n, (a, b) in enumerate(segs):
        viz[a].append(n)
        viz[b].append(n)
    usado = [False] * len(segs)

    def seguir(n, de):
        """Caminha a partir do segmento `n`, saindo pela ponta oposta a `de`."""
        cadeia = []
        atual = segs[n][1] if segs[n][0] == de else segs[n][0]
        while True:
            cadeia.append(atual)
            prox = [m for m in viz[atual] if not usado[m]]
            if not prox:
                return cadeia
            m = prox[0]
            usado[m] = True
            atual = segs[m][1] if segs[m][0] == atual else segs[m][0]

    saida = []
    for n, (a, b) in enumerate(segs):
        if usado[n]:
            continue
        usado[n] = True
        frente = seguir(n, a)                      # a → b → …
        tras = seguir(n, b) if frente[-1] != a else []
        cadeia = list(reversed(tras)) + [a] + frente if tras else [a] + frente
        fechada = len(cadeia) > 2 and cadeia[0] == cadeia[-1]
        saida.append((fechada, np.array([ponto(k) for k in cadeia], float)))
    return saida


# ----------------------------------------------------------------------------- dados do mapa
def _grade(modelo: dict, passo_m: float | None):
    gu = mbm.grade_utm(modelo, passo_m)
    if passo_m is None:                            # desenho leve: no máximo ~MAX_LADO células por lado
        for p in mbm.PASSOS_M:
            if p >= gu["passo"] and max(gu["nx"], gu["ny"]) <= MAX_LADO:
                break
            if p > gu["passo"]:
                gu = mbm.grade_utm(modelo, p)
    return gu


def lista(modelo: dict, passo_m: float | None = None) -> list[dict]:
    """Os mapas que dá para desenhar: [{nome, titulo, min, max, cota}]."""
    gu = _grade(modelo, passo_m)
    out = []
    for m in mbm.mapas(modelo, gu):
        z = m["z"]
        out.append({"nome": m["nome"], "titulo": m["titulo"], "min": float(np.nanmin(z)), "max": float(np.nanmax(z)),
                    "cota": "cota" in m["titulo"]})
    return out


def _niveis(zmin: float, zmax: float, intervalo: float | None) -> tuple[float, list[float]]:
    faixa = zmax - zmin
    if faixa < 1e-6:                                   # mapa plano (ex.: terreno com o mesmo valor em todos os poços): sem curvas
        return float(intervalo) if intervalo and intervalo > 0 else 1.0, []
    if intervalo is None or intervalo <= 0:
        intervalo = mbf._passo(faixa, 12)
    if faixa / intervalo > 200:
        raise ErroMapa2D(f"Curvas demais ({faixa / intervalo:.0f}): use um intervalo maior que {intervalo:g} m.")
    eps = intervalo * 1e-6
    k0 = math.ceil(zmin / intervalo - 1e-6)
    niveis, k = [], k0
    while k * intervalo <= zmax + eps and len(niveis) <= 400:
        niveis.append(round(k * intervalo, 6))
        k += 1
    return float(intervalo), niveis


# ----------------------------------------------------------------------------- desenho
def desenhar(modelo: dict, nome: str, *, intervalo_m: float | None = None, rotulo_cada: int = 1, paleta: str = "viridis",
             inverter: bool = False, profundidade: bool = False, desde_mesa: bool = False, preencher: bool = True, curvas_nivel: bool = True,
             pocos: bool = True, nomes_pocos: bool = False, titulo: str = "", passo_m: float | None = None) -> dict:
    """Desenha o mapa `nome` (de `lista`). Devolve {svg, intervalo_m, niveis, min, max, titulo}.
    `profundidade`: cota → profundidade positiva abaixo do nível do mar; com `desde_mesa`, abaixo da mesa rotativa
    (a mesa de cada poço, interpolada entre eles): é a profundidade da tabela feita à mão, medida desde a mesa."""
    if paleta not in PALETAS:
        raise ErroMapa2D(f"Paleta desconhecida: {paleta}.")
    gu = _grade(modelo, passo_m)
    todos = {m["nome"]: m for m in mbm.mapas(modelo, gu)}
    if nome not in todos:
        raise ErroMapa2D("Esse mapa não existe neste bloco (escolha outro na lista).")
    m = todos[nome]
    z = np.asarray(m["z"], float)
    texto_titulo = m["titulo"]
    if profundidade and "cota" in texto_titulo:        # cota (negativa abaixo do mar) → profundidade (positiva)
        if desde_mesa:
            mesas = [(q["x"], q["y"], float(q["mesa"])) for q in modelo["pocos"] if q.get("mesa") is not None]
            if not mesas:
                raise ErroMapa2D("Os poços deste bloco não têm a mesa rotativa no cadastro.")
            zm, _ = mbs.interpolar_grade([a[:2] for a in mesas], [a[2] for a in mesas], modelo["grade"])
            z = mbs.bilinear(zm, modelo["grade"], gu["x"], gu["y"]) - z
            texto_titulo = texto_titulo.replace("cota, m", "profundidade abaixo da mesa rotativa, m")
        else:
            z = -z
            texto_titulo = texto_titulo.replace("cota, m", "profundidade abaixo do nível do mar, m")
    zmin, zmax = float(np.nanmin(z)), float(np.nanmax(z))
    intervalo, niveis = _niveis(zmin, zmax, intervalo_m)

    # coordenadas locais em metros, a partir do centro do bloco
    o = modelo["origem"]
    e0, n0 = (float(v[0]) for v in utm.para_utm(np.array([o["lat"]]), np.array([o["lon"]]), gu["fuso"], gu["sul"]))
    p = gu["passo"]
    xs = gu["E"][0, :] - e0
    ys = gu["N"][:, 0] - n0
    pe, pn = utm.para_utm(np.array([q["lat"] for q in modelo["pocos"]], float),
                          np.array([q["lon"] for q in modelo["pocos"]], float), gu["fuso"], gu["sul"])
    pocos_xy = [(q["id"], float(e - e0), float(nn - n0)) for q, e, nn in zip(modelo["pocos"], pe, pn)]
    return desenhar_grade(z, xs, ys, p, pocos_xy, texto_titulo, intervalo_m=intervalo_m, rotulo_cada=rotulo_cada,
                          paleta=paleta, inverter=inverter, preencher=preencher, curvas_nivel=curvas_nivel,
                          pocos=pocos, nomes_pocos=nomes_pocos, titulo=titulo)


def desenhar_grade(z: np.ndarray, xs: np.ndarray, ys: np.ndarray, p: float, pocos_xy: list, texto_titulo: str, *,
                   intervalo_m: float | None = None, rotulo_cada: int = 1, paleta: str = "viridis", inverter: bool = False,
                   preencher: bool = True, curvas_nivel: bool = True, pocos: bool = True, nomes_pocos: bool = False,
                   titulo: str = "") -> dict:
    """Desenha uma grade qualquer: `z` (linhas do norte para o sul), `xs`/`ys` (m, centros dos pixels), `p` (pixel, m),
    `pocos_xy` [(nome, x, y)] em metros. É o que `desenhar` usa; serve também para comparar com grades de fora do SIAPP."""
    zmin, zmax = float(np.nanmin(z)), float(np.nanmax(z))
    intervalo, niveis = _niveis(zmin, zmax, intervalo_m)
    ny, nx = z.shape
    dx, dy = nx * p, ny * p

    esc = 720.0 / dx
    if dy * esc > 600:
        esc = 600.0 / dy
    larg_plot, alt_plot = dx * esc, dy * esc
    x0, y0 = 95.0, 60.0
    W, H = x0 + larg_plot + 150, y0 + alt_plot + 95
    xmin, ymax = xs[0] - p / 2, ys[0] + p / 2

    def X(x):
        return x0 + (x - xmin) * esc

    def Y(y):
        return y0 + (ymax - y) * esc

    t = mbf._t
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}" viewBox="0 0 {W:.0f} {H:.0f}">',
         f'<rect width="{W:.0f}" height="{H:.0f}" fill="#ffffff"/>',
         f'<defs><clipPath id="area"><rect x="{x0:.1f}" y="{y0:.1f}" width="{larg_plot:.1f}" height="{alt_plot:.1f}"/>'
         f'</clipPath></defs>']
    s.append(t(x0, 32, titulo.strip() or texto_titulo, 17, mbf.TINTA, "start", "bold"))

    plano = (zmax - zmin) < 1e-6                      # mapa plano (mesmo valor em todo lugar, ou só ruído de ponto flutuante)

    def idx(v):
        return 0 if plano else min(NIVEIS_COR - 1, max(0, int((v - zmin) / (zmax - zmin) * NIVEIS_COR)))

    cores = [cor_da_paleta(paleta, (k + 0.5) / NIVEIS_COR, inverter) for k in range(NIVEIS_COR)]
    s.append('<g clip-path="url(#area)">')
    if preencher:
        s.append('<g shape-rendering="crispEdges">')
        for i in range(ny):
            j = 0
            while j < nx:
                if not np.isfinite(z[i, j]):
                    j += 1
                    continue
                k, j2 = idx(z[i, j]), j
                while j2 + 1 < nx and np.isfinite(z[i, j2 + 1]) and idx(z[i, j2 + 1]) == k:
                    j2 += 1
                s.append(f'<rect x="{X(xs[j] - p / 2):.2f}" y="{Y(ys[i] + p / 2):.2f}" '
                         f'width="{(j2 - j + 1) * p * esc + 0.6:.2f}" height="{p * esc + 0.6:.2f}" fill="{cores[k]}"/>')
                j = j2 + 1
        s.append("</g>")
    rotulos = []
    if curvas_nivel:
        s.append(f'<g fill="none" stroke="{"#1c2227" if preencher else mbf.TINTA}" stroke-width="0.8" '
                 'stroke-linejoin="round" stroke-linecap="round" opacity="0.85">')
        colocados: list[tuple[float, float]] = []
        for n, nivel in enumerate(niveis):
            for fechada, pts in curvas(z, xs, ys, nivel):
                px, py = X(pts[:, 0]), Y(pts[:, 1])
                if len(pts) < 2:
                    continue
                s.append('<path d="M' + " L".join(f"{a:.1f},{b:.1f}" for a, b in zip(px, py)) + ('Z"/>' if fechada else '"/>'))
                if rotulo_cada and rotulo_cada > 0 and n % int(rotulo_cada) == 0:
                    comp = np.concatenate([[0], np.cumsum(np.hypot(np.diff(px), np.diff(py)))])
                    if comp[-1] < 70:
                        continue
                    k = int(np.searchsorted(comp, comp[-1] / 2))
                    k = min(max(k, 1), len(px) - 1)
                    a, b = max(0, k - 2), min(len(px) - 1, k + 2)
                    ang = math.degrees(math.atan2(py[b] - py[a], px[b] - px[a]))
                    ang = ang + 180 if ang > 90 else ang - 180 if ang < -90 else ang
                    cx, cy = float(px[k]), float(py[k])
                    if x0 + 14 < cx < x0 + larg_plot - 14 and y0 + 8 < cy < y0 + alt_plot - 8 and all(
                            math.hypot(cx - u, cy - v) > 38 for u, v in colocados):
                        colocados.append((cx, cy))
                        rotulos.append((cx, cy + 3.2, nivel, ang))
        s.append("</g>")
        casas = 0 if intervalo >= 1 or abs(intervalo - round(intervalo)) < 1e-9 else (1 if intervalo >= 0.1 else 2)
        for cx, cy, nivel, ang in rotulos:
            txt = mbf._fmt(nivel, casas)
            s.append(mbf._t(cx, cy, txt, 9, "#ffffff", "middle", "bold", rot=ang).replace(
                'fill="#ffffff"', 'fill="#ffffff" stroke="#ffffff" stroke-width="3" stroke-linejoin="round"'))
            s.append(mbf._t(cx, cy, txt, 9, "#1c2227", "middle", "bold", rot=ang))
    if pocos:
        for nome_p, e, nn in pocos_xy:
            cx, cy = X(e), Y(nn)
            s.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="4.2" fill="#ffffff" stroke="#1c2227" stroke-width="1.2"/>')
            if nomes_pocos:
                s.append(mbf._t(cx + 6, cy - 5, nome_p.replace("-RN", ""), 8.5, mbf.TINTA))
    s.append("</g>")

    # moldura e eixos
    s.append(f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{larg_plot:.1f}" height="{alt_plot:.1f}" fill="none" '
             f'stroke="{mbf.TINTA}" stroke-width="1"/>')
    pas = mbf._passo(max(dx, dy), 6)
    v = math.ceil(xmin / pas) * pas
    while v <= xmin + dx:
        s.append(f'<line x1="{X(v):.1f}" y1="{y0 + alt_plot:.1f}" x2="{X(v):.1f}" y2="{y0 + alt_plot + 4:.1f}" stroke="{mbf.TINTA}"/>')
        s.append(t(X(v), y0 + alt_plot + 17, mbf._fmt(v), 10, mbf.TINTA, "middle"))
        v += pas
    v = math.ceil((ymax - dy) / pas) * pas
    while v <= ymax:
        s.append(f'<line x1="{x0 - 4:.1f}" y1="{Y(v):.1f}" x2="{x0:.1f}" y2="{Y(v):.1f}" stroke="{mbf.TINTA}"/>')
        s.append(t(x0 - 7, Y(v) + 3.5, mbf._fmt(v), 10, mbf.TINTA, "end"))
        v += pas
    s.append(t(x0 + larg_plot / 2, y0 + alt_plot + 36, "Leste (m)", 11, mbf.TINTA2, "middle"))
    s.append(t(20, y0 + alt_plot / 2, "Norte (m)", 11, mbf.TINTA2, "middle", rot=-90))

    # barra de cores
    bx, bw = x0 + larg_plot + 28, 18
    bh = min(alt_plot, 300.0)
    by = y0 + (alt_plot - bh) / 2
    for k in range(NIVEIS_COR):
        s.append(f'<rect x="{bx:.1f}" y="{by + bh * (1 - (k + 1) / NIVEIS_COR):.2f}" width="{bw}" '
                 f'height="{bh / NIVEIS_COR + 0.6:.2f}" fill="{cores[k]}"/>')
    s.append(f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bw}" height="{bh:.1f}" fill="none" stroke="{mbf.TINTA}"/>')
    pb = 1.0 if plano else mbf._passo(zmax - zmin, 5)
    v = math.ceil(zmin / pb) * pb
    while v <= zmax + pb * 1e-6 and len(s) < 200000:
        yy = by + bh / 2 if plano else by + bh * (1 - (v - zmin) / (zmax - zmin))
        s.append(f'<line x1="{bx + bw:.1f}" y1="{yy:.1f}" x2="{bx + bw + 4:.1f}" y2="{yy:.1f}" stroke="{mbf.TINTA}"/>')
        s.append(t(bx + bw + 7, yy + 3.5, mbf._fmt(v, 0 if pb >= 1 else 1), 10, mbf.TINTA, "start"))
        v += pb
    s.append(t(bx, by - 8, "m", 10, mbf.TINTA2, "start"))
    s.append(t(x0, H - 14, f"Curvas de nível a cada {mbf._fmt(intervalo, 0 if intervalo >= 1 else 1)} m · coordenadas em metros "
                           f"a partir do centro do bloco · pixel de {p:g} m · SIAPP {__version__}", 9.5, mbf.TINTA2))
    s.append("</svg>")
    return {"svg": "\n".join(s), "intervalo_m": intervalo, "niveis": niveis, "min": zmin, "max": zmax,
            "titulo": texto_titulo, "rotulos": len(rotulos)}
