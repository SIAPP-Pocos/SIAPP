"""Volumetria preliminar por formação, a partir do bloco fechado.

Por formação (camada do bloco fechado):

    volume de rocha (GRV)     = área × espessura, integrado na malha do bloco
    volume poroso (VP)        = GRV × N/G × φ
    volume de hidrocarboneto  = VP × (1 − Sw)                (em condições de reservatório)
    óleo in place (VOIP)      = volume de hidrocarboneto / Bo (se Bo for informado)
    capacidade teórica de CO₂ = VP × E × ρ(CO₂)             (se E e ρ forem informados)

N/G, φ e Sw vêm da avaliação de formação (aba Perfis: a média dos poços avaliados naquela
formação) ou são **informados pelo usuário** — e cada valor diz de onde veio. Sem valor, a
conta daquela formação não sai: o SIAPP não inventa parâmetro.

É **preliminar**: o volume de rocha inclui a parte extrapolada do bloco (fora do contorno
dos poços com o dado), e uma média de poucos poços avaliados não representa a formação
inteira. Para aferir, compare com um volume oficial (Plano de Desenvolvimento da ANP).
"""

from __future__ import annotations

import numpy as np

from . import bloco_solido as mbs

PARAMETROS = ("ntg", "phi", "sw")
DA_AVALIACAO = {"ntg": "ntg", "phi": "phi_media_pay", "sw": "sw_media_pay"}


class ErroVolumetria(Exception):
    pass


def _num(v):
    if v in (None, ""):
        return None
    try:
        return float(str(v).replace(",", "."))
    except ValueError as e:
        raise ErroVolumetria(f"Valor inválido: {v}") from e


def calcular(modelo: dict, informados: dict | None = None, co2: dict | None = None) -> dict:
    """`informados`: {chave: {ntg, phi, sw, bo}} (o que o usuário digitou; vazio = da
    avaliação). `co2`: {eficiencia (fração), densidade (kg/m³)}."""
    sol = modelo.get("solido") or {}
    if not sol.get("ok"):
        raise ErroVolumetria("A volumetria usa o bloco fechado, que este bloco não tem.")
    informados = informados or {}
    co2 = co2 or {}
    eff, rho = _num(co2.get("eficiencia")), _num(co2.get("densidade"))
    if eff is not None and not 0 < eff <= 1:
        raise ErroVolumetria("A eficiência de armazenamento é uma fração entre 0 e 1 (ex.: 0,02).")
    props = modelo.get("propriedades") or {}
    linhas = []
    for c in sol["camadas"]:
        if c["chave"] in (mbs.CHAVE_COBERTURA, mbs.CHAVE_ABAIXO):
            continue
        info = props.get(c["chave"]) or {}
        dig = informados.get(c["chave"]) or {}
        par, fonte = {}, {}
        for p in PARAMETROS:
            v = _num(dig.get(p))
            if v is not None:
                if not 0 <= v <= 1:
                    raise ErroVolumetria(f"{p.upper()} de {c['nome']}: use fração entre 0 e 1 (ex.: 0,25).")
                par[p], fonte[p] = v, "informado"
                continue
            vals = [q[DA_AVALIACAO[p]] for q in info.get("pocos", []) if q.get(DA_AVALIACAO[p]) is not None]
            if vals:
                par[p], fonte[p] = float(np.mean(vals)), f"avaliação ({len(vals)} poço{'s' if len(vals) > 1 else ''})"
            else:
                par[p], fonte[p] = None, ""
        bo = _num(dig.get("bo"))
        grv = c["volume_km3"] * 1e9
        vp = grv * par["ntg"] * par["phi"] if par["ntg"] is not None and par["phi"] is not None else None
        hc = vp * (1 - par["sw"]) if vp is not None and par["sw"] is not None else None
        linhas.append({
            "chave": c["chave"], "nome": c["nome"], "cor": c["cor"], "area_km2": c["area_km2"],
            "espessura_media_m": round(c["volume_km3"] / c["area_km2"] * 1000, 1) if c["area_km2"] else None,
            "fracao_extrapolada": c["fracao_extrapolada"], "grv_m3": grv,
            "ntg": par["ntg"], "phi": par["phi"], "sw": par["sw"], "bo": bo, "fonte": fonte,
            "vp_m3": vp, "hc_m3": hc, "voip_m3": hc / bo if hc is not None and bo else None,
            "co2_t": vp * eff * rho / 1000 if vp is not None and eff is not None and rho is not None else None})
    soma = lambda k: sum(l[k] for l in linhas if l[k] is not None) if any(l[k] is not None for l in linhas) else None
    notas = ["Preliminar: o volume de rocha inclui a parte extrapolada do bloco; médias de poucos poços avaliados "
             "não representam a formação inteira. Afira com um volume oficial (Plano de Desenvolvimento da ANP)."]
    sem = [l["nome"] for l in linhas if l["vp_m3"] is None]
    if sem:
        notas.append(f"Sem N/G ou φ (nem avaliação, nem informado): {', '.join(sem)}.")
    return {"linhas": linhas, "total": {k: soma(k) for k in ("grv_m3", "vp_m3", "hc_m3", "voip_m3", "co2_t")},
            "co2": {"eficiencia": eff, "densidade": rho}, "notas": notas}


COLUNAS_CSV = ["formacao", "area_km2", "espessura_media_m", "fracao_extrapolada", "volume_rocha_m3", "ntg",
               "fonte_ntg", "phi", "fonte_phi", "sw", "fonte_sw", "bo", "volume_poroso_m3", "volume_hc_m3",
               "voip_m3", "co2_t"]


def linhas_csv(v: dict) -> list[list]:
    return [[l["nome"], l["area_km2"], l["espessura_media_m"], l["fracao_extrapolada"], l["grv_m3"], l["ntg"],
             l["fonte"]["ntg"], l["phi"], l["fonte"]["phi"], l["sw"], l["fonte"]["sw"], l["bo"], l["vp_m3"],
             l["hc_m3"], l["voip_m3"], l["co2_t"]] for l in v["linhas"]]
