"""Avaliação de formação: fórmulas com valores conhecidos e o cálculo só no intervalo-alvo."""
import json
import os

import lasio
import numpy as np
import pytest

from motor import avaliacao as av
from motor import perfis as mpf

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture
def cl():
    return mpf.Classificador(mpf.ler_familias(os.path.join(RAIZ, "recursos", "mnemonicos.json")))


# ------------------------------------------------------------ fórmulas
def test_vsh_linear_e_larionov():
    gr = np.array([30.0, 75.0, 120.0, 200.0, 0.0])
    assert av.vsh_de_gr(gr, 30, 120).tolist() == pytest.approx([0, 0.5, 1, 1, 0])
    # IGR = 0,5: terciárias 0,083·(2^1,85 − 1) ≈ 0,2162; mais antigas 0,33·(2^1 − 1) = 0,33
    assert av.vsh_de_gr(np.array([75.0]), 30, 120, "larionov_terciario")[0] == pytest.approx(0.2162, abs=1e-4)
    assert av.vsh_de_gr(np.array([75.0]), 30, 120, "larionov_antigo")[0] == pytest.approx(0.33)
    with pytest.raises(av.ErroAvaliacao):
        av.vsh_de_gr(gr, 120, 30)


def test_porosidades():
    assert av.phi_densidade(np.array([2.32]), 2.65, 1.0)[0] == pytest.approx(0.2)
    # sem gás: média; com gás (φN < φD): raiz da média dos quadrados
    assert av.phi_densidade_neutrao(np.array([0.20]), np.array([0.26]))[0] == pytest.approx(0.23)
    assert av.phi_densidade_neutrao(np.array([0.24]), np.array([0.10]))[0] == pytest.approx(np.sqrt((0.24**2 + 0.10**2) / 2))
    assert av.phi_sonico(np.array([89.9]), 55.5, 189.0)[0] == pytest.approx(0.2577, abs=1e-4)


def test_archie_e_simandoux():
    # φ = 0,2, Rt = 20, Rw = 0,05, a = 1, m = n = 2 → Sw = √(0,05 / (0,04·20)) = 0,25
    assert av.sw_archie(np.array([0.2]), np.array([20.0]), 0.05)[0] == pytest.approx(0.25)
    # sem argila, Simandoux = Archie
    assert av.sw_simandoux(np.array([0.2]), np.array([20.0]), 0.05, np.array([0.0]), 2.0)[0] == pytest.approx(0.25)
    # argila condutiva: Simandoux dá Sw menor que Archie para o mesmo Rt
    s = av.sw_simandoux(np.array([0.2]), np.array([5.0]), 0.05, np.array([0.3]), 2.0)[0]
    assert s < av.sw_archie(np.array([0.2]), np.array([5.0]), 0.05)[0]


# ----------------------------------------------------- cálculo completo
def las_reservatorio(caminho):
    """Poço sintético em metros: folhelho 1000–1010, arenito com óleo 1010–1020,
    arenito com água 1020–1030, folhelho 1030–1040. Passo 0,5 m."""
    prof = np.arange(1000.0, 1040.01, 0.5)
    gr = np.where((prof >= 1010) & (prof < 1030), 30.0, 120.0)
    rhob = np.where((prof >= 1010) & (prof < 1030), 2.32, 2.55)          # φD = 0,20 no arenito
    nphi = np.where((prof >= 1010) & (prof < 1030), 20.0, 35.0)          # em %, φN = 0,20
    rt = np.where((prof >= 1010) & (prof < 1020), 20.0, np.where((prof >= 1020) & (prof < 1030), 0.8, 2.0))
    cali = np.where((prof >= 1035), 10.0, 8.5)
    las = lasio.LASFile()
    las.well["WELL"].value = "7-TST-1-RN"
    las.append_curve("DEPT", prof, unit="M")
    for nome, v, u in (("GR", gr, "gAPI"), ("RHOB", rhob, "g/cm3"), ("NPHI", nphi, "%"),
                       ("ILD", rt, "ohmm"), ("CALI", cali, "in"), ("BS", np.full_like(prof, 8.5), "in")):
        las.append_curve(nome, v, unit=u)
    las.write(str(caminho), version=2.0)


def curvas_do_inventario(inv, cl):
    pad = {c["familia"]: c for c in mpf.curvas_padrao(inv, cl)}
    papel = {"GR": "GR", "RHOB": "RHOB", "NPHI": "NPHI", "RT": "RES_PROF", "CALI": "CALI", "BS": "BS"}
    return {k: pad[f] for k, f in papel.items() if f in pad}


def test_avaliacao_no_intervalo(tmp_path, cl):
    f = tmp_path / "tst.las"
    las_reservatorio(f)
    cache = str(tmp_path / "cache")
    inv = mpf.inventariar(str(f), cl, cache)
    curvas = curvas_do_inventario(inv, cl)
    r = av.avaliar(cache, "tst.las", curvas, [{"nome": "Açu", "topo": 1005, "base": 1035}],
                   {"gr_limpo": "30", "gr_argila": "120", "rw": "0,05"})
    i = r["intervalos"][0]
    assert r["parametros"]["phi_metodo"] == "densidade_neutrao"
    assert i["bruto_m"] == 30
    # arenito 1010–1030 (20 m, 40 amostras de 0,5 m; limites inclusivos → 20,0–20,5 m)
    assert i["reservatorio_m"] == pytest.approx(20.0, abs=0.5)
    # net pay só no arenito com óleo (Sw 0,25); na água, Sw = √(0,05/(0,04·0,8)) > 1 → 1
    assert i["net_pay_m"] == pytest.approx(10.0, abs=0.5)
    assert i["phi_media_pay"] == pytest.approx(0.2) and i["sw_media_pay"] == pytest.approx(0.25)
    assert i["hpv_m"] == pytest.approx(10 * 0.2 * 0.75, rel=0.06)
    # fora do intervalo não há cálculo
    prof = r["prof"]
    assert np.isnan(r["curvas"]["SW"][prof < 1005]).all() and np.isnan(r["curvas"]["SW"][prof > 1035]).all()
    # arrombamento a partir de 1035 m (cáliper 10 pol com broca de 8,5)
    assert i["qc_arrombado_m"] == pytest.approx(0.5, abs=0.5)


def test_parametros_automaticos_ficam_registrados(tmp_path, cl):
    f = tmp_path / "tst.las"
    las_reservatorio(f)
    cache = str(tmp_path / "cache")
    inv = mpf.inventariar(str(f), cl, cache)
    r = av.avaliar(cache, "tst.las", curvas_do_inventario(inv, cl), [{"nome": "A", "topo": 1000, "base": 1040}],
                   {"sw_metodo": "simandoux"})
    assert r["parametros"]["gr_limpo"] == 30 and r["parametros"]["gr_argila"] == 120
    assert set(r["automaticos"]) >= {"gr_limpo", "gr_argila", "rsh", "phi_metodo"}
    assert r["parametros"]["rsh"] == pytest.approx(2.0)
    ident, caminho = av.registrar(str(tmp_path / "execucoes"), poco="7-TST-1-RN", rel="bruto/x/tst.las",
                                  sha256="abc", resultado=r, autor="Ruan")
    reg = json.load(open(caminho, encoding="utf-8"))
    assert reg["parametros"]["rsh"] == pytest.approx(2.0) and reg["arquivo_sha256"] == "abc"
    assert "Archie" in reg["formulas"] and reg["curvas_usadas"]["GR"]["mnemonico"] == "GR"
    assert av.execucoes(str(tmp_path / "execucoes"), "bruto/x/tst.las")[0]["id"] == ident
    g = av.dados_grafico(str(tmp_path / "execucoes"), ident, 1000, 1040)
    assert [c["mnemonico"] for c in g] == ["VSH", "PHI", "SW", "RES", "PAY", "QC"]
    out = tmp_path / "exp" / "a.las"
    assert av.exportar(str(tmp_path / "execucoes"), ident, str(out), "las", "7-TST-1-RN")["amostras"] == 81
    assert "SW" in lasio.read(str(out)).keys()


def test_erros_claros(tmp_path, cl):
    f = tmp_path / "tst.las"
    las_reservatorio(f)
    cache = str(tmp_path / "cache")
    inv = mpf.inventariar(str(f), cl, cache)
    curvas = curvas_do_inventario(inv, cl)
    with pytest.raises(av.ErroAvaliacao, match="intervalo-alvo"):
        av.avaliar(cache, "tst.las", curvas, [])
    with pytest.raises(av.ErroAvaliacao, match="RT"):
        av.avaliar(cache, "tst.las", {k: v for k, v in curvas.items() if k != "RT"}, [{"topo": 1000, "base": 1010}])
    with pytest.raises(av.ErroAvaliacao, match="fora da profundidade"):
        av.avaliar(cache, "tst.las", curvas, [{"nome": "x", "topo": 3000, "base": 3010}])
    with pytest.raises(av.ErroAvaliacao, match="não é número"):
        av.avaliar(cache, "tst.las", curvas, [{"topo": 1000, "base": 1010}], {"rw": "abc"})
