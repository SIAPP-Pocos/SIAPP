"""Seção estratigráfica: poços lado a lado, correlacionados pelos topos do AGP.

A correlação é pela **identidade da unidade** que a operadora registrou no AGP (mesma
sigla de formação em poços vizinhos), não por semelhança de curvas. O SIAPP não
interpreta: desenha o que o AGP diz e aponta onde dois vizinhos discordam muito.

Ordem dos poços
- ``linha``: projeção na reta do primeiro ao último poço da lista (A→B);
- ``pca``: projeção na direção de maior espalhamento dos poços (componente principal),
  orientada de oeste para leste (ou de norte para sul, se a direção for mais N–S);
- ``lista``: na ordem dada, com a distância acumulada entre poços consecutivos.

Eixo vertical
- ``cota``: cota do AGP (m, positiva acima do nível do mar), como a operadora calculou;
- ``nivelado``: cota menos a cota do topo de uma unidade escolhida (datum = 0) — mostra a
  geometria relativa de deposição, sem a estrutura posterior. y = 0 é local de cada poço.

Curva GR (opcional): de um perfil já lido do mesmo poço. Profundidade medida → cota por
``cota = mesa rotativa − prof``; se as cotas do AGP mostram que o poço é desviado (cota ≠
mesa − prof), a conversão usa os próprios pares (prof, cota) do AGP como pontos de controle.
"""

from __future__ import annotations

import csv
import json
import math
import os
import re
from datetime import datetime
from html import escape

import numpy as np

from . import __version__
from . import agp as magp
from .banco import Banco, agora

MAX_POCOS = 20
LIMIAR_SALTO_M = 100.0
NIVEIS_SECAO = {
    "formacoes": ("F", ""),          # formações e unidades sem nível (Embasamento)
    "membros": ("M", "C"),           # membros e camadas
    "grupos": ("G", "S"),
}
ROTULO_NIVEL = {"formacoes": "formações", "membros": "membros e camadas", "grupos": "grupos"}

# Paleta categórica (validada para daltonismo nos pares vizinhos; ver docs/secao.md). A
# cor segue a unidade — vem do "slot" de recursos/estratigrafia.json, nunca da posição.
CORES = {1: "#2a78d6", 2: "#eb6834", 3: "#1baf7a", 4: "#eda100",
         5: "#e87ba4", 6: "#008300", 7: "#6250d6", 8: "#e34948"}
COR_SEM_SLOT = "#c3c2b7"
TINTA = "#0b0b0b"
TINTA_2 = "#52514e"
TINTA_FRACA = "#898781"
GRADE = "#e1e0d9"
FONTE = "Times New Roman, Times, Liberation Serif, DejaVu Serif, serif"

# litologia de calha: mesmas cores da trilha da aba Perfis
CORES_ROCHA = [
    (r"ARENITO|AREIA|CONGLOMERADO", "#f2d16b"), (r"FOLHELHO|ARGILITO|SILTITO|MARGA", "#8fa58a"),
    (r"CALC|DOLOMIT|COQUINA", "#8fb8d9"), (r"EVAPORIT|HALITA|ANIDRITA|SAL", "#d9a3c9"),
    (r"GRANITO|GNAISSE|EMBASAMENTO|BASALTO|DIABASIO|METAMORF", "#c98f7a"), (r"CARVAO|LINHITO", "#3d3d3d"),
]


class ErroSecao(ValueError):
    pass


# ================================================================ dicionário
def ler_slots(caminho: str) -> dict[str, int]:
    """{SIGLA: slot de cor} de recursos/estratigrafia.json."""
    try:
        with open(caminho, encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}
    return {" ".join(u.get("sigla", "").split()).upper(): int(u["slot"])
            for u in d.get("unidades", []) if u.get("slot")}


def cor_rocha(rocha: str) -> str:
    r = (rocha or "").upper()
    for padrao, cor in CORES_ROCHA:
        if re.search(padrao, r):
            return cor
    return "#d5d3cc"


# ============================================================== geometria
def _plano(lats, lons):
    """lat/lon → km num plano local (equiretangular na latitude média)."""
    lat0 = math.radians(float(np.mean(lats)))
    x = np.radians(np.asarray(lons, float)) * 6371.0 * math.cos(lat0)
    y = np.radians(np.asarray(lats, float)) * 6371.0
    return x, y


def _rumo(ux: float, uy: float) -> tuple[str, str]:
    """Letras das pontas da seção (esquerda, direita) para o vetor (leste, norte)."""
    ang = (math.degrees(math.atan2(ux, uy)) + 360) % 360    # azimute da direita
    pontos = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    d = pontos[int((ang + 22.5) // 45) % 8]
    e = pontos[int(((ang + 180) % 360 + 22.5) // 45) % 8]
    return e, d


def ordenar(coords: list[dict], modo: str = "linha") -> dict:
    """coords: [{id, lat, lon}] → {ordem: [ids], x_km: {id: x}, perp_km: {id: d}, pontas}."""
    if len(coords) < 2:
        raise ErroSecao("Escolha ao menos dois poços com coordenadas.")
    x, y = _plano([c["lat"] for c in coords], [c["lon"] for c in coords])
    ids = [c["id"] for c in coords]
    if modo == "lista":
        dist = [0.0]
        for i in range(1, len(ids)):
            dist.append(dist[-1] + float(math.hypot(x[i] - x[i - 1], y[i] - y[i - 1])))
        u = (x[-1] - x[0], y[-1] - y[0])
        n = math.hypot(*u) or 1.0
        return {"ordem": ids, "x_km": dict(zip(ids, dist)), "perp_km": dict.fromkeys(ids, 0.0),
                "pontas": _rumo(u[0] / n, u[1] / n), "modo": modo}
    if modo == "pca":
        m = np.column_stack([x - x.mean(), y - y.mean()])
        _, _, vt = np.linalg.svd(m, full_matrices=False)
        ux, uy = float(vt[0, 0]), float(vt[0, 1])
        if (abs(ux) >= abs(uy) and ux < 0) or (abs(ux) < abs(uy) and uy > 0):
            ux, uy = -ux, -uy
        x0, y0 = float(x.mean()), float(y.mean())
    else:   # linha: do primeiro ao último da lista
        dx, dy = float(x[-1] - x[0]), float(y[-1] - y[0])
        n = math.hypot(dx, dy)
        if n < 1e-6:
            raise ErroSecao("O primeiro e o último poço estão no mesmo lugar: use outra ordem.")
        ux, uy, x0, y0 = dx / n, dy / n, float(x[0]), float(y[0])
    t = (x - x0) * ux + (y - y0) * uy
    perp = -(x - x0) * uy + (y - y0) * ux
    t = t - t.min()
    ordem = [ids[i] for i in np.argsort(t, kind="stable")]
    return {"ordem": ordem, "x_km": {i: float(v) for i, v in zip(ids, t)},
            "perp_km": {i: float(abs(v)) for i, v in zip(ids, perp)}, "pontas": _rumo(ux, uy), "modo": modo}


def _subamostrar(itens: list, n: int) -> list:
    """n itens espaçados por igual, mantendo as pontas."""
    if len(itens) <= n:
        return itens
    idx = sorted({round(k * (len(itens) - 1) / (n - 1)) for k in range(n)})
    return [itens[i] for i in idx]


# ===================================================================== dados
def pocos_com_topos(banco: Banco, bacia: str | None = None) -> list[dict]:
    """Poços que têm topos litoestratigráficos no AGP e coordenadas no cadastro."""
    cond, args = "", []
    if bacia:
        cond, args = "AND u.bacia = ?", [bacia]
    with banco.conexao() as c:
        return [dict(r) for r in c.execute(
            f"""SELECT u.poco_id AS id, count(DISTINCT u.sigla) AS n_unidades, p.lat, p.lon, p.campo,
                       group_concat(DISTINCT u.sigla) AS siglas
                FROM agp_unidades u JOIN pocos p ON p.id = u.poco_id
                WHERE u.tip = 'L' AND u.topo IS NOT NULL AND p.lat IS NOT NULL {cond}
                GROUP BY u.poco_id ORDER BY u.poco_id""", args)]


def corredor(banco: Banco, poco_a: str, poco_b: str, largura_km: float = 2.0,
             bacia: str | None = None, maximo: int = MAX_POCOS) -> dict:
    """Poços com topos a até `largura_km` da reta A–B (entre A e B), na ordem A→B."""
    todos = {p["id"]: p for p in pocos_com_topos(banco, bacia)}
    with banco.conexao() as c:
        for pid in (poco_a, poco_b):
            if pid not in todos:
                r = c.execute("SELECT id, lat, lon, campo FROM pocos WHERE id = ?", (pid,)).fetchone()
                if not r or r["lat"] is None:
                    raise ErroSecao(f"{pid}: sem coordenadas no cadastro da ANP.")
                todos[pid] = {**dict(r), "n_unidades": 0, "siglas": ""}
    ids = list(todos)
    x, y = _plano([todos[i]["lat"] for i in ids], [todos[i]["lon"] for i in ids])
    ia, ib = ids.index(poco_a), ids.index(poco_b)
    dx, dy = float(x[ib] - x[ia]), float(y[ib] - y[ia])
    comp = math.hypot(dx, dy)
    if comp < 1e-6:
        raise ErroSecao("A e B estão no mesmo lugar.")
    ux, uy = dx / comp, dy / comp
    achados = []
    for k, pid in enumerate(ids):
        t = (x[k] - x[ia]) * ux + (y[k] - y[ia]) * uy
        d = abs(-(x[k] - x[ia]) * uy + (y[k] - y[ia]) * ux)
        if (-0.05 <= t <= comp + 0.05 and d <= largura_km) or pid in (poco_a, poco_b):
            achados.append({**todos[pid], "t_km": round(float(t), 3), "dist_linha_km": round(float(d), 3)})
    achados.sort(key=lambda p: p["t_km"])
    escolhidos = _subamostrar(achados, maximo)
    return {"pocos": escolhidos, "encontrados": len(achados), "comprimento_km": round(comp, 3)}


def _mesa(cab: dict, cadastro: dict | None, unidades: list[dict]) -> float | None:
    for v in (cab.get("mesa_rotativa"), (cadastro or {}).get("mesa_rotativa")):
        if v is not None:
            return float(v)
    pares = [u["topo"] + u["cota_topo"] for u in unidades if u["topo"] is not None and u["cota_topo"] is not None]
    return float(np.median(pares)) if pares else None


def _controle(mesa: float | None, unidades: list[dict]) -> tuple[np.ndarray, np.ndarray, bool]:
    """Pontos (prof medida, cota) do AGP. desviado=True se cota ≠ mesa − prof."""
    pts = {}
    for u in unidades:
        for p, c in ((u["topo"], u["cota_topo"]), (u["base"], u["cota_base"])):
            if p is not None and c is not None:
                pts[round(p, 2)] = c
    if mesa is not None:
        pts.setdefault(0.0, mesa)
    if not pts:
        return np.array([]), np.array([]), False
    md = np.array(sorted(pts))
    cota = np.array([pts[k] for k in md])
    desviado = mesa is not None and bool(np.any(np.abs(cota - (mesa - md)) > 1.5))
    return md, cota, desviado


def _md_para_cota(md: np.ndarray, mesa: float | None, ctrl) -> np.ndarray | None:
    pmd, pcota, desviado = ctrl
    if not desviado:
        return None if mesa is None else mesa - md
    if len(pmd) < 2:
        return None
    out = np.interp(md, pmd, pcota)
    # fora dos pontos: prolonga a inclinação da ponta
    a0 = (pcota[1] - pcota[0]) / ((pmd[1] - pmd[0]) or 1)
    a1 = (pcota[-1] - pcota[-2]) / ((pmd[-1] - pmd[-2]) or 1)
    out = np.where(md < pmd[0], pcota[0] + a0 * (md - pmd[0]), out)
    return np.where(md > pmd[-1], pcota[-1] + a1 * (md - pmd[-1]), out)


def _cadastro(banco: Banco, pid: str) -> dict | None:
    with banco.conexao() as c:
        r = c.execute("SELECT id, lat, lon, mesa_rotativa, cota_altimetrica, prof_sondador, campo, direcao "
                      "FROM pocos WHERE id = ?", (pid,)).fetchone()
    return dict(r) if r else None


def _classe_poco(txt: str) -> str:
    """Símbolo do poço pela (re)classificação do AGP ou do cadastro."""
    t = txt.upper()
    oleo, gas = "OLEO" in t or "ÓLEO" in t, "GAS" in t or "GÁS" in t
    if "SECO" in t and not (oleo or gas):
        return "seco"
    if oleo and gas:
        return "oleo_gas"
    return "oleo" if oleo else "gas" if gas else "outro"


def _rotulo_unidade(u: dict) -> str:
    nivel = magp.NIVEIS.get(u["nivel"], "")
    return f"{nivel} {u['nome']}".strip()


def _normalizar(u: dict, nomes: dict) -> dict:
    """Unidade como o leitor atual a veria: AGPs lidos por um leitor antigo podem ter
    "C PONTUB" sem a letra de nível separada, ou o nome de antes do dicionário."""
    u = dict(u)
    bruta = u["sigla"] or ""
    sigla = " ".join(bruta.split())
    m = re.match(r"^([FMGSC])\s+(\S.*)$", sigla) if u["tip"] == "L" and not u["nivel"] else None
    if m:
        u["nivel"], sigla = m.group(1), m.group(2)
    u["sigla"] = sigla
    guardado = u["nome"] if u["nome"] and u["nome"] != bruta else sigla
    u["nome"] = nomes.get(u.get("codigo") or "") or nomes.get(sigla.upper()) or guardado
    return u


def dados_poco(banco: Banco, pid: str, nomes: dict) -> dict | None:
    """Cadastro, AGP e unidades de um poço (None se não tiver coordenadas). Usado pela
    seção e pelo bloco 3D."""
    cad = _cadastro(banco, pid)
    agps = magp.do_poco(banco, pid)
    g = agps[0] if agps else None
    cab = g["dados"]["cabecalho"] if g else {}
    lat = cad["lat"] if cad and cad.get("lat") is not None else cab.get("lat")
    lon = cad["lon"] if cad and cad.get("lon") is not None else cab.get("lon")
    if lat is None or lon is None:
        return None
    todas = [_normalizar(u, nomes) for u in magp.unidades_do_poco(banco, pid)
             if not g or u["caminho"] == g["caminho"]]
    return {"id": pid, "lat": float(lat), "lon": float(lon), "cad": cad, "agp": g, "cab": cab,
            "lito": [u for u in todas if u["tip"] == "L"], "todas": todas}


def coluna_poco(d: dict, niveis: tuple) -> dict:
    """Mesa, pontos de controle (prof, cota), fundo do poço e unidades do nível pedido com
    topo e base em cota — a coluna estratigráfica do poço segundo o AGP."""
    mesa = _mesa(d["cab"], d["cad"], d["lito"])
    ctrl = _controle(mesa, d["todas"])
    prof_final = d["cab"].get("prof_final") or (d["cad"] or {}).get("prof_sondador")
    cota_fundo = None
    if prof_final:
        cf = _md_para_cota(np.array([float(prof_final)]), mesa, ctrl)
        cota_fundo = float(cf[0]) if cf is not None else None
    uns = []
    escolhidas = sorted([u for u in d["lito"] if u["nivel"] in niveis and u["topo"] is not None],
                        key=lambda u: (u["topo"], u["ordem"]))
    for k, u in enumerate(escolhidas):
        ct = u["cota_topo"] if u["cota_topo"] is not None else (mesa - u["topo"] if mesa is not None else None)
        if ct is None:
            continue
        base, cb = u["base"], u["cota_base"]
        # leiaute novo: "N" depois da base = base não atingida (a base é o fundo do poço)
        atingida = base is not None and (u.get("desc_base") or "") != "N"
        if base is not None and cb is None and mesa is not None:
            cb = mesa - base
        if cb is None:      # sem base: até a próxima unidade, ou até o fundo do poço
            prox = next((v for v in escolhidas[k + 1:] if v["topo"] > u["topo"]), None)
            if prox is not None:
                cb = prox["cota_topo"] if prox["cota_topo"] is not None else ct - (prox["topo"] - u["topo"])
                base = prox["topo"]
            elif cota_fundo is not None:
                cb, base, atingida = cota_fundo, prof_final, False
            else:
                cb, base, atingida = ct, u["topo"], False
        uns.append({"chave": u["sigla"].upper(), "sigla": u["sigla"], "nome": _rotulo_unidade(u),
                    "nivel": u["nivel"], "topo": u["topo"], "base": base, "cota_topo": float(ct),
                    "cota_base": float(cb), "base_atingida": atingida, "fonte": u["fonte"] or "",
                    "data": u["data"] or "", "qualidade": magp.QUALIDADES.get(u["ql"] or "", ""),
                    "metodo": u["metodo"] or ""})
    return {"mesa": mesa, "ctrl": ctrl, "prof_final": prof_final, "cota_fundo": cota_fundo, "unidades": uns}


def montar(banco: Banco, pocos: list[str], *, ordem: str = "linha", nivel: str = "formacoes",
           eixo: str = "cota", datum: str | None = None, espacamento: str = "proporcional",
           litologia: bool = True, gr: bool = True, gr_de=None, slots: dict | None = None,
           nomes: dict | None = None, estilo: str = "classico",
           limiar_salto_m: float = LIMIAR_SALTO_M, janela: tuple | None = None) -> dict:
    """Modelo da seção (dados, sem desenho). `gr_de(poco_id)` devolve
    {arquivo, mnemonico, prof, valores} ou None."""
    pocos = list(dict.fromkeys(p for p in pocos if p))
    if len(pocos) < 2:
        raise ErroSecao("Escolha ao menos dois poços.")
    if len(pocos) > MAX_POCOS:
        raise ErroSecao(f"No máximo {MAX_POCOS} poços por seção (há {len(pocos)}).")
    if nivel not in NIVEIS_SECAO:
        raise ErroSecao(f"Nível desconhecido: {nivel}")
    niveis = NIVEIS_SECAO[nivel]
    slots, nomes = slots or {}, nomes or {}
    avisos: list[str] = []

    dados = {}
    for pid in pocos:
        d = dados_poco(banco, pid, nomes)
        if d is None:
            avisos.append(f"{pid}: sem coordenadas — fora da seção.")
            continue
        dados[pid] = d
        if d["agp"] is None:
            avisos.append(f"{pid}: sem AGP lido — a coluna fica vazia.")
        elif d["agp"].get("confere") == 0:
            avisos.append(f"{pid}: o AGP usado estava na pasta de {d['agp']['poco_pasta']} no portal.")

    if len(dados) < 2:
        raise ErroSecao("Menos de dois poços com coordenadas.")
    geo = ordenar([{"id": p, "lat": d["lat"], "lon": d["lon"]} for p, d in dados.items()], ordem)

    saida_pocos = []
    for pid in geo["ordem"]:
        d = dados[pid]
        col = coluna_poco(d, niveis)
        mesa, ctrl, prof_final, cota_fundo, uns = (col["mesa"], col["ctrl"], col["prof_final"],
                                                   col["cota_fundo"], col["unidades"])
        if ctrl[2]:
            avisos.append(f"{pid}: poço desviado (as cotas do AGP não são mesa − profundidade); "
                          "a curva GR usa os pontos do AGP para converter.")
        if not uns:
            avisos.append(f"{pid}: o AGP não tem {ROTULO_NIVEL[nivel]} com topo.")
        lit = []
        if litologia and d["agp"]:
            for c in d["agp"]["dados"].get("litologia", []):
                if c.get("topo") is None or c.get("base") is None:
                    continue
                cc = _md_para_cota(np.array([c["topo"], c["base"]], float), mesa, ctrl)
                if cc is not None:
                    lit.append({"cota_topo": float(cc[0]), "cota_base": float(cc[1]), "rocha": c["rocha"],
                                "descricao": c.get("descricao", ""), "topo": c["topo"], "base": c["base"]})
        curva = None
        if gr and gr_de is not None:
            try:
                bruto = gr_de(pid)
            except Exception as e:          # um perfil ilegível não derruba a seção
                bruto = None
                avisos.append(f"{pid}: GR não lido ({e}).")
            if bruto and bruto.get("prof"):
                md = np.array(bruto["prof"], float)
                cotas = _md_para_cota(md, mesa, ctrl)
                if cotas is None:
                    avisos.append(f"{pid}: sem mesa rotativa — a curva GR não pode ser posta em cota.")
                else:
                    curva = {"arquivo": bruto.get("arquivo", ""), "mnemonico": bruto.get("mnemonico", ""),
                             "cota": [round(float(v), 2) for v in cotas],
                             "valores": [None if v is None or not math.isfinite(v) else float(v)
                                         for v in bruto["valores"]]}
        # para o estilo clássico: indícios, discordâncias, classe do poço, escala de prof. medida
        indic = []
        if d["agp"]:
            for c in d["agp"]["dados"].get("indicios", []):
                if c.get("topo") is None:
                    continue
                cc = _md_para_cota(np.array([c["topo"], c.get("base") or c["topo"]], float), mesa, ctrl)
                if cc is not None:
                    indic.append({"fluido": c.get("fluido", ""), "topo": c["topo"], "base": c.get("base"),
                                  "cota_topo": float(cc[0]), "cota_base": float(cc[1]), "amostra": c.get("amostra", "")})
        disc = [{"sigla": u["sigla"], "nome": u["nome"], "topo": u["topo"],
                 "cota_topo": float(u["cota_topo"] if u["cota_topo"] is not None else mesa - u["topo"])}
                for u in d["todas"] if u["tip"] == "D" and u["topo"] is not None
                and (u["cota_topo"] is not None or mesa is not None)]
        md_cota = []
        if prof_final:
            grade_md = np.arange(0.0, float(prof_final) + 0.01, 50.0)
            cg = _md_para_cota(grade_md, mesa, ctrl)
            if cg is not None:
                md_cota = [[float(a), float(b)] for a, b in zip(grade_md, cg)]
        classe_txt = " ".join(filter(None, [d["cab"].get("reclassificacao"), d["cab"].get("classificacao"),
                                            (d["cad"] or {}).get("reclassificacao")])).upper()
        saida_pocos.append({
            "id": pid, "lat": d["lat"], "lon": d["lon"], "x_km": round(geo["x_km"][pid], 3),
            "classe": _classe_poco(classe_txt), "classe_texto": classe_txt.strip(),
            "bacia": d["cab"].get("bacia") or "", "indicios": indic, "discordancias": disc, "md_cota": md_cota,
            "dist_linha_km": round(geo["perp_km"][pid], 3), "mesa": mesa, "desviado": ctrl[2],
            "prof_final": prof_final, "cota_fundo": cota_fundo, "campo": (d["cad"] or {}).get("campo") or "",
            "agp": (d["agp"] or {}).get("arquivo_local") or (d["agp"] or {}).get("caminho") or "",
            "agp_formato": ((d["agp"] or {}).get("dados") or {}).get("formato", ""),
            "unidades": uns, "litologia": lit, "gr": curva,
        })

    # eixo vertical: cota ou nivelado no topo do datum
    nome_datum = None
    if eixo == "nivelado":
        if not datum:
            raise ErroSecao("Para nivelar, escolha a unidade do datum.")
        chave_d = datum.upper()
        sem = []
        for p in saida_pocos:
            ref = next((u["cota_topo"] for u in p["unidades"] if u["chave"] == chave_d), None)
            if ref is None:   # o datum pode ser de outro nível: procura entre todas as unidades
                ref = next((u["cota_topo"] for u in dados[p["id"]]["lito"]
                            if u["sigla"].upper() == chave_d and u["cota_topo"] is not None), None)
            p["datum_cota"] = ref
            if ref is None:
                sem.append(p["id"])
        nome_datum = next((u["nome"] for p in saida_pocos for u in p["unidades"] if u["chave"] == chave_d),
                          None) or next((_rotulo_unidade(u) for d in dados.values() for u in d["lito"]
                                         if u["sigla"].upper() == chave_d), datum)
        if sem:
            avisos.append(f"Sem o topo do datum ({nome_datum}), fora da seção nivelada: {', '.join(sem)}.")
        saida_pocos = [p for p in saida_pocos if p["datum_cota"] is not None]
        if len(saida_pocos) < 2:
            raise ErroSecao(f"Menos de dois poços têm o topo de {nome_datum} para nivelar.")
        for p in saida_pocos:
            r = p["datum_cota"]
            for u in p["unidades"]:
                u["y_topo"], u["y_base"] = u["cota_topo"] - r, u["cota_base"] - r
            for c in p["litologia"] + p["indicios"]:
                c["y_topo"], c["y_base"] = c["cota_topo"] - r, c["cota_base"] - r
            for c in p["discordancias"]:
                c["y_topo"] = c["cota_topo"] - r
            p["md_y"] = [[a, b - r] for a, b in p["md_cota"]]
            if p["gr"]:
                p["gr"]["y"] = [v - r for v in p["gr"]["cota"]]
            p["y_mesa"] = None if p["mesa"] is None else p["mesa"] - r
            p["y_fundo"] = None if p["cota_fundo"] is None else p["cota_fundo"] - r
    else:
        for p in saida_pocos:
            p["datum_cota"] = None
            for u in p["unidades"]:
                u["y_topo"], u["y_base"] = u["cota_topo"], u["cota_base"]
            for c in p["litologia"] + p["indicios"]:
                c["y_topo"], c["y_base"] = c["cota_topo"], c["cota_base"]
            for c in p["discordancias"]:
                c["y_topo"] = c["cota_topo"]
            p["md_y"] = [list(x) for x in p["md_cota"]]
            if p["gr"]:
                p["gr"]["y"] = p["gr"]["cota"]
            p["y_mesa"], p["y_fundo"] = p["mesa"], p["cota_fundo"]
    # x recomeça no primeiro poço que ficou
    x0 = min(p["x_km"] for p in saida_pocos)
    for p in saida_pocos:
        p["x_km"] = round(p["x_km"] - x0, 3)

    # unidades da legenda, em ordem estratigráfica (topo médio de cima para baixo)
    # ordem: posição relativa da unidade dentro de cada poço (0 = a mais rasa, 1 = a mais
    # funda), em média — não a cota, que mistura altos e baixos estruturais
    acum: dict[str, list] = {}
    for p in saida_pocos:
        n_u = len(p["unidades"])
        for k, u in enumerate(p["unidades"]):
            u["_rank"] = k / (n_u - 1) if n_u > 1 else 0.5
            acum.setdefault(u["chave"], []).append((p["id"], u))
    legenda = []
    for ch, pares in acum.items():
        slot = slots.get(ch)
        lst = [u for _, u in pares]
        legenda.append({"chave": ch, "nome": lst[0]["nome"], "slot": slot,
                        "cor": CORES.get(slot, COR_SEM_SLOT), "n_pocos": len({pid for pid, _ in pares}),
                        "y_medio": float(np.mean([x["y_topo"] for x in lst])),
                        "posicao": float(np.mean([x.pop("_rank") for x in lst]))})
    legenda.sort(key=lambda u: (u["posicao"], -u["y_medio"]))
    cor = {u["chave"]: u["cor"] for u in legenda}
    for p in saida_pocos:
        for u in p["unidades"]:
            u["cor"] = cor[u["chave"]]

    # topos que saltam entre vizinhos: falha, mergulho forte ou interpretação divergente
    saltos = []
    for a, b in zip(saida_pocos, saida_pocos[1:]):
        ua = {u["chave"]: u for u in a["unidades"]}
        for u in b["unidades"]:
            if u["chave"] in ua:
                delta = u["y_topo"] - ua[u["chave"]]["y_topo"]
                if abs(delta) > limiar_salto_m:
                    saltos.append({"unidade": u["nome"], "de": a["id"], "para": b["id"],
                                   "delta_m": round(delta, 1), "dist_km": round(b["x_km"] - a["x_km"], 2)})
    for s in saltos:
        avisos.append(f"Topo de {s['unidade']} muda {abs(s['delta_m']):.0f} m entre {s['de']} e {s['para']} "
                      f"({s['dist_km']:.1f} km): falha, mergulho forte ou interpretação diferente — confira.")

    ys = [v for p in saida_pocos for v in (
        [u["y_topo"] for u in p["unidades"]] + [u["y_base"] for u in p["unidades"]] +
        ([p["y_mesa"]] if p["y_mesa"] is not None else []) + ([p["y_fundo"]] if p["y_fundo"] is not None else []))]
    if not ys:
        raise ErroSecao(f"Nenhum dos poços tem {ROTULO_NIVEL[nivel]} com topo no AGP.")
    y_max, y_min = max(ys), min(ys)
    if janela:
        a, b = janela
        if a is not None:
            y_max = float(a)
        if b is not None:
            y_min = float(b)
        if y_min >= y_max:
            raise ErroSecao("A janela vertical precisa ir de um valor maior (em cima) para um menor (embaixo).")
    return {
        "pocos": saida_pocos, "legenda": legenda, "saltos": saltos, "avisos": avisos,
        "pontas": list(geo["pontas"]), "comprimento_km": round(max(p["x_km"] for p in saida_pocos), 3),
        "y_max": y_max, "y_min": y_min,
        "datum_nome": nome_datum if eixo == "nivelado" else None,
        "parametros": {"estilo": estilo, "ordem": ordem, "nivel": nivel, "eixo": eixo, "datum": datum,
                       "espacamento": espacamento,
                       "litologia": litologia, "gr": gr, "limiar_salto_m": limiar_salto_m,
                       "janela": list(janela) if janela else None},
    }


# ===================================================================== desenho
def _fmt(v: float | None, casas: int = 1) -> str:
    if v is None:
        return "—"
    s = f"{v:,.{casas}f}"
    return s.replace(",", "§").replace(".", ",").replace("§", ".").replace("-", "−")


def _data(d: str) -> str:
    """01/01/1900 é o "sem data" do AGP antigo."""
    return "" if d == "01/01/1900" else d


def _passo_grade(intervalo: float, alvo: int = 10) -> float:
    bruto = intervalo / max(alvo, 1)
    p10 = 10 ** math.floor(math.log10(bruto)) if bruto > 0 else 1
    for m in (1, 2, 2.5, 5, 10):
        if bruto <= m * p10:
            return m * p10
    return 10 * p10


def _t(x, y, texto, tam=11, cor=TINTA, ancora="middle", peso="normal", rot=None, extra=""):
    tr = f' transform="rotate({rot} {x:.1f} {y:.1f})"' if rot is not None else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{tam}" fill="{cor}" text-anchor="{ancora}" '
            f'font-weight="{peso}"{tr}{extra}>{escape(texto)}</text>')


def desenhar(modelo: dict, titulo: str = "", estilo: str | None = None, autor: str = "", data: str = "") -> str:
    """SVG da seção: estilo "classico" (convenções de seção de correlação da indústria)
    ou "moderno" (estilo de artigo, cores sólidas)."""
    estilo = estilo or modelo["parametros"].get("estilo", "classico")
    if estilo == "moderno":
        return _desenhar_moderno(modelo, titulo)
    from .secao_classica import desenhar_classico
    return desenhar_classico(modelo, titulo, autor=autor, data=data)


def _desenhar_moderno(modelo: dict, titulo: str = "") -> str:
    """SVG da seção no estilo de artigo: fundo branco, moldura fechada, marcas para
    dentro, grade fina, fonte serifada, legenda com moldura."""
    pocos = modelo["pocos"]
    tem_gr = any(p["gr"] for p in pocos)
    tem_lit = any(p["litologia"] for p in pocos)
    w_lit, w_col, w_gr = (9 if tem_lit else 0), 36, (62 if tem_gr else 0)
    w_poco = w_lit + w_col + w_gr
    gap_min = max(46, 104 - w_poco)          # nome do poço cabe por cima
    esq, dir_, topo_area, alt = 74, 74, 96, 760
    n = len(pocos)
    # posição horizontal
    if modelo["parametros"]["espacamento"] == "igual" or modelo["comprimento_km"] <= 0:
        xs_km = [float(i) for i in range(n)]
    else:
        xs_km = [p["x_km"] for p in pocos]
    largura_util = max(760, n * (w_poco + gap_min) - gap_min)
    esc = (largura_util - w_poco) / ((xs_km[-1] - xs_km[0]) or 1)
    margem = 14                              # colunas afastadas da moldura
    xs = [esq + margem + (v - xs_km[0]) * esc for v in xs_km]
    for i in range(1, n):                    # espaço mínimo entre colunas
        if xs[i] - xs[i - 1] < w_poco + gap_min:
            xs[i] = xs[i - 1] + w_poco + gap_min
    largura_plot = xs[-1] + w_poco + margem - esq
    W = esq + largura_plot + dir_
    y_max, y_min = modelo["y_max"], modelo["y_min"]
    folga = 0.03 * (y_max - y_min or 1)
    y_max, y_min = y_max + folga, y_min - folga

    def Y(v):
        """y na tela, preso à área do gráfico (o PyMuPDF ignora clipPath ao exportar)."""
        return min(max(topo_area + (y_max - v) / (y_max - y_min) * alt, topo_area), topo_area + alt)

    def dentro(v):
        return y_min <= v <= y_max

    def Yl(v):          # sem prender: para recortar polígonos e linhas
        return topo_area + (y_max - v) / (y_max - y_min) * alt

    y_cima, y_baixo = topo_area, topo_area + alt

    def recortar(pts):
        """Sutherland–Hodgman nas duas bordas horizontais da área do gráfico."""
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

    def recortar_linha(x1, y1, x2, y2):
        """Segmento recortado nas bordas horizontais; None se fica todo fora."""
        t0, t1 = 0.0, 1.0
        dy = y2 - y1
        for borda, sinal in ((y_cima, 1), (y_baixo, -1)):
            # dentro: sinal * (y - borda) >= 0
            ini = sinal * (y1 - borda)
            d = sinal * dy
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
        return (x1 + t0 * (x2 - x1), y1 + t0 * dy, x1 + t1 * (x2 - x1), y1 + t1 * dy)

    leg = modelo["legenda"]
    por_linha = max(1, int((W - 40) // 190))
    linhas_leg = math.ceil((len(leg) + (1 if tem_gr else 0)) / por_linha) + (1 if tem_lit else 0)
    H = topo_area + alt + 46 + 22 * linhas_leg + 46
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}" '
         f'viewBox="0 0 {W:.0f} {H:.0f}" font-family="{FONTE}">',
         f'<rect width="{W:.0f}" height="{H:.0f}" fill="#ffffff"/>']
    if titulo:
        o.append(_t(esq, 22, titulo, 14, ancora="start", peso="bold"))
    # grade e eixos
    passo = _passo_grade(y_max - y_min)
    v = math.ceil(y_min / passo) * passo
    x_dir = esq + largura_plot
    while v <= y_max:
        y = Y(v)
        o.append(f'<line x1="{esq}" y1="{y:.1f}" x2="{x_dir:.1f}" y2="{y:.1f}" stroke="{GRADE}" stroke-width="0.6"/>')
        o.append(f'<line x1="{esq}" y1="{y:.1f}" x2="{esq + 6}" y2="{y:.1f}" stroke="{TINTA}" stroke-width="0.8"/>')
        o.append(f'<line x1="{x_dir - 6:.1f}" y1="{y:.1f}" x2="{x_dir:.1f}" y2="{y:.1f}" stroke="{TINTA}" stroke-width="0.8"/>')
        rot = _fmt(v, 0 if passo >= 1 else 1)
        o.append(_t(esq - 6, y + 4, rot, 10, ancora="end"))
        o.append(_t(x_dir + 6, y + 4, rot, 10, ancora="start"))
        v += passo
    par = modelo["parametros"]
    rotulo_y = (f"Distância ao topo — {modelo.get('datum_nome') or par['datum']} (m)" if par["eixo"] == "nivelado"
                else "Cota (m)")
    meio = topo_area + alt / 2
    o.append(_t(20, meio, rotulo_y, 12, rot=-90))
    o.append(_t(W - 16, meio, rotulo_y, 12, rot=90))
    if par["eixo"] == "nivelado" and y_min < 0 < y_max:
        o.append(f'<line x1="{esq}" y1="{Y(0):.1f}" x2="{x_dir:.1f}" y2="{Y(0):.1f}" stroke="{TINTA}" '
                 f'stroke-width="0.9" stroke-dasharray="6,3"/>')
    elif par["eixo"] == "cota" and y_min < 0 < y_max:
        o.append(f'<line x1="{esq}" y1="{Y(0):.1f}" x2="{x_dir:.1f}" y2="{Y(0):.1f}" stroke="{TINTA_FRACA}" '
                 f'stroke-width="0.7" stroke-dasharray="2,3"/>')
    o.append(f'<clipPath id="plot"><rect x="{esq}" y="{topo_area}" width="{largura_plot:.1f}" height="{alt}"/></clipPath>')
    o.append('<g clip-path="url(#plot)">')
    # correlação entre vizinhos: faixa da unidade (topo a base) e linha do topo
    for i in range(n - 1):
        a, b = pocos[i], pocos[i + 1]
        # a faixa sai depois da trilha GR do poço da esquerda, se ele tiver
        xa, xb = xs[i] + (w_poco if a["gr"] else w_lit + w_col), xs[i + 1] + w_lit
        ub = {u["chave"]: u for u in b["unidades"]}
        for u in a["unidades"]:
            v2 = ub.get(u["chave"])
            if not v2:
                continue
            poli = recortar([(xa, Yl(u["y_topo"])), (xb, Yl(v2["y_topo"])),
                             (xb, Yl(v2["y_base"])), (xa, Yl(u["y_base"]))])
            if len(poli) >= 3:
                pts = " ".join(f"{px:.1f},{py:.1f}" for px, py in poli)
                o.append(f'<polygon points="{pts}" fill="{u["cor"]}" fill-opacity="0.16" stroke="none">'
                         f'<title>{escape(u["nome"])}: {escape(a["id"])} → {escape(b["id"])}</title></polygon>')
            seg = recortar_linha(xa, Yl(u["y_topo"]), xb, Yl(v2["y_topo"]))
            if seg:
                x1, y1, x2, y2 = seg
                o.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                         f'stroke="{u["cor"]}" stroke-width="1.6"/>')
    # colunas
    for i, p in enumerate(pocos):
        x = xs[i]
        xc = x + w_lit
        for c in p["litologia"]:
            y0, y1 = Y(c["y_topo"]), Y(c["y_base"])
            o.append(f'<rect x="{x:.1f}" y="{y0:.1f}" width="{w_lit - 1}" height="{max(0.6, y1 - y0):.1f}" '
                     f'fill="{cor_rocha(c["rocha"])}"><title>{escape(p["id"])} · {_fmt(c["topo"])}–{_fmt(c["base"])} m: '
                     f'{escape(c["rocha"])} {escape(c["descricao"])}</title></rect>')
        for u in p["unidades"]:
            y0, y1 = Y(u["y_topo"]), Y(u["y_base"])
            h = max(1.0, y1 - y0)
            dica = (f'{p["id"]} · {u["nome"]}\nTopo {_fmt(u["topo"])} m (cota {_fmt(u["cota_topo"])}) · base '
                    f'{_fmt(u["base"])} m (cota {_fmt(u["cota_base"])})'
                    f'{"" if u["base_atingida"] else " — base não atingida"}\n'
                    f'Fonte: {u["fonte"]} {_data(u["data"])} · qualidade {u["qualidade"] or "—"} · {u["metodo"]}')
            o.append(f'<g><title>{escape(dica)}</title>'
                     f'<rect x="{xc:.1f}" y="{y0:.1f}" width="{w_col}" height="{h:.1f}" fill="{u["cor"]}" '
                     f'fill-opacity="0.6" stroke="#ffffff" stroke-width="1"/>')
            if not u["base_atingida"]:
                o.append(f'<line x1="{xc:.1f}" y1="{y1:.1f}" x2="{xc + w_col:.1f}" y2="{y1:.1f}" stroke="{TINTA}" '
                         f'stroke-width="1" stroke-dasharray="3,2"/>')
            if h > 34:
                nome_curto = u["nome"].split(" ", 1)[-1] if " " in u["nome"] else u["nome"]
                o.append(_t(xc + w_col / 2 + 4, (y0 + y1) / 2, nome_curto, 10, rot=-90))
            o.append("</g>")
        # contorno do poço: da mesa ao fundo, quando conhecidos
        ya = Y(p["y_mesa"]) if p["y_mesa"] is not None else topo_area
        yb = Y(p["y_fundo"]) if p["y_fundo"] is not None else topo_area + alt
        o.append(f'<rect x="{xc:.1f}" y="{ya:.1f}" width="{w_col}" height="{max(0.0, yb - ya):.1f}" fill="none" '
                 f'stroke="{TINTA_FRACA}" stroke-width="0.5" stroke-dasharray="1,3"/>')
        if p["y_fundo"] is not None and dentro(p["y_fundo"]):
            yf = Y(p["y_fundo"])
            o.append(f'<line x1="{x:.1f}" y1="{yf:.1f}" x2="{x + w_poco:.1f}" y2="{yf:.1f}" stroke="{TINTA}" stroke-width="1.4"/>')
            o.append(_t(x + w_poco / 2, yf + 12, f'PF {_fmt(p["prof_final"], 0)} m', 9, TINTA_2))
        if p["gr"]:
            xg = xc + w_col + 3
            wg = w_gr - 5
            o.append(f'<rect x="{xg:.1f}" y="{topo_area}" width="{wg}" height="{alt}" fill="none" '
                     f'stroke="{GRADE}" stroke-width="0.6"/>')
            seg, pts = [], []
            for yv, gv in zip(p["gr"]["y"], p["gr"]["valores"]):
                if gv is None or not dentro(yv):
                    if len(pts) > 1:
                        seg.append(pts)
                    pts = []
                    continue
                pts.append(f"{xg + min(max(gv, 0), 150) / 150 * wg:.1f},{Y(yv):.1f}")
            if len(pts) > 1:
                seg.append(pts)
            for s in seg:
                o.append(f'<polyline points="{" ".join(s)}" fill="none" stroke="{TINTA_2}" stroke-width="0.8">'
                         f'<title>{escape(p["id"])} · {escape(p["gr"]["mnemonico"])} ({escape(os.path.basename(p["gr"]["arquivo"]))})</title></polyline>')
    o.append("</g>")
    # moldura e cabeçalho dos poços
    o.append(f'<rect x="{esq}" y="{topo_area}" width="{largura_plot:.1f}" height="{alt}" fill="none" '
             f'stroke="{TINTA}" stroke-width="0.9"/>')
    for i, p in enumerate(pocos):
        cx = xs[i] + w_poco / 2
        o.append(_t(cx, topo_area - 24, p["id"], 11, peso="bold"))
        sub = f'mesa {_fmt(p["mesa"], 0)} m' if p["mesa"] is not None else ""
        o.append(_t(cx, topo_area - 10, sub, 9, TINTA_2,
                    extra=f' data-dist-linha="{p["dist_linha_km"]}"'))
        if p["gr"]:
            o.append(_t(xs[i] + w_lit + w_col + 3 + (w_gr - 5) / 2, topo_area + 12, "GR 0–150", 8, TINTA_FRACA))
        if i:
            d = p["x_km"] - pocos[i - 1]["x_km"]
            o.append(_t((xs[i - 1] + w_poco + xs[i]) / 2, topo_area - 46, f"{_fmt(d, 1)} km" if d >= 0.05 else "< 0,1 km",
                        9, TINTA_FRACA))
    e, d = modelo["pontas"]
    o.append(_t(esq, topo_area - 46, e, 12, ancora="start", peso="bold"))
    o.append(_t(x_dir, topo_area - 46, d, 12, ancora="end", peso="bold"))
    # legenda com moldura
    y_leg = topo_area + alt + 30
    itens = [(u["cor"], u["nome"], "faixa") for u in leg]
    if tem_gr:
        itens.append((TINTA_2, "Raios gama (API)", "linha"))
    caixa_h = 22 * linhas_leg + 14
    o.append(f'<rect x="{esq}" y="{y_leg - 14}" width="{largura_plot:.1f}" height="{caixa_h}" fill="#ffffff" '
             f'stroke="{TINTA}" stroke-width="0.6"/>')
    for k, (c, nome, tipo) in enumerate(itens):
        lx = esq + 12 + (k % por_linha) * 190
        ly = y_leg + (k // por_linha) * 22
        if tipo == "faixa":
            o.append(f'<rect x="{lx}" y="{ly - 9}" width="16" height="12" fill="{c}" fill-opacity="0.6" stroke="{c}"/>')
        else:
            o.append(f'<line x1="{lx}" y1="{ly - 3}" x2="{lx + 16}" y2="{ly - 3}" stroke="{c}" stroke-width="1.2"/>')
        o.append(_t(lx + 22, ly + 1, nome, 10.5, ancora="start"))
    if tem_lit:
        ly = y_leg + (math.ceil(len(itens) / por_linha)) * 22
        o.append(_t(esq + 12, ly + 1, "Calha:", 10, TINTA_2, ancora="start"))
        for k, (nome, c) in enumerate([("arenito", "#f2d16b"), ("folhelho/argilito", "#8fa58a"),
                                       ("carbonato", "#8fb8d9"), ("evaporito", "#d9a3c9"),
                                       ("embasamento/ígnea", "#c98f7a"), ("outra", "#d5d3cc")]):
            lx = esq + 62 + k * 120
            o.append(f'<rect x="{lx}" y="{ly - 8}" width="9" height="11" fill="{c}"/>')
            o.append(_t(lx + 13, ly + 1, nome, 9.5, ancora="start"))
    exag = ""
    if par["espacamento"] != "igual" and modelo["comprimento_km"] > 0:
        m_por_px_h = modelo["comprimento_km"] * 1000 / ((xs[-1] - xs[0]) or 1)
        m_por_px_v = (y_max - y_min) / alt
        exag = f" · exagero vertical ≈ {m_por_px_h / m_por_px_v:,.0f}×".replace(",", ".")
    rodape = (f"Topos: AGP da ANP (portal REATE), interpretados pela operadora · {len(pocos)} poços, "
              f"{_fmt(modelo['comprimento_km'], 1)} km{exag} · SIAPP {__version__}")
    o.append(_t(esq, H - 14, rodape, 9.5, TINTA_2, ancora="start"))
    o.append("</svg>")
    return "\n".join(o)


# ============================================================ registro e saída
def registrar(pasta_execucoes: str, modelo: dict, svg: str, autor: str = "") -> tuple[str, str]:
    os.makedirs(pasta_execucoes, exist_ok=True)
    ident = base = f"secao_{datetime.now():%Y%m%d-%H%M%S}"
    k = 2
    while os.path.exists(os.path.join(pasta_execucoes, ident + ".json")):   # duas no mesmo segundo
        ident, k = f"{base}-{k}", k + 1
    leve = json.loads(json.dumps(modelo))
    for p in leve["pocos"]:          # a curva fica no SVG; o registro guarda de onde veio
        if p.get("gr"):
            p["gr"] = {"arquivo": p["gr"]["arquivo"], "mnemonico": p["gr"]["mnemonico"],
                       "n_pontos": len(p["gr"]["cota"])}
    reg = {"id": ident, "tipo": "secao_estratigrafica", "siapp_versao": __version__, "criado_em": agora(),
           "autor": autor, **leve}
    with open(os.path.join(pasta_execucoes, ident + ".json"), "w", encoding="utf-8") as f:
        json.dump(reg, f, ensure_ascii=False, indent=1)
    with open(os.path.join(pasta_execucoes, ident + ".svg"), "w", encoding="utf-8") as f:
        f.write(svg)
    return ident, os.path.join(pasta_execucoes, ident + ".json")


def execucoes(pasta_execucoes: str) -> list[dict]:
    if not os.path.isdir(pasta_execucoes):
        return []
    saida = []
    for nome in sorted(os.listdir(pasta_execucoes), reverse=True):
        if nome.startswith("secao_") and nome.endswith(".json"):
            try:
                with open(os.path.join(pasta_execucoes, nome), encoding="utf-8") as f:
                    r = json.load(f)
            except (OSError, json.JSONDecodeError):
                continue
            saida.append({"id": r["id"], "criado_em": r.get("criado_em"), "pocos": [p["id"] for p in r["pocos"]],
                          "parametros": r.get("parametros", {})})

    def ordem(r):       # mais recente primeiro; no mesmo segundo, o sufixo -2, -3…
        partes = r["id"].split("-")
        return r["criado_em"] or "", int(partes[2]) if len(partes) > 2 and partes[2].isdigit() else 1
    return sorted(saida, key=ordem, reverse=True)


def exportar(pasta_execucoes: str, ident: str, saida: str, formato: str) -> dict:
    """svg | png (300 ppp) | pdf (vetorial) | csv (topos usados)."""
    base = os.path.join(pasta_execucoes, ident)
    if not os.path.isfile(base + ".json"):
        raise ErroSecao("Seção não encontrada.")
    os.makedirs(os.path.dirname(saida), exist_ok=True)
    if formato == "csv":
        with open(base + ".json", encoding="utf-8") as f:
            reg = json.load(f)
        with open(saida, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["poco", "distancia_km", "dist_linha_km", "mesa_m", "unidade", "sigla", "topo_m", "base_m",
                        "cota_topo_m", "cota_base_m", "espessura_m", "base_atingida", "fonte", "data", "qualidade",
                        "metodo", "arquivo_agp"])
            for p in reg["pocos"]:
                for u in p["unidades"]:
                    esp = None if u["base"] is None else u["base"] - u["topo"]
                    w.writerow([p["id"], _num(p["x_km"]), _num(p["dist_linha_km"]), _num(p["mesa"]), u["nome"],
                                u["sigla"], _num(u["topo"]), _num(u["base"]), _num(u["cota_topo"]),
                                _num(u["cota_base"]), _num(esp), "sim" if u["base_atingida"] else "não",
                                u["fonte"], u["data"], u["qualidade"], u["metodo"], p["agp"]])
        return {"formato": "csv"}
    with open(base + ".svg", encoding="utf-8") as f:
        svg = f.read()
    if formato == "svg":
        with open(saida, "w", encoding="utf-8") as f:
            f.write(svg)
        return {"formato": "svg"}
    import pymupdf   # já é dependência (documentos)
    doc = pymupdf.open(stream=svg.encode("utf-8"), filetype="svg")
    if formato == "png":
        doc[0].get_pixmap(dpi=300).save(saida)
    elif formato == "pdf":
        with pymupdf.open("pdf", doc.convert_to_pdf()) as pdf:
            pdf.save(saida)
    else:
        raise ErroSecao(f"Formato desconhecido: {formato}")
    return {"formato": formato}


def _num(v, casas: int = 2) -> str:
    return "" if v is None else f"{v:.{casas}f}".replace(".", ",")
