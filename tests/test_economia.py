"""Viabilidade econômica: custo do duto, capacidade de injeção nos três métodos, o indicador e a
memória de cálculo (constantes e equações editáveis)."""
import json
import os

import pytest

from motor import economia as mec
from motor import producao as mpr
from motor.banco import Banco

# densidades de referência (Span-Wagner, Leachman, Setzmann-Wagner — CoolProp/NIST), kg/m³
REFERENCIA = [("co2", 80, 35, 419.09, 0.03), ("co2", 100, 40, 628.61, 0.08), ("co2", 200, 60, 723.68, 0.03),
              ("co2", 300, 80, 745.60, 0.05), ("h2", 100, 40, 7.32, 0.04), ("h2", 300, 80, 17.72, 0.04),
              ("ch4", 100, 40, 69.97, 0.04), ("ch4", 200, 60, 129.17, 0.04)]


@pytest.mark.parametrize("fluido,p,t,ref,tol", REFERENCIA)
def test_densidade_peng_robinson(fluido, p, t, ref, tol):
    assert mec.densidade(fluido, p, t) == pytest.approx(ref, rel=tol)


def test_densidade_na_condicao_padrao_e_constantes_criticas():
    assert mec.densidade("h2", 1.01325, 20) == pytest.approx(0.08375, rel=2e-3)
    assert mec.densidade("co2", 1.01325, 20) == pytest.approx(1.8393, rel=2e-3)
    det = []
    rho = mec.densidade("co2", 100, 40, mec.parametros({}), det)
    assert det[-1][2] == pytest.approx(rho) and any(n == "Z" for n, _, _ in det)
    # trocar a massa molar muda a densidade na mesma proporção
    p = mec.parametros({"constantes": {"co2_m": 88.019}})
    assert mec.densidade("co2", 100, 40, p) == pytest.approx(2 * rho, rel=1e-9)


# ------------------------------------------------------------------ leitor de fórmulas
def test_formula_segura():
    a = mec.compilar("max(0, Gp - Np * Rs) + 2^3")
    assert mec.nomes(a) == {"Gp", "Np", "Rs"}
    assert mec.avaliar_formula(a, {"Gp": 10, "Np": 2, "Rs": 3}) == 4 + 8
    assert mec.avaliar_formula(mec.compilar("sqrt(x) + ln(exp(1)) - abs(-y)"), {"x": 9, "y": 2}) == 2
    for ruim in ("__import__('os')", "x.real", "(lambda: 1)()", "'a'", "x if y else z", "x < y", "[x]",
                 "open('f')", "x; y", "f(x=1)"):
        with pytest.raises(mec.ErroEconomia):
            mec.compilar(ruim)
    with pytest.raises(mec.ErroEconomia):
        mec.compilar("")


def test_substituir_e_formatar():
    assert mec.fmt(1651720.0) == "1.651.720" and mec.fmt(0.012) == "0,012" and mec.fmt(415.14058) == "415,141"
    assert mec.fmt(2.5e13) == "2,5×10^13"
    assert mec.substituir("Np + Gp / gas_por_oe", {"Np": 1e6, "Gp": 2e8, "gas_por_oe": 1000}) == \
        "1.000.000 + 200.000.000 / 1.000"
    assert mec.substituir("max(0, a - b)", {"a": -1, "b": 2}) == "max(0, (-1) - 2)"


# ------------------------------------------------------------------ parâmetros
def test_parametros_padrao_referencia_manual_constantes_e_equacoes():
    p = mec.parametros(None)
    assert p["fonte_custo"] == "pig2024" and p["custo_mil_pol_km"] == 488 and p["fluido"] == "co2"
    assert p["constantes"] == {} and p["equacoes"] == {}
    assert mec.parametros({"fonte_custo": "pig2019_plano"})["custo_mil_pol_km"] == 325
    p = mec.parametros({"fonte_custo": "pig2024", "custo_mil_pol_km": "600", "bo": "1,25", "bg": "0,0045"})
    assert p["fonte_custo"] == "manual" and p["custo_mil_pol_km"] == 600 and p["bo"] == 1.25 and p["bg"] == 0.0045
    assert mec.parametros({"bo": ""})["bo"] is None
    # constante igual ao padrão não conta como alterada; equação igual ao padrão também não
    p = mec.parametros({"constantes": {"f_co2": "1,2", "bw": "1,02"},
                        "equacoes": {"espaco_simples": "Np+Gp/gas_por_oe", "gas_livre": "Gp"}})
    assert p["constantes"] == {"bw": 1.02} and p["equacoes"] == {"gas_livre": "Gp"}
    for ruim in ({"bo": "12"}, {"fluido": "plasma"}, {"diametro_pol": "abc"}, {"constantes": {"xyz": 1}},
                 {"constantes": {"f_co2": 9}}, {"equacoes": {"nada": "Np"}}, {"equacoes": {"espaco_simples": "Np + Zz"}},
                 {"equacoes": {"espaco_simples": "oe * 2"}}, {"equacoes": {"massa": "V * import"}}):
        with pytest.raises(mec.ErroEconomia):
            mec.parametros(ruim)


# ------------------------------------------------------------------ produção acumulada
def _banco(tmp_path, inicio="01/01/2010", pd=True):
    b = Banco(str(tmp_path / "p.sqlite"))
    dados = {"ficha": {"nome": "CAMPO TESTE", "inicio_producao": inicio}}
    if pd:
        dados["pd"] = {"fonte": "BAR/2021", "acumulada": {"data": "31/12/2021", "oleo_milhoes_m3": 1.0,
                                                          "condensado_milhoes_m3": 0.1, "gas_total_milhoes_m3": 200.0}}
    mpr.guardar_campo(b, "Campo Teste", **dados)
    return b


def _mes(b, periodo, oleo=0, gas=0, agua=0, inj_agua=0, inj_gas=0, poco="1-AA-1-RN"):
    with b.conexao() as c:
        c.execute("INSERT INTO producao_poco (campo, poco_anp, periodo, instalacao, oleo_m3, gas_assoc_mil_m3, agua_m3, "
                  "inj_agua_rec_m3, inj_gas_mil_m3, arquivo) VALUES ('CAMPO TESTE', ?, ?, '', ?, ?, ?, ?, ?, 'pt.csv')",
                  (poco, periodo, oleo, gas, agua, inj_agua, inj_gas))


def test_acumulados_pelo_pd_e_continuacao(tmp_path):
    b = _banco(tmp_path)
    ac = mec.acumulados(b, "Campo Teste")
    assert ac["np"] == pytest.approx(1.1e6) and ac["gp"] == pytest.approx(200e6) and ac["wp"] is None
    assert "Plano de Desenvolvimento" in ac["fonte"] and ac["avisos"]
    _mes(b, "2022-01", oleo=1000, gas=50)
    _mes(b, "2022-02", oleo=500, gas=20)
    ac = mec.acumulados(b, "Campo Teste")
    assert ac["np"] == pytest.approx(1.1e6 + 1500) and ac["gp"] == pytest.approx(200e6 + 70e3)
    assert ac["ate"] == "2022-02" and "até 02/2022" in ac["fonte"]


def test_acumulados_serie_completa_tem_agua_e_injecao(tmp_path):
    b = _banco(tmp_path, inicio="15/03/2010")
    _mes(b, "2010-03", oleo=1000, gas=100, agua=400, inj_agua=100)
    _mes(b, "2010-04", oleo=1000, gas=100, agua=600, inj_agua=300, inj_gas=10)
    ac = mec.acumulados(b, "Campo Teste")
    assert ac["serie_completa"] and "todo o histórico" in ac["fonte"]
    assert (ac["np"], ac["gp"], ac["wp"], ac["wi"], ac["gi"]) == (2000, 200e3, 1000, 400, 10e3)


def test_acumulados_serie_parcial_e_sem_nada(tmp_path):
    b = _banco(tmp_path, pd=False)
    with pytest.raises(mec.ErroEconomia, match="Bloco 3D"):
        mec.acumulados(b, "Campo Teste")
    _mes(b, "2020-01", oleo=100)
    ac = mec.acumulados(b, "Campo Teste")
    assert ac["np"] == 100 and "só o período baixado" in ac["fonte"] and "desde 2010" in ac["avisos"][0]
    _mes(b, "2010-01", oleo=50)
    ac = mec.acumulados(b, "Campo Teste")
    assert not ac["serie_completa"] and ac["np"] == 150 and "faltam" in ac["avisos"][0]


# ------------------------------------------------------------------ avaliação e memória
DIST = [{"id": "epe_gasodutos_transporte", "rotulo": "Gasoduto", "baixada": True, "distancia_km": 10.0,
         "fonte": "EPE", "feicao": {"Nome_Dut_1": "Nordestão"}},
        {"id": "epe_termeletricas_fosseis", "rotulo": "Termelétrica", "baixada": True, "distancia_km": 40.0},
        {"id": "epe_dutos_escoamento", "rotulo": "Escoamento", "baixada": True, "distancia_km": 0.0, "toca_o_campo": True},
        {"id": "ibge_portos", "rotulo": "Porto", "baixada": False}]
NP, GP = 1.1e6, 200e6


def _passo(av, eq, metodo=None):
    return next(s for s in av["memoria"]["passos"] if s["id"] == eq and (metodo is None or s["metodo"] == metodo))


def _entrada(av, simb):
    return next(e for e in av["memoria"]["entradas"] if e["simbolo"] == simb)


def test_simples_custo_e_indicador_com_memoria(tmp_path):
    b = _banco(tmp_path)
    av = mec.avaliar(b, "Campo Teste", DIST, {"diametro_pol": 8, "fator_tracado": 1.2})
    custo_km = 488e3 * 8 * 1.2
    assert av["custo"]["r_por_km"] == pytest.approx(custo_km)
    assert av["metodos"]["simples"]["valor"] == pytest.approx(NP + GP / 1000)
    assert len(av["linhas"]) == 3
    g = av["linhas"][0]
    assert g["comprimento_km"] == pytest.approx(12) and g["custo_r"] == pytest.approx(12 * custo_km)
    assert g["indicadores"]["simples"] == pytest.approx(12 * custo_km / (NP + GP / 1000))
    falta = ["Bo (ou o grau API, para estimar)", "Bg (ou profundidade ou P e T, para estimar)"]
    assert g["indicadores"]["poroso"] is None and av["metodos"]["poroso"]["falta"] == falta
    assert av["metodos"]["molecula"]["falta"] == falta + ["profundidade ou P e T"]
    assert av["linhas"][1]["origem_tipica"] and not g["origem_tipica"]
    assert av["linhas"][2]["custo_r"] == 0 and any("No campo" in a for a in av["avisos"])
    # memória: equação, números substituídos, resultado e fonte de cada entrada
    s = _passo(av, "espaco_simples")
    assert s["equacao"] == "Np + Gp / gas_por_oe" and s["substituida"] == "1.100.000 + 200.000.000 / 1.000"
    assert s["resultado"] == pytest.approx(1.3e6) and not s["alterada"]
    assert "Plano de Desenvolvimento" in _entrada(av, "Np")["fonte"]
    assert "PIG 2024" in _entrada(av, "custo_pol_km")["fonte"] and "padrão" in _entrada(av, "f_fluido")["fonte"]
    assert "indisponível" in _entrada(av, "Wp")["fonte"]
    passos_g = g["memoria"]
    assert [x["id"] for x in passos_g] == ["comprimento", "custo_duto", "indicador"]
    assert passos_g[0]["substituida"] == "10 * 1,2" and "Nordestão" in g["fonte_distancia"]


def test_poroso_e_molecula(tmp_path):
    b = _banco(tmp_path)
    av = mec.avaliar(b, "Campo Teste", DIST, {"bo": 1.2, "bg": 0.005, "rs": 100, "pressao_bar": 100,
                                               "temperatura_c": 40, "eficiencia": 0.5})
    V = NP * 1.2 + (GP - NP * 100) * 0.005
    assert av["metodos"]["poroso"]["valor"] == pytest.approx(V)
    rho = mec.densidade("co2", 100, 40)
    m = av["metodos"]["molecula"]
    assert m["valor"] == pytest.approx(V * rho * 0.5 / 1000) and m["unidade"] == "t de CO₂"
    assert m["massa_mt"] == pytest.approx(m["valor"] / 1e6) and m["condicoes"]["origem_pressao"] == "informada"
    nota = next(s for s in av["memoria"]["passos"] if s["id"] == "nota")
    assert nota["resultado"] == pytest.approx(rho) and len(nota["detalhes"]) > 8
    g = av["linhas"][0]
    assert g["indicadores"]["molecula"] == pytest.approx(g["custo_r"] / m["valor"])
    # H₂: colchão e energia
    av = mec.avaliar(b, "Campo Teste", DIST, {"bo": 1.2, "bg": 0.005, "rs": 100, "pressao_bar": 100,
                                               "temperatura_c": 40, "fluido": "h2", "colchao": 0.4})
    util = V * mec.densidade("h2", 100, 40) / 1000 * 0.6
    m = av["metodos"]["molecula"]
    assert m["valor"] == pytest.approx(util) and m["energia_util_mwh"] == pytest.approx(util * 33.33)
    assert av["linhas"][0]["r_por_mwh"] == pytest.approx(av["linhas"][0]["custo_r"] / m["energia_util_mwh"])
    assert av["custo"]["fator_fluido"] == 1.05
    # densidade informada
    av = mec.avaliar(b, "Campo Teste", DIST, {"bo": 1.2, "bg": 0.005, "rs": 100, "pressao_bar": 100,
                                               "temperatura_c": 40, "densidade_kg_m3": 600})
    assert av["metodos"]["molecula"]["valor"] == pytest.approx(V * 600 / 1000)


def test_agua_injecao_e_espaco_zerado(tmp_path):
    b = _banco(tmp_path, inicio="15/03/2010", pd=False)
    _mes(b, "2010-03", oleo=1e5, agua=5e5, inj_agua=1e6)
    av = mec.avaliar(b, "Campo Teste", DIST, {"bo": 1.1})
    assert av["metodos"]["poroso"]["valor"] == 0 and any("repôs" in a for a in av["avisos"])
    assert _entrada(av, "Bg")["valor"] == 0          # sem gás: Bg não se aplica


def test_profundidade_dos_pocos(tmp_path):
    b = _banco(tmp_path)
    with b.conexao() as c:
        for k, prof in enumerate([500, 700, 900]):
            c.execute("INSERT INTO pocos (id, campo, prof_vertical) VALUES (?, 'CAMPO TESTE', ?)", (f"P{k}", prof))
    av = mec.avaliar(b, "Campo Teste", DIST, {"bo": 1.2, "bg": 0.005})
    cond = av["metodos"]["molecula"]["condicoes"]
    assert cond["profundidade_m"] == 700 and "mediana" in cond["origem_profundidade"]
    assert cond["pressao_bar"] == pytest.approx(1.01325 + 70) and cond["temperatura_c"] == pytest.approx(25 + 21)
    assert _passo(av, "pressao")["substituida"] == "1,01325 + 0,1 * 700"


def test_equacoes_e_constantes_alteradas(tmp_path):
    b = _banco(tmp_path)
    alt = mec.EQUACOES["espaco_simples"]["alternativas"]["só óleo e condensado"]
    av = mec.avaliar(b, "Campo Teste", DIST, {"equacoes": {"espaco_simples": alt},
                                               "constantes": {"f_co2": 1.5, "gas_por_oe": 500}})
    assert av["metodos"]["simples"]["valor"] == pytest.approx(NP)
    s = _passo(av, "espaco_simples")
    assert s["alterada"] and s["alternativa"] == "só óleo e condensado" and not s["personalizada"]
    assert av["custo"]["r_por_km"] == pytest.approx(488e3 * 8 * 1.5)
    assert "alterada pelo usuário" in _entrada(av, "f_fluido")["fonte"]
    assert av["avisos"][0].startswith("2 constante") and "equação" in av["avisos"][1]
    # fórmula do usuário
    av = mec.avaliar(b, "Campo Teste", DIST, {"equacoes": {"espaco_simples": "Np + 2 * Gp / gas_por_oe",
                                                           "custo_km": "(custo_fixo_km + custo_pol_km * D) * 1000"},
                                               "custo_fixo_km": 100})
    assert av["metodos"]["simples"]["valor"] == pytest.approx(NP + 2 * GP / 1000)
    assert _passo(av, "espaco_simples")["personalizada"]
    assert av["custo"]["r_por_km"] == pytest.approx((100 + 488 * 8) * 1000)
    alts = {a["id"]: a for a in av["memoria"]["meta"]["equacoes_alteradas"]}
    assert alts["custo_km"]["padrao"] == "custo_pol_km * 1000 * D * f_fluido"
    # variável que não existe naquele passo
    with pytest.raises(mec.ErroEconomia, match="variável desconhecida"):
        mec.avaliar(b, "Campo Teste", DIST, {"equacoes": {"custo_km": "custo_pol_km * V"}})
    with pytest.raises(mec.ErroEconomia, match="divisão por zero"):
        mec.avaliar(b, "Campo Teste", DIST, {"equacoes": {"espaco_simples": "Np / Wp"}})


def test_memoria_salva_em_json_html_e_csv(tmp_path):
    b = _banco(tmp_path)
    av = mec.avaliar(b, "Campo Teste", DIST, {"bo": 1.2, "bg": 0.005, "pressao_bar": 80, "temperatura_c": 35,
                                               "equacoes": {"espaco_simples": "Np"}})
    r = mec.salvar_memoria(str(tmp_path), av)
    assert r["json"].startswith("execucoes/viabilidade/") and r["html"].endswith("_campo_teste.html")
    dados = json.load(open(tmp_path / r["json"], encoding="utf-8"))
    assert dados["memoria"]["passos"][0]["id"] == "custo_km" and dados["parametros"]["equacoes"] == {"espaco_simples": "Np"}
    pagina = open(tmp_path / r["html"], encoding="utf-8").read()
    assert "Memória de cálculo" in pagina and "1.100.000 + 200.000.000 / 1.000" not in pagina
    assert "oe = Np" in pagina and "alternativa: só óleo e condensado" in pagina and "Peng-Robinson" in pagina
    assert "PIG 2024" in pagina and "Diferenças em relação ao padrão" in pagina
    linhas = mec.linhas_csv_memoria(av)
    assert ["# entradas"] in linhas and any(l[:2] == ["simples", "Espaço — método simples (PIBIC)"] for l in linhas)
    assert len(mec.linhas_csv(av)) == 3


# ------------------------------------------------------------------ correlações PVT
def _standing(P, T, api, gg):
    """Conta à mão, independente do motor: Standing (Rs, Bo) e Sutton + Papay (Bg)."""
    psia, tf = P * 14.5038, T * 1.8 + 32
    rs_scf = gg * ((psia / 18.2 + 1.4) * 10 ** (0.0125 * api - 0.00091 * tf)) ** 1.2048
    go = 141.5 / (131.5 + api)
    bo = 0.9759 + 0.00012 * (rs_scf * (gg / go) ** 0.5 + 1.25 * tf) ** 1.2
    tpc = (169.2 + 349.5 * gg - 74 * gg ** 2) / 1.8
    ppc = (756.8 - 131 * gg - 3.6 * gg ** 2) / 14.5038
    tpr, ppr = (T + 273.15) / tpc, P / ppc
    z = 1 - 3.52 * ppr / 10 ** (0.9813 * tpr) + 0.274 * ppr ** 2 / 10 ** (0.8157 * tpr)
    bg = z * (T + 273.15) / P * 1.01325 / 293.15
    return rs_scf * 0.178108, bo, bg, z


def test_bo_rs_bg_estimados_por_correlacao(tmp_path):
    b = _banco(tmp_path)
    av = mec.avaliar(b, "Campo Teste", DIST, {"pressao_bar": 61, "temperatura_c": 43, "api": 30})
    rs, bo, bg, z = _standing(61, 43, 30, 0.65)
    assert (rs, bo) == (pytest.approx(27.8, abs=0.5), pytest.approx(1.075, abs=0.005))   # ordem de grandeza
    assert bg == pytest.approx(0.0159, abs=0.0005) and z == pytest.approx(0.888, abs=0.005)
    v = {e["simbolo"]: e["valor"] for e in av["memoria"]["entradas"]}
    pas = {s["resultado_simbolo"]: s["resultado"] for s in av["memoria"]["passos"] if s["id"] != "nota"}
    assert pas["Rs"] == pytest.approx(rs) and pas["Bo"] == pytest.approx(bo) and pas["Bg"] == pytest.approx(bg)
    assert v["gg"] == 0.65 and v["API"] == 30
    poroso = av["metodos"]["poroso"]
    assert poroso["estimados"] == ["Rs (Standing)", "Bo (Standing)", "Bg (Sutton + Papay)"]
    assert poroso["valor"] == pytest.approx(NP * bo + max(0, GP - NP * rs) * bg)
    assert any("Estimados por correlação" in a for a in av["avisos"])
    assert any(s["metodo"] == "pvt" and s["id"] == "z_gas" for s in av["memoria"]["passos"])
    # sem estimar: falta Bo e Bg
    av = mec.avaliar(b, "Campo Teste", DIST, {"pressao_bar": 61, "temperatura_c": 43, "api": 30, "estimar_pvt": "nao"})
    assert av["metodos"]["poroso"]["falta"] == ["Bo", "Bg"]
    # Rs informado entra convertido no Bo; Bo informado não é estimado
    av = mec.avaliar(b, "Campo Teste", DIST, {"pressao_bar": 61, "temperatura_c": 43, "api": 30, "rs": 20, "bo": 1.1})
    assert av["metodos"]["poroso"]["estimados"] == ["Bg (Sutton + Papay)"]
    # fora da faixa de Standing: aviso
    av = mec.avaliar(b, "Campo Teste", DIST, {"pressao_bar": 61, "temperatura_c": 43, "api": 12})
    assert any("Standing fora da faixa" in a for a in av["avisos"])


def test_campo_de_gas_so_precisa_de_bg(tmp_path):
    b = Banco(str(tmp_path / "p.sqlite"))
    mpr.guardar_campo(b, "Campo Teste", ficha={"nome": "CAMPO TESTE", "inicio_producao": "2010"},
                      pd={"fonte": "BAR", "acumulada": {"data": "31/12/2021", "gas_total_milhoes_m3": 500.0}})
    av = mec.avaliar(b, "Campo Teste", DIST, {"pressao_bar": 150, "temperatura_c": 70, "densidade_gas": 0.6,
                                               "fluido": "h2"})
    _, _, bg, _ = _standing(150, 70, 30, 0.6)
    assert av["metodos"]["poroso"]["valor"] == pytest.approx(500e6 * bg)
    assert av["metodos"]["poroso"]["estimados"] == ["Bg (Sutton + Papay)"] and av["metodos"]["molecula"]["valor"] > 0
