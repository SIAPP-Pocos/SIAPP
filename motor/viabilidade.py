"""Um campo diante da infraestrutura: distâncias e depleção (primeiro passo da viabilidade de
injetar CO₂ ou H₂ num campo depletado).

- **Polígono do campo**: o da ANP (vértices da área de produção, guardados ao baixar a
  produção), senão o da camada "Campos de produção" da ANP, senão o contorno convexo dos
  poços do campo no cadastro — e a resposta diz qual foi usado.
- **Distâncias** do polígono até a feição mais próxima de cada camada guardada em `sig/`
  (gasoduto de transporte, duto de escoamento, UPGN, city gate, projeto de H₂, termelétrica,
  porto…). Zero quando a feição toca ou atravessa o campo. O par de pontos mais próximo sai
  de uma projeção azimutal equidistante centrada no campo; a distância informada é a
  geodésica (haversine) entre esses dois pontos.
- **Depleção**: a fração do volume in place já produzida, pelo sumário do Plano de
  Desenvolvimento (data do BAR) e, quando a produção mensal baixada vai além dessa data, a
  mesma fração atualizada com o que foi produzido depois — indicada como estimativa.

Custos (R$/km de duto), capacidade de injeção e o indicador econômico ficam para a próxima
etapa: dependem de parâmetros que o usuário vai informar.
"""

from __future__ import annotations

import json
import math
import os

import numpy as np

from . import camadas as mca
from . import producao as mpr
from .banco import Banco

R_TERRA_KM = 6371.0088
# camadas usadas nas distâncias (as que fazem sentido para injeção); rótulo curto e campos a mostrar
ALVOS = [
    ("epe_gasodutos_transporte", "Gasoduto de transporte", ["Nome_Dut_1", "Diam_Pol_x", "Transporta", "Categoria"]),
    ("epe_dutos_escoamento", "Duto de escoamento", ["DUTO_ID", "DIAM_POL", "FLUIDO", "INST_ORIG", "INST_DEST", "Categoria"]),
    ("epe_gasodutos_distribuicao", "Gasoduto de distribuição", ["Distrib", "UF"]),
    ("epe_upgn", "UPGN", ["Nome", "MMm3d", "Situacao", "Municipio"]),
    ("epe_compressao", "Estação de compressão", ["Nome", "Municipio"]),
    ("epe_citygates", "City gate", ["Nome", "Municipio", "Transporta", "Segmento"]),
    ("epe_terminais_gnl", "Terminal de GNL", ["Nome", "Municipio"]),
    ("epe_h2_projetos", "Hidrogênio verde (unidade ou projeto)", ["Nome", "Capacidade", "Finalidade", "Estagio", "Local"]),
    ("epe_termeletricas_fosseis", "Termelétrica fóssil (fonte de CO₂)", ["nome", "potencia", "combust", "propriet"]),
    ("ibge_dutos", "Duto (IBGE)", ["nome", "mattransp", "situacaofi"]),
    ("ibge_termeletricas", "Termelétrica (IBGE)", ["nome", "potenciaou", "tipocombus"]),
    ("ibge_portos", "Porto", ["nome", "administra", "tipotransp"]),
    ("ibge_cidades", "Cidade (sede municipal)", ["nome", "nomeabrev", "geocodigo"]),
]


class ErroViabilidade(ValueError):
    pass


# ====================================================================== geometria
class Plano:
    """Projeção azimutal equidistante (esfera) centrada em (lat0, lon0): km."""

    def __init__(self, lat0: float, lon0: float):
        self.f0, self.l0 = math.radians(lat0), math.radians(lon0)

    def xy(self, lat, lon):
        f, l = np.radians(np.asarray(lat, float)), np.radians(np.asarray(lon, float))
        dl = l - self.l0
        cosc = np.sin(self.f0) * np.sin(f) + np.cos(self.f0) * np.cos(f) * np.cos(dl)
        c = np.arccos(np.clip(cosc, -1, 1))
        k = np.where(c < 1e-12, 1.0, c / np.where(np.sin(c) == 0, 1, np.sin(c)))
        x = R_TERRA_KM * k * np.cos(f) * np.sin(dl)
        y = R_TERRA_KM * k * (np.cos(self.f0) * np.sin(f) - np.sin(self.f0) * np.cos(f) * np.cos(dl))
        return x, y

    def latlon(self, x, y):
        x, y = np.asarray(x, float), np.asarray(y, float)
        rho = np.hypot(x, y)
        c = rho / R_TERRA_KM
        with np.errstate(invalid="ignore", divide="ignore"):
            f = np.arcsin(np.cos(c) * np.sin(self.f0) + np.where(rho == 0, 0, y * np.sin(c) * np.cos(self.f0) / rho))
            l = self.l0 + np.arctan2(x * np.sin(c), rho * np.cos(self.f0) * np.cos(c) - y * np.sin(self.f0) * np.sin(c))
        return np.degrees(f), np.degrees(l)


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    f1, f2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((f2 - f1) / 2) ** 2 + math.cos(f1) * math.cos(f2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * R_TERRA_KM * math.asin(min(1.0, math.sqrt(a)))


def _ponto_segmentos(px, py, ax, ay, bx, by):
    """Distância do ponto (px, py) a cada segmento (a→b) e o ponto mais próximo."""
    dx, dy = bx - ax, by - ay
    l2 = dx * dx + dy * dy
    t = np.where(l2 > 0, ((px - ax) * dx + (py - ay) * dy) / np.where(l2 > 0, l2, 1), 0.0)
    t = np.clip(t, 0, 1)
    qx, qy = ax + t * dx, ay + t * dy
    return np.hypot(px - qx, py - qy), qx, qy


def _cruzam(a, b, c, d) -> np.ndarray:
    """Segmentos a→b (n) cruzam c→d (m)? matriz n×m."""
    def orient(p, q, r):
        return (q[0][:, None] - p[0][:, None]) * (r[1][None] - p[1][:, None]) - \
               (q[1][:, None] - p[1][:, None]) * (r[0][None] - p[0][:, None])
    o1 = orient(a, b, c)
    o2 = orient(a, b, d)
    o3 = -((d[0][None] - c[0][None]) * (a[1][:, None] - c[1][None]) - (d[1][None] - c[1][None]) * (a[0][:, None] - c[0][None]))
    o4 = -((d[0][None] - c[0][None]) * (b[1][:, None] - c[1][None]) - (d[1][None] - c[1][None]) * (b[0][:, None] - c[0][None]))
    return (o1 * o2 <= 0) & (o3 * o4 <= 0)


def _dentro(px, py, poli_x, poli_y) -> np.ndarray:
    """Pontos dentro do polígono (raio par/ímpar)."""
    px, py = np.atleast_1d(px), np.atleast_1d(py)
    dentro = np.zeros(px.shape, bool)
    n = len(poli_x)
    j = n - 1
    for i in range(n):
        xi, yi, xj, yj = poli_x[i], poli_y[i], poli_x[j], poli_y[j]
        cruza = ((yi > py) != (yj > py)) & (px < (xj - xi) * (py - yi) / ((yj - yi) or 1e-300) + xi)
        dentro ^= cruza
        j = i
    return dentro


def _partes(geo) -> tuple[list, list]:
    """(pontos, linhas) de uma geometria GeoJSON; polígonos entram pelos anéis."""
    t, c = geo["type"], geo["coordinates"]
    if t == "Point":
        return [c], []
    if t == "MultiPoint":
        return list(c), []
    if t == "LineString":
        return [], [c]
    if t == "MultiLineString":
        return [], list(c)
    if t == "Polygon":
        return [], list(c)
    if t == "MultiPolygon":
        return [], [anel for p in c for anel in p]
    return [], []


def distancia_feicao(poli_xy, plano: Plano, geo) -> tuple[float, tuple[float, float], tuple[float, float]] | None:
    """(km no plano, ponto do campo, ponto da feição) — ou None se a geometria é vazia."""
    px, py = poli_xy
    ax, ay, bx, by = px[:-1], py[:-1], px[1:], py[1:]
    pontos, linhas = _partes(geo)
    melhor = None

    def considera(d, pc, pf):
        nonlocal melhor
        if melhor is None or d < melhor[0]:
            melhor = (float(d), pc, pf)
    if pontos:
        P = np.asarray(pontos, float)
        x, y = plano.xy(P[:, 1], P[:, 0])
        den = _dentro(x, y, px, py)
        for k in range(len(x)):
            if den[k]:
                considera(0.0, (x[k], y[k]), (x[k], y[k]))
                continue
            d, qx, qy = _ponto_segmentos(x[k], y[k], ax, ay, bx, by)
            i = int(np.argmin(d))
            considera(d[i], (qx[i], qy[i]), (x[k], y[k]))
    for linha in linhas:
        L = np.asarray(linha, float)
        if len(L) == 0:
            continue
        x, y = plano.xy(L[:, 1], L[:, 0])
        if _dentro(x[:1], y[:1], px, py)[0]:
            considera(0.0, (x[0], y[0]), (x[0], y[0]))
            continue
        if len(L) > 1:
            cx, cy, dx, dy = x[:-1], y[:-1], x[1:], y[1:]
            cruza = _cruzam((ax, ay), (bx, by), (cx, cy), (dx, dy))
            if cruza.any():
                i, j = np.argwhere(cruza)[0]
                considera(0.0, (cx[j], cy[j]), (cx[j], cy[j]))
                continue
        # vértices da linha contra as arestas do campo, e vértices do campo contra os segmentos da linha
        for k in range(len(x)):
            d, qx, qy = _ponto_segmentos(x[k], y[k], ax, ay, bx, by)
            i = int(np.argmin(d))
            considera(d[i], (qx[i], qy[i]), (x[k], y[k]))
        if len(L) > 1:
            for k in range(len(px) - 1):
                d, qx, qy = _ponto_segmentos(px[k], py[k], x[:-1], y[:-1], x[1:], y[1:])
                i = int(np.argmin(d))
                considera(d[i], (px[k], py[k]), (qx[i], qy[i]))
    return melhor


# ====================================================================== polígono do campo
def poligono_campo(banco: Banco, pasta_projeto: str, campo: str) -> tuple[list[list[float]], str]:
    """[[lat, lon], …] fechado, e de onde veio."""
    ficha = mpr.campo_guardado(banco, campo) or {}
    if ficha.get("poligono") and len(ficha["poligono"]) >= 3:
        return _fechar(ficha["poligono"]), "ANP — vértices da área do campo"
    caminho = os.path.join(pasta_projeto, mca.PASTA_SIG, "anp", "anp_campos_producao.geojson")
    if os.path.exists(caminho):
        with open(caminho, encoding="utf-8") as f:
            g = json.load(f)
        alvo = mpr.chave_campo(campo)
        for feat in g["features"]:
            if mpr.chave_campo(str((feat.get("properties") or {}).get("NOM_CAMPO", ""))) == alvo:
                geo = feat["geometry"]
                anel = geo["coordinates"][0] if geo["type"] == "Polygon" else \
                    max((p[0] for p in geo["coordinates"]), key=len)
                return _fechar([[b, a] for a, b in anel]), "ANP — camada Campos de produção"
    with banco.conexao() as c:
        rows = c.execute("SELECT campo, lat, lon FROM pocos WHERE lat IS NOT NULL AND lon IS NOT NULL").fetchall()
    alvo = mpr.chave_campo(campo)
    pts = np.array([(r["lon"], r["lat"]) for r in rows if mpr.chave_campo(r["campo"] or "") == alvo], float)
    if len(pts) >= 3:
        from .bloco import contorno_convexo
        h = contorno_convexo(pts)
        if len(h) >= 3:
            return _fechar([[float(b), float(a)] for a, b in h]), "contorno convexo dos poços do cadastro"
    raise ErroViabilidade(f"Sem polígono para o campo {campo}: baixe a produção do campo (traz os vértices da ANP) "
                          "ou a camada Campos de produção.")


def _fechar(pts: list) -> list:
    pts = [[float(a), float(b)] for a, b in pts]
    if pts[0] != pts[-1]:
        pts.append(pts[0])
    return pts


# ====================================================================== distâncias
def distancias(pasta_projeto: str, poligono: list[list[float]]) -> list[dict]:
    """Para cada camada guardada em sig/: a feição mais próxima do campo e a distância."""
    lat = np.array([p[0] for p in poligono])
    lon = np.array([p[1] for p in poligono])
    plano = Plano(float(lat[:-1].mean()), float(lon[:-1].mean()))
    pxy = plano.xy(lat, lon)
    idx = mca.indice(pasta_projeto)["camadas"]
    out = []
    for ident, rotulo, campos in ALVOS:
        reg = idx.get(ident)
        if not reg:
            out.append({"id": ident, "rotulo": rotulo, "baixada": False})
            continue
        with open(os.path.join(pasta_projeto, reg["arquivo"]), encoding="utf-8") as f:
            g = json.load(f)
        melhor = None
        for feat in g.get("features", []):
            geo = feat.get("geometry")
            if not geo:
                continue
            r = distancia_feicao(pxy, plano, geo)
            if r and (melhor is None or r[0] < melhor[0][0]):
                melhor = (r, feat.get("properties") or {})
        if melhor is None:
            out.append({"id": ident, "rotulo": rotulo, "baixada": True, "feicoes": reg.get("feicoes", 0),
                        "distancia_km": None})
            continue
        (d, pc, pf), props = melhor
        la_c, lo_c = plano.latlon(*pc)
        la_f, lo_f = plano.latlon(*pf)
        dist = 0.0 if d == 0 else haversine_km(float(la_c), float(lo_c), float(la_f), float(lo_f))
        out.append({"id": ident, "rotulo": rotulo, "baixada": True, "fonte": reg.get("fonte"),
                    "distancia_km": round(dist, 2), "toca_o_campo": d == 0,
                    "ponto_campo": [round(float(la_c), 6), round(float(lo_c), 6)],
                    "ponto_feicao": [round(float(la_f), 6), round(float(lo_f), 6)],
                    "feicao": {k: props.get(k) for k in campos if props.get(k) not in (None, "", " ")}})
    return out


# ====================================================================== depleção
def deplecao(banco: Banco, campo: str) -> dict | None:
    """Fração do in place já produzida, pelo PD e, se der, atualizada com a produção mensal."""
    ficha = mpr.campo_guardado(banco, campo) or {}
    pd = ficha.get("pd")
    if not pd or not pd.get("in_place"):
        return None
    vip, acu = pd["in_place"], pd.get("acumulada") or {}

    def gas(d):
        if d.get("gas_total_milhoes_m3") is not None:
            return d["gas_total_milhoes_m3"]
        g = [d.get(k) for k in ("gas_associado_milhoes_m3", "gas_nao_associado_milhoes_m3") if d.get(k) is not None]
        return sum(g) if g else None
    data = acu.get("data") or vip.get("data")
    corte = None
    if data and len(data) == 10:                      # 31/12/2021 → 2021-12
        corte = f"{data[6:10]}-{data[3:5]}"
    depois = None
    if corte:
        with banco.conexao() as c:
            r = c.execute("SELECT MAX(periodo) AS ate, MIN(periodo) AS de, SUM(oleo_m3) AS oleo, "
                          "SUM(COALESCE(gas_assoc_mil_m3, 0) + COALESCE(gas_nassoc_mil_m3, 0)) AS gas "
                          "FROM producao_poco WHERE campo = ? AND periodo > ?", (mpr.chave_campo(campo), corte)).fetchone()
            continua = c.execute("SELECT COUNT(*) FROM producao_poco WHERE campo = ? AND substr(periodo, 1, 7) = ?",
                                 (mpr.chave_campo(campo), _mes_seguinte(corte))).fetchone()[0]
        if r and r["ate"] and continua:              # só soma se a série começa logo depois da data do PD
            depois = {"de": r["de"], "ate": r["ate"], "oleo_milhoes_m3": (r["oleo"] or 0) / 1e6,
                      "gas_milhoes_m3": (r["gas"] or 0) / 1e3}
    out = {"fonte": pd.get("fonte"), "data_pd": data, "url_pd": pd.get("url")}
    for nome, vin, np_ in (("oleo", vip.get("oleo_milhoes_m3"), acu.get("oleo_milhoes_m3")),
                           ("gas", gas(vip), gas(acu))):
        if not vin:
            continue
        d = {"in_place_milhoes_m3": vin, "produzido_pd_milhoes_m3": np_,
             "fracao_pd": round(np_ / vin, 4) if np_ is not None else None}
        if depois and np_ is not None:
            extra = depois["oleo_milhoes_m3"] if nome == "oleo" else depois["gas_milhoes_m3"]
            d.update(produzido_depois_milhoes_m3=round(extra, 4), ate=depois["ate"],
                     fracao_atual_estimada=round((np_ + extra) / vin, 4))
        out[nome] = d
    return out


def _mes_seguinte(p: str) -> str:
    a, m = int(p[:4]), int(p[5:7])
    return f"{a + (m == 12)}-{m % 12 + 1:02d}"


def relatorio(banco: Banco, pasta_projeto: str, campo: str) -> dict:
    poli, fonte = poligono_campo(banco, pasta_projeto, campo)
    return {"campo": campo, "poligono": poli, "fonte_poligono": fonte,
            "distancias": distancias(pasta_projeto, poli), "deplecao": deplecao(banco, campo)}


COLUNAS_CSV = ["camada", "fonte", "distancia_km", "toca_o_campo", "lat_campo", "lon_campo", "lat_feicao", "lon_feicao",
               "atributos"]


def linhas_csv(rel: dict) -> list[list]:
    out = []
    for d in rel["distancias"]:
        if not d.get("baixada") or d.get("distancia_km") is None:
            continue
        out.append([d["rotulo"], d.get("fonte"), d["distancia_km"], "sim" if d["toca_o_campo"] else "não",
                    *d["ponto_campo"], *d["ponto_feicao"],
                    "; ".join(f"{k}={v}" for k, v in d["feicao"].items())])
    return out
