"""
Qual método de interpolação usar: uma sugestão em três camadas, cada uma com o motivo.

1. **Ambiente do reservatório** (`recursos/guia_interpolacao.json`, editável): regras práticas
   — ex.: em leque, superfícies lisas (RBF, spline); em fluvial, krigagem com anisotropia; em
   rifte, a linear (o SIAPP não modela falhas).
2. **Os dados**: quantos poços (krigagem pede 8, e 20+ para um variograma confiável), se estão
   agrupados (o IDW faz olhos de boi) e se há mergulho regional forte (tendência).
3. **A comparação dos métodos** nos poços do bloco (deixar um poço de fora), quando já foi feita:
   é a evidência — pesa mais que as outras duas.

Cada método recebe pontos de cada camada; a soma vira "indicado", "possível" ou "evitar". Nada
aqui muda o bloco: a janela mostra a lista e o botão "Usar o indicado" só preenche o formulário.
"""

from __future__ import annotations

import json
import math
import os

import numpy as np

from . import interpolacao as mint

CAMINHO_PADRAO = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                              "recursos", "guia_interpolacao.json")
POCOS_VARIOGRAMA = 20          # krigagem com variograma confiável
R2_TENDENCIA = 0.7             # um plano explica 70%+ da variação do topo: mergulho regional forte
AGRUPADO = 0.6                 # vizinho mais próximo médio / o esperado ao acaso abaixo disso: agrupados


def ler_guia(caminho: str = CAMINHO_PADRAO) -> dict:
    try:
        with open(caminho, encoding="utf-8") as f:
            g = json.load(f)
    except (OSError, json.JSONDecodeError):
        g = {}
    ambientes = [a for a in g.get("ambientes", []) if isinstance(a, dict) and a.get("id")]
    if not any(a["id"] == "nao_sei" for a in ambientes):
        ambientes.insert(0, {"id": "nao_sei", "nome": "Não sei / misto", "recomendados": [], "evitar": [],
                             "porque": {}, "resumo": ""})
    for a in ambientes:
        a["recomendados"] = [m for m in a.get("recomendados", []) if m in mint.METODOS]
        a["evitar"] = [m for m in a.get("evitar", []) if m in mint.METODOS]
        a.setdefault("porque", {})
        a.setdefault("parametros", {})
    return {"ambientes": ambientes}


def diagnostico(pts, valores=None) -> dict:
    """Números dos dados que pesam na escolha: poços, espaçamento, agrupamento e, com os
    valores do topo de referência, quanto um plano explica (R²)."""
    pts = np.asarray(pts, float).reshape(-1, 2)
    vals = None if valores is None else np.asarray(valores, float)
    grupos: dict = {}                                   # posições repetidas: uma, com a média
    for i, (x, y) in enumerate(pts):
        grupos.setdefault((round(x, 6), round(y, 6)), []).append(i)
    pts = np.array([pts[g[0]] for g in grupos.values()], float).reshape(-1, 2)
    if vals is not None and len(vals) == sum(len(g) for g in grupos.values()):
        valores = [float(vals[g].mean()) for g in grupos.values()]
    n = len(pts)
    d = {"n": n, "espacamento_km": None, "agrupamento": None, "r2_plano": None}
    if n >= 2:
        dist = np.hypot(pts[:, None, 0] - pts[None, :, 0], pts[:, None, 1] - pts[None, :, 1])
        np.fill_diagonal(dist, np.inf)
        viz = dist.min(1)
        d["espacamento_km"] = round(float(np.median(viz)), 3)
        if n >= 5:
            w, h = np.ptp(pts[:, 0]), np.ptp(pts[:, 1])
            area = max(w * h, 1e-9)
            esperado = 0.5 * math.sqrt(area / n)           # Clark e Evans (1954): pontos ao acaso
            if esperado > 0:
                d["agrupamento"] = round(float(viz.mean() / esperado), 2)
    if valores is not None and n >= 5:
        v = np.asarray(valores, float)
        if len(v) == len(pts) and np.ptp(v) > 0:
            A = np.column_stack([np.ones(len(v)), pts])
            beta = np.linalg.lstsq(A, v, rcond=None)[0]
            res = v - A @ beta
            d["r2_plano"] = round(float(1 - res.var() / v.var()), 2)
    return d


def _metodo_do_candidato(c: dict) -> str:
    est = (c.get("interpolacao") or {}).get("estrutura") or {}
    return est.get("metodo") or c.get("id", "").split("_")[0]


def recomendar(ambiente: str, dados: dict, comparacao: dict | None = None, guia: dict | None = None) -> dict:
    """[{id, nome, nota, pontos, motivos: [{fonte, texto, sinal}]}] do mais ao menos indicado,
    e o indicado (com os parâmetros sugeridos pelo ambiente)."""
    guia = guia or ler_guia()
    amb = next((a for a in guia["ambientes"] if a["id"] == ambiente), guia["ambientes"][0])
    nomes = {i["id"]: i["nome"] for i in mint.INFO}
    linhas = {m: {"id": m, "nome": nomes[m], "pontos": 0, "motivos": []} for m in mint.METODOS}

    def add(m, pts, fonte, texto):
        linhas[m]["pontos"] += pts
        linhas[m]["motivos"].append({"fonte": fonte, "texto": texto, "sinal": (pts > 0) - (pts < 0)})

    # 1. ambiente
    for k, m in enumerate(amb["recomendados"]):
        add(m, 2 if k == 0 else 1, "ambiente", amb["porque"].get(m) or f"indicado para {amb['nome'].lower()}")
    for m in amb["evitar"]:
        add(m, -2, "ambiente", amb["porque"].get(m) or f"pouco indicado para {amb['nome'].lower()}")

    # 2. dados
    n = dados.get("n") or 0
    if n:
        if n < mint.MIN_KRIGAGEM:
            for m in ("krigagem", "tendencia"):
                add(m, -4, "dados", f"só {n} poços: krigagem pede {mint.MIN_KRIGAGEM} ou mais (o SIAPP usaria a linear)")
        elif n < POCOS_VARIOGRAMA:
            for m in ("krigagem", "tendencia"):
                add(m, -1, "dados", f"{n} poços: o variograma ainda é pouco confiável (melhor com {POCOS_VARIOGRAMA}+)")
        else:
            add("krigagem", 1, "dados", f"{n} poços: dá um variograma confiável e o mapa de incerteza")
        if n < 6:
            add("linear", 1, "dados", f"poucos poços ({n}): a linear não inventa nada além deles")
        if 6 <= n <= 60:
            for m in ("spline", "rbf"):
                add(m, 1, "dados", f"{n} poços: bom número para uma superfície lisa ajustada pela validação cruzada")
    ag = dados.get("agrupamento")
    if ag is not None and ag < AGRUPADO:
        add("idw", -1, "dados", "poços agrupados: o IDW faz 'olhos de boi' em volta de cada grupo")
        if n >= mint.MIN_KRIGAGEM:
            add("krigagem", 1, "dados", "poços agrupados: a krigagem não deixa um grupo pesar demais")
    r2 = dados.get("r2_plano")
    if r2 is not None and n >= mint.MIN_KRIGAGEM:
        if r2 >= R2_TENDENCIA:
            add("tendencia", 2, "dados", f"um plano explica {round(100 * r2)}% da variação do topo: mergulho "
                                         "regional forte — tire a tendência antes de krigar")
        elif r2 < 0.3:
            add("tendencia", -1, "dados", f"sem mergulho regional claro (um plano explica só {round(100 * r2)}%)")

    # 3. comparação nos poços (a evidência)
    if comparacao and comparacao.get("candidatos"):
        crit = comparacao.get("criterio", "fechado")
        por_metodo: dict = {}
        for c in comparacao["candidatos"]:
            med = (c["global"].get(crit) or {}).get("mediana")
            m = _metodo_do_candidato(c)
            if med is not None and m in linhas and (m not in por_metodo or med < por_metodo[m][0]):
                por_metodo[m] = (med, c["nome"])
        if por_metodo:
            melhor_m, (melhor, nome_melhor) = min(por_metodo.items(), key=lambda t: t[1][0])
            for m, (med, nome_c) in por_metodo.items():
                txt = f"{nome_c}: mediana do erro {med:.1f} m deixando cada poço de fora"
                if m == melhor_m:
                    add(m, 4, "comparacao", "errou menos nos seus poços — " + txt)
                elif med <= melhor * 1.1 + 1.0:
                    add(m, 2, "comparacao", "empatou com o melhor (diferença dentro do ruído dos topos) — " + txt)
                elif med > melhor * 1.5:
                    add(m, -2, "comparacao", "errou bem mais que o melhor — " + txt)
                else:
                    add(m, 0, "comparacao", txt)

    for L in linhas.values():
        p = L["pontos"]
        L["nota"] = "indicado" if p >= 3 else "possivel" if p >= 0 else "evitar"
        if not L["motivos"]:
            L["motivos"].append({"fonte": "geral", "texto": next(i["quando"] for i in mint.INFO if i["id"] == L["id"]),
                                 "sinal": 0})
    ordem = sorted(linhas.values(), key=lambda L: (-L["pontos"], mint.METODOS.index(L["id"])))
    topo = ordem[0]
    return {"ambiente": {k: amb.get(k) for k in ("id", "nome", "resumo", "nota")}, "dados": dados,
            "com_comparacao": bool(comparacao and comparacao.get("candidatos")),
            "metodos": ordem, "indicado": {"metodo": topo["id"], "nome": topo["nome"],
                                           "parametros": amb.get("parametros", {}).get(topo["id"], {})}}
