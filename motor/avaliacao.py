"""Avaliação de formação no intervalo-alvo: argilosidade, porosidade, saturação e net pay.

Tudo é calculado **só dentro dos intervalos-alvo** escolhidos, numa grade de
profundidade comum (ver perfis.reamostrar). Cada execução grava um registro em
`execucoes/` com as curvas usadas, os métodos, todos os parâmetros (inclusive os
estimados automaticamente) e o resumo — o suficiente para refazer o cálculo e
citá-lo.

Fórmulas (unidades: frações, g/cm³, µs/pé, ohm·m):

    IGR   = (GR − GR_limpo) / (GR_argila − GR_limpo)            índice de raios gama
            GR_limpo e GR_argila, se não informados: mínimo e máximo do GR numa janela de
            referência (padrão: o arquivo inteiro), ou os percentis 5 e 95 — o "mínimo" e o
            "máximo" sem os 5% de leituras mais baixas e mais altas (picos, minerais radioativos)
    Vsh   = IGR                                                  linear
          = 0,083 · (2^(3,7·IGR) − 1)                            Larionov, rochas terciárias
          = 0,33 · (2^(2·IGR) − 1)                               Larionov, rochas mais antigas
    φD    = (ρma − ρb) / (ρma − ρf)                              densidade
    φND   = (φD + φN) / 2;  se φN < φD (efeito de gás): √((φD² + φN²)/2)
    φS    = (Δt − Δtma) / (Δtf − Δtma)                           sônico (Wyllie)
    φe    = φ − Vsh · φsh                                        correção de argila (opcional)
    Sw    = (a·Rw / (φ^m · Rt))^(1/n)                            Archie
    Sw    = a·Rw/(2φ^m) · [√((Vsh/Rsh)² + 4φ^m/(a·Rw·Rt)) − Vsh/Rsh]   Simandoux (n = 2)

    reservatório: Vsh ≤ Vsh_corte e φ ≥ φ_corte;  net pay: reservatório e Sw ≤ Sw_corte
    HPV (coluna de hidrocarboneto) = Σ φ·(1 − Sw)·Δh no net pay   [m]
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime

import numpy as np

from . import __version__
from . import perfis as mpf
from .banco import agora

PAPEIS = {
    # papel: (famílias aceitas, obrigatório?)
    "GR": (("GR",), True),
    "RHOB": (("RHOB",), False),
    "NPHI": (("NPHI",), False),
    "DT": (("DT",), False),
    "RT": (("RES_PROF",), True),
    "CALI": (("CALI",), False),
    "BS": (("BS",), False),
    "DRHO": (("DRHO",), False),
}

PADRAO = {
    "vsh_metodo": "linear",          # linear | larionov_terciario | larionov_antigo
    "gr_limpo": None,                # None = estimado na janela de referência (gr_estatistica)
    "gr_argila": None,
    "gr_referencia": "arquivo",      # arquivo | intervalos | janela — onde procurar o arenito limpo e o folhelho
    "gr_estatistica": "percentil",   # percentil (P5 e P95) | extremos (mínimo e máximo)
    "gr_ref_topo": None,             # m, só com gr_referencia = janela
    "gr_ref_base": None,
    "phi_metodo": "auto",            # auto | densidade | densidade_neutrao | sonico
    "rho_matriz": 2.65,              # arenito (quartzo); calcário 2,71; dolomito 2,87
    "rho_fluido": 1.0,
    "dt_matriz": 55.5,               # arenito, µs/pé
    "dt_fluido": 189.0,
    "phi_argila": 0.0,               # φ aparente da argila para φe = φ − Vsh·φsh (0 = sem correção)
    "sw_metodo": "archie",           # archie | simandoux
    "rw": 0.05,                      # ohm·m, na temperatura da formação
    "a": 1.0, "m": 2.0, "n": 2.0,
    "rsh": None,                     # None = mediana de Rt onde Vsh ≥ 0,8 (Simandoux)
    "corte_vsh": 0.5, "corte_phi": 0.08, "corte_sw": 0.6,
    "qc_cali_pol": 1.0,              # arrombamento: cáliper − broca acima disto (pol)
    "qc_drho": 0.15,                 # |DRHO| acima disto: densidade não confiável (g/cm³)
    "bs_pol": None,                  # diâmetro da broca, se não houver curva BS
    "passo": None,                   # m; None = menor passo entre as curvas
}

NOMES_METODO = {
    "linear": "linear", "larionov_terciario": "Larionov (terciárias)", "larionov_antigo": "Larionov (mais antigas)",
    "densidade": "densidade", "densidade_neutrao": "densidade-nêutron", "sonico": "sônico (Wyllie)",
    "archie": "Archie", "simandoux": "Simandoux",
}


REFERENCIAS_GR = {"arquivo": "no arquivo inteiro", "intervalos": "só nos intervalos", "janela": "na janela"}
ESTATISTICAS_GR = {"percentil": "P5 e P95", "extremos": "mínimo e máximo"}
CONTRASTE_MIN_GR = 20.0     # API: abaixo disto entre o limpo e a argila, a janela quase não tem folhelho (ou arenito)


class ErroAvaliacao(ValueError):
    pass


# ================================================================ fórmulas
def vsh_de_gr(gr, gr_limpo, gr_argila, metodo="linear"):
    if gr_argila <= gr_limpo:
        raise ErroAvaliacao(f"GR da argila ({gr_argila:g}) precisa ser maior que o GR limpo ({gr_limpo:g}).")
    igr = np.clip((gr - gr_limpo) / (gr_argila - gr_limpo), 0, 1)
    if metodo == "linear":
        v = igr
    elif metodo == "larionov_terciario":
        v = 0.083 * (2 ** (3.7 * igr) - 1)
    elif metodo == "larionov_antigo":
        v = 0.33 * (2 ** (2 * igr) - 1)
    else:
        raise ErroAvaliacao(f"Método de Vsh desconhecido: {metodo}")
    return np.clip(v, 0, 1)


def phi_densidade(rhob, rho_matriz, rho_fluido):
    if rho_matriz <= rho_fluido:
        raise ErroAvaliacao("A densidade da matriz precisa ser maior que a do fluido.")
    return (rho_matriz - rhob) / (rho_matriz - rho_fluido)


def phi_densidade_neutrao(phi_d, phi_n):
    media = (phi_d + phi_n) / 2
    gas = np.sqrt((phi_d ** 2 + phi_n ** 2) / 2)
    return np.where(phi_n < phi_d, gas, media)


def phi_sonico(dt, dt_matriz, dt_fluido):
    if dt_fluido <= dt_matriz:
        raise ErroAvaliacao("Δt do fluido precisa ser maior que o da matriz.")
    return (dt - dt_matriz) / (dt_fluido - dt_matriz)


def sw_archie(phi, rt, rw, a=1.0, m=2.0, n=2.0):
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.clip((a * rw / (np.power(phi, m) * rt)) ** (1.0 / n), 0, 1)


def sw_simandoux(phi, rt, rw, vsh, rsh, a=1.0, m=2.0):
    """Simandoux (1963) com n = 2, forma fechada."""
    with np.errstate(divide="ignore", invalid="ignore"):
        pm = np.power(phi, m)
        c = vsh / rsh
        sw = (a * rw / (2 * pm)) * (np.sqrt(c ** 2 + 4 * pm / (a * rw * rt)) - c)
    return np.clip(sw, 0, 1)


# ============================================================ conversões
def _em_fracao(v, unidade):
    u = (unidade or "").strip().lower()
    if u in ("%", "pu", "p.u.", "percent") or (np.nanmedian(v) > 1.5 if np.isfinite(v).any() else False):
        return v / 100.0
    return v


def _densidade_gcc(v, unidade):
    u = (unidade or "").strip().lower()
    if "kg" in u or (np.isfinite(v).any() and np.nanmedian(v) > 100):
        return v / 1000.0
    return v


def _dt_us_pe(v, unidade):
    u = (unidade or "").strip().lower().replace(" ", "")
    if u in ("us/m", "µs/m", "uspm"):
        return v * 0.3048
    return v


def _pol(v, unidade):
    u = (unidade or "").strip().lower()
    if u in ("mm",):
        return v / 25.4
    if u in ("cm",):
        return v / 2.54
    if u in ("m",):
        return v / 0.0254
    return v


# ================================================================ cálculo
def _num(p, chave):
    v = p.get(chave)
    if v is None or v == "":
        return None
    try:
        return float(str(v).replace(",", "."))
    except ValueError as e:
        raise ErroAvaliacao(f"Parâmetro {chave}: “{v}” não é número.") from e


def parametros(entrada: dict | None) -> dict:
    p = dict(PADRAO)
    for k, v in (entrada or {}).items():
        if k in PADRAO:
            p[k] = v
    for k in ("gr_limpo", "gr_argila", "gr_ref_topo", "gr_ref_base", "rho_matriz", "rho_fluido", "dt_matriz", "dt_fluido", "phi_argila",
              "rw", "a", "m", "n", "rsh", "corte_vsh", "corte_phi", "corte_sw", "qc_cali_pol",
              "qc_drho", "bs_pol", "passo"):
        p[k] = _num(p, k)
    if p["gr_referencia"] not in REFERENCIAS_GR:
        raise ErroAvaliacao(f"Referência do GR desconhecida: {p['gr_referencia']!r}.")
    if p["gr_estatistica"] not in ESTATISTICAS_GR:
        raise ErroAvaliacao(f"Estatística do GR desconhecida: {p['gr_estatistica']!r}.")
    if p["gr_referencia"] == "janela":
        if p["gr_ref_topo"] is None or p["gr_ref_base"] is None or p["gr_ref_base"] <= p["gr_ref_topo"]:
            raise ErroAvaliacao("Janela de referência do GR: informe topo e base (base abaixo do topo).")
    for k, minimo in (("rw", 1e-4), ("a", 1e-3), ("m", 0.5), ("n", 0.5)):
        if p[k] is None or p[k] < minimo:
            raise ErroAvaliacao(f"Parâmetro {k} precisa ser um número positivo.")
    return p


def avaliar(pasta_cache: str, arquivo: str, curvas: dict, intervalos: list[dict],
            entrada: dict | None = None) -> dict:
    """`curvas`: {papel: {quadro, mnemonico, unidade}} (GR e RT obrigatórios).
    `intervalos`: [{nome, topo, base}] em metros. Devolve as curvas calculadas
    (só nos intervalos), o resumo por intervalo e os parâmetros efetivos."""
    p = parametros(entrada)
    if not intervalos:
        raise ErroAvaliacao("Escolha ao menos um intervalo-alvo. Marque-o arrastando sobre o gráfico.")
    for i in intervalos:
        if i.get("topo") is None or i.get("base") is None or float(i["base"]) <= float(i["topo"]):
            raise ErroAvaliacao(f"Intervalo “{i.get('nome', '?')}” sem topo e base válidos.")
    for papel, (_, obrig) in PAPEIS.items():
        if obrig and not curvas.get(papel):
            raise ErroAvaliacao(f"Falta a curva de {papel} (obrigatória).")
    usados = {k: v for k, v in curvas.items() if v and k in PAPEIS}
    auto = {}
    avisos: list[str] = []
    selecao = [{**v, "papel": k} for k, v in usados.items()]
    if p["passo"] is None:
        # a grade segue o passo do GR (a curva da passada principal); um cáliper
        # de alta resolução (1 pol) não deve multiplicar o número de amostras
        q = mpf.carregar_quadro(pasta_cache, arquivo, usados["GR"]["quadro"])
        pr = q["__prof__"][np.isfinite(q["__prof__"])]
        p["passo"] = round(float(np.median(np.abs(np.diff(pr)))), 5) if len(pr) > 1 else None
        auto["passo"] = "passo do GR"
    grade, colunas, passo = mpf.reamostrar(pasta_cache, arquivo, selecao, p["passo"])
    dados = {s["papel"]: (r, s.get("unidade", "")) for s, r in colunas}
    if "GR" not in dados or "RT" not in dados:
        raise ErroAvaliacao("GR e resistividade profunda precisam ter dados no arquivo.")

    dentro = np.zeros(len(grade), bool)
    rotulo = np.full(len(grade), -1)
    for k, i in enumerate(intervalos):
        m = (grade >= float(i["topo"])) & (grade <= float(i["base"]))
        dentro |= m
        rotulo[m & (rotulo < 0)] = k
    if not dentro.any():
        raise ErroAvaliacao("Os intervalos escolhidos ficam fora da profundidade do arquivo.")

    gr = dados["GR"][0]
    rt = dados["RT"][0]
    rhob = _densidade_gcc(*dados["RHOB"]) if "RHOB" in dados else None
    nphi = _em_fracao(*dados["NPHI"]) if "NPHI" in dados else None
    dt = _dt_us_pe(*dados["DT"]) if "DT" in dados else None

    # --- argilosidade (parâmetros automáticos registrados)
    if not (dentro & np.isfinite(gr)).any():
        raise ErroAvaliacao("O GR não tem dados dentro dos intervalos.")
    ref = p["gr_referencia"]
    if ref == "intervalos":
        mref = dentro
    elif ref == "janela":
        mref = (grade >= p["gr_ref_topo"]) & (grade <= p["gr_ref_base"])
    else:
        mref = np.ones(len(grade), bool)
    mref = mref & np.isfinite(gr)
    if not mref.any():
        raise ErroAvaliacao("O GR não tem dados na janela de referência.")
    g_ref = gr[mref]
    janela = (round(float(grade[mref].min()), 2), round(float(grade[mref].max()), 2))
    onde = (f"{REFERENCIAS_GR[ref]} ({janela[0]:.1f}–{janela[1]:.1f} m)".replace(".", ",")
            if ref != "intervalos" else REFERENCIAS_GR[ref])
    extremos = p["gr_estatistica"] == "extremos"
    if p["gr_limpo"] is None:
        p["gr_limpo"] = round(float(g_ref.min() if extremos else np.percentile(g_ref, 5)), 2)
        auto["gr_limpo"] = f"{'mínimo' if extremos else 'percentil 5'} do GR {onde}"
    if p["gr_argila"] is None:
        p["gr_argila"] = round(float(g_ref.max() if extremos else np.percentile(g_ref, 95)), 2)
        auto["gr_argila"] = f"{'máximo' if extremos else 'percentil 95'} do GR {onde}"
    if p["gr_argila"] <= p["gr_limpo"]:
        raise ErroAvaliacao(f"GR da argila ({p['gr_argila']}) precisa ser maior que o GR limpo ({p['gr_limpo']}).")
    if p["gr_argila"] - p["gr_limpo"] < CONTRASTE_MIN_GR:
        avisos.append(f"GR limpo e GR da argila diferem só {p['gr_argila'] - p['gr_limpo']:.0f} API: a janela de "
                      "referência quase não tem folhelho (ou arenito). Use uma janela maior ou digite os valores.")
    if extremos and ("gr_limpo" in auto or "gr_argila" in auto):
        avisos.append("Mínimo e máximo pegam picos (minerais radioativos, leitura ruim): confira as linhas no GR.")
    referencia_gr = {"topo": janela[0], "base": janela[1], "tipo": ref, "estatistica": p["gr_estatistica"]}
    vsh = vsh_de_gr(gr, p["gr_limpo"], p["gr_argila"], p["vsh_metodo"])

    # --- porosidade
    metodo = p["phi_metodo"]
    if metodo == "auto":
        metodo = ("densidade_neutrao" if rhob is not None and nphi is not None
                  else "densidade" if rhob is not None else "sonico" if dt is not None else "")
        auto["phi_metodo"] = "escolhido pelas curvas disponíveis"
    if metodo == "densidade_neutrao":
        if rhob is None or nphi is None:
            raise ErroAvaliacao("Porosidade densidade-nêutron precisa de RHOB e NPHI.")
        phi = phi_densidade_neutrao(phi_densidade(rhob, p["rho_matriz"], p["rho_fluido"]), nphi)
    elif metodo == "densidade":
        if rhob is None:
            raise ErroAvaliacao("Porosidade por densidade precisa de RHOB.")
        phi = phi_densidade(rhob, p["rho_matriz"], p["rho_fluido"])
    elif metodo == "sonico":
        if dt is None:
            raise ErroAvaliacao("Porosidade sônica precisa de DT.")
        phi = phi_sonico(dt, p["dt_matriz"], p["dt_fluido"])
    else:
        raise ErroAvaliacao("Sem curva de porosidade: escolha RHOB, NPHI ou DT.")
    p["phi_metodo"] = metodo
    if p["phi_argila"]:
        phi = phi - vsh * p["phi_argila"]
    phi = np.clip(phi, 0, 0.5)

    # --- saturação
    if p["sw_metodo"] == "simandoux":
        if p["rsh"] is None:
            arg = dentro & (vsh >= 0.8) & np.isfinite(rt)
            if not arg.any():
                arg = dentro & np.isfinite(rt) & (vsh >= np.nanpercentile(vsh[dentro], 90))
            p["rsh"] = round(float(np.nanmedian(rt[arg])), 3) if arg.any() else None
            auto["rsh"] = "mediana de Rt onde Vsh ≥ 0,8 nos intervalos"
        if not p["rsh"] or p["rsh"] <= 0:
            raise ErroAvaliacao("Simandoux precisa de Rsh (não foi possível estimar: informe).")
        sw = sw_simandoux(phi, rt, p["rw"], vsh, p["rsh"], p["a"], p["m"])
        if p["n"] != 2:
            auto["n"] = "Simandoux na forma fechada usa n = 2 (o n informado não entra)"
    elif p["sw_metodo"] == "archie":
        sw = sw_archie(phi, rt, p["rw"], p["a"], p["m"], p["n"])
    else:
        raise ErroAvaliacao(f"Método de Sw desconhecido: {p['sw_metodo']}")
    sw = np.where(phi > 0, sw, 1.0)

    # --- controle de qualidade
    qc_cali = np.zeros(len(grade), bool)
    if "CALI" in dados:
        cali = _pol(*dados["CALI"])
        bs = _pol(*dados["BS"]) if "BS" in dados else (np.full(len(grade), p["bs_pol"]) if p["bs_pol"] else None)
        if bs is not None:
            qc_cali = np.nan_to_num(cali - bs, nan=0) > p["qc_cali_pol"]
    qc_drho = np.zeros(len(grade), bool)
    if "DRHO" in dados and metodo in ("densidade", "densidade_neutrao"):
        qc_drho = np.abs(np.nan_to_num(_densidade_gcc(*dados["DRHO"]), nan=0)) > p["qc_drho"]

    valido = dentro & np.isfinite(vsh) & np.isfinite(phi) & np.isfinite(sw) & np.isfinite(rt)
    reservatorio = valido & (vsh <= p["corte_vsh"]) & (phi >= p["corte_phi"])
    pay = reservatorio & (sw <= p["corte_sw"])

    def so_dentro(a):
        return np.where(dentro, a, np.nan)

    saida = {
        "VSH": so_dentro(vsh), "PHI": so_dentro(phi), "SW": so_dentro(sw),
        "RES": so_dentro(reservatorio.astype(float)), "PAY": so_dentro(pay.astype(float)),
        "QC": so_dentro((qc_cali | qc_drho).astype(float)),
    }

    resumo = []
    for k, i in enumerate(intervalos):
        m = rotulo == k
        resumo.append(_resumir(i, grade, passo, m, valido, reservatorio, pay, vsh, phi, sw, qc_cali, qc_drho))
    return {"prof": grade, "passo": passo, "curvas": saida, "intervalos": resumo,
            "parametros": p, "automaticos": auto, "avisos": avisos, "referencia_gr": referencia_gr,
            "curvas_usadas": {k: {"quadro": v["quadro"], "mnemonico": v["mnemonico"], "unidade": v.get("unidade", "")}
                              for k, v in usados.items()}}


def _resumir(intervalo, grade, passo, m, valido, res, pay, vsh, phi, sw, qc_cali, qc_drho):
    def media(v, mask):
        return round(float(np.mean(v[mask])), 4) if mask.any() else None
    h = lambda mask: round(float(mask.sum() * passo), 2)   # noqa: E731
    bruto = round(float(intervalo["base"]) - float(intervalo["topo"]), 2)
    mv = m & valido
    return {
        "nome": intervalo.get("nome") or "", "origem": intervalo.get("origem", ""),
        "topo": float(intervalo["topo"]), "base": float(intervalo["base"]),
        "bruto_m": bruto, "com_dados_m": h(mv),
        "reservatorio_m": h(m & res), "net_pay_m": h(m & pay),
        "ntg": round(float((m & res).sum() / mv.sum()), 4) if mv.any() else None,
        "ntg_pay": round(float((m & pay).sum() / mv.sum()), 4) if mv.any() else None,
        "vsh_medio": media(vsh, mv), "phi_media_pay": media(phi, m & pay), "sw_media_pay": media(sw, m & pay),
        "phi_media_res": media(phi, m & res),
        "hpv_m": round(float(np.sum((phi * (1 - sw))[m & pay]) * passo), 3),
        "qc_arrombado_m": h(m & qc_cali), "qc_drho_m": h(m & qc_drho),
        "pay_com_qc_m": h(m & pay & (qc_cali | qc_drho)),
    }


# ============================================================ registro
def registrar(pasta_execucoes: str, *, poco: str, rel: str, sha256: str | None, resultado: dict,
              autor: str = "") -> tuple[str, str]:
    """Grava o registro da execução (JSON) e as curvas (npz). Devolve (id, caminho do JSON)."""
    os.makedirs(pasta_execucoes, exist_ok=True)
    quando = datetime.now()
    ident = f"avaliacao_{re.sub(r'[^A-Za-z0-9-]+', '_', poco or 'sem_poco')}_{quando:%Y%m%d-%H%M%S}"
    base, n = ident, 2
    while os.path.exists(os.path.join(pasta_execucoes, ident + ".json")):   # duas no mesmo segundo
        ident, n = f"{base}-{n}", n + 1
    np.savez_compressed(os.path.join(pasta_execucoes, ident + ".npz"), prof=resultado["prof"],
                        **{k: v.astype(np.float32) for k, v in resultado["curvas"].items()})
    reg = {
        "id": ident, "tipo": "avaliacao_formacao", "siapp_versao": __version__, "criado_em": agora(),
        "autor": autor, "poco": poco, "arquivo": rel, "arquivo_sha256": sha256,
        "curvas_usadas": resultado["curvas_usadas"],
        "metodos": {"vsh": resultado["parametros"]["vsh_metodo"], "phi": resultado["parametros"]["phi_metodo"],
                    "sw": resultado["parametros"]["sw_metodo"]},
        "parametros": resultado["parametros"], "parametros_automaticos": resultado["automaticos"],
        "avisos": resultado.get("avisos", []), "referencia_gr": resultado.get("referencia_gr"),
        "passo_m": resultado["passo"], "intervalos": resultado["intervalos"],
        "formulas": __doc__.split("Fórmulas", 1)[1].strip() if "Fórmulas" in (__doc__ or "") else "",
    }
    caminho = os.path.join(pasta_execucoes, ident + ".json")
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(reg, f, ensure_ascii=False, indent=1)
    return ident, caminho


def execucoes(pasta_execucoes: str, rel: str | None = None) -> list[dict]:
    if not os.path.isdir(pasta_execucoes):
        return []
    saida = []
    for nome in sorted(os.listdir(pasta_execucoes), reverse=True):
        if not (nome.startswith("avaliacao_") and nome.endswith(".json")):
            continue
        try:
            with open(os.path.join(pasta_execucoes, nome), encoding="utf-8") as f:
                reg = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        if rel is None or reg.get("arquivo") == rel:
            saida.append(reg)
    return saida


def carregar_curvas(pasta_execucoes: str, ident: str) -> dict:
    caminho = os.path.join(pasta_execucoes, os.path.basename(ident) + ".npz")
    if not os.path.isfile(caminho):
        raise ErroAvaliacao("Curvas desta avaliação não encontradas: calcule de novo.")
    with np.load(caminho) as z:
        return {k: z[k] for k in z.files}


def dados_grafico(pasta_execucoes: str, ident: str, topo=None, base=None, max_pontos: int = 2500) -> list[dict]:
    z = carregar_curvas(pasta_execucoes, ident)
    prof = z.pop("prof")
    sel = np.isfinite(prof)
    if topo is not None:
        sel &= prof >= topo
    if base is not None:
        sel &= prof <= base
    saida = []
    unidades = {"VSH": "v/v", "PHI": "v/v", "SW": "v/v", "PAY": "", "RES": "", "QC": ""}
    for nome in ("VSH", "PHI", "SW", "RES", "PAY", "QC"):
        if nome not in z:
            continue
        p, v = mpf._decimar(prof[sel], z[nome][sel].astype(np.float64), max_pontos)
        saida.append({"quadro": "avaliação", "mnemonico": nome, "familia": "AV_" + nome,
                      "unidade": unidades[nome], "prof": [round(float(x), 3) for x in p],
                      "valores": [None if not np.isfinite(x) else round(float(x), 4) for x in v]})
    return saida


def exportar(pasta_execucoes: str, ident: str, caminho_saida: str, formato: str, poco: str) -> dict:
    """Curvas calculadas (só nos intervalos) em CSV ou LAS 2.0."""
    z = carregar_curvas(pasta_execucoes, ident)
    prof = z.pop("prof")
    linhas = np.zeros(len(prof), bool)
    for v in z.values():
        linhas |= np.isfinite(v)
    prof = prof[linhas]
    cols = {k: v[linhas] for k, v in z.items()}
    os.makedirs(os.path.dirname(caminho_saida), exist_ok=True)
    if formato == "csv":
        with open(caminho_saida, "w", encoding="utf-8", newline="") as f:
            f.write("PROF_M;" + ";".join(cols) + "\n")
            for i, pr in enumerate(prof):
                vals = ["" if not np.isfinite(cols[k][i]) else f"{cols[k][i]:.4f}".replace(".", ",") for k in cols]
                f.write(f"{pr:.4f}".replace(".", ",") + ";" + ";".join(vals) + "\n")
    elif formato == "las":
        import lasio
        las = lasio.LASFile()
        las.well["STRT"].value, las.well["STRT"].unit = float(prof[0]), "M"
        las.well["STOP"].value, las.well["STOP"].unit = float(prof[-1]), "M"
        las.well["NULL"].value = -999.25
        las.well["WELL"].value = poco
        las.well["SRVC"].value = f"SIAPP {__version__} — avaliação {ident}"
        las.append_curve("DEPT", prof, unit="M")
        descr = {"VSH": "Volume de argila", "PHI": "Porosidade", "SW": "Saturação de água",
                 "RES": "Reservatório (1/0)", "PAY": "Net pay (1/0)", "QC": "Controle de qualidade (1 = suspeito)"}
        for k, v in cols.items():
            las.append_curve(k, np.where(np.isfinite(v), v, -999.25), unit="V/V" if k in ("VSH", "PHI", "SW") else "",
                             descr=descr.get(k, ""))
        las.other = f"Parâmetros e fórmulas: execucoes/{ident}.json"
        with open(caminho_saida, "w", encoding="utf-8") as f:
            las.write(f, version=2.0)
    else:
        raise ErroAvaliacao("Formato: csv ou las.")
    return {"amostras": int(len(prof))}
