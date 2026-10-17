"""Bloco 3D: poços e superfícies de topo das unidades, a partir dos topos do AGP.

O bloco é **contexto espacial, não resultado** (Especificação Funcional, M4): mostra onde
estão os poços e como os topos registrados no AGP se arranjam no espaço. O resultado
quantitativo continua sendo a seção (M5) e a avaliação (M6).

Regras (requisitos 4.4–4.8 da Especificação):

- coordenadas num **plano local** em km (equiretangular na latitude média — o mesmo da
  seção; ≈ 111,3 km por grau de latitude);
- cada superfície é interpolada **só dentro do contorno convexo** dos poços que têm aquela
  unidade, mais uma **margem** opcional (0 para um campo isolado: margem infla a área);
- dentro do contorno: **interpolação linear** nos triângulos de Delaunay dos poços; na faixa
  da margem: **vizinho mais próximo**; fora: nulo (NaN, de propósito);
- **área do contorno** pela fórmula do *shoelace*, calculada e mostrada (não estimada);
- poços quase **colineares** não sustentam superfície (a interpolação na direção
  transversal não tem dado): a unidade fica só nos poços, com aviso;
- opcional: esconder a superfície onde o poço mais próximo com a unidade está longe.

Poço desviado: desenhado na vertical, na posição da cabeça (o cadastro só tem esta
posição; a trajetória dos arquivos de dados direcionais fica para depois). A **cota** dos
topos é a do AGP, que já considera o desvio.

Só numpy: a triangulação (Bowyer–Watson) e o contorno (cadeia monótona) estão aqui.
"""

from __future__ import annotations

import csv
import json
import math
import os
from datetime import datetime

import numpy as np

from . import __version__
from . import secao as msc
from .banco import Banco, agora

MAX_POCOS = 1000
CELULAS_PADRAO = 160          # células no lado maior da grade
FRACAO_COLINEAR = 0.04        # largura / comprimento do contorno abaixo disso = colinear
LONGE_KM = 100.0              # poço a mais que isso (e 5× a distância mediana) do centro: fora
NIVEIS = msc.NIVEIS_SECAO


class ErroBloco(Exception):
    """Pedido que não dá para atender, com mensagem para o usuário."""


# ============================================================== geometria
def plano(lats, lons, lat0: float | None = None, lon0: float | None = None):
    """lat/lon → (x leste, y norte) em km, com origem em (lat0, lon0) (padrão: o centro)."""
    lats, lons = np.asarray(lats, float), np.asarray(lons, float)
    lat0 = float(np.mean(lats)) if lat0 is None else lat0
    lon0 = float(np.mean(lons)) if lon0 is None else lon0
    r = 6371.0
    x = np.radians(lons - lon0) * r * math.cos(math.radians(lat0))
    y = np.radians(lats - lat0) * r
    return x, y, lat0, lon0


def para_geo(x, y, lat0: float, lon0: float):
    r = 6371.0
    lat = lat0 + np.degrees(np.asarray(y, float) / r)
    lon = lon0 + np.degrees(np.asarray(x, float) / (r * math.cos(math.radians(lat0))))
    return lat, lon


def contorno_convexo(pts) -> np.ndarray:
    """Contorno convexo (cadeia monótona de Andrew), anti-horário, sem repetir o 1º ponto."""
    p = sorted(set(map(tuple, np.asarray(pts, float).round(9))))
    if len(p) <= 2:
        return np.array(p, float)

    def giro(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    baixo, cima = [], []
    for q in p:
        while len(baixo) >= 2 and giro(baixo[-2], baixo[-1], q) <= 0:
            baixo.pop()
        baixo.append(q)
    for q in reversed(p):
        while len(cima) >= 2 and giro(cima[-2], cima[-1], q) <= 0:
            cima.pop()
        cima.append(q)
    return np.array(baixo[:-1] + cima[:-1], float)


def area_shoelace(poligono) -> float:
    p = np.asarray(poligono, float)
    if len(p) < 3:
        return 0.0
    x, y = p[:, 0], p[:, 1]
    return float(abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))) / 2)


def largura_relativa(poligono) -> float:
    """Menor largura do contorno / maior comprimento (0 = colinear)."""
    p = np.asarray(poligono, float)
    if len(p) < 3:
        return 0.0
    comp = max(float(np.hypot(*(a - b))) for a in p for b in p)
    if comp <= 0:
        return 0.0
    largura = math.inf
    for i in range(len(p)):
        a, b = p[i], p[(i + 1) % len(p)]
        d = b - a
        n = float(np.hypot(*d))
        if n == 0:
            continue
        dist = np.abs(d[0] * (p[:, 1] - a[1]) - d[1] * (p[:, 0] - a[0])) / n
        largura = min(largura, float(dist.max()))
    return largura / comp


def com_margem(poligono, margem_km: float, n_arco: int = 16) -> np.ndarray:
    """Contorno convexo expandido de `margem_km` (soma de Minkowski com um círculo)."""
    p = np.asarray(poligono, float)
    if margem_km <= 0 or len(p) == 0:
        return p
    ang = np.linspace(0, 2 * math.pi, n_arco, endpoint=False)
    circ = np.c_[np.cos(ang), np.sin(ang)] * margem_km
    return contorno_convexo((p[:, None, :] + circ[None, :, :]).reshape(-1, 2))


def dentro(poligono, x, y) -> np.ndarray:
    """Máscara dos pontos (x, y) dentro do polígono convexo anti-horário (borda conta)."""
    p = np.asarray(poligono, float)
    x, y = np.asarray(x, float), np.asarray(y, float)
    if len(p) < 3:
        return np.zeros(np.broadcast(x, y).shape, bool)
    ok = np.ones(np.broadcast(x, y).shape, bool)
    escala = max(1.0, float(np.abs(p).max()))
    for i in range(len(p)):
        a, b = p[i], p[(i + 1) % len(p)]
        ok &= (b[0] - a[0]) * (y - a[1]) - (b[1] - a[1]) * (x - a[0]) >= -1e-9 * escala
    return ok


def delaunay(pts) -> np.ndarray:
    """Triângulos de Delaunay (índices) por Bowyer–Watson. Pontos repetidos: só o 1º entra."""
    pts = np.asarray(pts, float)
    n = len(pts)
    if n < 3:
        return np.zeros((0, 3), int)
    lo, hi = pts.min(0), pts.max(0)
    centro, tam = (lo + hi) / 2, float(max(hi - lo)) or 1.0
    s = np.array([centro + [-20 * tam, -10 * tam], centro + [20 * tam, -10 * tam], centro + [0, 20 * tam]])
    todos = np.vstack([pts, s])
    tris = [(n, n + 1, n + 2)]

    def circ(t):
        (ax, ay), (bx, by), (cx, cy) = todos[list(t)]
        d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
        if abs(d) < 1e-18:
            return (0.0, 0.0, math.inf)
        ux = ((ax * ax + ay * ay) * (by - cy) + (bx * bx + by * by) * (cy - ay) + (cx * cx + cy * cy) * (ay - by)) / d
        uy = ((ax * ax + ay * ay) * (cx - bx) + (bx * bx + by * by) * (ax - cx) + (cx * cx + cy * cy) * (bx - ax)) / d
        return (ux, uy, (ax - ux) ** 2 + (ay - uy) ** 2)
    circs = {tris[0]: circ(tris[0])}
    vistos = set()
    for i in range(n):
        chave = (round(pts[i, 0], 9), round(pts[i, 1], 9))
        if chave in vistos:
            continue
        vistos.add(chave)
        px, py = pts[i]
        ruins = [t for t in tris if (px - circs[t][0]) ** 2 + (py - circs[t][1]) ** 2 < circs[t][2] * (1 + 1e-12)]
        arestas: dict = {}
        for t in ruins:
            for e in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
                k = tuple(sorted(e))
                arestas[k] = arestas.get(k, 0) + 1
        ruins_set = set(ruins)
        tris = [t for t in tris if t not in ruins_set]
        for t in ruins:
            circs.pop(t, None)
        for (a, b), c in arestas.items():
            if c == 1:
                t = (a, b, i)
                tris.append(t)
                circs[t] = circ(t)
    out = [t for t in tris if max(t) < n]
    # tira triângulos degenerados (área ~0)
    bons = []
    for t in out:
        a, b, c = pts[list(t)]
        if abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])) > 1e-12 * tam * tam:
            bons.append(t)
    return np.array(bons, int).reshape(-1, 3)


def interpolar_linear(pts, valores, tris, gx, gy) -> np.ndarray:
    """Interpolação linear (baricêntrica) nos triângulos; NaN fora deles."""
    pts, valores = np.asarray(pts, float), np.asarray(valores, float)
    z = np.full(gx.shape, np.nan)
    for t in tris:
        (ax, ay), (bx, by), (cx, cy) = pts[t]
        x0, x1 = min(ax, bx, cx), max(ax, bx, cx)
        y0, y1 = min(ay, by, cy), max(ay, by, cy)
        sel = (gx >= x0 - 1e-9) & (gx <= x1 + 1e-9) & (gy >= y0 - 1e-9) & (gy <= y1 + 1e-9) & np.isnan(z)
        if not sel.any():
            continue
        X, Y = gx[sel], gy[sel]
        det = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(det) < 1e-15:
            continue
        l1 = ((by - cy) * (X - cx) + (cx - bx) * (Y - cy)) / det
        l2 = ((cy - ay) * (X - cx) + (ax - cx) * (Y - cy)) / det
        l3 = 1 - l1 - l2
        ok = (l1 >= -1e-9) & (l2 >= -1e-9) & (l3 >= -1e-9)
        v = l1 * valores[t[0]] + l2 * valores[t[1]] + l3 * valores[t[2]]
        idx = np.flatnonzero(sel)
        z.flat[idx[ok]] = v[ok]
    return z


def distancia_mais_proximo(pts, gx, gy) -> tuple[np.ndarray, np.ndarray]:
    """(distância ao ponto mais próximo, índice dele) para cada nó da grade."""
    pts = np.asarray(pts, float)
    d = np.full(gx.shape, np.inf)
    k = np.zeros(gx.shape, int)
    for i, (px, py) in enumerate(pts):
        di = np.hypot(gx - px, gy - py)
        m = di < d
        d[m], k[m] = di[m], i
    return d, k


# =================================================================== dados
def pocos_disponiveis(banco: Banco, bacia: str | None = None) -> list[dict]:
    return msc.pocos_com_topos(banco, bacia)


def campos(banco: Banco) -> list[dict]:
    """Campos (do cadastro) com poços que têm topos no AGP."""
    cont: dict[str, int] = {}
    for p in msc.pocos_com_topos(banco):
        if p["campo"]:
            cont[p["campo"]] = cont.get(p["campo"], 0) + 1
    return [{"campo": c, "pocos": n} for c, n in sorted(cont.items(), key=lambda kv: (-kv[1], kv[0]))]


def selecionar(banco: Banco, *, modo: str, campo: str = "", poco: str = "", raio_km: float = 5.0,
               bacia: str | None = None) -> list[str]:
    """Ids dos poços com topos: todos (da bacia), de um campo ou num raio em torno de um poço."""
    todos = msc.pocos_com_topos(banco, bacia)
    if modo == "todos":
        if not bacia:
            raise ErroBloco("Escolha a bacia.")
        return [p["id"] for p in todos]
    if modo == "campo":
        return [p["id"] for p in todos if (p["campo"] or "").upper() == campo.upper()]
    if modo == "raio":
        with banco.conexao() as c:
            r = c.execute("SELECT lat, lon FROM pocos WHERE id = ?", (poco,)).fetchone()
        if not r or r["lat"] is None:
            raise ErroBloco(f"{poco}: sem coordenadas no cadastro da ANP.")
        if not todos:
            return []
        x, y, _, _ = plano([p["lat"] for p in todos] + [r["lat"]], [p["lon"] for p in todos] + [r["lon"]])
        d = np.hypot(x[:-1] - x[-1], y[:-1] - y[-1])
        return [p["id"] for p, di in sorted(zip(todos, d), key=lambda t: t[1]) if di <= raio_km]
    raise ErroBloco(f"Modo de seleção desconhecido: {modo}")


# ================================================================== modelo
def montar(banco: Banco, pocos: list[str], *, nivel: str = "formacoes", margem_km: float = 0.0,
           celulas: int = CELULAS_PADRAO, dist_max_km: float | None = None, nomes: dict | None = None,
           slots: dict | None = None) -> dict:
    """Modelo do bloco (só dados; o desenho é da janela)."""
    pocos = list(dict.fromkeys(p for p in pocos if p))
    if len(pocos) < 3:
        raise ErroBloco("Escolha ao menos três poços.")
    if len(pocos) > MAX_POCOS:
        raise ErroBloco(f"No máximo {MAX_POCOS} poços por bloco (há {len(pocos)}).")
    if nivel not in NIVEIS:
        raise ErroBloco(f"Nível desconhecido: {nivel}")
    celulas = int(min(max(celulas or CELULAS_PADRAO, 20), 300))
    margem_km = max(0.0, float(margem_km or 0))
    nomes, slots = nomes or {}, slots or {}
    avisos: list[str] = []

    dados = []
    for pid in pocos:
        d = msc.dados_poco(banco, pid, nomes)
        if d is None:
            avisos.append(f"{pid}: sem coordenadas — fora do bloco.")
            continue
        col = msc.coluna_poco(d, NIVEIS[nivel])
        dados.append((d, col))
    if len(dados) < 3:
        raise ErroBloco("Menos de três poços com coordenadas.")
    # poço muito longe de todos os outros (ex.: AGP de um poço do ES na pasta da Potiguar)
    # estragaria o bloco inteiro: fica de fora, com aviso
    x, y, _, _ = plano([d["lat"] for d, _ in dados], [d["lon"] for d, _ in dados])
    cx, cy = float(np.median(x)), float(np.median(y))
    dist = np.hypot(x - cx, y - cy)
    limite = max(LONGE_KM, 5 * float(np.median(dist)))
    longe = [d["id"] for (d, _), di in zip(dados, dist) if di > limite]
    if longe and len(dados) - len(longe) >= 3:
        avisos.append(f"Longe de todos os outros (mais de {limite:.0f} km do centro), fora do bloco — confira "
                      f"as coordenadas e o AGP: {', '.join(longe)}.")
        dados = [(d, c) for d, c in dados if d["id"] not in longe]
    x, y, lat0, lon0 = plano([d["lat"] for d, _ in dados], [d["lon"] for d, _ in dados])

    saida = []
    desviados = []
    for (d, col), xi, yi in zip(dados, x, y):
        if col["ctrl"][2]:
            desviados.append(d["id"])
        classe_txt = " ".join(filter(None, [d["cab"].get("reclassificacao"), d["cab"].get("classificacao"),
                                            (d["cad"] or {}).get("reclassificacao")])).upper()
        saida.append({
            "id": d["id"], "lat": d["lat"], "lon": d["lon"], "x": round(float(xi), 4), "y": round(float(yi), 4),
            "mesa": col["mesa"], "prof_final": col["prof_final"], "cota_fundo": col["cota_fundo"],
            "desviado": col["ctrl"][2], "campo": (d["cad"] or {}).get("campo") or "",
            "classe": msc._classe_poco(classe_txt),
            "unidades": [{k: u[k] for k in ("chave", "nome", "topo", "base", "cota_topo", "cota_base",
                                             "base_atingida")} for u in col["unidades"]]})
    if desviados:
        avisos.append(f"Poços desviados desenhados na vertical, na posição da cabeça (a cota dos topos é a do "
                      f"AGP): {', '.join(desviados)}.")
    sem = [p["id"] for p in saida if not p["unidades"]]
    if sem:
        avisos.append(f"Sem {msc.ROTULO_NIVEL[nivel]} com topo no AGP: {', '.join(sem)}.")

    xy = np.c_[[p["x"] for p in saida], [p["y"] for p in saida]]
    hull = contorno_convexo(xy)
    area = area_shoelace(hull)
    externo = com_margem(hull, margem_km)
    # grade sobre o contorno com margem
    lo, hi = externo.min(0), externo.max(0)
    lado = float(max(hi - lo)) or 1.0
    passo = lado / celulas
    nx = max(2, int(math.ceil((hi[0] - lo[0]) / passo)) + 1)
    ny = max(2, int(math.ceil((hi[1] - lo[1]) / passo)) + 1)
    gx, gy = np.meshgrid(lo[0] + passo * np.arange(nx), lo[1] + passo * np.arange(ny))

    # unidades em ordem estratigráfica (posição relativa média dentro de cada poço)
    acum: dict[str, list] = {}
    for p in saida:
        n_u = len(p["unidades"])
        for k, u in enumerate(p["unidades"]):
            acum.setdefault(u["chave"], []).append((p, u, k / (n_u - 1) if n_u > 1 else 0.5))
    legenda = []
    for ch, trios in acum.items():
        slot = slots.get(ch)
        legenda.append({"chave": ch, "nome": trios[0][1]["nome"], "slot": slot,
                        "cor": msc.CORES.get(slot, msc.COR_SEM_SLOT), "n_pocos": len(trios),
                        "posicao": float(np.mean([r for _, _, r in trios])),
                        "cota_media": float(np.mean([u["cota_topo"] for _, u, _ in trios]))})
    legenda.sort(key=lambda u: (u["posicao"], -u["cota_media"]))
    cor = {u["chave"]: u["cor"] for u in legenda}
    for p in saida:
        for u in p["unidades"]:
            u["cor"] = cor[u["chave"]]

    superficies = []
    for item in legenda:
        trios = acum[item["chave"]]
        pts = np.array([[p["x"], p["y"]] for p, _, _ in trios])
        val = np.array([u["cota_topo"] for _, u, _ in trios])
        sup = {"chave": item["chave"], "nome": item["nome"], "cor": item["cor"], "n_pocos": len(trios),
               "z": None, "area_km2": None, "contorno": None, "aviso": ""}
        h = contorno_convexo(pts)
        if len(trios) < 3:
            sup["aviso"] = f"{item['nome']}: só {len(trios)} poço(s) — sem superfície."
        elif len(h) < 3 or largura_relativa(h) < FRACAO_COLINEAR:
            sup["aviso"] = (f"{item['nome']}: poços quase alinhados — a interpolação de lado não teria dado; "
                            "só os topos nos poços.")
        else:
            tris = delaunay(pts)
            z = interpolar_linear(pts, val, tris, gx, gy)
            dentro_h = dentro(h, gx, gy)
            z[~dentro_h] = np.nan
            ext = com_margem(h, margem_km)
            if margem_km > 0:                     # faixa da margem: vizinho mais próximo
                faixa = dentro(ext, gx, gy) & ~dentro_h
                _, k = distancia_mais_proximo(pts, gx, gy)
                z[faixa] = val[k[faixa]]
            if dist_max_km:
                dmin, _ = distancia_mais_proximo(pts, gx, gy)
                z[dmin > float(dist_max_km)] = np.nan
            sup.update(z=z, area_km2=round(area_shoelace(h), 3),
                       contorno=[[round(float(a), 4), round(float(b), 4)] for a, b in ext])
            if margem_km <= 0 and not dist_max_km:
                # sem margem nem corte por distância, a superfície é exatamente a malha dos
                # triângulos entre os poços: a janela desenha esta (borda reta no contorno)
                sup["malha"] = {"pts": [[round(float(a), 4), round(float(b), 4), round(float(c), 2)]
                                        for (a, b), c in zip(pts, val)],
                                "tris": tris.tolist()}
        superficies.append(sup)

    # superfícies que se cruzam (unidade mais funda acima da mais rasa): pouco controle
    for a, b in zip(superficies, superficies[1:]):
        if a["z"] is None or b["z"] is None:
            continue
        ambos = ~np.isnan(a["z"]) & ~np.isnan(b["z"])
        if ambos.sum() == 0:
            continue
        frac = float((b["z"][ambos] > a["z"][ambos] + 0.5).sum()) / float(ambos.sum())
        if frac > 0.01:
            avisos.append(f"Em {frac:.0%} da área a superfície de {b['nome']} passa acima da de {a['nome']}: "
                          "as duas vêm de poços diferentes — pouco controle ali.")
    for s in superficies:
        if s["aviso"]:
            avisos.append(s["aviso"])
        if s["z"] is not None:
            zz = s["z"]
            s["cota_min"], s["cota_max"] = float(np.nanmin(zz)), float(np.nanmax(zz))
            s["z"] = [[None if math.isnan(v) else round(float(v), 2) for v in linha] for linha in zz]

    cotas = [v for p in saida for v in ([p["mesa"]] if p["mesa"] is not None else []) +
             ([p["cota_fundo"]] if p["cota_fundo"] is not None else []) +
             [u["cota_topo"] for u in p["unidades"]]]
    return {
        "versao": 1, "pocos": saida, "legenda": legenda, "superficies": superficies, "avisos": avisos,
        "origem": {"lat": lat0, "lon": lon0},
        "contorno": [[round(float(a), 4), round(float(b), 4)] for a, b in hull],
        "area_km2": round(area, 3), "margem_km": margem_km,
        "grade": {"x0": float(lo[0]), "y0": float(lo[1]), "passo": passo, "nx": nx, "ny": ny},
        "cota_max": max(cotas) if cotas else 0.0, "cota_min": min(cotas) if cotas else -1000.0,
        "parametros": {"nivel": nivel, "margem_km": margem_km, "celulas": celulas, "dist_max_km": dist_max_km,
                       "pocos": [p["id"] for p in saida]},
    }


# ========================================================= registro e saída
def registrar(pasta_execucoes: str, modelo: dict, autor: str = "") -> tuple[str, str]:
    os.makedirs(pasta_execucoes, exist_ok=True)
    base = "bloco_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    ident, k = base, 1
    while os.path.exists(os.path.join(pasta_execucoes, ident + ".json")):
        k += 1
        ident = f"{base}-{k}"
    reg = {"id": ident, "tipo": "bloco3d", "criado_em": agora(), "siapp_versao": __version__, "autor": autor,
           **modelo}
    caminho = os.path.join(pasta_execucoes, ident + ".json")
    with open(caminho + ".tmp", "w", encoding="utf-8") as f:
        json.dump(reg, f, ensure_ascii=False)
    os.replace(caminho + ".tmp", caminho)
    return ident, caminho


def abrir(pasta_execucoes: str, ident: str) -> dict:
    if not ident or not ident.startswith("bloco_") or "/" in ident or "\\" in ident:
        raise ErroBloco("Bloco inválido.")
    try:
        with open(os.path.join(pasta_execucoes, ident + ".json"), encoding="utf-8") as f:
            return json.load(f)
    except OSError as e:
        raise ErroBloco("Bloco não encontrado.") from e


def execucoes(pasta_execucoes: str) -> list[dict]:
    out = []
    if not os.path.isdir(pasta_execucoes):
        return out
    for nome in os.listdir(pasta_execucoes):
        if nome.startswith("bloco_") and nome.endswith(".json"):
            try:
                with open(os.path.join(pasta_execucoes, nome), encoding="utf-8") as f:
                    r = json.load(f)
            except (OSError, json.JSONDecodeError):
                continue
            out.append({"id": r.get("id", nome[:-5]), "criado_em": r.get("criado_em", ""),
                        "n_pocos": len(r.get("pocos", [])), "area_km2": r.get("area_km2"),
                        "parametros": r.get("parametros", {})})
    return sorted(out, key=lambda e: (e["criado_em"], e["id"]), reverse=True)


def exportar_csv(modelo: dict, pasta: str, ident: str) -> list[str]:
    """Dois CSV (';' e vírgula decimal): topos por poço e a grade das superfícies."""
    os.makedirs(pasta, exist_ok=True)

    def n(v, casas=2):
        return "" if v is None else f"{v:.{casas}f}".replace(".", ",")
    topos = os.path.join(pasta, f"{ident}_topos.csv")
    with open(topos, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["poco", "lat", "lon", "x_km", "y_km", "unidade", "topo_m", "cota_topo_m", "cota_base_m"])
        for p in modelo["pocos"]:
            for u in p["unidades"]:
                w.writerow([p["id"], n(p["lat"], 6), n(p["lon"], 6), n(p["x"], 3), n(p["y"], 3), u["nome"],
                            n(u["topo"]), n(u["cota_topo"]), n(u["cota_base"])])
    grade = os.path.join(pasta, f"{ident}_superficies.csv")
    g, o = modelo["grade"], modelo["origem"]
    sups = [s for s in modelo["superficies"] if s.get("z")]
    with open(grade, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["x_km", "y_km", "lat", "lon"] + [f"cota_topo_{s['chave']}_m" for s in sups])
        for j in range(g["ny"]):
            for i in range(g["nx"]):
                vals = [s["z"][j][i] for s in sups]
                if all(v is None for v in vals):
                    continue
                xx, yy = g["x0"] + i * g["passo"], g["y0"] + j * g["passo"]
                la, lo = para_geo(xx, yy, o["lat"], o["lon"])
                w.writerow([n(xx, 3), n(yy, 3), n(float(la), 6), n(float(lo), 6)] + [n(v) for v in vals])
    return [topos, grade]
