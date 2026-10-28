"""Perfis: unidades de profundidade, nulos, famílias, cache, gráfico e exportação."""
import os

import lasio
import numpy as np
import pytest

from motor import perfis as mpf

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(scope="module")
def cl():
    return mpf.Classificador(mpf.ler_familias(os.path.join(RAIZ, "recursos", "mnemonicos.json")))


@pytest.mark.parametrize("unidade, fator", [
    ("m", 1.0), ("M", 1.0), ("ft", 0.3048), ("F", 0.3048), ("0.1 in", 0.00254),
    (".1IN", 0.00254), ("in", 0.0254), ("0.5 ms", None), ("", None), ("s", None),
])
def test_fator_metros(unidade, fator):
    r = mpf.fator_metros(unidade)
    assert (r is None and fator is None) or r == pytest.approx(fator)


def test_familias(cl):
    assert cl.familia("ECGR") == "GR" and cl.familia("HGR") == "GR"
    assert cl.familia("GREZ") is None                     # "cost function", não é raio gama
    assert cl.familia("AHT90") == "RES_PROF" and cl.familia("AE10") == "RES_RASA"
    assert cl.familia("RHOZ") == "RHOB" and cl.familia("TNPH") == "NPHI"
    assert cl.familia("DCAL") is None                     # cáliper diferencial
    assert cl.prioridade("GR", "GR") < cl.prioridade("GR", "HGR")


def las_exemplo(caminho, unidade="F"):
    las = lasio.LASFile()
    prof = np.arange(3000.0, 2000.0, -0.5)               # em pés e DECRESCENTE
    gr = 60 + 40 * np.sin(prof / 50)
    gr[10:20] = -999.25
    las.well["WELL"].value = "7-GMR-13-RN"
    las.well["UWI"].value = "72100000013"
    las.append_curve("DEPT", prof, unit=unidade)
    las.append_curve("GR", gr, unit="gAPI")
    las.append_curve("ILD", np.full_like(prof, 12.0), unit="ohmm")
    las.append_curve("XYZ", np.zeros_like(prof), unit="")
    las.write(str(caminho), version=2.0)


def test_inventario_las_em_pes(tmp_path, cl):
    f = tmp_path / "poco.las"
    las_exemplo(f)
    inv = mpf.inventariar(str(f), cl, str(tmp_path / "cache"))
    q = inv["quadros"][0]
    assert q["indice"]["fator_m"] == pytest.approx(0.3048)
    assert inv["topo_m"] == pytest.approx(2000.5 * 0.3048) and inv["base_m"] == pytest.approx(3000 * 0.3048)
    gr = next(c for c in q["curvas"] if c["mnemonico"] == "GR")
    assert gr["familia"] == "GR" and gr["n_validas"] == len(np.arange(3000.0, 2000.0, -0.5)) - 10
    assert inv["cabecalho"]["cadastro"] == "72100000013"
    assert {c["familia"] for c in mpf.curvas_padrao(inv, cl)} == {"GR", "RES_PROF"}
    assert mpf.ler_inventario(str(tmp_path / "cache"), "poco.las")["arquivo"] == "poco.las"


def test_grafico_recorta_e_decima(tmp_path, cl):
    f = tmp_path / "poco.las"
    las_exemplo(f)
    inv = mpf.inventariar(str(f), cl, str(tmp_path / "cache"))
    sel = mpf.curvas_padrao(inv, cl)
    g = mpf.dados_grafico(str(tmp_path / "cache"), "poco.las", sel, topo=700, base=800, max_pontos=100)
    for c in g:
        assert len(c["prof"]) <= 102 and min(c["prof"]) >= 700 and max(c["prof"]) <= 800
        assert c["prof"] == sorted(c["prof"])             # sempre crescente


def test_exportar_las_e_csv(tmp_path, cl):
    f = tmp_path / "poco.las"
    las_exemplo(f)
    inv = mpf.inventariar(str(f), cl, str(tmp_path / "cache"))
    sel = mpf.curvas_padrao(inv, cl)
    r = mpf.exportar_las(str(tmp_path / "out" / "x.las"), str(tmp_path / "cache"), "poco.las", sel,
                         inv["cabecalho"], "7-GMR-13-RN", passo=0.5)
    assert r["passo_m"] == 0.5
    lido = lasio.read(str(tmp_path / "out" / "x.las"))
    assert lido.well["WELL"].value == "7-GMR-13-RN" and lido.curves[0].unit == "M"
    assert np.isnan(lido["GR"]).sum() > 0                 # a falha original continua falha
    mpf.exportar_csv(str(tmp_path / "out" / "x.csv"), str(tmp_path / "cache"), "poco.las", sel)
    primeira = (tmp_path / "out" / "x.csv").read_text(encoding="utf-8").splitlines()[0]
    assert primeira.startswith("PROF_M;GR (gAPI)")


def test_formato_desconhecido(tmp_path, cl):
    f = tmp_path / "x.txt"
    f.write_text("nada")
    with pytest.raises(mpf.ErroPerfil):
        mpf.inventariar(str(f), cl, str(tmp_path / "c"))


DLIS_REAL = os.environ.get("SIAPP_DLIS_REAL")


@pytest.mark.skipif(not DLIS_REAL, reason="defina SIAPP_DLIS_REAL com o caminho de um DLIS real")
def test_dlis_real_1_auri_12(tmp_path, cl):
    """Conferência com o arquivo real 1-AURI-12-RN_AIT_P.DLIS (192 MB)."""
    inv = mpf.inventariar(DLIS_REAL, cl, str(tmp_path / "c"))
    assert inv["cabecalho"]["cadastro"] == "72100021414"
    assert inv["topo_m"] == pytest.approx(23.47, abs=0.01)
    assert inv["base_m"] == pytest.approx(2155.24, abs=0.01)       # índice em 0,1 pol.
    fams = {c["familia"] for c in mpf.curvas_padrao(inv, cl)}
    assert {"GR", "RES_PROF", "RHOB", "NPHI", "DT", "CALI"} <= fams


def test_ponte_perfil(api, tmp_path):
    api.escolher_pasta()
    pasta = tmp_path / "ambiente_teste" / "bruto" / "Potiguar" / "7-GMR-13-RN" / "Perfis"
    pasta.mkdir(parents=True)
    las_exemplo(pasta / "7gmr13.las")
    api._abrir_projeto(str(tmp_path / "ambiente_teste"))
    lista = api.perfis()["perfis"]
    assert len(lista) == 1 and not lista[0]["inventariado"]
    rel = lista[0]["rel"]
    assert api.curvas_perfil(rel)["inventario"] is None
    r = api.inventariar_perfil(rel)
    assert r["ok"] and r["poco"] == "7-GMR-13-RN" and r["padrao"]
    assert api.perfis()["perfis"][0]["n_curvas"] == 3
    g = api.grafico_perfil(rel, r["padrao"], 650, 700)
    assert g["ok"] and g["curvas"]
    e = api.exportar_perfil(rel, r["padrao"], "las")
    assert e["ok"] and e["arquivo"].startswith("exportacoes/7-GMR-13-RN/")
    assert not api.salvar_intervalo(rel, {"tipo": "intervalo_alvo", "nome": "Açu", "prof_topo": "700"})["ok"]
    s = api.salvar_intervalo(rel, {"tipo": "intervalo_alvo", "nome": "Açu", "prof_topo": "700,5",
                                   "prof_base": "720"})
    assert s["ok"] and s["fato"]["prof_topo"] == 700.5 and s["fato"]["fonte_rel"] == rel
    assert api.curvas_perfil(rel)["fatos"][0]["nome"] == "Açu"
    assert api.ficha_poco("7-GMR-13-RN")["curvas"]
    assert api.remover_fato(s["fato"]["id"])["ok"]


def test_sugerir_curvas_por_objetivo(tmp_path, cl):
    f = tmp_path / "poco.las"
    las_exemplo(f)
    inv = mpf.inventariar(str(f), cl, str(tmp_path / "cache"))
    s = mpf.sugerir_curvas(inv, cl, "saturacao")
    assert [c["mnemonico"] for c in s["curvas"]] == ["ILD", "GR"]          # na ordem do objetivo
    assert {x["familia"] for x in s["faltam"]} == {"RES_MED", "RES_RASA", "RHOB", "NPHI"}
    assert "Archie" in s["porque"] and s["nome"].startswith("Saturação")
    assert [c["mnemonico"] for c in mpf.sugerir_curvas(inv, cl, "porosidade")["curvas"]] == []
    with pytest.raises(ValueError):
        mpf.sugerir_curvas(inv, cl, "magia")
    for ob in mpf.OBJETIVOS.values():
        assert all(f in cl.familias for f in ob["familias"]), ob["nome"]
