"""Viabilidade econômica de injetar num campo depletado: quanto custa o duto até a
infraestrutura mais próxima, dividido por quanto o campo comporta (o indicador do PIBIC).

Tudo aqui é **auditável e editável**:

- cada número de entrada entra na *memória de cálculo* com a sua fonte (arquivo da ANP, PD,
  camada, valor informado ou constante padrão);
- cada passo é uma **equação escrita** (texto), avaliada por um leitor seguro de fórmulas
  (`compilar`/`avaliar_formula`: só números, variáveis conhecidas, + − × ÷ ^ e min, max, abs,
  sqrt, exp, ln, log10 — nada de código). A memória guarda a equação, a equação com os números
  substituídos e o resultado;
- as **constantes** (fator do fluido, gás por óleo equivalente, Bw, PCI, propriedades críticas…)
  têm valor padrão e fonte, e podem ser trocadas;
- as **equações** podem ser trocadas por uma alternativa pronta ou por uma fórmula escrita pelo
  usuário, com as mesmas variáveis. Equação alterada fica marcada na memória.

Custo do duto (padrão)
    custo_km = custo_pol_km × 1000 × D × f_fluido;  L = dist × f_tracado;  custo = L × custo_km.
    Referências de R$ por polegada·km dos Planos Indicativos de Gasodutos da EPE (FONTES_CUSTO).

Capacidade de injeção — três níveis, do que funciona para todo campo ao mais específico
    1. **Simples (PIBIC)**: volume produzido em m³ de óleo equivalente, Np + Gp ÷ 1.000.
    2. **Espaço poroso** (voidage): Np·Bo + Gl·Bg + (Wp − Wi)·Bw − Gi·Bg, com Gl = max(0, Gp − Np·Rs).
    3. **Pela molécula**: V × ρ(P, T) × eficiência [× (1 − colchão) para H₂ e CH₄]; ρ por
       Peng-Robinson com translação de volume de Peneloux, ou informada.

Nada aqui substitui simulação: o limite real pode ser pressão ou injetividade, não espaço.
É uma triagem para comparar campos.
"""

from __future__ import annotations

import ast
import html
import json
import math
import os
import re
from datetime import datetime
from statistics import median

import numpy as np

from . import producao as mpr
from . import pvt as mpvt
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

# ====================================================================== constantes (editáveis)
# valor padrão, unidade, rótulo, fonte, faixa aceita, grupo
def _c(valor, unidade, rotulo, fonte, faixa, grupo):
    return {"valor": valor, "unidade": unidade, "rotulo": rotulo, "fonte": fonte, "faixa": faixa, "grupo": grupo}


CONSTANTES = {
    "gas_por_oe": _c(1000.0, "m³/m³", "Gás por m³ de óleo equivalente",
                     "ANP: 1.000 m³ de gás natural = 1 m³ de óleo equivalente", (1, 1e5), "Gerais"),
    "bw": _c(1.0, "m³/m³", "Bw — fator volume-formação da água",
             "aproximação usual: água pouco compressível", (0.9, 1.2), "Gerais"),
    "p_atm": _c(1.01325, "bar", "Pressão na superfície", "1 atm", (0.5, 2), "Gerais"),
    "p_padrao": _c(1.01325, "bar", "Pressão da condição padrão", "ANP: 1 atm", (0.5, 2), "Gerais"),
    "t_padrao": _c(20.0, "°C", "Temperatura da condição padrão", "ANP: 20 °C", (0, 30), "Gerais"),
    "pci_h2": _c(33.33, "kWh/kg", "PCI do H₂", "120 MJ/kg (poder calorífico inferior)", (30, 40), "Gerais"),
    "gg_padrao": _c(0.65, "—", "Densidade relativa do gás (ar = 1), quando não informada",
                    "valor típico de gás natural; informe a do campo", (0.55, 1.8), "Gerais"),
    "f_co2": _c(1.20, "—", "Fator de custo do duto — CO₂",
                "estimativa do SIAPP: CO₂ em fase densa (~150 bar contra ~100 do gás) pede ~50% mais aço; a "
                "tubulação é ~45% do CAPEX no PIG 2024 → ≈ +20%", (0.5, 3), "Fatores de custo"),
    "f_h2": _c(1.05, "—", "Fator de custo do duto — H₂",
               "EPRI (2023): aço ~10% mais caro → +1,4 a 4,6% por polegada·milha; arredondado para +5%",
               (0.5, 3), "Fatores de custo"),
    "f_ch4": _c(1.00, "—", "Fator de custo do duto — CH₄", "gás natural: a própria referência", (0.5, 3),
                "Fatores de custo"),
}
_FLUIDOS_BASE = {          # Tc (K), Pc (bar), ω, M (g/mol), Z_RA (Rackett) — DIPPR/NIST
    "co2": ("CO₂", 304.1282, 73.773, 0.22394, 44.0095, 0.27256),
    "h2": ("H₂", 33.145, 12.964, -0.219, 2.01588, 0.3048),
    "ch4": ("CH₄", 190.564, 45.992, 0.01142, 16.0428, 0.28766),
}
for _k, (_r, _tc, _pc, _w, _m, _z) in _FLUIDOS_BASE.items():
    CONSTANTES[f"{_k}_tc"] = _c(_tc, "K", f"{_r}: temperatura crítica", "NIST", (1, 1000), f"Fluido {_r}")
    CONSTANTES[f"{_k}_pc"] = _c(_pc, "bar", f"{_r}: pressão crítica", "NIST", (1, 500), f"Fluido {_r}")
    CONSTANTES[f"{_k}_w"] = _c(_w, "—", f"{_r}: fator acêntrico ω", "DIPPR", (-1, 2), f"Fluido {_r}")
    CONSTANTES[f"{_k}_m"] = _c(_m, "g/mol", f"{_r}: massa molar", "NIST", (1, 500), f"Fluido {_r}")
    CONSTANTES[f"{_k}_zra"] = _c(_z, "—", f"{_r}: Z de Rackett (translação de Peneloux)", "Reid, Prausnitz e Poling",
                                 (0.1, 0.5), f"Fluido {_r}")

FLUIDOS = {"co2": {"rotulo": "CO₂", "armazenado": False},
           "h2": {"rotulo": "H₂", "armazenado": True},
           "ch4": {"rotulo": "CH₄ (gás natural)", "armazenado": True}}
# camadas que são a origem natural de cada fluido (o quadro marca)
ORIGENS = {
    "co2": {"epe_termeletricas_fosseis", "ibge_termeletricas", "epe_upgn"},
    "h2": {"epe_h2_projetos"},
    "ch4": {"epe_gasodutos_transporte", "epe_dutos_escoamento", "epe_upgn"},
}

PADROES = {
    "fonte_custo": "pig2024", "custo_mil_pol_km": 488.0, "custo_fixo_km": 0.0, "diametro_pol": 8.0,
    "fator_tracado": 1.0, "fluido": "co2", "bo": None, "bg": None, "rs": None,
    "profundidade_m": None, "pressao_bar": None, "temperatura_c": None, "densidade_kg_m3": None,
    "t_superficie_c": 25.0, "gradiente_t_c_km": 30.0, "gradiente_p_bar_m": 0.1,
    "eficiencia": 1.0, "colchao": 0.5, "api": None, "densidade_gas": None, "estimar_pvt": "sim",
}
LIMITES = {
    "custo_mil_pol_km": (0, 100000), "custo_fixo_km": (0, 1e6), "diametro_pol": (1, 60), "fator_tracado": (1, 3),
    "bo": (0.8, 5), "bg": (0.0001, 0.5), "rs": (0, 5000),
    "profundidade_m": (50, 8000), "pressao_bar": (1, 1500), "temperatura_c": (0, 250), "densidade_kg_m3": (0.01, 2000),
    "t_superficie_c": (-10, 50), "gradiente_t_c_km": (5, 80), "gradiente_p_bar_m": (0.05, 0.3),
    "eficiencia": (0.01, 1), "colchao": (0, 0.95), "api": (5, 70), "densidade_gas": (0.55, 1.8),
}
ROTULOS = {"custo_mil_pol_km": "Custo (R$ mil por polegada·km)", "custo_fixo_km": "Parcela fixa (R$ mil por km)",
           "diametro_pol": "Diâmetro (pol)", "fator_tracado": "Fator de traçado", "bo": "Bo", "bg": "Bg", "rs": "Rs",
           "profundidade_m": "Profundidade (m)", "pressao_bar": "Pressão (bar)", "temperatura_c": "Temperatura (°C)",
           "densidade_kg_m3": "Densidade (kg/m³)", "t_superficie_c": "Temperatura na superfície (°C)",
           "gradiente_t_c_km": "Gradiente de temperatura (°C/km)", "gradiente_p_bar_m": "Gradiente de pressão (bar/m)",
           "eficiencia": "Eficiência", "colchao": "Gás de colchão (fração)", "api": "Grau API do óleo",
           "densidade_gas": "Densidade relativa do gás"}

# ====================================================================== símbolos e equações
SIMBOLOS = {
    "custo_pol_km": ("custo de gasoduto por polegada de diâmetro e por km", "R$ mil/(pol·km)"),
    "custo_fixo_km": ("parcela fixa do custo por km (ou o custo por km informado)", "R$ mil/km"),
    "D": ("diâmetro do duto", "pol"), "f_fluido": ("fator de custo do fluido", "—"),
    "custo_km": ("custo do duto por km", "R$/km"),
    "dist": ("distância do campo à infraestrutura (geodésica)", "km"), "f_tracado": ("fator de traçado", "—"),
    "L": ("comprimento do duto", "km"), "custo": ("custo do duto", "R$"),
    "Np": ("óleo + condensado produzidos (acumulado)", "m³"), "Gp": ("gás produzido (acumulado)", "m³"),
    "Wp": ("água produzida (acumulado)", "m³"), "Wi": ("água e outros líquidos injetados (acumulado)", "m³"),
    "Gi": ("gás injetado (acumulado)", "m³"), "gas_por_oe": ("gás por m³ de óleo equivalente", "m³/m³"),
    "Bo": ("fator volume-formação do óleo", "m³/m³"), "Bg": ("fator volume-formação do gás", "m³/m³"),
    "Rs": ("razão de solubilidade inicial", "m³/m³"), "Bw": ("fator volume-formação da água", "m³/m³"),
    "Gl": ("gás livre produzido (fora o dissolvido no óleo)", "m³"),
    "oe": ("espaço pelo método simples", "m³ oe"), "V": ("espaço poroso liberado", "m³ de reservatório"),
    "p_atm": ("pressão na superfície", "bar"), "grad_p": ("gradiente de pressão", "bar/m"),
    "prof": ("profundidade do reservatório", "m"), "t_sup": ("temperatura na superfície", "°C"),
    "grad_t": ("gradiente geotérmico", "°C/km"), "P": ("pressão do reservatório", "bar"),
    "T": ("temperatura do reservatório", "°C"), "rho": ("densidade do fluido no reservatório", "kg/m³"),
    "rho_padrao": ("densidade do fluido na condição padrão", "kg/m³"), "ef": ("eficiência de ocupação", "—"),
    "colchao": ("fração de gás de colchão", "—"), "m": ("massa que cabe no espaço poroso", "t"),
    "m_util": ("massa útil (descontado o colchão)", "t"), "pci_h2": ("PCI do H₂", "kWh/kg"),
    "capacidade": ("capacidade do método", "unidade do método"),
}


def _e(titulo, resultado, unidade, padrao, explicacao, alternativas=None):
    return {"titulo": titulo, "resultado": resultado, "unidade": unidade, "padrao": padrao,
            "explicacao": explicacao, "alternativas": alternativas or {}}


EQUACOES = {
    "custo_km": _e("Custo do duto por km", "custo_km", "R$/km", "custo_pol_km * 1000 * D * f_fluido",
                   "Custo de um gasoduto de gás natural por polegada de diâmetro e por km (projetos da EPE), vezes o "
                   "diâmetro e o fator do fluido. Linear no diâmetro: para dutos finos tende a subestimar.",
                   {"afim: parcela fixa + por polegada": "(custo_fixo_km + custo_pol_km * D) * 1000 * f_fluido",
                    "valor por km informado": "custo_fixo_km * 1000 * f_fluido"}),
    "comprimento": _e("Comprimento do duto", "L", "km", "dist * f_tracado",
                      "Distância em linha reta (geodésica) vezes o fator de traçado (1 = linha reta, como no PIBIC)."),
    "custo_duto": _e("Custo do duto", "custo", "R$", "L * custo_km", "Comprimento vezes o custo por km."),
    "espaco_simples": _e("Espaço — método simples (PIBIC)", "oe", "m³ oe", "Np + Gp / gas_por_oe",
                         "Volume produzido em m³ de óleo equivalente: óleo e condensado mais o gás convertido pela "
                         "convenção da ANP. Vale para todo campo com produção.",
                         {"só óleo e condensado": "Np",
                          "com a água líquida (produzida − injetada)": "Np + Gp / gas_por_oe + max(0, Wp - Wi)"}),
    "gas_livre": _e("Gás livre produzido", "Gl", "m³", "max(0, Gp - Np * Rs)",
                    "Gás produzido menos o que estava dissolvido no óleo (Np·Rs): é o gás que ocupava poros como "
                    "gás livre. Sem Rs, todo o gás conta como livre."),
    "espaco_poroso": _e("Espaço poroso liberado (voidage)", "V", "m³ de reservatório",
                        "Np * Bo + Gl * Bg + (Wp - Wi) * Bw - Gi * Bg",
                        "Volume que a produção liberou no reservatório, em condições de reservatório (método baseado "
                        "na produção, Bachu et al., CSLF 2007). Não considera influxo de aquífero.",
                        {"sem água e injeção": "Np * Bo + Gl * Bg"}),
    "pressao": _e("Pressão do reservatório", "P", "bar", "p_atm + grad_p * prof",
                  "Pressão hidrostática inicial na profundidade do reservatório: a pressão a que o reservatório "
                  "volta com a injeção."),
    "temperatura": _e("Temperatura do reservatório", "T", "°C", "t_sup + grad_t * prof / 1000",
                      "Temperatura na superfície mais o gradiente geotérmico."),
    "massa": _e("Massa que cabe no espaço poroso", "m", "t", "V * rho * ef / 1000",
                "Espaço poroso vezes a densidade do fluido nas condições do reservatório e a eficiência de ocupação."),
    "massa_util": _e("Massa útil", "m_util", "t", "m * (1 - colchao)",
                     "Para gás armazenado (H₂, CH₄), parte fica no reservatório como gás de colchão para manter a "
                     "pressão. CO₂ é armazenamento permanente: colchão = 0."),
    "volume_padrao": _e("Volume na condição padrão", "Vp", "m³", "m_util * 1000 / rho_padrao",
                        "A massa útil expressa em volume a 20 °C e 1 atm."),
    "energia": _e("Energia útil (H₂)", "E", "MWh", "m_util * pci_h2",
                  "Massa útil (t) vezes o PCI (kWh/kg): t × kWh/kg = MWh."),
    "indicador": _e("Indicador: custo ÷ capacidade", "ind", "R$ por unidade de capacidade", "custo / capacidade",
                    "O indicador do PIBIC: investimento no duto por unidade de espaço. Menor = mais viável."),
}
SIMBOLOS.update({"Vp": ("volume útil na condição padrão", "m³"), "E": ("energia útil", "MWh"),
                 "ind": ("indicador", "R$ por unidade"),
                 "Tc": ("temperatura crítica do fluido", "K"), "Pc": ("pressão crítica do fluido", "bar"),
                 "w": ("fator acêntrico ω do fluido", "—"), "M": ("massa molar do fluido", "g/mol"),
                 "Z_RA": ("Z de Rackett do fluido (Peneloux)", "—"),
                 "API": ("grau API do óleo", "°API"), "gg": ("densidade relativa do gás (ar = 1)", "—"),
                 "go": ("densidade relativa do óleo (água = 1)", "—"), "Ppsia": ("pressão do reservatório", "psia"),
                 "TF": ("temperatura do reservatório", "°F"), "Rs_scf": ("razão de solubilidade", "scf/STB"),
                 "Tpc": ("temperatura pseudocrítica do gás", "K"), "Ppc": ("pressão pseudocrítica do gás", "bar"),
                 "Tpr": ("temperatura pseudorreduzida do gás", "—"), "Ppr": ("pressão pseudorreduzida do gás", "—"),
                 "Zg": ("fator de compressibilidade do gás do reservatório", "—"),
                 "p_padrao": ("pressão da condição padrão", "bar"), "t_padrao": ("temperatura da condição padrão", "°C")})

_ST = "Standing (1947), correlação para óleos da Califórnia; faixa original: 16,5–63,8 °API, 100–258 °F. "
EQUACOES.update({
    "p_psia": _e("Pressão em psia", "Ppsia", "psia", "P * 14.5038", "Conversão de bar para psia (as correlações "
                 "são em unidades de campo)."),
    "t_f": _e("Temperatura em °F", "TF", "°F", "T * 1.8 + 32", "Conversão de °C para °F."),
    "go": _e("Densidade relativa do óleo", "go", "—", "141.5 / (131.5 + API)", "Definição do grau API."),
    "rs_scf": _e("Razão de solubilidade (Standing)", "Rs_scf", "scf/STB",
                 "gg * ((Ppsia / 18.2 + 1.4) * 10 ^ (0.0125 * API - 0.00091 * TF)) ^ 1.2048",
                 _ST + "Supõe o óleo saturado na pressão inicial do reservatório (Rs na pressão de bolha = P)."),
    "rs": _e("Razão de solubilidade em m³/m³", "Rs", "m³/m³", "Rs_scf * 0.178108",
             "1 scf/STB = 0,178108 m³/m³."),
    "bo": _e("Fator volume-formação do óleo (Standing)", "Bo", "m³/m³",
             "0.9759 + 0.00012 * (Rs_scf * (gg / go) ^ 0.5 + 1.25 * TF) ^ 1.2", _ST + "Bo na pressão de bolha."),
    "tpc": _e("Temperatura pseudocrítica do gás (Sutton)", "Tpc", "K", "(169.2 + 349.5 * gg - 74 * gg ^ 2) / 1.8",
              "Sutton (1985), gás natural pela densidade relativa; a fórmula original dá °R (÷ 1,8 → K)."),
    "ppc": _e("Pressão pseudocrítica do gás (Sutton)", "Ppc", "bar", "(756.8 - 131 * gg - 3.6 * gg ^ 2) / 14.5038",
              "Sutton (1985); a fórmula original dá psia (÷ 14,5038 → bar)."),
    "tpr": _e("Temperatura pseudorreduzida", "Tpr", "—", "(T + 273.15) / Tpc", "Temperatura absoluta ÷ pseudocrítica."),
    "ppr": _e("Pressão pseudorreduzida", "Ppr", "—", "P / Ppc", "Pressão ÷ pseudocrítica."),
    "z_gas": _e("Fator de compressibilidade do gás (Papay)", "Zg", "—",
                "1 - 3.52 * Ppr / 10 ^ (0.9813 * Tpr) + 0.274 * Ppr ^ 2 / 10 ^ (0.8157 * Tpr)",
                "Papay (1968): forma explícita do gráfico de Standing-Katz; boa para Tpr entre 1,2 e 3 e Ppr até ~8."),
    "bg": _e("Fator volume-formação do gás", "Bg", "m³/m³", "Zg * (T + 273.15) / P * p_padrao / (t_padrao + 273.15)",
             "Volume no reservatório ÷ volume na condição padrão: Bg = Z·T·Pp ÷ (P·Tp)."),
})

# ====================================================================== leitor seguro de fórmulas
_FUNCOES = {"min": min, "max": max, "abs": abs, "sqrt": math.sqrt, "exp": math.exp, "ln": math.log,
            "log10": math.log10}
_OPS = {ast.Add: lambda a, b: a + b, ast.Sub: lambda a, b: a - b, ast.Mult: lambda a, b: a * b,
        ast.Div: lambda a, b: a / b, ast.Pow: lambda a, b: a ** b}


class ErroEconomia(ValueError):
    pass


def compilar(expr: str, titulo: str = "fórmula") -> ast.Expression:
    """Lê a fórmula e recusa tudo que não seja número, variável, + − × ÷ ^ e as funções permitidas."""
    texto = (expr or "").strip().replace("^", "**").replace("×", "*").replace("÷", "/").replace("−", "-")
    if not texto:
        raise ErroEconomia(f"{titulo}: fórmula vazia.")
    if len(texto) > 500:
        raise ErroEconomia(f"{titulo}: fórmula longa demais.")
    try:
        arvore = ast.parse(texto, mode="eval")
    except SyntaxError:
        raise ErroEconomia(f"{titulo}: fórmula com erro de escrita: {expr}") from None
    for no in ast.walk(arvore):
        if isinstance(no, (ast.Expression, ast.Load, ast.operator, ast.unaryop)):
            if isinstance(no, ast.operator) and type(no) not in _OPS:
                raise ErroEconomia(f"{titulo}: operador não permitido em {expr} (use + − * / ^).")
            if isinstance(no, ast.unaryop) and not isinstance(no, (ast.USub, ast.UAdd)):
                raise ErroEconomia(f"{titulo}: operador não permitido em {expr}.")
            continue
        if isinstance(no, ast.BinOp) or isinstance(no, ast.UnaryOp) or isinstance(no, ast.Name):
            continue
        if isinstance(no, ast.Constant) and isinstance(no.value, (int, float)) and not isinstance(no.value, bool):
            continue
        if isinstance(no, ast.Call) and isinstance(no.func, ast.Name) and no.func.id in _FUNCOES and not no.keywords:
            continue
        raise ErroEconomia(f"{titulo}: só números, variáveis, + − * / ^ e {', '.join(_FUNCOES)}: {expr}")
    return arvore


def nomes(arvore: ast.Expression) -> set[str]:
    funcs = {n.func.id for n in ast.walk(arvore) if isinstance(n, ast.Call)}
    return {n.id for n in ast.walk(arvore) if isinstance(n, ast.Name)} - (funcs & set(_FUNCOES))


def avaliar_formula(arvore: ast.Expression, valores: dict) -> float:
    def ev(no):
        if isinstance(no, ast.Expression):
            return ev(no.body)
        if isinstance(no, ast.Constant):
            return float(no.value)
        if isinstance(no, ast.Name):
            return float(valores[no.id])
        if isinstance(no, ast.UnaryOp):
            v = ev(no.operand)
            return -v if isinstance(no.op, ast.USub) else v
        if isinstance(no, ast.BinOp):
            return _OPS[type(no.op)](ev(no.left), ev(no.right))
        if isinstance(no, ast.Call):
            return float(_FUNCOES[no.func.id](*[ev(a) for a in no.args]))
        raise ErroEconomia("fórmula inválida")
    v = ev(arvore)
    if isinstance(v, complex) or not math.isfinite(v):
        raise ValueError("resultado não é um número finito")
    return v


def fmt(v) -> str:
    """Número para a memória: até 6 algarismos significativos, vírgula decimal."""
    if v is None:
        return "—"
    if isinstance(v, str):
        return v
    v = float(v)
    if v == 0:
        return "0"
    a = abs(v)
    if 1e-3 <= a < 1e12:
        casas = max(0, 5 - int(math.floor(math.log10(a))))
        t = f"{v:,.{casas}f}"
        if "." in t:
            t = t.rstrip("0").rstrip(".")
        return t.replace(",", "§").replace(".", ",").replace("§", ".")
    m, e = f"{v:.5e}".split("e")
    return f"{m.rstrip('0').rstrip('.').replace('.', ',')}×10^{int(e)}"


def substituir(expr: str, valores: dict) -> str:
    """A fórmula com cada variável trocada pelo seu valor (os parênteses do usuário ficam)."""
    def troca(m):
        nome = m.group(1)
        if nome in _FUNCOES or nome not in valores:
            return nome
        v = valores[nome]
        t = fmt(v)
        return f"({t})" if isinstance(v, (int, float)) and v < 0 else t
    return re.sub(r"(?<![\w.])([A-Za-z_]\w*)\b(?!\s*\()", troca, expr)


# ====================================================================== memória de cálculo
class Falta(Exception):
    """Um dado necessário não existe (o método fica sem valor, com a lista do que falta)."""


class Memoria:
    """Registro de tudo que entrou e de cada passo: é o que torna o cálculo auditável."""

    def __init__(self, equacoes: dict):
        self.equacoes = equacoes            # id → fórmula escolhida
        self.valores: dict = {}
        self.entradas: list[dict] = []
        self.passos: list[dict] = []

    def entrada(self, simb: str, valor, fonte: str, grupo: str = "", unidade: str | None = None):
        desc, un = SIMBOLOS.get(simb, (simb, ""))
        self.valores[simb] = valor
        self.entradas.append({"simbolo": simb, "descricao": desc, "valor": valor, "unidade": unidade or un,
                              "fonte": fonte, "grupo": grupo})

    def calcular(self, eq: str, metodo: str, local: dict | None = None, guardar: bool = True,
                 destino: list | None = None) -> float:
        info = EQUACOES[eq]
        expr = self.equacoes.get(eq) or info["padrao"]
        arvore = compilar(expr, info["titulo"])
        valores = {**self.valores, **(local or {})}
        desconhecidas = sorted(n for n in nomes(arvore) if n not in valores)
        if desconhecidas:
            raise ErroEconomia(f"Equação «{info['titulo']}»: variável desconhecida {', '.join(desconhecidas)}. "
                               f"Disponíveis aqui: {', '.join(sorted(k for k, v in valores.items() if v is not None))}.")
        vazias = sorted((n for n in nomes(arvore) if valores[n] is None), key=lambda n: _posicao(expr, n))
        if vazias:
            raise Falta(vazias)
        try:
            v = avaliar_formula(arvore, valores)
        except ZeroDivisionError:
            raise ErroEconomia(f"Equação «{info['titulo']}»: divisão por zero ({substituir(expr, valores)}).") from None
        except (ValueError, OverflowError) as e:
            raise ErroEconomia(f"Equação «{info['titulo']}»: {e} ({substituir(expr, valores)}).") from None
        usados = sorted(nomes(arvore), key=lambda n: _posicao(expr, n))
        alternativa = next((k for k, f in info["alternativas"].items() if _norm(f) == _norm(expr)), None)
        alterada = _norm(expr) != _norm(info["padrao"])
        passo = {"id": eq, "metodo": metodo, "titulo": info["titulo"], "explicacao": info["explicacao"],
                 "resultado_simbolo": info["resultado"], "equacao": expr, "padrao": info["padrao"],
                 "alterada": alterada, "alternativa": alternativa,
                 "personalizada": alterada and alternativa is None,
                 "variaveis": [{"simbolo": n, "valor": valores[n], "descricao": SIMBOLOS.get(n, (n, ""))[0],
                                "unidade": SIMBOLOS.get(n, ("", ""))[1]} for n in usados],
                 "substituida": substituir(expr, valores), "resultado": v, "unidade": info["unidade"]}
        (destino if destino is not None else self.passos).append(passo)
        if guardar:
            self.valores[info["resultado"]] = v
        return v

    def nota(self, titulo: str, metodo: str, texto: str, detalhes: list | None = None, resultado=None,
             unidade: str = ""):
        """Passo que não é uma fórmula editável (ex.: a equação de estado), com o detalhe intermediário."""
        self.passos.append({"id": "nota", "metodo": metodo, "titulo": titulo, "explicacao": texto,
                            "detalhes": detalhes or [], "resultado": resultado, "unidade": unidade, "alterada": False})


def _posicao(expr: str, nome: str) -> int:
    m = re.search(rf"(?<![\w.]){re.escape(nome)}\b", expr)
    return m.start() if m else len(expr)


def _norm(expr: str) -> str:
    return re.sub(r"\s+", "", (expr or "").replace("^", "**"))


# ====================================================================== parâmetros
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


def parametros(dados: dict | None) -> dict:
    """Os parâmetros do usuário sobre os padrões, conferidos (inclusive constantes e equações)."""
    dados = dados or {}
    p = dict(PADROES)
    for k, v in dados.items():
        if k not in PADROES:
            continue
        if k in ("fonte_custo", "fluido", "estimar_pvt"):
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
    if p["estimar_pvt"] not in ("sim", "nao"):
        raise ErroEconomia("Estimar Bo, Rs e Bg: use sim ou nao.")
    fonte = next((f for f in FONTES_CUSTO if f["id"] == p["fonte_custo"]), None)
    if fonte is None and p["fonte_custo"] != "manual":
        raise ErroEconomia(f"Referência de custo desconhecida: {p['fonte_custo']}.")
    if fonte is not None:            # custo não informado → o da referência; informado e diferente → manual
        if _num(dados.get("custo_mil_pol_km")) is None:
            p["custo_mil_pol_km"] = float(fonte["r_mil_pol_km"])
        elif abs(p["custo_mil_pol_km"] - fonte["r_mil_pol_km"]) > 1e-9:
            p["fonte_custo"] = "manual"
    # constantes
    const = {}
    for k, v in (dados.get("constantes") or {}).items():
        if k not in CONSTANTES:
            raise ErroEconomia(f"Constante desconhecida: {k}.")
        x = _num(v)
        if x is None:
            continue
        lo, hi = CONSTANTES[k]["faixa"]
        if not lo <= x <= hi:
            raise ErroEconomia(f"{CONSTANTES[k]['rotulo']}: {x:g} fora do intervalo aceito ({lo:g} a {hi:g}).")
        if abs(x - CONSTANTES[k]["valor"]) > 1e-12:
            const[k] = x
    p["constantes"] = const
    # equações: só as diferentes do padrão; conferidas (escrita e variáveis)
    eqs = {}
    for k, v in (dados.get("equacoes") or {}).items():
        if k not in EQUACOES:
            raise ErroEconomia(f"Equação desconhecida: {k}.")
        texto = str(v or "").strip()
        if not texto or _norm(texto) == _norm(EQUACOES[k]["padrao"]):
            continue
        arv = compilar(texto, EQUACOES[k]["titulo"])
        estranhas = sorted(n for n in nomes(arv) if n not in SIMBOLOS)
        if estranhas:
            raise ErroEconomia(f"Equação «{EQUACOES[k]['titulo']}»: variável desconhecida {', '.join(estranhas)}.")
        if EQUACOES[k]["resultado"] in nomes(arv):
            raise ErroEconomia(f"Equação «{EQUACOES[k]['titulo']}»: o resultado não pode aparecer na própria fórmula.")
        eqs[k] = texto
    p["equacoes"] = eqs
    return p


def constante(p: dict, k: str) -> float:
    return p["constantes"].get(k, CONSTANTES[k]["valor"])


def _fonte_const(p: dict, k: str) -> str:
    c = CONSTANTES[k]
    if k in p["constantes"]:
        return f"alterada pelo usuário (padrão {fmt(c['valor'])} — {c['fonte']})"
    return f"padrão — {c['fonte']}"

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



# ====================================================================== densidade (Peng-Robinson)
R = 8.314462618                     # J/(mol·K)


def densidade(fluido: str, pressao_bar: float, temperatura_c: float, p: dict | None = None,
              detalhes: list | None = None) -> float:
    """kg/m³ por Peng-Robinson (1976) com translação de volume de Peneloux (1982). Contra as
    equações de referência (NIST/CoolProp): CO₂ dentro de ~7% (o pior perto do ponto crítico),
    H₂ e CH₄ dentro de ~5%, entre 60 e 300 bar. As propriedades críticas vêm das constantes
    (editáveis); `detalhes` recebe cada valor intermediário, para a memória de cálculo."""
    p = p or {"constantes": {}}
    tc, pc = constante(p, f"{fluido}_tc"), constante(p, f"{fluido}_pc") * 1e5
    w, M, zra = constante(p, f"{fluido}_w"), constante(p, f"{fluido}_m") / 1000, constante(p, f"{fluido}_zra")
    T, P = temperatura_c + 273.15, pressao_bar * 1e5
    k = 0.37464 + 1.54226 * w - 0.26992 * w ** 2
    alfa = (1 + k * (1 - math.sqrt(T / tc))) ** 2
    a = 0.45724 * R ** 2 * tc ** 2 / pc * alfa
    b = 0.07780 * R * tc / pc
    A, B = a * P / (R * T) ** 2, b * P / (R * T)
    coef = [1.0, -(1 - B), A - 3 * B * B - 2 * B, -(A * B - B * B - B ** 3)]
    raizes = np.roots(coef)
    reais = [float(z.real) for z in raizes if abs(z.imag) < 1e-9 and z.real > B]
    s2 = math.sqrt(2)

    def g(Z):                        # energia de Gibbs residual (ln φ): fica a raiz estável
        return Z - 1 - math.log(Z - B) - A / (2 * s2 * B) * math.log((Z + (1 + s2) * B) / (Z + (1 - s2) * B))
    Z = min(reais, key=g)
    c = 0.40768 * (0.29441 - zra) * R * tc / pc
    v = Z * R * T / P - c
    rho = M / v
    if detalhes is not None:
        detalhes += [
            ("T (K)", "T + 273,15", T), ("Tr", "T / Tc", T / tc),
            ("κ", "0,37464 + 1,54226·ω − 0,26992·ω²", k), ("α", "[1 + κ·(1 − √Tr)]²", alfa),
            ("a (Pa·m⁶/mol²)", "0,45724·R²·Tc²/Pc·α", a), ("b (m³/mol)", "0,07780·R·Tc/Pc", b),
            ("A", "a·P/(R·T)²", A), ("B", "b·P/(R·T)", B),
            ("raízes reais de Z", "Z³ − (1−B)Z² + (A−3B²−2B)Z − (AB−B²−B³) = 0", ", ".join(fmt(z) for z in reais)),
            ("Z", "raiz de menor energia de Gibbs", Z),
            ("c (m³/mol)", "0,40768·(0,29441 − Z_RA)·R·Tc/Pc (Peneloux)", c),
            ("v (m³/mol)", "Z·R·T/P − c", v), ("ρ (kg/m³)", "M / v", rho)]
    return float(rho)


def profundidade_campo(banco: Banco, campo: str) -> float | None:
    """Mediana da profundidade vertical final dos poços do campo no cadastro."""
    alvo = mpr.chave_campo(campo)
    with banco.conexao() as c:
        rows = c.execute("SELECT campo, prof_vertical, prof_sondador FROM pocos WHERE campo IS NOT NULL").fetchall()
    profs = [r["prof_vertical"] or r["prof_sondador"] for r in rows if mpr.chave_campo(r["campo"] or "") == alvo]
    profs = [x for x in profs if x and x > 0]
    return float(median(profs)) if profs else None


def _arquivos_producao(banco: Banco, campo: str) -> list[str]:
    with banco.conexao() as c:
        return [r[0] for r in c.execute("SELECT DISTINCT arquivo FROM producao_poco WHERE campo = ? ORDER BY arquivo",
                                        (mpr.chave_campo(campo),)) if r[0]]


# ====================================================================== avaliação
ROTULO_FALTA = {"Bo": "Bo", "Bg": "Bg", "prof": "profundidade ou P e T", "V": "espaço poroso"}
ROTULO_FALTA_EST = {"Bo": "Bo (ou o grau API, para estimar)", "Bg": "Bg (ou profundidade ou P e T, para estimar)"}


def _informado(p: dict, k: str) -> str:
    return "informado pelo usuário" if p.get(k) != PADROES.get(k) else "padrão do SIAPP"


def _custo_por_km(mem: "Memoria", p: dict):
    """Entradas e passo do custo do duto por km (comum ao campo e às áreas em lote)."""
    fl = p["fluido"]
    ref = next((f for f in FONTES_CUSTO if f["id"] == p["fonte_custo"]), None)
    G = "Custo do duto"
    mem.entrada("custo_pol_km", p["custo_mil_pol_km"],
                f"{ref['rotulo']}, data-base {ref['data_base']}" if ref else "informado pelo usuário", G)
    mem.entrada("custo_fixo_km", p["custo_fixo_km"], _informado(p, "custo_fixo_km"), G)
    mem.entrada("D", p["diametro_pol"], _informado(p, "diametro_pol"), G)
    mem.entrada("f_fluido", constante(p, f"f_{fl}"), f"constante f_{fl}: " + _fonte_const(p, f"f_{fl}"), G)
    mem.entrada("f_tracado", p["fator_tracado"], _informado(p, "fator_tracado"), G)
    return mem.calcular("custo_km", "custo"), ref


def _resumo_custo(p: dict, custo_km: float, ref) -> dict:
    fl = p["fluido"]
    return {"r_por_km": custo_km, "fator_fluido": constante(p, f"f_{fl}"),
            "motivo_fator": CONSTANTES[f"f_{fl}"]["fonte"], "r_mil_pol_km": p["custo_mil_pol_km"],
            "diametro_pol": p["diametro_pol"], "referencia": ref["rotulo"] if ref else "informado pelo usuário",
            "data_base": ref["data_base"] if ref else None}


def custos_duto(dados: dict | None, distancias_km: list) -> dict:
    """Custo do duto para uma lista de distâncias (áreas em lote), com a memória do custo por km."""
    p = parametros(dados)
    mem = Memoria(p["equacoes"])
    custo_km, ref = _custo_por_km(mem, p)
    linhas = []
    for d in distancias_km:
        if d is None:
            linhas.append((None, None))
            continue
        lixo: list = []
        L = mem.calcular("comprimento", "linha", {"dist": d}, guardar=False, destino=lixo)
        c = mem.calcular("custo_duto", "linha", {"dist": d, "L": L}, guardar=False, destino=lixo)
        linhas.append((L, c))
    return {"parametros": p, "custo": _resumo_custo(p, custo_km, ref), "linhas": linhas,
            "memoria": {"entradas": mem.entradas, "passos": mem.passos},
            "formulas": {k: f"{EQUACOES[k]['resultado']} = {p['equacoes'].get(k) or EQUACOES[k]['padrao']}"
                         for k in ("custo_km", "comprimento", "custo_duto")}}


def avaliar(banco: Banco, campo: str, distancias: list[dict], dados: dict | None,
            sugeridos: dict | None = None) -> dict:
    """Custo do duto até cada infraestrutura medida e o indicador (R$ ÷ capacidade) em cada
    método, com a memória de cálculo completa. `sugeridos`: API e densidade do gás achados nos
    documentos dos poços ({"api": {"valor", "fonte", "origem"}, "densidade_gas": {...}}), usados
    quando o usuário não informa."""
    from . import __version__
    p = parametros(dados)
    fl = p["fluido"]
    mem = Memoria(p["equacoes"])
    avisos: list[str] = []
    # ------------------------------------------------ custo do duto
    custo_km, ref = _custo_por_km(mem, p)
    # ------------------------------------------------ produção acumulada
    ac = acumulados(banco, campo)
    avisos += ac["avisos"]
    G = "Produção acumulada"
    mem.entrada("Np", ac["np"] or 0.0, ac["fonte"], G)
    mem.entrada("Gp", ac["gp"] or 0.0, ac["fonte"], G)
    for s, k in (("Wp", "wp"), ("Wi", "wi"), ("Gi", "gi")):
        if ac[k] is None:
            mem.entrada(s, 0.0, "indisponível (a série mensal não cobre todo o histórico) — usado 0", G)
        else:
            mem.entrada(s, ac[k], ac["fonte"], G)
    mem.entrada("gas_por_oe", constante(p, "gas_por_oe"), _fonte_const(p, "gas_por_oe"), "Constantes")
    metodos: dict = {}
    # ------------------------------------------------ 1. simples
    try:
        oe = mem.calcular("espaco_simples", "simples")
        metodos["simples"] = {"valor": oe}
    except Falta as f:
        metodos["simples"] = {"valor": None, "falta": [ROTULO_FALTA.get(n, n) for n in f.args[0]]}
    metodos["simples"].update(metodo="simples", rotulo="Simples (PIBIC): volume produzido", unidade="m³ de óleo equivalente",
                              formula=p["equacoes"].get("espaco_simples") or EQUACOES["espaco_simples"]["padrao"])
    # ------------------------------------------------ condições do reservatório (molécula e correlações)
    G = "Condições do reservatório"
    cond: dict = {}
    falta_pt: list[str] = []
    precisa_prof = p["pressao_bar"] is None or p["temperatura_c"] is None
    if precisa_prof:
        if p["profundidade_m"] is not None:
            prof, origem = p["profundidade_m"], "informada pelo usuário"
        else:
            prof = profundidade_campo(banco, campo)
            origem = ("mediana da profundidade vertical final dos poços do campo (cadastro)" if prof is not None
                      else "não informada e sem poços do campo com profundidade no cadastro")
        mem.entrada("prof", prof, origem, G)
        cond.update(profundidade_m=prof, origem_profundidade=origem if prof is not None else None)
    for simb, chave_p, eq, rot, extras in (
            ("P", "pressao_bar", "pressao", "pressao_bar",
             (("p_atm", constante(p, "p_atm"), _fonte_const(p, "p_atm")),
              ("grad_p", p["gradiente_p_bar_m"], _informado(p, "gradiente_p_bar_m")))),
            ("T", "temperatura_c", "temperatura", "temperatura_c",
             (("t_sup", p["t_superficie_c"], _informado(p, "t_superficie_c")),
              ("grad_t", p["gradiente_t_c_km"], _informado(p, "gradiente_t_c_km"))))):
        if p[chave_p] is not None:
            mem.entrada(simb, p[chave_p], "informada pelo usuário", G)
            cond[rot] = p[chave_p]
            cond["origem_" + ("pressao" if simb == "P" else "temperatura")] = "informada"
            continue
        for s, v, fonte in extras:
            mem.entrada(s, v, fonte, G)
        try:
            cond[rot] = mem.calcular(eq, "condicoes")
            cond["origem_" + ("pressao" if simb == "P" else "temperatura")] = \
                ("hidrostática pela profundidade" if simb == "P" else "gradiente geotérmico pela profundidade")
        except Falta:
            mem.valores[simb] = None
            if "profundidade ou P e T" not in falta_pt:
                falta_pt.append("profundidade ou P e T")
    # ------------------------------------------------ 2. espaço poroso (Bo, Rs, Bg informados ou estimados)
    G = "Dados do reservatório"
    np_, gp, gi = mem.valores["Np"], mem.valores["Gp"], mem.valores["Gi"]
    estimar = p["estimar_pvt"] == "sim"
    tem_pt = mem.valores.get("P") is not None and mem.valores.get("T") is not None
    precisa = {"Bo": p["bo"] is None and np_ > 0, "Rs": p["rs"] is None and np_ > 0 and gp > 0,
               "Bg": p["bg"] is None and (gp > 0 or gi > 0)}
    estimados: list[str] = []
    rotulos_falta = ROTULO_FALTA_EST if estimar else ROTULO_FALTA
    sug = sugeridos or {}
    if p["api"] is not None:
        api_v, api_f = p["api"], "informado pelo usuário"
    elif sug.get("api"):
        api_v, api_f = sug["api"]["valor"], sug["api"]["fonte"]
    else:
        api_v, api_f = None, "não informado (nem transcrito, nem lido nos documentos dos poços do campo)"
    if p["densidade_gas"] is not None:
        gg_v, gg_f = p["densidade_gas"], "informada pelo usuário"
    elif sug.get("densidade_gas"):
        gg_v, gg_f = sug["densidade_gas"]["valor"], sug["densidade_gas"]["fonte"]
    else:
        gg_v, gg_f = constante(p, "gg_padrao"), "constante gg_padrao: " + _fonte_const(p, "gg_padrao")
    if estimar and tem_pt and any(precisa.values()):
        GF = "Dados dos fluidos (para as correlações)"
        mem.entrada("gg", gg_v, gg_f, GF)
        mem.entrada("API", api_v, api_f, GF)
        mem.calcular("p_psia", "pvt")
        mem.calcular("t_f", "pvt")
        for g, rot in (("api", "grau API"), ("densidade_gas", "densidade do gás")):
            usado = (p["api"] is None) if g == "api" else (p["densidade_gas"] is None)
            if usado and sug.get(g, {}).get("origem") == "leitura":
                avisos.append(f"O {rot} veio de leitura automática dos documentos dos poços (o OCR pode errar "
                              "números): confira as páginas e confirme ou descarte cada leitura.")
    tem_api = estimar and tem_pt and api_v is not None
    # análise PVT de laboratório de um poço do campo (0.39): vale antes das correlações
    pvt_med = sug.get("pvt")
    p_res = mem.valores.get("P")

    def do_pvt(chave: str):
        if not pvt_med or not pvt_med.get("tabela"):
            return None, ""
        tab = pvt_med["tabela"]
        sat = pvt_med.get("saturacao") or {}
        if p_res is None:
            if chave == "bg":
                return None, ""
            v, onde = sat.get(chave), f"na pressão de saturação ({fmt(sat.get('p_bar'))} bar)"
        else:
            pk = p_res / mpvt.KGF_BAR
            faixa = [r["p_kgf_cm2"] for r in tab if r.get(chave) is not None]
            if chave == "bg" and (not faixa or pk > max(faixa) or pk < min(faixa)):
                return None, ""            # acima da saturação não há gás livre medido: fica a correlação
            v, onde = mpvt.interpolar(tab, chave, pk), f"interpolado a {fmt(p_res)} bar"
        if v is None:
            return None, ""
        return v, f"medido: {pvt_med['fonte']}, {onde}"
    # Rs
    rs_pvt, rs_f = do_pvt("rs")
    if p["rs"] is not None:
        mem.entrada("Rs", p["rs"], "informado pelo usuário", G)
    elif precisa["Rs"] and rs_pvt is not None:
        mem.entrada("Rs", rs_pvt, rs_f, G)
    elif precisa["Rs"] and tem_api:
        mem.calcular("rs_scf", "pvt")
        mem.calcular("rs", "pvt")
        estimados.append("Rs (Standing)")
    else:
        mem.entrada("Rs", 0.0, "não informado — usado 0: todo o gás produzido conta como gás livre", G)
        if np_ > 0 and gp > 0:
            avisos.append("Sem Rs: todo o gás produzido conta como gás livre no reservatório (superestima num campo de "
                          "óleo). Informe a razão de solubilidade inicial ou o grau API para estimá-la.")
    # Bo
    bo_pvt, bo_f = do_pvt("bo")
    if p["bo"] is not None:
        mem.entrada("Bo", p["bo"], "informado pelo usuário", G)
    elif np_ == 0:
        mem.entrada("Bo", 0.0, "sem óleo produzido: não se aplica (0)", G)
    elif bo_pvt is not None:
        mem.entrada("Bo", bo_pvt, bo_f, G)
    elif tem_api:
        if "Rs_scf" not in mem.valores:
            mem.entrada("Rs_scf", mem.valores["Rs"] / 0.178108, "Rs (m³/m³) ÷ 0,178108", "Dados dos fluidos (para as correlações)")
        mem.calcular("go", "pvt")
        mem.calcular("bo", "pvt")
        estimados.append("Bo (Standing)")
    else:
        mem.entrada("Bo", None, "não informado" + (" (informe o grau API para estimar)" if estimar else ""), G)
    # Bg
    bg_pvt, bg_f = do_pvt("bg")
    if p["bg"] is not None:
        mem.entrada("Bg", p["bg"], "informado pelo usuário", G)
    elif not precisa["Bg"]:
        mem.entrada("Bg", 0.0, "sem gás produzido nem injetado: não se aplica (0)", G)
    elif bg_pvt is not None:
        mem.entrada("Bg", bg_pvt, bg_f, G)
    elif estimar and tem_pt:
        mem.entrada("p_padrao", constante(p, "p_padrao"), _fonte_const(p, "p_padrao"), "Constantes")
        mem.entrada("t_padrao", constante(p, "t_padrao"), _fonte_const(p, "t_padrao"), "Constantes")
        for eq in ("tpc", "ppc", "tpr", "ppr", "z_gas", "bg"):
            mem.calcular(eq, "pvt")
        estimados.append("Bg (Sutton + Papay)")
    else:
        mem.entrada("Bg", None, "não informado", G)
    if estimados:
        avisos.append("Estimados por correlação, nas condições do reservatório: " + ", ".join(estimados)
                      + ". Confira com dados do campo (análise PVT) quando houver.")
        v = mem.valores
        if "Bo (Standing)" in estimados or "Rs (Standing)" in estimados:
            if not 16.5 <= v["API"] <= 63.8 or not 100 <= v["TF"] <= 258:
                avisos.append(f"Standing fora da faixa original (16,5–63,8 °API e 100–258 °F): API {fmt(v['API'])}, "
                              f"{fmt(v['TF'])} °F.")
        if "Bg (Sutton + Papay)" in estimados and (not 1.2 <= v["Tpr"] <= 3 or v["Ppr"] > 8):
            avisos.append(f"Papay fora da faixa recomendada (Tpr 1,2–3; Ppr até 8): Tpr {fmt(v['Tpr'])}, Ppr {fmt(v['Ppr'])}.")
    mem.entrada("Bw", constante(p, "bw"), _fonte_const(p, "bw"), "Constantes")
    falta_poroso: list[str] = []
    try:
        mem.calcular("gas_livre", "poroso")
        V = mem.calcular("espaco_poroso", "poroso")
        if V <= 0:
            avisos.append("A injeção já repôs todo o volume produzido: não sobra espaço pelo método do espaço poroso.")
            mem.valores["V"] = 0.0
        metodos["poroso"] = {"valor": max(V, 0.0)}
        avisos.append("Espaço poroso sem influxo de aquífero (We): com aquífero ativo o espaço disponível é menor.")
    except Falta as f:
        falta_poroso = [rotulos_falta.get(n, ROTULO_FALTA.get(n, n)) for n in f.args[0]]
        metodos["poroso"] = {"valor": None, "falta": falta_poroso}
        mem.valores["V"] = None
    metodos["poroso"].update(metodo="poroso", rotulo="Espaço poroso liberado (voidage)", unidade="m³ de reservatório",
                             formula=p["equacoes"].get("espaco_poroso") or EQUACOES["espaco_poroso"]["padrao"],
                             estimados=estimados)
    G = "Fluido"
    mem.entrada("ef", p["eficiencia"], _informado(p, "eficiencia"), G)
    if FLUIDOS[fl]["armazenado"]:
        mem.entrada("colchao", p["colchao"], _informado(p, "colchao"), G)
    else:
        mem.entrada("colchao", 0.0, "CO₂: armazenamento permanente, sem gás de colchão", G)
    mol: dict = {"metodo": "molecula", "rotulo": f"Pela molécula ({FLUIDOS[fl]['rotulo']})", "fluido": fl,
                 "condicoes": cond, "formula": p["equacoes"].get("massa") or EQUACOES["massa"]["padrao"]}
    falta_mol = falta_poroso + falta_pt
    if falta_mol:
        mol.update(valor=None, falta=falta_mol)
    else:
        P, T = mem.valores["P"], mem.valores["T"]
        if p["densidade_kg_m3"] is not None:
            rho = p["densidade_kg_m3"]
            mem.entrada("rho", rho, "informada pelo usuário", G)
            metodo_rho = "informada"
        else:
            for simb, k in (("Tc", "tc"), ("Pc", "pc"), ("w", "w"), ("M", "m"), ("Z_RA", "zra")):
                mem.entrada(simb, constante(p, f"{fl}_{k}"), f"constante {fl}_{k}: " + _fonte_const(p, f"{fl}_{k}"),
                            "Constantes do fluido")
            det: list = []
            rho = densidade(fl, P, T, p, det)
            mem.nota(f"Densidade do {FLUIDOS[fl]['rotulo']} a {fmt(P)} bar e {fmt(T)} °C", "molecula",
                     "Equação de estado de Peng-Robinson (1976) com translação de volume de Peneloux (1982); "
                     "propriedades críticas nas constantes. R = 8,314462618 J/(mol·K).",
                     [{"grandeza": n, "expressao": e, "valor": v} for n, e, v in det], rho, "kg/m³")
            mem.valores["rho"] = rho
            metodo_rho = "Peng-Robinson + Peneloux"
        tp, pp = constante(p, "t_padrao"), constante(p, "p_padrao")
        rho_p = densidade(fl, pp, tp, p)
        mem.nota(f"Densidade na condição padrão ({fmt(pp)} bar, {fmt(tp)} °C)", "molecula",
                 "Mesma equação de estado na condição padrão da ANP.", [], rho_p, "kg/m³")
        mem.valores["rho_padrao"] = rho_p
        m = mem.calcular("massa", "molecula")
        mu = mem.calcular("massa_util", "molecula")
        vp = mem.calcular("volume_padrao", "molecula")
        mol.update(densidade_kg_m3=rho, densidade_metodo=metodo_rho, eficiencia=p["eficiencia"], massa_total_t=m)
        if FLUIDOS[fl]["armazenado"]:
            mol.update(valor=mu, unidade=f"t de {FLUIDOS[fl]['rotulo']} (gás útil)", colchao=p["colchao"],
                       volume_padrao_util_milhoes_m3=vp / 1e6)
            if fl == "h2":
                mem.entrada("pci_h2", constante(p, "pci_h2"), _fonte_const(p, "pci_h2"), "Constantes")
                mol["energia_util_mwh"] = mem.calcular("energia", "molecula")
        else:
            mol.update(valor=mu, unidade="t de CO₂", massa_mt=mu / 1e6, volume_padrao_milhoes_m3=vp / 1e6)
    metodos["molecula"] = mol
    # ------------------------------------------------ por infraestrutura
    linhas = []
    for d in distancias:
        if not d.get("baixada") or d.get("distancia_km") is None:
            continue
        passos: list = []
        local = {"dist": d["distancia_km"]}
        L = mem.calcular("comprimento", "linha", local, guardar=False, destino=passos)
        custo = mem.calcular("custo_duto", "linha", {**local, "L": L}, guardar=False, destino=passos)
        ind = {}
        for nome, mt in metodos.items():
            v = mt.get("valor")
            ind[nome] = (mem.calcular("indicador", nome, {**local, "L": L, "custo": custo, "capacidade": v},
                                      guardar=False, destino=passos) if v else None)
        extra = {}
        if mol.get("energia_util_mwh"):
            extra["r_por_mwh"] = mem.calcular("indicador", "molecula_mwh",
                                              {**local, "L": L, "custo": custo, "capacidade": mol["energia_util_mwh"]},
                                              guardar=False, destino=passos)
        feicao = "; ".join(f"{k}={v}" for k, v in (d.get("feicao") or {}).items())
        linhas.append({"id": d["id"], "rotulo": d["rotulo"], "distancia_km": d["distancia_km"],
                       "toca_o_campo": d.get("toca_o_campo", False), "comprimento_km": L, "custo_r": custo,
                       "indicadores": ind, **extra, "origem_tipica": d["id"] in ORIGENS.get(fl, set()),
                       "fonte_distancia": f"camada {d['rotulo']} ({d.get('fonte') or 'sig'}); feição mais próxima: "
                                          f"{feicao or '—'}; distância geodésica entre os pontos mais próximos",
                       "memoria": passos})
    if any(l["toca_o_campo"] for l in linhas):
        avisos.append("\"No campo\": a infraestrutura já cruza o polígono — o duto novo é só a ligação interna "
                      "(custo ≈ 0 neste modelo).")
    alteradas = [{"id": k, "titulo": EQUACOES[k]["titulo"], "equacao": v, "padrao": EQUACOES[k]["padrao"]}
                 for k, v in p["equacoes"].items()]
    if alteradas:
        avisos.insert(0, f"{len(alteradas)} equação(ões) diferente(s) do padrão: "
                         + ", ".join(a["titulo"] for a in alteradas) + ".")
    if p["constantes"]:
        avisos.insert(0, f"{len(p['constantes'])} constante(s) alterada(s): "
                         + ", ".join(CONSTANTES[k]["rotulo"] for k in p["constantes"]) + ".")
    ficha = mpr.campo_guardado(banco, campo) or {}
    meta = {"campo": campo, "quando": datetime.now().isoformat(timespec="seconds"), "versao_siapp": __version__,
            "fluido": FLUIDOS[fl]["rotulo"], "fonte_producao": ac["fonte"],
            "arquivos_producao": _arquivos_producao(banco, campo), "url_pd": (ficha.get("pd") or {}).get("url"),
            "equacoes_alteradas": alteradas,
            "constantes_alteradas": [{"id": k, "rotulo": CONSTANTES[k]["rotulo"], "valor": v,
                                      "padrao": CONSTANTES[k]["valor"]} for k, v in p["constantes"].items()]}
    return {"campo": campo, "parametros": p,
            "custo": _resumo_custo(p, custo_km, ref),
            "acumulados": {k: v for k, v in ac.items() if k != "avisos"}, "metodos": metodos, "linhas": linhas,
            "avisos": avisos,
            "unidades_indicador": {"simples": "R$/m³ oe", "poroso": "R$/m³ res", "molecula": "R$/t"},
            "memoria": {"meta": meta, "entradas": mem.entradas, "passos": mem.passos}}


# ====================================================================== saídas
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


def linhas_csv_memoria(av: dict) -> list[list]:
    """A memória de cálculo em linhas (para o Excel): entradas e passos."""
    out = [["# entradas"], ["símbolo", "descrição", "valor", "unidade", "fonte"]]
    for e in av["memoria"]["entradas"]:
        out.append([e["simbolo"], e["descricao"], e["valor"], e["unidade"], e["fonte"]])
    out += [[], ["# passos"], ["método", "passo", "equação", "com os valores", "resultado", "unidade", "alterada"]]
    for s in av["memoria"]["passos"]:
        if s["id"] == "nota":
            out.append([s["metodo"], s["titulo"], s["explicacao"], "", s.get("resultado"), s.get("unidade"), ""])
            for d in s.get("detalhes", []):
                out.append(["", "  " + d["grandeza"], d["expressao"], "", d["valor"], "", ""])
            continue
        out.append([s["metodo"], s["titulo"], f"{s['resultado_simbolo']} = {s['equacao']}", s["substituida"],
                    s["resultado"], s["unidade"], "sim" if s["alterada"] else ""])
    for l in av["linhas"]:
        for s in l["memoria"]:
            out.append([f"{l['rotulo']} · {s['metodo']}", s["titulo"], f"{s['resultado_simbolo']} = {s['equacao']}",
                        s["substituida"], s["resultado"], s["unidade"], "sim" if s["alterada"] else ""])
    return out


def _r(v):
    return None if v is None else round(v, 4)


_CSS = """body{font:14px/1.45 Georgia,serif;color:#1b1f23;max-width:1000px;margin:24px auto;padding:0 16px}
h1{font-size:22px;margin:0 0 4px}h2{font-size:17px;margin:26px 0 6px;border-bottom:1px solid #ccc}
h3{font-size:14.5px;margin:16px 0 2px}table{border-collapse:collapse;width:100%;font-size:12.5px;margin:6px 0}
th,td{border-bottom:1px solid #e3e3e3;padding:3px 6px;text-align:left;vertical-align:top}th{color:#555;font-weight:600}
td.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}code,.eq{font-family:Consolas,monospace;font-size:12.5px}
.eq{display:block;background:#f6f6f4;padding:4px 8px;margin:2px 0;border-left:3px solid #9aa}
.alt{border-left-color:#c0392b}.tag{font:600 11px sans-serif;color:#fff;background:#c0392b;padding:1px 5px;border-radius:3px}
.sub{color:#666;font-size:12.5px}.res{font-weight:700}ul{margin:4px 0}"""


def memoria_html(av: dict) -> str:
    """A memória de cálculo como página HTML independente (abre no navegador, imprime em PDF)."""
    e = html.escape
    m = av["memoria"]
    me = m["meta"]
    out = [f"<!doctype html><html lang='pt-BR'><meta charset='utf-8'><title>Memória de cálculo — {e(av['campo'])}</title>"
           f"<style>{_CSS}</style><body>",
           f"<h1>Memória de cálculo — viabilidade de injeção</h1>",
           f"<p class='sub'>Campo <b>{e(av['campo'])}</b> · fluido {e(me['fluido'])} · {e(me['quando'])} · "
           f"SIAPP {e(me['versao_siapp'])}</p>"]
    if av["avisos"]:
        out.append("<h2>Avisos</h2><ul>" + "".join(f"<li>{e(a)}</li>" for a in av["avisos"]) + "</ul>")
    out.append("<h2>Resultado</h2><table><tr><th>Método</th><th>Capacidade</th><th>Equação usada</th></tr>")
    for mt in av["metodos"].values():
        val = (f"{fmt(mt['valor'])} {e(mt.get('unidade') or '')}" if mt.get("valor") is not None
               else "falta: " + e(", ".join(mt.get("falta", []))))
        out.append(f"<tr><td>{e(mt['rotulo'])}</td><td class='n'>{val}</td><td><code>{e(mt.get('formula') or '')}</code></td></tr>")
    out.append("</table>")
    out.append("<table><tr><th>Até</th><th>Distância (km)</th><th>Duto (R$)</th><th>R$/m³ oe</th><th>R$/m³ res</th>"
               "<th>R$/t</th><th>R$/MWh</th></tr>")
    for l in av["linhas"]:
        i = l["indicadores"]
        out.append(f"<tr><td>{'★ ' if l['origem_tipica'] else ''}{e(l['rotulo'])}</td><td class='n'>{fmt(l['distancia_km'])}</td>"
                   f"<td class='n'>{fmt(l['custo_r'])}</td><td class='n'>{fmt(i.get('simples'))}</td>"
                   f"<td class='n'>{fmt(i.get('poroso'))}</td><td class='n'>{fmt(i.get('molecula'))}</td>"
                   f"<td class='n'>{fmt(l.get('r_por_mwh'))}</td></tr>")
    out.append("</table>")
    # entradas
    out.append("<h2>1. Dados de entrada e de onde vieram</h2>")
    grupos: dict = {}
    for x in m["entradas"]:
        grupos.setdefault(x["grupo"] or "Outros", []).append(x)
    for g, xs in grupos.items():
        out.append(f"<h3>{e(g)}</h3><table><tr><th>Símbolo</th><th>O que é</th><th>Valor</th><th>Unidade</th><th>Fonte</th></tr>")
        for x in xs:
            out.append(f"<tr><td><code>{e(x['simbolo'])}</code></td><td>{e(x['descricao'])}</td>"
                       f"<td class='n'>{fmt(x['valor'])}</td><td>{e(x['unidade'])}</td><td>{e(x['fonte'])}</td></tr>")
        out.append("</table>")
    if me.get("arquivos_producao") or me.get("url_pd"):
        out.append("<p class='sub'>Arquivos da ANP usados: " + e(", ".join(me.get("arquivos_producao") or ["—"]))
                   + (f" · sumário do PD: {e(me['url_pd'])}" if me.get("url_pd") else "") + "</p>")
    # passos
    out.append("<h2>2. Passo a passo</h2>")
    nomes_m = {"custo": "Custo do duto por km", "simples": "Método simples (PIBIC)", "poroso": "Espaço poroso",
               "molecula": "Pela molécula", "condicoes": "Condições do reservatório",
               "pvt": "Propriedades dos fluidos (correlações)"}
    atual = None
    for s in m["passos"]:
        if s["metodo"] != atual:
            atual = s["metodo"]
            out.append(f"<h3>{e(nomes_m.get(atual, atual))}</h3>")
        out.append(_passo_html(s))
    out.append("<h2>3. Por infraestrutura</h2>")
    for l in av["linhas"]:
        out.append(f"<h3>{e(l['rotulo'])}</h3><p class='sub'>{e(l['fonte_distancia'])}</p>")
        for s in l["memoria"]:
            out.append(_passo_html(s, curto=True))
    if me.get("equacoes_alteradas") or me.get("constantes_alteradas"):
        out.append("<h2>4. Diferenças em relação ao padrão</h2><ul>")
        for a in me.get("equacoes_alteradas", []):
            out.append(f"<li>{e(a['titulo'])}: <code>{e(a['equacao'])}</code> (padrão <code>{e(a['padrao'])}</code>)</li>")
        for a in me.get("constantes_alteradas", []):
            out.append(f"<li>{e(a['rotulo'])}: {fmt(a['valor'])} (padrão {fmt(a['padrao'])})</li>")
        out.append("</ul>")
    out.append("<p class='sub'>Triagem para comparar campos e rotas: pressão e injetividade só a simulação responde. "
               "Os mesmos dados estão no arquivo .json ao lado desta página.</p></body></html>")
    return "\n".join(out)


def _passo_html(s: dict, curto: bool = False) -> str:
    e = html.escape
    if s["id"] == "nota":
        det = "".join(f"<tr><td>{e(d['grandeza'])}</td><td><code>{e(d['expressao'])}</code></td>"
                      f"<td class='n'>{fmt(d['valor'])}</td></tr>" for d in s.get("detalhes", []))
        return (f"<p><b>{e(s['titulo'])}</b><br><span class='sub'>{e(s['explicacao'])}</span></p>"
                + (f"<table><tr><th>Grandeza</th><th>Expressão</th><th>Valor</th></tr>{det}</table>" if det else "")
                + f"<p class='res'>= {fmt(s.get('resultado'))} {e(s.get('unidade') or '')}</p>")
    tag = ""
    if s["alterada"]:
        tag = " <span class='tag'>" + ("alternativa: " + e(s["alternativa"]) if s["alternativa"] else "fórmula do usuário") \
              + "</span>"
    rot = {"simples": " (simples)", "poroso": " (espaço poroso)", "molecula": " (molécula)",
           "molecula_mwh": " (molécula, por MWh)"}.get(s["metodo"], "") if curto else ""
    expl = "" if curto else f"<br><span class='sub'>{e(s['explicacao'])}</span>"
    return (f"<p><b>{e(s['titulo'])}{rot}</b>{tag}{expl}"
            f"<span class='eq{' alt' if s['alterada'] else ''}'>{e(s['resultado_simbolo'])} = {e(s['equacao'])}</span>"
            f"<span class='eq'>{e(s['resultado_simbolo'])} = {e(s['substituida'])}</span>"
            f"<span class='res'>{e(s['resultado_simbolo'])} = {fmt(s['resultado'])} {e(s['unidade'])}</span></p>")


def salvar_memoria(pasta_projeto: str, av: dict) -> dict:
    """Grava a memória de cálculo (JSON completo + página HTML) em execucoes/viabilidade/."""
    pasta = os.path.join(pasta_projeto, "execucoes", "viabilidade")
    os.makedirs(pasta, exist_ok=True)
    carimbo = av["memoria"]["meta"]["quando"].replace(":", "").replace("-", "").replace("T", "-")
    base = f"{carimbo}_{mpr.chave_campo(av['campo']).replace(' ', '_').lower()}"
    cj, ch = os.path.join(pasta, base + ".json"), os.path.join(pasta, base + ".html")
    with open(cj, "w", encoding="utf-8") as f:
        json.dump(av, f, ensure_ascii=False, indent=1, default=float)
    with open(ch, "w", encoding="utf-8") as f:
        f.write(memoria_html(av))
    rel = lambda c: os.path.relpath(c, pasta_projeto).replace(os.sep, "/")  # noqa: E731
    return {"json": rel(cj), "html": rel(ch)}
