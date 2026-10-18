"""Viabilidade econômica de injetar num campo depletado: quanto custa o duto até a
infraestrutura mais próxima, dividido por quanto o campo comporta (o indicador do PIBIC).

Custo do duto
    comprimento (distância × fator de traçado) × custo por km. O custo por km é linear no
    diâmetro (R$ por polegada·km, como a EPE e a literatura comparam gasodutos) e multiplicado
    por um fator do fluido (CO₂ em fase densa pede parede mais grossa; H₂ pede aço um pouco
    mais caro). As referências são dos Planos Indicativos de Gasodutos da EPE (FONTES_CUSTO).

Capacidade de injeção — três níveis, do que funciona para todo campo ao mais específico
    1. **Simples (PIBIC)**: o espaço é o volume produzido, em m³ de óleo equivalente (óleo +
       condensado + gás ÷ 1.000, a convenção da ANP). Só precisa da produção.
    2. **Espaço poroso**: o volume que a produção liberou no reservatório (voidage):
       Np·Bo + (Gp − Np·Rs)·Bg + Wp − Wi − Gi·Bg. Precisa de Bo e/ou Bg (e Rs, se houver).
    3. **Pela molécula**: o espaço poroso cheio com o fluido injetado nas condições do
       reservatório — massa = espaço × ρ(P, T) × eficiência. A densidade sai de Peng-Robinson
       com translação de volume (Peneloux) para CO₂, H₂ ou CH₄; P e T vêm do usuário ou de
       gradientes sobre a profundidade. Para gás armazenado (H₂, CH₄) desconta o gás de colchão.

Nada aqui substitui simulação: o limite real pode ser pressão ou injetividade, não espaço.
É uma triagem para comparar campos.
"""

from __future__ import annotations

import math
import re
from statistics import median

import numpy as np

from . import producao as mpr
from .banco import Banco

# ====================================================================== custo do duto
# R$ mil por polegada de diâmetro por km, calculado de projetos reais da EPE (CAPEX total ÷
# (extensão × diâmetro)); valores da data-base de cada estudo, sem correção.
FONTES_CUSTO = [
    {"id": "pig2024", "r_mil_pol_km": 488, "data_base": "jun/2024",
     "rotulo": "EPE PIG 2024 — Porto Murtinho–Campo Grande (392 km, 32″, R$ 6,12 bi)",
     "url": "https://www.epe.gov.br/pt/publicacoes-dados-abertos/publicacoes/plano-indicativo-de-gasodutos-de-transporte-pig"},
    {"id": "pig2022", "r_mil_pol_km": 694, "data_base": "2022",
     "rotulo": "EPE PIG 2022 — Brasil Central, São Carlos–Brasília (893 km, 18–20″, R$ 11,15 bi)",
     "url": "https://www.epe.gov.br/pt/publicacoes-dados-abertos/publicacoes/plano-indicativo-de-gasodutos-de-transporte-pig"},
    {"id": "pig2019_plano", "r_mil_pol_km": 325, "data_base": "jun/2019",
     "rotulo": "EPE PIG 2019 — Uruguaiana–Triunfo (594 km, 24″, relevo plano, R$ 4,63 bi)",
     "url": "https://www.epe.gov.br/pt/publicacoes-dados-abertos/publicacoes/plano-indicativo-de-gasodutos-de-transporte-pig"},
    {"id": "pig2019_serra", "r_mil_pol_km": 457, "data_base": "jun/2019",
     "rotulo": "EPE PIG 2019 — Siderópolis–Porto Alegre (249 km, 16″, Serra do Mar, R$ 1,82 bi)",
     "url": "https://www.epe.gov.br/pt/publicacoes-dados-abertos/publicacoes/plano-indicativo-de-gasodutos-de-transporte-pig"},
]
# fator sobre o custo de um gasoduto de gás natural do mesmo diâmetro
FATOR_FLUIDO = {
    "co2": (1.20, "CO₂ em fase densa: ~50% mais aço (150 contra 100 bar) sobre a tubulação, que é ~45% do CAPEX "
                  "no PIG 2024 → ≈ +20% (estimativa do SIAPP)"),
    "h2": (1.05, "H₂: aço ~10% mais caro → +1,4 a 4,6% por polegada·milha (EPRI, 2023); arredondado para +5%"),
    "ch4": (1.00, "gás natural: a própria referência"),
}

# ====================================================================== fluidos (Peng-Robinson)
R = 8.314462618                     # J/(mol·K)
P_PADRAO, T_PADRAO = 101325.0, 293.15   # condição padrão da ANP: 20 °C e 1 atm
FLUIDOS = {
    "co2": {"rotulo": "CO₂", "Tc": 304.1282, "Pc": 73.773e5, "w": 0.22394, "M": 44.0095e-3, "zra": 0.27256,
            "armazenado": False},
    "h2": {"rotulo": "H₂", "Tc": 33.145, "Pc": 12.964e5, "w": -0.219, "M": 2.01588e-3, "zra": 0.3048,
           "armazenado": True, "pci_kwh_kg": 33.33},
    "ch4": {"rotulo": "CH₄ (gás natural)", "Tc": 190.564, "Pc": 45.992e5, "w": 0.01142, "M": 16.0428e-3,
            "zra": 0.28766, "armazenado": True},
}

PADROES = {
    "fonte_custo": "pig2024", "custo_mil_pol_km": 488.0, "diametro_pol": 8.0, "fator_tracado": 1.0,
    "fluido": "co2", "bo": None, "bg": None, "rs": None,
    "profundidade_m": None, "pressao_bar": None, "temperatura_c": None,
    "t_superficie_c": 25.0, "gradiente_t_c_km": 30.0, "gradiente_p_bar_m": 0.1,
    "eficiencia": 1.0, "colchao": 0.5,
}
# (mínimo, máximo) aceitos; fora disso é erro de digitação
LIMITES = {
    "custo_mil_pol_km": (1, 100000), "diametro_pol": (1, 60), "fator_tracado": (1, 3),
    "bo": (0.8, 5), "bg": (0.0001, 0.5), "rs": (0, 5000),
    "profundidade_m": (50, 8000), "pressao_bar": (1, 1500), "temperatura_c": (0, 250),
    "t_superficie_c": (-10, 50), "gradiente_t_c_km": (5, 80), "gradiente_p_bar_m": (0.05, 0.3),
    "eficiencia": (0.01, 1), "colchao": (0, 0.95),
}
# camadas que são a origem natural de cada fluido (o quadro marca)
ORIGENS = {
    "co2": {"epe_termeletricas_fosseis", "ibge_termeletricas", "epe_upgn"},
    "h2": {"epe_h2_projetos"},
    "ch4": {"epe_gasodutos_transporte", "epe_dutos_escoamento", "epe_upgn"},
}
GAS_POR_OE = 1000.0                 # m³ de gás por m³ de óleo equivalente (ANP)


class ErroEconomia(ValueError):
    pass


def _num(v):
    if v is None or (isinstance(v, str) and not v.strip()):
        return None
    if isinstance(v, str):
        v = v.strip().replace(" ", "")
        v = v.replace(".", "").replace(",", ".") if "," in v else v
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise ErroEconomia(f"Número inválido: {v!r}.") from None
    if not math.isfinite(x):
        raise ErroEconomia(f"Número inválido: {v!r}.")
    return x


ROTULOS = {"custo_mil_pol_km": "Custo (R$ mil por polegada·km)", "diametro_pol": "Diâmetro (pol)",
           "fator_tracado": "Fator de traçado", "bo": "Bo", "bg": "Bg", "rs": "Rs",
           "profundidade_m": "Profundidade (m)", "pressao_bar": "Pressão (bar)", "temperatura_c": "Temperatura (°C)",
           "t_superficie_c": "Temperatura na superfície (°C)", "gradiente_t_c_km": "Gradiente de temperatura (°C/km)",
           "gradiente_p_bar_m": "Gradiente de pressão (bar/m)", "eficiencia": "Eficiência",
           "colchao": "Gás de colchão (fração)"}


def parametros(dados: dict | None) -> dict:
    """Os parâmetros do usuário sobre os padrões, conferidos."""
    p = dict(PADROES)
    for k, v in (dados or {}).items():
        if k not in PADROES:
            continue
        if k in ("fonte_custo", "fluido"):
            p[k] = str(v) if v else PADROES[k]
            continue
        x = _num(v)
        if x is None:
            p[k] = PADROES[k]
            continue
        lo, hi = LIMITES[k]
        if not lo <= x <= hi:
            raise ErroEconomia(f"{ROTULOS[k]}: {x:g} fora do intervalo aceito ({lo:g} a {hi:g}).")
        p[k] = x
    if p["fluido"] not in FLUIDOS:
        raise ErroEconomia(f"Fluido desconhecido: {p['fluido']}.")
    fonte = next((f for f in FONTES_CUSTO if f["id"] == p["fonte_custo"]), None)
    if fonte is None and p["fonte_custo"] != "manual":
        raise ErroEconomia(f"Referência de custo desconhecida: {p['fonte_custo']}.")
    if fonte is not None:            # custo não informado → o da referência; informado e diferente → manual
        if _num((dados or {}).get("custo_mil_pol_km")) is None:
            p["custo_mil_pol_km"] = float(fonte["r_mil_pol_km"])
        elif abs(p["custo_mil_pol_km"] - fonte["r_mil_pol_km"]) > 1e-9:
            p["fonte_custo"] = "manual"
    return p


def custo_por_km(p: dict) -> dict:
    """R$ por km de duto e de onde veio."""
    fator, motivo = FATOR_FLUIDO[p["fluido"]]
    base = p["custo_mil_pol_km"] * 1e3 * p["diametro_pol"]
    fonte = next((f for f in FONTES_CUSTO if f["id"] == p["fonte_custo"]), None)
    return {"r_por_km": base * fator, "r_por_km_gas_natural": base, "fator_fluido": fator, "motivo_fator": motivo,
            "r_mil_pol_km": p["custo_mil_pol_km"], "diametro_pol": p["diametro_pol"],
            "referencia": fonte["rotulo"] if fonte else "informado pelo usuário",
            "data_base": fonte["data_base"] if fonte else None}


# ====================================================================== produção acumulada
def _ano(texto) -> int | None:
    m = re.search(r"(19|20)\d{2}", str(texto or ""))
    return int(m.group(0)) if m else None


_SOMAS = ("SUM(COALESCE(oleo_m3, 0) + COALESCE(condensado_m3, 0)) AS np, "
          "SUM(COALESCE(gas_assoc_mil_m3, 0) + COALESCE(gas_nassoc_mil_m3, 0)) * 1000 AS gp, "
          "SUM(COALESCE(agua_m3, 0)) AS wp, "
          "SUM(COALESCE(inj_agua_rec_m3, 0) + COALESCE(inj_agua_desc_m3, 0) + COALESCE(inj_polimeros_m3, 0) + "
          "COALESCE(inj_outros_m3, 0) + COALESCE(inj_vapor_t, 0)) AS wi, "
          "SUM(COALESCE(inj_gas_mil_m3, 0) + COALESCE(inj_co2_mil_m3, 0) + COALESCE(inj_n2_mil_m3, 0)) * 1000 AS gi")


def acumulados(banco: Banco, campo: str) -> dict:
    """Óleo, gás, água produzidos e injetados desde o início do campo — o melhor que os dados
    guardados permitem — e de onde veio cada número. Volumes em m³ (gás em m³ padrão)."""
    chave = mpr.chave_campo(campo)
    ficha = mpr.campo_guardado(banco, campo) or {}
    pd = ficha.get("pd") or {}
    acu = pd.get("acumulada") or {}
    inicio = _ano((ficha.get("ficha") or {}).get("inicio_producao")) or _ano(pd.get("inicio_producao"))
    with banco.conexao() as c:
        s = c.execute(f"SELECT MIN(periodo) AS de, MAX(periodo) AS ate, COUNT(*) AS n, "
                      f"COUNT(DISTINCT periodo) AS meses, {_SOMAS} FROM producao_poco WHERE campo = ?",
                      (chave,)).fetchone()
    serie = dict(s) if s and s["n"] else None
    avisos: list[str] = []
    if serie:                         # meses sem nenhuma linha no meio da série = arquivo não baixado
        esperados = (int(serie["ate"][:4]) - int(serie["de"][:4])) * 12 + int(serie["ate"][5:7]) - int(serie["de"][5:7]) + 1
        serie["meses_faltando"] = esperados - serie["meses"]
    completa = bool(serie and inicio and int(serie["de"][:4]) <= inicio and serie["meses_faltando"] == 0)
    out = {"inicio_producao": inicio, "serie": serie, "serie_completa": completa}

    oleo_pd = sum(acu.get(k) or 0 for k in ("oleo_milhoes_m3", "condensado_milhoes_m3")) * 1e6
    if acu.get("gas_total_milhoes_m3") is not None:
        gas_pd = acu["gas_total_milhoes_m3"] * 1e6
    else:
        gas_pd = sum(acu.get(k) or 0 for k in ("gas_associado_milhoes_m3", "gas_nao_associado_milhoes_m3")) * 1e6
    tem_pd = bool(oleo_pd or gas_pd)

    if completa:
        out.update(np=serie["np"], gp=serie["gp"], wp=serie["wp"], wi=serie["wi"], gi=serie["gi"],
                   fonte=f"produção mensal da ANP, {_mes(serie['de'])} a {_mes(serie['ate'])} (todo o histórico)",
                   ate=serie["ate"])
    elif tem_pd:
        data = acu.get("data") or ""
        out.update(np=oleo_pd, gp=gas_pd, wp=None, wi=None, gi=None, ate=None,
                   fonte=f"produção acumulada do Plano de Desenvolvimento ({pd.get('fonte') or 'BAR'}"
                         f"{', ' + data if data else ''})")
        if len(data) == 10:
            corte = f"{data[6:10]}-{data[3:5]}"
            out["ate"] = corte
            with banco.conexao() as c:
                d = c.execute(f"SELECT MAX(periodo) AS ate, COUNT(*) AS n, {_SOMAS} FROM producao_poco "
                              "WHERE campo = ? AND periodo > ?", (chave, corte)).fetchone()
                continua = c.execute("SELECT COUNT(*) FROM producao_poco WHERE campo = ? AND periodo = ?",
                                     (chave, _mes_seguinte(corte))).fetchone()[0]
            if d and d["n"] and continua:
                out["np"] += d["np"] or 0
                out["gp"] += d["gp"] or 0
                out["ate"] = d["ate"]
                out["fonte"] += f" + produção mensal até {_mes(d['ate'])}"
        avisos.append("Água produzida e fluidos injetados ficam de fora do espaço poroso: só existem na série "
                      "mensal, que não cobre todo o histórico do campo (baixe a produção com \"todo o histórico\").")
    elif serie:
        out.update(np=serie["np"], gp=serie["gp"], wp=None, wi=None, gi=None, ate=serie["ate"],
                   fonte=f"produção mensal da ANP, {_mes(serie['de'])} a {_mes(serie['ate'])} — só o período baixado")
        if inicio and int(serie["de"][:4]) <= inicio:
            motivo = f"faltam {serie['meses_faltando']} meses no meio da série"
        else:
            motivo = (f"a série baixada começa em {_mes(serie['de'])}"
                      + (f", mas o campo produz desde {inicio}" if inicio else " e o início do campo é desconhecido"))
        avisos.append(f"Produção incompleta ({motivo}): a capacidade fica subestimada. Baixe \"todo o histórico\" "
                      "ou o sumário do PD.")
    else:
        raise ErroEconomia(f"Nada da produção de {campo} guardado: baixe a produção do campo na aba Bloco 3D.")
    out["avisos"] = avisos
    return out


def _mes(p: str | None) -> str:
    return f"{p[5:7]}/{p[:4]}" if p else "—"


def _mes_seguinte(p: str) -> str:
    a, m = int(p[:4]), int(p[5:7])
    return f"{a + (m == 12)}-{m % 12 + 1:02d}"


# ====================================================================== capacidade
def capacidade_simples(ac: dict) -> dict:
    """Método do PIBIC: o espaço é o volume produzido, em m³ de óleo equivalente."""
    oe = (ac["np"] or 0) + (ac["gp"] or 0) / GAS_POR_OE
    return {"metodo": "simples", "rotulo": "Simples (PIBIC): volume produzido", "valor": oe,
            "unidade": "m³ de óleo equivalente",
            "detalhe": {"oleo_condensado_m3": ac["np"], "gas_m3": ac["gp"], "gas_em_oe_m3": (ac["gp"] or 0) / GAS_POR_OE},
            "formula": "óleo + condensado + gás ÷ 1.000 (convenção da ANP)"}


def capacidade_porosa(ac: dict, p: dict) -> dict:
    """Volume liberado no reservatório (m³ de reservatório): Np·Bo + (Gp − Np·Rs)·Bg + Wp − Wi − Gi·Bg."""
    np_, gp = ac["np"] or 0, ac["gp"] or 0
    falta = []
    if np_ > 0 and p["bo"] is None:
        falta.append("Bo")
    if gp > 0 and p["bg"] is None:
        falta.append("Bg")
    base = {"metodo": "poroso", "rotulo": "Espaço poroso liberado (voidage)", "unidade": "m³ de reservatório",
            "formula": "Np·Bo + (Gp − Np·Rs)·Bg + Wp − Wi − Gi·Bg"}
    if falta:
        return {**base, "valor": None, "falta": falta}
    avisos = []
    bo, bg = p["bo"] or 0, p["bg"] or 0
    rs = p["rs"]
    if rs is None:
        rs = 0.0
        if np_ > 0 and gp > 0:
            avisos.append("Sem Rs: todo o gás produzido conta como gás livre no reservatório (superestima num "
                          "campo de óleo). Informe a razão de solubilidade inicial.")
    livre = max(0.0, gp - np_ * rs)
    agua = None
    gi = 0.0
    if ac.get("wp") is not None:
        agua = (ac["wp"] or 0) - (ac["wi"] or 0)
        gi = ac["gi"] or 0
    parcelas = {"oleo": np_ * bo, "gas_livre": livre * bg, "agua_liquida": agua, "gas_injetado": -gi * bg}
    valor = sum(v for v in parcelas.values() if v is not None)
    if valor <= 0:
        avisos.append("A injeção já repôs todo o volume produzido: não sobra espaço por este método.")
        valor = 0.0
    avisos.append("Sem influxo de aquífero (We): com aquífero ativo o espaço disponível é menor.")
    return {**base, "valor": valor, "parcelas": parcelas, "rs_usado": rs, "avisos": avisos}


def densidade(fluido: str, pressao_bar: float, temperatura_c: float) -> float:
    """kg/m³ por Peng-Robinson (1976) com translação de volume de Peneloux. Contra a referência
    (Span-Wagner para CO₂, Leachman para H₂): erro típico < 7% para CO₂ (maior perto do ponto
    crítico) e < 5% para H₂ e CH₄, entre 60 e 300 bar."""
    d = FLUIDOS[fluido]
    T, P = temperatura_c + 273.15, pressao_bar * 1e5
    k = 0.37464 + 1.54226 * d["w"] - 0.26992 * d["w"] ** 2
    a = 0.45724 * R ** 2 * d["Tc"] ** 2 / d["Pc"] * (1 + k * (1 - math.sqrt(T / d["Tc"]))) ** 2
    b = 0.07780 * R * d["Tc"] / d["Pc"]
    A, B = a * P / (R * T) ** 2, b * P / (R * T)
    raizes = np.roots([1.0, -(1 - B), A - 3 * B * B - 2 * B, -(A * B - B * B - B ** 3)])
    reais = [float(z.real) for z in raizes if abs(z.imag) < 1e-9 and z.real > B]
    s2 = math.sqrt(2)

    def g(Z):                        # energia de Gibbs residual (ln φ): fica a raiz estável
        return Z - 1 - math.log(Z - B) - A / (2 * s2 * B) * math.log((Z + (1 + s2) * B) / (Z + (1 - s2) * B))
    Z = min(reais, key=g)
    c = 0.40768 * (0.29441 - d["zra"]) * R * d["Tc"] / d["Pc"]
    return d["M"] / (Z * R * T / P - c)


def profundidade_campo(banco: Banco, campo: str) -> float | None:
    """Mediana da profundidade vertical final dos poços do campo no cadastro."""
    alvo = mpr.chave_campo(campo)
    with banco.conexao() as c:
        rows = c.execute("SELECT campo, prof_vertical, prof_sondador FROM pocos WHERE campo IS NOT NULL").fetchall()
    profs = [r["prof_vertical"] or r["prof_sondador"] for r in rows if mpr.chave_campo(r["campo"] or "") == alvo]
    profs = [x for x in profs if x and x > 0]
    return float(median(profs)) if profs else None


def condicoes(banco: Banco, campo: str, p: dict) -> dict:
    """Pressão e temperatura do reservatório: as informadas ou por gradiente sobre a profundidade."""
    prof, origem_prof = p["profundidade_m"], "informada"
    if prof is None and (p["pressao_bar"] is None or p["temperatura_c"] is None):
        prof = profundidade_campo(banco, campo)
        origem_prof = "mediana da profundidade final dos poços do campo (cadastro)"
    out = {"profundidade_m": prof, "origem_profundidade": origem_prof if prof is not None else None}
    if p["pressao_bar"] is not None:
        out.update(pressao_bar=p["pressao_bar"], origem_pressao="informada")
    elif prof is not None:
        out.update(pressao_bar=1.01325 + p["gradiente_p_bar_m"] * prof,
                   origem_pressao=f"hidrostática inicial, {p['gradiente_p_bar_m']:g} bar/m")
    if p["temperatura_c"] is not None:
        out.update(temperatura_c=p["temperatura_c"], origem_temperatura="informada")
    elif prof is not None:
        out.update(temperatura_c=p["t_superficie_c"] + p["gradiente_t_c_km"] * prof / 1000,
                   origem_temperatura=f"{p['t_superficie_c']:g} °C + {p['gradiente_t_c_km']:g} °C/km")
    return out


def capacidade_molecula(poroso: dict, cond: dict, p: dict) -> dict:
    """O espaço poroso cheio com o fluido injetado nas condições do reservatório."""
    fl = p["fluido"]
    d = FLUIDOS[fl]
    base = {"metodo": "molecula", "rotulo": f"Pela molécula ({d['rotulo']})", "fluido": fl,
            "formula": "espaço poroso × ρ(P, T) × eficiência" + (" × (1 − colchão)" if d["armazenado"] else "")}
    falta = []
    if poroso.get("valor") is None:
        falta += poroso.get("falta", [])
    if cond.get("pressao_bar") is None or cond.get("temperatura_c") is None:
        falta.append("profundidade ou P e T")
    if falta:
        return {**base, "valor": None, "falta": falta}
    P, T = cond["pressao_bar"], cond["temperatura_c"]
    rho = densidade(fl, P, T)
    rho_padrao = densidade(fl, P_PADRAO / 1e5, T_PADRAO - 273.15)
    massa = poroso["valor"] * rho * p["eficiencia"]           # kg
    out = {**base, "condicoes": cond, "densidade_kg_m3": rho, "eficiencia": p["eficiencia"],
           "massa_total_t": massa / 1e3}
    if not d["armazenado"]:                                     # CO₂: armazenamento permanente
        out.update(valor=massa / 1e3, unidade="t de CO₂", massa_mt=massa / 1e9,
                   volume_padrao_milhoes_m3=massa / rho_padrao / 1e6)
        return out
    util = massa * (1 - p["colchao"])
    out.update(valor=util / 1e3, unidade=f"t de {d['rotulo']} (gás útil)", colchao=p["colchao"],
               volume_padrao_util_milhoes_m3=util / rho_padrao / 1e6)
    if fl == "h2":
        out["energia_util_mwh"] = util * d["pci_kwh_kg"] / 1e3
    return out


# ====================================================================== indicador
def avaliar(banco: Banco, campo: str, distancias: list[dict], dados: dict | None) -> dict:
    """Custo do duto até cada infraestrutura medida e o indicador (R$ ÷ capacidade) em cada método."""
    p = parametros(dados)
    custo = custo_por_km(p)
    ac = acumulados(banco, campo)
    simples = capacidade_simples(ac)
    poroso = capacidade_porosa(ac, p)
    cond = condicoes(banco, campo, p)
    metodos = {"simples": simples, "poroso": poroso, "molecula": capacidade_molecula(poroso, cond, p)}
    linhas = []
    for d in distancias:
        if not d.get("baixada") or d.get("distancia_km") is None:
            continue
        comp = d["distancia_km"] * p["fator_tracado"]
        reais = comp * custo["r_por_km"]
        ind = {}
        for nome, m in metodos.items():
            v = m.get("valor")
            ind[nome] = (reais / v) if v else None
        mol = metodos.get("molecula") or {}
        extra = {}
        if mol.get("energia_util_mwh"):
            extra["r_por_mwh"] = reais / mol["energia_util_mwh"]
        linhas.append({"id": d["id"], "rotulo": d["rotulo"], "distancia_km": d["distancia_km"],
                       "toca_o_campo": d.get("toca_o_campo", False), "comprimento_km": comp,
                       "custo_r": reais, "indicadores": ind, **extra,
                       "origem_tipica": d["id"] in ORIGENS.get(p["fluido"], set())})
    avisos = list(ac["avisos"])
    for m in metodos.values():
        avisos += m.get("avisos", [])
    if any(l["toca_o_campo"] for l in linhas):
        avisos.append("\"No campo\": a infraestrutura já cruza o polígono — o duto novo é só a ligação interna "
                      "(custo ≈ 0 neste modelo).")
    return {"campo": campo, "parametros": p, "custo": custo, "acumulados": {k: v for k, v in ac.items() if k != "avisos"},
            "metodos": metodos, "linhas": linhas, "avisos": avisos,
            "unidades_indicador": {"simples": "R$/m³ oe", "poroso": "R$/m³ res",
                                   "molecula": "R$/t"}}


COLUNAS_CSV = ["infraestrutura", "distancia_km", "comprimento_km", "custo_milhoes_r", "r_por_m3_oe",
               "r_por_m3_reservatorio", "r_por_t", "r_por_mwh", "origem_tipica"]


def linhas_csv(av: dict) -> list[list]:
    out = []
    for l in av["linhas"]:
        i = l["indicadores"]
        out.append([l["rotulo"], l["distancia_km"], round(l["comprimento_km"], 3), round(l["custo_r"] / 1e6, 3),
                    _r(i.get("simples")), _r(i.get("poroso")), _r(i.get("molecula")), _r(l.get("r_por_mwh")),
                    "sim" if l["origem_tipica"] else ""])
    return out


def _r(v):
    return None if v is None else round(v, 4)
