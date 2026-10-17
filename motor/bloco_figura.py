"""Figura estática do bloco 3D no estilo artigo (SVG → PNG 300 ppp / PDF vetorial).

A mesma vista do visor (azimute, elevação e exagero vertical), em **projeção ortográfica**
— sem a deformação de perspectiva, que numa figura impressa engana as distâncias. Desenho
pelo algoritmo do pintor: triângulos das superfícies, trechos dos poços, trilhas e
marcas ordenados do fundo para a frente. Sombreamento Lambert com luz fixa (noroeste,
alta), cor da unidade (a mesma da seção) ou da propriedade no topo.

Estilo artigo: fonte serifada, moldura, legenda com moldura, escala de cor, seta do norte,
exagero vertical e a fonte dos dados escritos na figura.

Limites do MuPDF (como na seção): nada de <pattern>, <clipPath> ou fonte herdada — cada
<text> leva a sua fonte.
"""

from __future__ import annotations

import math
import os
from html import escape

import numpy as np

from . import __version__
from . import bloco_solido as mbs

FONTE = "Times New Roman, Times, Liberation Serif, DejaVu Serif, serif"
TINTA, TINTA2, GRADE = "#1c2227", "#5f6b73", "#9aa3a8"
LARGURA, ALTURA = 1100, 770
AREA = (70, 60, 830, 640)            # x0, y0, x1, y1 do desenho
RAMPA = ["#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7", "#3987e5", "#2a78d6",
         "#256abf", "#1c5cab", "#184f95", "#104281", "#0d366b"]
NEUTRO = "#d5d3cc"
MAX_CELULAS_FIG = 70


class ErroFigura(Exception):
    pass


def _hex(c: str) -> np.ndarray:
    c = c.lstrip("#")
    return np.array([int(c[i:i + 2], 16) for i in (0, 2, 4)], float)


def _cor(rgb) -> str:
    r, g, b = (int(max(0, min(255, round(v)))) for v in rgb)
    return f"#{r:02x}{g:02x}{b:02x}"


def cor_rampa(t: float) -> str:
    t = min(1.0, max(0.0, t))
    f = t * (len(RAMPA) - 1)
    k = min(len(RAMPA) - 2, int(f))
    return _cor(_hex(RAMPA[k]) + (f - k) * (_hex(RAMPA[k + 1]) - _hex(RAMPA[k])))


def _t(x, y, texto, tam=11, cor=TINTA, ancora="start", peso="normal", estilo="normal", rot=None):
    r = f' transform="rotate({rot:.1f} {x:.1f} {y:.1f})"' if rot is not None else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{FONTE}" font-size="{tam}" fill="{cor}" '
            f'text-anchor="{ancora}" font-weight="{peso}" font-style="{estilo}"{r}>{escape(str(texto))}</text>')


def _fmt(v, casas=0):
    s = f"{v:,.{casas}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def _passo(faixa, alvo=5):
    bruto = faixa / alvo
    p = 10 ** math.floor(math.log10(bruto)) if bruto > 0 else 1
    for m in (1, 2, 2.5, 5, 10):
        if bruto <= m * p:
            return m * p
    return 10 * p


class _Camera:
    """Projeção ortográfica. Mundo: (leste km, norte km, cima km = cota·exagero/1000)."""

    def __init__(self, az_rad: float, el_rad: float):
        # direção do alvo para a câmera (mesma convenção do visor: azimute a partir do sul)
        self.d = np.array([math.cos(el_rad) * math.sin(az_rad), -math.cos(el_rad) * math.cos(az_rad),
                           math.sin(el_rad)])
        v = -self.d
        cima = np.array([0.0, 0.0, 1.0]) if abs(self.d[2]) < 0.999 else np.array([0.0, 1.0, 0.0])
        self.dir = np.cross(v, cima)
        self.dir /= np.linalg.norm(self.dir)
        self.cima = np.cross(self.dir, v)

    def proj(self, p):
        p = np.asarray(p, float)
        return p @ self.dir, p @ self.cima, p @ self.d          # x, y (para cima), profundidade


def desenhar(modelo: dict, *, azimute: float = -0.61, elevacao: float = 0.61, exagero: float = 10,
             visiveis: list[str] | None = None, trilha: str = "nenhuma", drape: dict | None = None,
             titulo: str = "", autor: str = "", data: str = "", nomes: bool = True,
             opacidade: float = 0.7, modo: str = "superficies", camadas: list[str] | None = None,
             corte: dict | None = None, afastar: float = 0.0, parede: list[str] | None = None) -> str:
    """SVG da vista. `azimute` e `elevacao` em radianos (os do visor). `modo` "fechado": o
    bloco fechado, com `camadas` ligadas, `corte` ({quadrante, fx, fy}), camadas afastadas
    (`afastar`, 0–1) e a parede da seção A–A′ pelos poços `parede`."""
    m = modelo
    g = m["grade"]
    sol = m.get("solido") or {}
    fechado = modo == "fechado" and sol.get("ok")
    if modo == "fechado" and not fechado:
        raise ErroFigura("Este bloco não tem bloco fechado (monte de novo nesta versão).")
    visiveis = set(visiveis) if visiveis is not None else {u["chave"] for u in m["legenda"]}
    cam = _Camera(azimute, elevacao)
    luz = np.array([-0.45, 0.55, 0.7])
    luz /= np.linalg.norm(luz)
    ez = exagero / 1000.0

    def W(x, y, cota):
        return np.array([x, y, cota * ez])

    prims = []      # (profundidade, svg)

    # ---------------------------------------------------------- superfícies
    drape = drape or {}
    prop = m.get("propriedades", {}).get(drape.get("chave", ""), {}) if drape else {}
    grade_prop = (prop.get("grades") or {}).get(drape.get("prop")) if drape else None
    faixa = (prop.get("faixas") or {}).get(drape.get("prop")) if drape else None
    if faixa and faixa[0] == faixa[1]:
        faixa = [faixa[0] - 1e-9, faixa[1] + 1e-9]
    linha_parede = None
    if fechado:
        if parede:
            por_id = {p["id"]: p for p in m["pocos"]}
            pts_p = [[por_id[i]["x"], por_id[i]["y"]] for i in parede if i in por_id]
            linha_parede = mbs.prolongar(pts_p, sol["contorno"]) if len(pts_p) >= 2 else None
        camadas = set(camadas) if camadas is not None else {c["chave"] for c in sol["camadas"]}
        prims += _prims_fechado(m, cam, W, luz, camadas=camadas, corte=corte, afastar=afastar,
                                parede=linha_parede, opacidade=max(opacidade, 0.9) if not parede else opacidade)
        k_corte = geometria_corte(sol, corte) if corte else None
        if linha_parede:
            topo_l = sol["cota_topo_max"] + 0.04 * (sol["cota_topo_max"] - sol["base"])
            for (xl, yl), letra in ((linha_parede[0], "A"), (linha_parede[-1], "A′")):
                prims.append((1e6, ("letra", cam.proj(W(xl, yl, topo_l)), letra)))
    for s in ([] if fechado else m["superficies"]):
        if not s.get("z") or s["chave"] not in visiveis:
            continue
        base_cor = _hex(s["cor"])
        com_drape = bool(drape) and s["chave"] == drape.get("chave") and faixa
        tris = []          # [(p1, p2, p3, valor da propriedade ou None)]
        if s.get("malha") and not com_drape:
            pts = s["malha"]["pts"]
            for a, b, c in s["malha"]["tris"]:
                tris.append((W(*pts[a]), W(*pts[b]), W(*pts[c]), None))
        else:
            passo_i = max(1, math.ceil(max(g["nx"], g["ny"]) / MAX_CELULAS_FIG))
            ii = list(range(0, g["nx"], passo_i))
            jj = list(range(0, g["ny"], passo_i))
            z = s["z"]
            gp = grade_prop if com_drape else None

            def no(j, i):
                return (None if z[j][i] is None else
                        W(g["x0"] + i * g["passo"], g["y0"] + j * g["passo"], z[j][i]))

            def val(*ks):
                if gp is None:
                    return None
                vs = [gp[j][i] for j, i in ks]
                return None if any(v is None for v in vs) else float(np.mean(vs))
            for a in range(len(jj) - 1):
                for b in range(len(ii) - 1):
                    j0, j1, i0, i1 = jj[a], jj[a + 1], ii[b], ii[b + 1]
                    A, B, C, D = no(j0, i0), no(j0, i1), no(j1, i0), no(j1, i1)
                    if A is not None and B is not None and C is not None:
                        tris.append((A, C, B, val((j0, i0), (j1, i0), (j0, i1))))
                    if B is not None and C is not None and D is not None:
                        tris.append((B, C, D, val((j0, i1), (j1, i0), (j1, i1))))
        for p1, p2, p3, valor in tris:
            n = np.cross(p2 - p1, p3 - p1)
            nn = np.linalg.norm(n)
            if nn == 0:
                continue
            n /= nn
            if n[2] < 0:
                n = -n
            luzf = 0.55 + 0.45 * max(0.0, float(n @ luz))
            if com_drape:
                rgb = _hex(cor_rampa((valor - faixa[0]) / (faixa[1] - faixa[0]))) if valor is not None \
                    else _hex(NEUTRO)
            else:
                rgb = base_cor
            q = [cam.proj(p) for p in (p1, p2, p3)]
            prof = sum(c[2] for c in q) / 3
            pts_txt = " ".join(f"{x:.2f},{y:.2f}" for x, y, _ in q)
            op = opacidade if not drape else (max(opacidade, 0.85) if com_drape else min(opacidade, 0.3))
            prims.append((prof, ("poly", pts_txt, _cor(rgb * luzf), op)))

    # ---------------------------------------------------------- poços
    classes = m.get("classes", {})
    # bloco fechado: o poço só aparece onde não está dentro do bloco (acima do terreno, no
    # quadrante do corte ou com a parede); com as camadas afastadas, nenhum (como no visor)
    terreno = np.asarray(sol["limites"][0], float) if fechado else None

    def visivel_no_bloco(x, y, cota):
        if not fechado:
            return True
        if afastar:
            return False
        if parede or _no_corte(k_corte, x, y):
            return True
        return cota >= float(mbs.bilinear(terreno, g, x, y)) - 1
    for p in m["pocos"]:
        cam_p = p.get("caminho") or []
        if fechado and afastar:
            continue
        for (md1, x1, y1, c1), (md2, x2, y2, c2) in zip(cam_p, cam_p[1:]):
            if not visivel_no_bloco((x1 + x2) / 2, (y1 + y2) / 2, (c1 + c2) / 2):
                continue
            a, b = cam.proj(W(x1, y1, c1)), cam.proj(W(x2, y2, c2))
            prims.append(((a[2] + b[2]) / 2, ("linha", a, b, TINTA, 0.9)))
        trechos = []
        if trilha == "avaliacao":
            trechos = [(t0, t1, (classes.get(str(c)) or classes.get(c) or {}).get("cor", TINTA2))
                       for t0, t1, c in p.get("classes", [])]
        elif trilha == "indicios":
            cores = {"óleo": "#008300", "gás": "#e34948"}
            trechos = [(i["md_topo"], i["md_base"], cores.get(i["fluido"], "#898781")) for i in p.get("indicios", [])]
        for t0, t1, cor in trechos:
            mds = [t0] + [q[0] for q in cam_p if t0 < q[0] < t1] + [t1]
            pts = [_no_caminho(p, md) for md in mds]
            for (xa, ya, ca), (xb, yb, cb) in zip(pts, pts[1:]):
                if not visivel_no_bloco((xa + xb) / 2, (ya + yb) / 2, (ca + cb) / 2):
                    continue
                a, b = cam.proj(W(xa, ya, ca)), cam.proj(W(xb, yb, cb))
                prims.append(((a[2] + b[2]) / 2 + 1e-4, ("linha", a, b, cor, 3.6)))
        for u in p["unidades"]:
            if u["chave"] in visiveis and visivel_no_bloco(u.get("x", p["x"]), u.get("y", p["y"]), u["cota_topo"]):
                q = cam.proj(W(u.get("x", p["x"]), u.get("y", p["y"]), u["cota_topo"]))
                prims.append((q[2] + 2e-4, ("disco", q, u["cor"], 3.2)))
        topo = p["mesa"] if p["mesa"] is not None else (cam_p[0][3] if cam_p else 0)
        q = cam.proj(W(p["x"], p["y"], topo))
        prims.append((q[2] + 3e-4, ("cabeca", q, p["id"] if nomes else "")))
    if drape and prop:
        for q0 in prop.get("pocos", []):
            v0 = q0.get(drape.get("prop"))
            if v0 is None or not faixa:
                continue
            q = cam.proj(W(q0["x"], q0["y"], q0["cota"]))
            prims.append((q[2] + 4e-4, ("disco", q, cor_rampa((v0 - faixa[0]) / (faixa[1] - faixa[0])), 5)))

    # ---------------------------------------------------------- caixa
    x0, x1 = g["x0"], g["x0"] + (g["nx"] - 1) * g["passo"]
    y0, y1 = g["y0"], g["y0"] + (g["ny"] - 1) * g["passo"]
    cmax = max(m["cota_max"], sol["cota_topo_max"]) if sol.get("ok") else m["cota_max"]
    cmin = min(m["cota_min"], sol["base"]) if sol.get("ok") else m["cota_min"]
    pc = _passo(cmax - cmin or 100)
    c0, c1 = math.floor(cmin / pc) * pc, math.ceil(cmax / pc) * pc
    cantos = {(i, j, k): W(xx, yy, cc) for i, xx in enumerate((x0, x1)) for j, yy in enumerate((y0, y1))
              for k, cc in enumerate((c0, c1))}
    arestas = [((0, 0, k), (1, 0, k)) for k in (0, 1)] + [((0, 1, k), (1, 1, k)) for k in (0, 1)] + \
              [((0, 0, k), (0, 1, k)) for k in (0, 1)] + [((1, 0, k), (1, 1, k)) for k in (0, 1)] + \
              [((i, j, 0), (i, j, 1)) for i in (0, 1) for j in (0, 1)]
    for a, b in arestas:
        pa, pb = cam.proj(cantos[a]), cam.proj(cantos[b])
        prims.append(((pa[2] + pb[2]) / 2 - 1e3, ("linha", pa, pb, GRADE, 0.7)))   # sempre atrás

    # enquadramento: projeta tudo e escala para a área do desenho
    xs, ys = [], []
    for _, pr in prims:
        if pr[0] == "poly":
            for par in pr[1].split():
                a, b = par.split(",")
                xs.append(float(a)); ys.append(float(b))
        elif pr[0] == "linha":
            xs += [pr[1][0], pr[2][0]]; ys += [pr[1][1], pr[2][1]]
        else:
            xs.append(pr[1][0]); ys.append(pr[1][1])
    if not xs:
        raise ErroFigura("Nada para desenhar.")
    ax0, ay0, ax1, ay1 = AREA
    escala = min((ax1 - ax0 - 60) / ((max(xs) - min(xs)) or 1), (ay1 - ay0 - 60) / ((max(ys) - min(ys)) or 1))
    cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
    mx, my = (ax0 + ax1) / 2, (ay0 + ay1) / 2

    def T(x, y):
        return mx + (x - cx) * escala, my - (y - cy) * escala

    corpo = []
    rotulos = []
    for _, pr in sorted(prims, key=lambda t: t[0]):
        tipo = pr[0]
        if tipo == "poly":
            pts = []
            for par in pr[1].split():
                a, b = par.split(",")
                X, Y = T(float(a), float(b))
                pts.append(f"{X:.1f},{Y:.1f}")
            corpo.append(f'<polygon points="{" ".join(pts)}" fill="{pr[2]}" fill-opacity="{pr[3]}" '
                         f'stroke="{pr[2]}" stroke-opacity="{pr[3]}" stroke-width="0.4"/>')
        elif tipo == "linha":
            (xa, ya), (xb, yb) = T(pr[1][0], pr[1][1]), T(pr[2][0], pr[2][1])
            corpo.append(f'<line x1="{xa:.1f}" y1="{ya:.1f}" x2="{xb:.1f}" y2="{yb:.1f}" stroke="{pr[3]}" '
                         f'stroke-width="{pr[4]}" stroke-linecap="round"/>')
        elif tipo == "disco":
            X, Y = T(pr[1][0], pr[1][1])
            corpo.append(f'<ellipse cx="{X:.1f}" cy="{Y:.1f}" rx="{pr[3] * 1.3:.1f}" ry="{pr[3] * 0.7:.1f}" '
                         f'fill="{pr[2]}" stroke="{TINTA}" stroke-width="0.4"/>')
        elif tipo == "letra":
            X, Y = T(pr[1][0], pr[1][1])
            rotulos.append(_t(X, Y, pr[2], 13, TINTA, "middle", "bold"))
        elif tipo == "cabeca":
            X, Y = T(pr[1][0], pr[1][1])
            corpo.append(f'<circle cx="{X:.1f}" cy="{Y:.1f}" r="2.6" fill="{TINTA}"/>')
            if pr[2]:
                rotulos.append(_t(X + 4, Y - 4, pr[2], 8.5, TINTA))

    # marcas dos eixos (borda sul, borda oeste, canto sudeste)
    eixos = []
    ph = _passo(max(x1 - x0, y1 - y0))

    def marca(p_mundo, dx, dy, texto, ancora="middle"):
        X, Y = T(*cam.proj(p_mundo)[:2])
        eixos.append(f'<line x1="{X:.1f}" y1="{Y:.1f}" x2="{X + dx * 0.5:.1f}" y2="{Y + dy * 0.5:.1f}" '
                     f'stroke="{TINTA2}" stroke-width="0.7"/>')
        eixos.append(_t(X + dx, Y + dy + 3, texto, 9, TINTA2, ancora))
    d = 0.0
    while d <= x1 - x0 + 1e-9:
        marca(W(x0 + d, y0, c0), 0, 12, _fmt(d, 1 if ph < 1 else 0))
        d += ph
    d = 0.0
    while d <= y1 - y0 + 1e-9:
        marca(W(x0, y0 + d, c0), -12, 4, _fmt(d, 1 if ph < 1 else 0), "end")
        d += ph
    c = c0
    while c <= c1 + 1e-9:
        marca(W(x1, y0, c), 12, 0, _fmt(c), "start")
        c += pc
    Xa, Ya = T(*cam.proj(W((x0 + x1) / 2, y0, c0))[:2])
    eixos.append(_t(Xa, Ya + 30, "leste (km)", 10, TINTA2, "middle", estilo="italic"))
    Xb, Yb = T(*cam.proj(W(x0, (y0 + y1) / 2, c0))[:2])
    eixos.append(_t(Xb - 26, Yb + 18, "norte (km)", 10, TINTA2, "end", estilo="italic"))
    Xc, Yc = T(*cam.proj(W(x1, y0, c0))[:2])
    eixos.append(_t(Xc + 12, Yc + 20, "cota (m)", 10, TINTA2, "start", estilo="italic"))

    # seta do norte
    o = np.array(cam.proj(W(0, 0, 0))[:2])
    n = np.array(cam.proj(W(0, 1, 0))[:2]) - o
    ang = math.degrees(math.atan2(n[0], n[1])) if np.linalg.norm(n) > 1e-9 else 0.0
    nx_, ny_ = 790, 95
    norte = (f'<g transform="translate({nx_} {ny_}) rotate({ang:.1f})">'
             f'<polygon points="0,-16 5,0 -5,0" fill="{TINTA}"/>'
             f'<polygon points="0,16 5,0 -5,0" fill="#ffffff" stroke="{TINTA}" stroke-width="0.8"/></g>'
             f'<circle cx="{nx_}" cy="{ny_}" r="19" fill="none" stroke="{GRADE}" stroke-width="0.8"/>'
             + _t(nx_ + 27 * math.sin(math.radians(ang)), ny_ - 27 * math.cos(math.radians(ang)) + 4, "N", 11,
                  TINTA, "middle", "bold"))

    # legenda (moldura), à direita
    lx, ly = 850, 70
    leg = [_t(lx, ly, "Bloco fechado (AGP)" if fechado else "Topo das unidades (AGP)", 11, TINTA, peso="bold")]
    ly += 18
    for u in (sol["camadas"] if fechado else m["legenda"]):
        if u["chave"] not in (camadas if fechado else visiveis):
            continue
        leg.append(f'<rect x="{lx}" y="{ly - 9}" width="14" height="10" fill="{u["cor"]}" stroke="{TINTA}" '
                   f'stroke-width="0.4"/>')
        leg.append(_t(lx + 20, ly, u["nome"], 10.5))
        ly += 16
    if fechado:
        leg.append(f'<rect x="{lx}" y="{ly - 9}" width="14" height="10" fill="{_cor(_clarear(_hex("#7a7a7a"), False))}" '
                   f'stroke="{TINTA}" stroke-width="0.4"/>')
        leg.append(_t(lx + 20, ly, "mais claro: extrapolado", 10.5, TINTA2, estilo="italic"))
        ly += 16
    if trilha in ("avaliacao", "indicios") and not (fechado and afastar):
        ly += 8
        leg.append(_t(lx, ly, "Nos poços" + (" (avaliação)" if trilha == "avaliacao" else " (AGP)"), 11, TINTA,
                      peso="bold"))
        ly += 18
        if trilha == "avaliacao":
            usadas = {c for p in m["pocos"] for _, _, c in p.get("classes", [])}
            itens = [(c["cor"], c["nome"]) for k, c in sorted(classes.items(), key=lambda t: int(t[0]))
                     if int(k) in usadas]
        else:
            usados = {i["fluido"] for p in m["pocos"] for i in p.get("indicios", [])}
            cores = {"óleo": "#008300", "gás": "#e34948", "outro": "#898781"}
            itens = [(cores[f], f"indício de {f}") for f in ("óleo", "gás", "outro") if f in usados]
        for cor, nome in itens:
            leg.append(f'<line x1="{lx}" y1="{ly - 4}" x2="{lx + 14}" y2="{ly - 4}" stroke="{cor}" stroke-width="3.6"/>')
            leg.append(_t(lx + 20, ly, nome, 10.5))
            ly += 16
    if faixa:
        ly += 10
        nome_prop = dict(m.get("nomes_propriedades", {})).get(drape.get("prop"), drape.get("prop"))
        nome_u = next((u["nome"] for u in m["legenda"] if u["chave"] == drape.get("chave")), "")
        leg.append(_t(lx, ly, nome_prop, 11, TINTA, peso="bold"))
        leg.append(_t(lx, ly + 13, f"no topo: {nome_u}", 9.5, TINTA2))
        ly += 20
        n_seg = 40
        for k in range(n_seg):
            leg.append(f'<rect x="{lx + k * 180 / n_seg:.2f}" y="{ly}" width="{180 / n_seg + 0.3:.2f}" height="10" '
                       f'fill="{cor_rampa(k / (n_seg - 1))}"/>')
        leg.append(f'<rect x="{lx}" y="{ly}" width="180" height="10" fill="none" stroke="{TINTA}" stroke-width="0.4"/>')
        casas = 2 if drape.get("prop") in ("ntg", "phi_media_pay", "sw_media_pay") else 1
        leg.append(_t(lx, ly + 23, _fmt(faixa[0], casas), 9.5, TINTA2))
        leg.append(_t(lx + 180, ly + 23, _fmt(faixa[1], casas), 9.5, TINTA2, "end"))
        ly += 32
    leg_box = f'<rect x="{lx - 10}" y="52" width="235" height="{ly - 52 + 4}" fill="#ffffff" stroke="{TINTA}" ' \
              f'stroke-width="0.6"/>'

    # carimbo e notas
    origem = m["origem"]
    lat_sw = origem["lat"] + math.degrees(g["y0"] / 6371.0)
    lon_sw = origem["lon"] + math.degrees(g["x0"] / (6371.0 * math.cos(math.radians(origem["lat"]))))
    notas = [
        f"{len(m['pocos'])} poços · contorno dos poços {_fmt(m['area_km2'], 1)} km² · exagero vertical {_fmt(exagero)}× · "
        f"projeção ortográfica · distâncias a partir do canto SW ({_fmt(lat_sw, 4)}°, {_fmt(lon_sw, 4)}°)",
        (f"Contexto espacial: camadas empilhadas por espessura (linear entre os poços; fora do contorno deles, valor da "
         f"borda mais próxima, mais claro), do terreno à base plana em {_fmt(sol['base'])} m."
         + (" Seção A–A′: " + " – ".join(parede) + "." if fechado and parede else "")
         + (" Camadas afastadas na vertical." if fechado and afastar else "")) if fechado else
        "Contexto espacial: entre os poços, superfícies interpoladas (linear nos triângulos de Delaunay, só dentro do "
        "contorno dos poços que têm a unidade).",
        "Topos: AGP (ANP), interpretação da operadora." + (" Trilhas: avaliação de formação mais recente de cada poço "
                                                           "(SIAPP)." if trilha == "avaliacao" else "")
        + (" Indícios: AGP." if trilha == "indicios" else ""),
        f"SIAPP {__version__}" + (f" · {autor}" if autor else "") + (f" · {data}" if data else ""),
    ]
    notas_svg = [_t(AREA[0], AREA[3] + 34 + 15 * k, t, 10, TINTA2) for k, t in enumerate(notas)]
    tit = _t(AREA[0], 36, titulo, 17, TINTA, peso="bold") if titulo else ""
    moldura = f'<rect x="{AREA[0] - 10}" y="{AREA[1] - 8}" width="{AREA[2] - AREA[0] + 20}" ' \
              f'height="{AREA[3] - AREA[1] + 16}" fill="none" stroke="{TINTA}" stroke-width="0.8"/>'
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{LARGURA}" height="{ALTURA}" '
            f'viewBox="0 0 {LARGURA} {ALTURA}"><rect width="100%" height="100%" fill="#ffffff"/>'
            + tit + moldura + "".join(corpo) + "".join(eixos) + "".join(rotulos) + norte + leg_box + "".join(leg)
            + "".join(notas_svg) + "</svg>")


# ================================================================ bloco fechado
def _clarear(rgb, controlado: bool):
    return rgb if controlado else rgb + 0.55 * (255 - rgb)


def _recortar_espessura(pol):
    """Polígono de vértices [x, y, topo, fundo] recortado onde a espessura < ESPESSURA_MIN_M."""
    f = [p[2] - p[3] - mbs.ESPESSURA_MIN_M for p in pol]
    out = []
    for i in range(len(pol)):
        P, Q, fp, fq = pol[i], pol[(i + 1) % len(pol)], f[i], f[(i + 1) % len(pol)]
        if fp >= 0:
            out.append(P)
        if (fp >= 0) != (fq >= 0):
            t = fp / (fp - fq)
            out.append([a + t * (b - a) for a, b in zip(P, Q)])
    return out


def _recortar_por(pol, j: int, lado: int):
    """Parte do polígono (vértices com atributos) onde o atributo j (uma espessura) está
    acima de ESPESSURA_MIN_M (lado +1) ou abaixo (lado −1); atributos interpolados."""
    f = [lado * (p[j] - mbs.ESPESSURA_MIN_M) for p in pol]
    out = []
    for i in range(len(pol)):
        P, Q, fp, fq = pol[i], pol[(i + 1) % len(pol)], f[i], f[(i + 1) % len(pol)]
        if fp >= 0:
            out.append(P)
        if (fp >= 0) != (fq >= 0):
            t = fp / (fp - fq)
            out.append([a + t * (b - a) for a, b in zip(P, Q)])
    return out


def geometria_corte(solido: dict, corte: dict) -> dict:
    """Canto do corte (x, y em km), lados tirados e as linhas das tampas (como no visor)."""
    pol = np.asarray(solido["contorno"], float)
    (xmin, ymin), (xmax, ymax) = pol.min(0), pol.max(0)
    cx = xmin + float(corte.get("fx", 0.5)) * (xmax - xmin)
    cy = ymin + float(corte.get("fy", 0.5)) * (ymax - ymin)
    q = str(corte.get("quadrante", "SW")).upper()
    oeste, sul = "W" in q, "S" in q
    sx, sy = (1 if oeste else -1), (1 if sul else -1)
    return {"cx": cx, "cy": cy, "oeste": oeste, "sul": sul,
            # o que fica: o outro lado em x, ou o mesmo lado em x e o outro em y
            "pedacos": [[(sx, 0.0, -sx * cx)], [(-sx, 0.0, sx * cx), (0.0, sy, -sy * cy)]],
            "linhas": [[[cx, ymin - 1 if sul else cy], [cx, cy if sul else ymax + 1]],
                       [[xmin - 1 if oeste else cx, cy], [cx if oeste else xmax + 1, cy]]],
            "normais": [(-sx, 0.0), (0.0, -sy)]}


def _no_corte(k: dict | None, x: float, y: float) -> bool:
    if not k:
        return False
    return ((x < k["cx"]) if k["oeste"] else (x > k["cx"])) and ((y < k["cy"]) if k["sul"] else (y > k["cy"]))


def _prims_fechado(m: dict, cam, W, luz, *, camadas: set, corte: dict | None, afastar: float,
                   parede: list | None, opacidade: float) -> list:
    s, g = m["solido"], m["grade"]
    lims = [np.asarray(z, float) for z in s["limites"]]
    pol = s["contorno"]
    lado = max((g["nx"] - 1) * g["passo"], (g["ny"] - 1) * g["passo"])
    gc = dict(g)
    gc["passo"] = max(g["passo"], lado / MAX_CELULAS_FIG)
    gc["nx"] = int(math.ceil((g["nx"] - 1) * g["passo"] / gc["passo"])) + 1
    gc["ny"] = int(math.ceil((g["ny"] - 1) * g["passo"] / gc["passo"])) + 1
    k_corte = geometria_corte(s, corte) if corte else None
    pedacos = k_corte["pedacos"] if k_corte else [[]]
    malhas = [mbs.malha_contorno(gc, pol, extra=p) for p in pedacos]
    n_cam = len(s["camadas"])
    passo_af = float(afastar or 0) * (s["cota_topo_max"] - s["base"]) * 0.6 / max(1, n_cam)
    com_parede = bool(parede)
    op_bloco = min(opacidade, 0.12) if com_parede else opacidade
    prims = []

    def face(pts3, rgb, op, normal=None):
        if normal is None:
            n = np.cross(pts3[1] - pts3[0], pts3[2] - pts3[0])
            nn = np.linalg.norm(n)
            if nn == 0:
                return
            n = n / nn
            if n @ cam.d < 0:
                n = -n
        else:
            n = normal
        luzf = 0.55 + 0.45 * max(0.0, float(n @ luz))
        q = [cam.proj(p) for p in pts3]
        # face vertical (paredes, tampas): pelo vértice mais longe, para sair antes do topo
        # vizinho — a face da frente de um prisma convexo nunca cobre o topo, nem é coberta
        prof = min(c[2] for c in q) if normal is not None or abs(n[2]) < 1e-6 else sum(c[2] for c in q) / len(q)
        prims.append((prof, ("poly", " ".join(f"{x:.2f},{y:.2f}" for x, y, _ in q), _cor(rgb * luzf), op)))

    # vértices da malha: topo/fundo de cada limite
    vals = []
    for mal in malhas:
        xs, ys = mal["pts"][:, 0], mal["pts"][:, 1]
        vals.append([mbs.bilinear(z, g, xs, ys) for z in lims])
    ligadas = [k for k, c in enumerate(s["camadas"]) if c["chave"] in camadas]
    if not passo_af:
        # camadas juntas: só a superfície exposta, em pedaços que não se sobrepõem (cada
        # triângulo é dividido pelas linhas de acunhamento das camadas ligadas, de cima para
        # baixo) — o algoritmo do pintor não tem o que errar no topo
        for mal, vv in zip(malhas, vals):
            for a, b, c in mal["tris"]:
                resto = [[mal["pts"][i][0], mal["pts"][i][1]] + [vv[k][i] - vv[k + 1][i] for k in ligadas]
                         + [vv[k][i] for k in ligadas] for i in (a, b, c)]
                for n_, k in enumerate(ligadas):
                    if len(resto) < 3:
                        break
                    peca = _recortar_por(resto, 2 + n_, +1)
                    resto = _recortar_por(resto, 2 + n_, -1)
                    if len(peca) < 3:
                        continue
                    cam_ = s["camadas"][k]
                    cx_, cy_ = np.mean([p[0] for p in peca]), np.mean([p[1] for p in peca])
                    rgb = _clarear(_hex(cam_["cor"]), bool(mbs.controlado(cam_["controle"], cx_, cy_)))
                    face([W(p[0], p[1], p[2 + len(ligadas) + n_]) for p in peca], rgb, op_bloco)
    for k, cam_ in enumerate(s["camadas"]):
        if cam_["chave"] not in camadas:
            continue
        rgb0 = _hex(cam_["cor"])
        dz = -k * passo_af
        # topo de cada camada (só com as camadas afastadas; juntas, foi feito acima)
        for mal, vv in zip(malhas if passo_af else [], vals):
            T, B = vv[k], vv[k + 1]
            for a, b, c in mal["tris"]:
                e = [T[i] - B[i] for i in (a, b, c)]
                if max(e) < mbs.ESPESSURA_MIN_M:
                    continue
                poli = [[mal["pts"][i][0], mal["pts"][i][1], T[i], B[i]] for i in (a, b, c)]
                if min(e) < mbs.ESPESSURA_MIN_M:
                    poli = _recortar_espessura(poli)
                if len(poli) < 3:
                    continue
                cx_, cy_ = np.mean([p[0] for p in poli]), np.mean([p[1] for p in poli])
                rgb = _clarear(rgb0, bool(mbs.controlado(cam_["controle"], cx_, cy_)))
                face([W(p[0], p[1], p[2] + dz) for p in poli], rgb, op_bloco, normal=None)
        # paredes ao longo do contorno, viradas para a câmera
        borda = _borda_com_corte(gc, pol, k_corte)
        Tb = mbs.bilinear(lims[k], g, borda[:, 0], borda[:, 1])
        Bb = mbs.bilinear(lims[k + 1], g, borda[:, 0], borda[:, 1])
        for i in range(len(borda) - 1):
            P = [borda[i][0], borda[i][1], Tb[i], Bb[i]]
            Q = [borda[i + 1][0], borda[i + 1][1], Tb[i + 1], Bb[i + 1]]
            if _no_corte(k_corte, (P[0] + Q[0]) / 2, (P[1] + Q[1]) / 2):
                continue
            dx, dy = Q[0] - P[0], Q[1] - P[1]
            L = math.hypot(dx, dy)
            if L == 0:
                continue
            n = np.array([dy / L, -dx / L, 0.0])           # para fora (contorno anti-horário)
            if n @ cam.d <= 0:
                continue
            fp, fq = P[2] - P[3] - mbs.ESPESSURA_MIN_M, Q[2] - Q[3] - mbs.ESPESSURA_MIN_M
            if fp < 0 and fq < 0:
                continue
            if fp < 0 or fq < 0:
                t = fp / (fp - fq)
                M = [a + t * (b - a) for a, b in zip(P, Q)]
                P, Q = (M, Q) if fp < 0 else (P, M)
            rgb = _clarear(rgb0, bool(mbs.controlado(cam_["controle"], (P[0] + Q[0]) / 2, (P[1] + Q[1]) / 2)))
            face([W(P[0], P[1], P[2] + dz), W(Q[0], Q[1], Q[2] + dz), W(Q[0], Q[1], Q[3] + dz),
                  W(P[0], P[1], P[3] + dz)], rgb, op_bloco, normal=n)
        # tampas do corte
        if k_corte:
            for linha, (nx_, ny_) in zip(k_corte["linhas"], k_corte["normais"]):
                n = np.array([nx_, ny_, 0.0])
                if n @ cam.d <= 0:
                    continue
                _faixa(s, g, linha, k, cam_, rgb0, dz, W, face, gc["passo"] / 2, op_bloco, n)
        # parede da seção A–A′ (opaca, as duas faces)
        if com_parede:
            _faixa(s, g, parede, k, cam_, rgb0, dz, W, face, gc["passo"] / 2, 1.0, None)
    return prims


def _faixa(s, g, linha, k, cam_, rgb0, dz, W, face, passo, op, normal):
    pf = mbs.perfil(s, g, linha, passo_km=passo)
    xy, T, B = pf["xy"], pf["limites"][k] if pf["xy"] else [], pf["limites"][k + 1] if pf["xy"] else []
    for i in range(1, len(xy)):
        if max(T[i] - B[i], T[i - 1] - B[i - 1]) < mbs.ESPESSURA_MIN_M:
            continue
        (xa, ya), (xb, yb) = xy[i - 1], xy[i]
        rgb = _clarear(rgb0, bool(mbs.controlado(cam_["controle"], (xa + xb) / 2, (ya + yb) / 2)))
        face([W(xa, ya, T[i - 1] + dz), W(xb, yb, T[i] + dz), W(xb, yb, B[i] + dz), W(xa, ya, B[i - 1] + dz)],
             rgb, op, normal=normal)


def _borda_com_corte(gc, pol, k_corte) -> np.ndarray:
    """Pontos da borda, com os pontos onde ela cruza as linhas do corte (para a parede parar ali)."""
    b = mbs.borda(gc, pol)
    if not k_corte:
        return b
    out = [b[0]]
    for p, q in zip(b[:-1], b[1:]):
        ts = []
        for e, v in ((0, k_corte["cx"]), (1, k_corte["cy"])):
            if (p[e] - v) * (q[e] - v) < 0:
                ts.append((v - p[e]) / (q[e] - p[e]))
        out += [p + t * (q - p) for t in sorted(ts)] + [q]
    return np.array(out)


def _no_caminho(p: dict, md: float):
    c = p.get("caminho") or []
    if not c:
        return p["x"], p["y"], 0.0
    mds = [q[0] for q in c]
    return (float(np.interp(md, mds, [q[1] for q in c])), float(np.interp(md, mds, [q[2] for q in c])),
            float(np.interp(md, mds, [q[3] for q in c])))


def exportar(svg: str, saida: str, formato: str) -> str:
    os.makedirs(os.path.dirname(saida), exist_ok=True)
    if formato == "svg":
        with open(saida, "w", encoding="utf-8") as f:
            f.write(svg)
        return saida
    import pymupdf
    doc = pymupdf.open(stream=svg.encode("utf-8"), filetype="svg")
    if formato == "png":
        doc[0].get_pixmap(dpi=300).save(saida)
    elif formato == "pdf":
        with pymupdf.open("pdf", doc.convert_to_pdf()) as pdf:
            pdf.save(saida)
    else:
        raise ErroFigura(f"Formato desconhecido: {formato}")
    return saida
