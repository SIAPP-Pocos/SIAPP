"""Viabilidade econômica: custo do duto, capacidade de injeção nos três métodos e o indicador."""
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


def test_densidade_na_condicao_padrao():
    assert mec.densidade("h2", 1.01325, 20) == pytest.approx(0.08375, rel=2e-3)
    assert mec.densidade("co2", 1.01325, 20) == pytest.approx(1.8393, rel=2e-3)


def test_parametros_padrao_referencia_e_manual():
    p = mec.parametros(None)
    assert p["fonte_custo"] == "pig2024" and p["custo_mil_pol_km"] == 488 and p["fluido"] == "co2"
    p = mec.parametros({"fonte_custo": "pig2019_plano"})
    assert p["custo_mil_pol_km"] == 325
    p = mec.parametros({"fonte_custo": "pig2024", "custo_mil_pol_km": "600", "bo": "1,25", "bg": "0,0045"})
    assert p["fonte_custo"] == "manual" and p["custo_mil_pol_km"] == 600 and p["bo"] == 1.25 and p["bg"] == 0.0045
    assert mec.parametros({"bo": ""})["bo"] is None
    with pytest.raises(mec.ErroEconomia, match="Bo"):
        mec.parametros({"bo": "12"})
    with pytest.raises(mec.ErroEconomia):
        mec.parametros({"fluido": "plasma"})
    with pytest.raises(mec.ErroEconomia):
        mec.parametros({"diametro_pol": "abc"})


def test_custo_por_km_com_fator_do_fluido():
    c = mec.custo_por_km(mec.parametros({"diametro_pol": 10}))
    assert c["r_por_km_gas_natural"] == pytest.approx(4.88e6)
    assert c["r_por_km"] == pytest.approx(4.88e6 * 1.20) and c["data_base"] == "jun/2024"
    assert mec.custo_por_km(mec.parametros({"diametro_pol": 10, "fluido": "h2"}))["r_por_km"] == pytest.approx(4.88e6 * 1.05)


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
                  "inj_agua_rec_m3, inj_gas_mil_m3) VALUES ('CAMPO TESTE', ?, ?, '', ?, ?, ?, ?, ?)",
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
    # começa no início do campo, mas com um buraco: não é completa
    _mes(b, "2010-01", oleo=50)
    ac = mec.acumulados(b, "Campo Teste")
    assert not ac["serie_completa"] and ac["np"] == 150 and "faltam" in ac["avisos"][0]


# ------------------------------------------------------------------ capacidade
def test_simples_em_oleo_equivalente():
    c = mec.capacidade_simples({"np": 1e6, "gp": 300e6})
    assert c["valor"] == pytest.approx(1.3e6) and c["unidade"] == "m³ de óleo equivalente"


def test_poroso_pede_bo_bg_e_aplica_a_formula():
    ac = {"np": 1e6, "gp": 300e6, "wp": None}
    assert mec.capacidade_porosa(ac, mec.parametros({}))["falta"] == ["Bo", "Bg"]
    # campo de gás puro: só Bg
    assert mec.capacidade_porosa({"np": 0, "gp": 1e8, "wp": None}, mec.parametros({"bg": 0.005}))["valor"] == pytest.approx(5e5)
    c = mec.capacidade_porosa(ac, mec.parametros({"bo": 1.2, "bg": 0.005, "rs": 100}))
    assert c["valor"] == pytest.approx(1e6 * 1.2 + (300e6 - 1e8) * 0.005)
    assert c["parcelas"]["agua_liquida"] is None
    # sem Rs: aviso; com água e injeção (série completa)
    ac2 = {"np": 1e6, "gp": 300e6, "wp": 5e6, "wi": 4e6, "gi": 10e6}
    c = mec.capacidade_porosa(ac2, mec.parametros({"bo": 1.2, "bg": 0.005}))
    assert c["valor"] == pytest.approx(1.2e6 + 1.5e6 + 1e6 - 5e4) and any("Rs" in a for a in c["avisos"])
    # injeção maior que a produção → zero
    c = mec.capacidade_porosa({"np": 1e5, "gp": 0, "wp": 0, "wi": 1e6, "gi": 0}, mec.parametros({"bo": 1.1}))
    assert c["valor"] == 0 and any("repôs" in a for a in c["avisos"])


def test_molecula_co2_e_h2():
    poroso = {"valor": 1e6}
    cond = {"pressao_bar": 100.0, "temperatura_c": 40.0}
    c = mec.capacidade_molecula(poroso, cond, mec.parametros({"eficiencia": 0.5}))
    rho = mec.densidade("co2", 100, 40)
    assert c["valor"] == pytest.approx(1e6 * rho * 0.5 / 1e3) and c["unidade"] == "t de CO₂"
    assert c["massa_mt"] == pytest.approx(c["valor"] / 1e6)
    h = mec.capacidade_molecula(poroso, cond, mec.parametros({"fluido": "h2", "colchao": 0.4}))
    util_kg = 1e6 * mec.densidade("h2", 100, 40) * 0.6
    assert h["valor"] == pytest.approx(util_kg / 1e3) and h["energia_util_mwh"] == pytest.approx(util_kg * 33.33 / 1e3)
    falta = mec.capacidade_molecula({"valor": None, "falta": ["Bo"]}, {}, mec.parametros({}))
    assert falta["valor"] is None and falta["falta"] == ["Bo", "profundidade ou P e T"]


def test_condicoes_pela_profundidade_dos_pocos(tmp_path):
    b = _banco(tmp_path)
    with b.conexao() as c:
        for k, prof in enumerate([500, 700, 900]):
            c.execute("INSERT INTO pocos (id, campo, prof_vertical) VALUES (?, 'CAMPO TESTE', ?)", (f"P{k}", prof))
    cond = mec.condicoes(b, "Campo Teste", mec.parametros({}))
    assert cond["profundidade_m"] == 700 and "mediana" in cond["origem_profundidade"]
    assert cond["pressao_bar"] == pytest.approx(1.01325 + 70) and cond["temperatura_c"] == pytest.approx(25 + 21)
    cond = mec.condicoes(b, "Campo Teste", mec.parametros({"pressao_bar": 80, "temperatura_c": 35}))
    assert (cond["pressao_bar"], cond["temperatura_c"], cond["origem_pressao"]) == (80, 35, "informada")


# ------------------------------------------------------------------ indicador
def test_avaliar_custo_sobre_capacidade(tmp_path):
    b = _banco(tmp_path)
    dist = [{"id": "epe_gasodutos_transporte", "rotulo": "Gasoduto", "baixada": True, "distancia_km": 10.0},
            {"id": "epe_termeletricas_fosseis", "rotulo": "Termelétrica", "baixada": True, "distancia_km": 40.0},
            {"id": "epe_dutos_escoamento", "rotulo": "Escoamento", "baixada": True, "distancia_km": 0.0,
             "toca_o_campo": True},
            {"id": "ibge_portos", "rotulo": "Porto", "baixada": False}]
    av = mec.avaliar(b, "Campo Teste", dist, {"diametro_pol": 8, "fator_tracado": 1.2})
    assert len(av["linhas"]) == 3
    g = av["linhas"][0]
    custo_km = 488e3 * 8 * 1.2
    assert g["comprimento_km"] == pytest.approx(12) and g["custo_r"] == pytest.approx(12 * custo_km)
    assert g["indicadores"]["simples"] == pytest.approx(12 * custo_km / (1.1e6 + 200e6 / 1000))
    assert g["indicadores"]["poroso"] is None and av["metodos"]["poroso"]["falta"] == ["Bo", "Bg"]
    assert av["linhas"][1]["origem_tipica"] and not g["origem_tipica"]
    assert av["linhas"][2]["custo_r"] == 0 and any("No campo" in a for a in av["avisos"])
    av = mec.avaliar(b, "Campo Teste", dist, {"bo": 1.3, "bg": 0.006, "rs": 120, "pressao_bar": 90,
                                               "temperatura_c": 38})
    m = av["metodos"]["molecula"]
    assert m["valor"] > 0 and av["linhas"][0]["indicadores"]["molecula"] == pytest.approx(av["linhas"][0]["custo_r"] / m["valor"])
    assert len(mec.linhas_csv(av)) == 3
