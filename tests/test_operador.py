"""Perfis processados pela operadora (0.41): famílias, pesquisa no levantamento, comparação com a avaliação."""
import json
import os

import lasio
import numpy as np
import pytest

from motor import banco as mb
from motor import levantamento as mlv
from motor import operador as mop
from motor import perfis as mpf
from motor import pocos as mpo
from test_avaliacao import las_reservatorio

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POCO = "7-TST-1-RN"
REL = f"bruto/Potiguar/{POCO}/Perfil Convencional/tst.las"
REL_OP = f"bruto/Potiguar/{POCO}/Perfil Digital Processado/tst_adic.las"


@pytest.fixture(scope="module")
def cl():
    return mpf.Classificador(mpf.ler_familias(os.path.join(RAIZ, "recursos", "mnemonicos.json")))


def las_operador(caminho, *, sw_oleo=25.0):
    """Interpretação da operadora em %: arenito 1010–1030 com φ 21 %, Vsh 10 %, Sw 25 % (óleo) / 90 % (água)."""
    prof = np.arange(1000.0, 1040.01, 0.5)
    are = (prof >= 1010) & (prof < 1030)
    las = lasio.LASFile()
    las.well["WELL"].value = POCO
    las.append_curve("DEPT", prof, unit="M")
    las.append_curve("VSH", np.where(are, 10.0, 80.0), unit="%")
    las.append_curve("PHIE", np.where(are, 21.0, 2.0), unit="%")
    las.append_curve("SW", np.where(are & (prof < 1020), sw_oleo, 90.0), unit="%")
    las.write(str(caminho), version=2.0)


def test_familias_de_interpretacao(cl):
    assert cl.familia("PHIE") == "PHIE" and cl.familia("SWE") == "SW" and cl.familia("VCL") == "VSH"
    assert cl.familia("PHIT") == "PHIT" and cl.familia("KINT") == "PERM"
    fams = mop.familias_interpretacao(cl.familias)
    assert set(fams) == set(mlv.FAMILIAS_INTERP) == set(mop.FAMILIAS)
    assert cl.familia("GR") == "GR" and cl.familia("SXO") is None


def _acervo(b):
    with b.conexao() as c:
        for poco, curvas in (("1-A-1-RN", ["GR", "PHIE", "SW", "VSH"]), ("1-B-1-RN", ["GR", "ILD"]),
                             ("1-C-1-RN", ["PHIT"])):
            cam = f"/POCO/Categoria-1/{poco}/"
            c.execute("INSERT INTO acervo_pocos (bacia, caminho, poco_id, categoria, familias) VALUES (?,?,?,?,?)",
                      ("Potiguar", cam, poco, "Categoria-1", "GR"))
            c.execute("INSERT INTO acervo_arquivos (bacia, caminho, poco_caminho, nome, pasta, curvas, familias) "
                      "VALUES (?,?,?,?,?,?,?)", ("Potiguar", cam + "x.las", cam, f"{poco}_adic.las",
                                                 "Perfil Digital Processado", json.dumps(curvas), '["GR"]'))
        c.execute("INSERT INTO pocos (id, bacia, lat, lon) VALUES ('1-A-1-RN', 'Potiguar', -5.1, -37.1)")
        c.execute("INSERT INTO pocos (id, bacia, lat, lon) VALUES ('1-B-1-RN', 'Potiguar', -5.2, -37.2)")


def test_reclassificar_e_pesquisar_sem_baixar(tmp_path, cl):
    b = mb.Banco(str(tmp_path / "p.sqlite"))
    _acervo(b)
    assert mop.pesquisar(b, list(mlv.FAMILIAS_INTERP))["n_pocos"] == 0       # famílias antigas, sem as novas
    assert mop.reclassificar_acervo(b, cl) == 3
    assert mop.reclassificar_acervo(b, cl) == 0                               # idempotente
    r = mop.pesquisar(b, list(mlv.FAMILIAS_INTERP))
    assert [p["poco"] for p in r["pocos"]] == ["1-A-1-RN", "1-C-1-RN"] and r["completos"] == 1
    assert r["pocos"][0]["familias"] == ["PHIE", "SW", "VSH"] and r["pocos"][1]["completo"] is False
    assert mlv.resumo(b, "Potiguar")["pocos_com_interpretacao"] == 2
    m = mpo.pocos_mapa(b, familia="INTERP")
    assert [ln[0] for ln in m["linhas"]] == ["1-A-1-RN"]                    # o 1-C não tem coordenadas
    assert [ln[0] for ln in mpo.pocos_mapa(b, familia="SW")["linhas"]] == ["1-A-1-RN"]


def test_fracao_e_grade():
    assert np.allclose(mop._fracao(np.array([10.0, 20.0]), ""), [0.1, 0.2])
    assert np.allclose(mop._fracao(np.array([0.1, 0.2]), "v/v"), [0.1, 0.2])
    assert np.allclose(mop._fracao(np.array([0.5]), "%"), [0.005])


@pytest.fixture
def projeto(api, tmp_path):
    api.escolher_pasta()
    base = tmp_path / "ambiente_teste" / "bruto" / "Potiguar" / POCO
    (base / "Perfil Convencional").mkdir(parents=True)
    (base / "Perfil Digital Processado").mkdir()
    las_reservatorio(base / "Perfil Convencional" / "tst.las")
    las_operador(base / "Perfil Digital Processado" / "tst_adic.las")
    api._abrir_projeto(str(tmp_path / "ambiente_teste"))
    assert api.inventariar_perfil(REL)["ok"]
    return api


def test_comparar_com_a_avaliacao(projeto):
    api = projeto
    info = api.avaliacao_info(REL)
    assert info["operador"] == {}                                  # o processado ainda não foi aberto
    assert api.inventariar_perfil(REL_OP)["ok"]
    info = api.avaliacao_info(REL)
    assert {k: v["mnemonico"] for k, v in info["operador"].items()} == {"VSH": "VSH", "PHIE": "PHIE", "SW": "SW"}
    s = api.salvar_intervalo(REL, {"tipo": "intervalo_alvo", "nome": "Açu", "prof_topo": "1010", "prof_base": "1020"})
    curvas = {p: d["padrao"] for p, d in info["papeis"].items() if d["padrao"]}
    ex = api.avaliar_formacao(REL, curvas, [s["fato"]["id"]], {"gr_limpo": "30", "gr_argila": "120", "rw": "0,05"})
    assert ex["ok"], ex
    r = api.comparar_operador(ex["id"])
    assert r["ok"] and r["faltam"] == [] and r["curvas"]["phi"]["familia"] == "PHIE"
    i = r["intervalos"][0]
    assert i["vsh"]["operador"] == pytest.approx(0.10, abs=1e-3) and i["phi"]["operador"] == pytest.approx(0.21, abs=1e-3)
    assert i["sw"]["operador"] == pytest.approx(0.25, abs=0.04)            # 1020 é o primeiro ponto de água
    assert i["phi"]["siapp"] == pytest.approx(0.20, abs=0.02) and i["phi"]["diferenca"] == pytest.approx(-0.01, abs=0.02)
    assert i["sw"]["siapp_pay"] is not None and i["cobertura_operador"] == 1.0
    assert "não encontrada" in api.comparar_operador("avaliacao_x")["erro"]


def test_sem_processado_explica(projeto):
    api = projeto
    info = api.avaliacao_info(REL)
    s = api.salvar_intervalo(REL, {"tipo": "intervalo_alvo", "nome": "Açu", "prof_topo": "1010", "prof_base": "1020"})
    curvas = {p: d["padrao"] for p, d in info["papeis"].items() if d["padrao"]}
    ex = api.avaliar_formacao(REL, curvas, [s["fato"]["id"]], {"gr_limpo": "30", "gr_argila": "120", "rw": "0,05"})
    assert "Abra o perfil processado" in api.comparar_operador(ex["id"])["erro"]


def test_reclassificacao_na_abertura(api, tmp_path):
    api.escolher_pasta()
    _acervo(api._banco)
    api._banco.definir_meta("mnemonicos_versao", "2")
    api._abrir_projeto(str(tmp_path / "ambiente_teste"))
    assert api.perfis_processados("Potiguar")["n_pocos"] == 2
    assert api._banco.meta("mnemonicos_versao") == "3"
