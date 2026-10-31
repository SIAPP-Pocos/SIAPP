"""Petrofísica básica de testemunho (0.48): plugs e gama do testemunho, em planilhas sintéticas."""
import os

import pytest

import petrofisica_util as pu
from motor import dados_poco as mdp
from motor import petrofisica as pf

POCO = "1-SIAPP-1-RN"
PASTA = f"bruto/Potiguar/{POCO}/Dados de Rochas e Fluidos/PETROFISICA_BASICA"


def test_reconhece_pela_pasta_e_pelo_nome():
    assert pf.tipo_pelo_nome(f"{PASTA}/1ALG 0001  RN-Petrofisica Basica.xls") == "petrofisica_plugs"
    assert pf.tipo_pelo_nome(f"{PASTA}/00610.119452.xls") == "petrofisica_plugs"          # nome numérico: vale a pasta
    assert pf.tipo_pelo_nome(f"{PASTA}/1-ALG-0001-RN_COREGAMA.xls") == "petrofisica_gama"
    assert pf.tipo_pelo_nome(PASTA.replace("/", "\\") + "\\x_coregama.xlsx") == "petrofisica_gama"
    # as grafias da pasta que existem no acervo (levantamento de 31/10: 162 poços)
    for pasta in ("Dados de Rochas e Fluidos/PETROFISICABASICA", "Petrofisica_basica", "Petrofica_basica",
                  "Petrofisicabasica", "PETROFISICABASICA", "Dados de Rochas de Fluidos/PETROFISICABASICA"):
        assert pf.tipo_pelo_nome(f"bruto/Potiguar/{POCO}/{pasta}/7-ET-854-RN_COREGAMA.xls") == "petrofisica_gama", pasta
        assert pf.tipo_pelo_nome(f"bruto/Potiguar/{POCO}/{pasta}/PETROFISICA7ET0854RN-7ET854RN.xls") == "petrofisica_plugs"
    assert pf.tipo_pelo_nome("a/Dados de Rochas e Fluidos/PETROFISICAAVANCADA/x_PressaoCapilar_7-MAG-50-RN.xls") is None
    assert not pf.reconhece(f"bruto/Potiguar/{POCO}/Pasta de Poco/dados.xls")
    assert not pf.reconhece(f"{PASTA}/relatorio.pdf")
    assert mdp.leitor_para(f"{PASTA}/x_COREGAMA.xls") == "petrofisica"


def test_numeros_com_virgula_decimal_e_milhar():
    assert pf._num("206,39") == 206.39 and pf._num("1.234,5") == 1234.5 and pf._num("2330") == 2330.0
    assert pf._num(12) == 12.0 and pf._num("") is None and pf._num("-") is None and pf._num("abc") is None
    assert pf._num(None) is None and pf._num(True) is None


def test_plugs_colunas_pelo_cabecalho(tmp_path):
    os.makedirs(tmp_path / "PETROFISICA_BASICA")
    alvo = tmp_path / "PETROFISICA_BASICA" / "1SIAPP 0001  RN-Petrofisica Basica.xlsx"
    pu.plugs(str(alvo))
    d = pf.ler(str(alvo))
    assert d["documento"] == "petrofisica_plugs" and d["gerais"]["poco"] == pu.POCO_ANP
    a = d["amostras"]
    assert len(a) == 3                                        # as duas linhas em branco do fim não contam
    assert a[0]["prof"] == 1000.5 and a[0]["porosidade"] == 18.2 and a[0]["permeabilidade"] == 1234.5
    assert a[0]["densidade"] == 2.66 and a[0]["pressao"] == 2330.0
    assert (a[0]["direcao"], a[0]["numero"], a[0]["tipo"]) == ("VH1", "1", "Plug")
    assert {"direcao", "numero", "prof", "porosidade", "permeabilidade"} <= set(d["colunas_lidas"])


def test_coluna_desconhecida_nao_se_perde():
    linhas = [["Profundidade", "Porosidade%", "Permeabilidade Vertical (mD)", "Saturação de água (%)"],
              ["1500,2", "15,5", "3,1", "32"]]
    d = pf.ler_plugs_linhas(linhas)
    a = d["amostras"][0]
    assert a["porosidade"] == 15.5 and a["permeabilidade"] == 3.1            # só uma permeabilidade: a primeira que casa
    assert pf.itens(d)[0]["extra"]["permeabilidade"] == 3.1
    outras = pf.ler_plugs_linhas([["Profundidade", "Porosidade%", "Saturação de água (%)"], ["1500,2", "15,5", "32"]])
    assert outras["amostras"][0]["colunas"] == {"Saturação de água (%)": "32"}


def test_planilha_que_nao_e_petrofisica_levanta_erro_claro():
    with pytest.raises(pf.ErroPetrofisica, match="Profundidade"):
        pf.ler_plugs_linhas([["A", "B"], ["1", "2"]])
    with pytest.raises(pf.ErroPetrofisica, match="porosidade nem permeabilidade"):
        pf.ler_plugs_linhas([["Profundidade", "Cor"], ["10", "azul"]])
    with pytest.raises(pf.ErroPetrofisica, match="nenhuma amostra"):
        pf.ler_plugs_linhas([["Profundidade", "Porosidade%"], ["", ""]])
    with pytest.raises(pf.ErroPetrofisica, match="raios gama"):
        pf.ler_gama_linhas([["A", "B"]])
    with pytest.raises(pf.ErroPetrofisica, match="Não é uma planilha"):
        pf.ler("qualquer/coisa.xls")


def test_gama_do_testemunho(tmp_path):
    os.makedirs(tmp_path / "PETROFISICA_BASICA")
    alvo = tmp_path / "PETROFISICA_BASICA" / "x_COREGAMA.xlsx"
    pu.coregama(str(alvo))
    d = pf.ler(str(alvo))
    assert d["documento"] == "petrofisica_gama" and d["gerais"]["poco"] == pu.POCO_ANP
    assert [p["prof"] for p in d["pontos"]] == [1000.0, 1000.5, 1001.0, 1001.5]
    p = d["pontos"][0]
    assert (p["gr"], p["testemunho"], p["topo"], p["base"]) == (20.0, 1, 1000.0, 1002.0)
    it = pf.itens(d)
    assert len(it) == 4 and it[0]["tipo"] == "gama_testemunho" and it[0]["unidade"] == "API" and it[0]["nome"] == "1"


def test_itens_dos_plugs_e_resumo_sem_estatistica_inventada():
    d = pf.ler_plugs_linhas([pu.CAB_PLUGS] + [["UO", pu.POCO_ANP, pu.POCO_ANP, "Plug", dr, n, p, phi, rho, k, "100"]
                                              for p, phi, rho, k, dr, n in pu.PLUGS])
    it = pf.itens(d)
    assert [i["tipo"] for i in it] == ["plug_testemunho"] * 3
    assert (it[0]["prof_topo"], it[0]["valor"], it[0]["nome"], it[0]["texto"]) == (1000.5, 18.2, "1 VH1", "Plug")
    assert it[0]["extra"]["permeabilidade"] == 1234.5 and it[0]["extra"]["densidade"] == 2.66
    r = pf.resumo_plugs(d["amostras"])
    assert r["n"] == 3 and r["porosidade"] == {"n": 3, "min": 9.8, "max": 21.0}
    assert r["permeabilidade"]["max"] == 1234.5 and set(r) == {"n", "porosidade", "permeabilidade", "densidade"}
    vazio = pf.resumo_plugs([{"porosidade": None}])
    assert vazio["porosidade"] == {"n": 0, "min": None, "max": None}


def test_no_projeto_dois_arquivos_com_os_mesmos_plugs_ficam_uma_vez(api):
    api.escolher_pasta()
    pasta = os.path.join(api._projeto.pasta, *PASTA.split("/"))
    os.makedirs(pasta)
    pu.plugs(os.path.join(pasta, "1SIAPP 0001  RN-Petrofisica Basica.xlsx"))
    pu.plugs(os.path.join(pasta, "00610.119452.xlsx"), com_data=True)                  # a mesma amostra, com a data
    pu.coregama(os.path.join(pasta, f"{POCO}_COREGAMA.xlsx"))
    api._abrir_projeto(api._projeto.pasta)
    f = api.ficha_poco(POCO)
    it = f["dados_poco"]["itens"]
    plugs = it["plug_testemunho"]
    assert len(plugs) == 3                                     # duas planilhas, três plugs (VH1 e VV na mesma profundidade)
    assert sorted(p["nome"] for p in plugs) == ["1 VH1", "2 VH1", "3 VV"]
    assert all(p.get("tambem_em") for p in plugs)
    assert len(it["gama_testemunho"]) == 4
    assert {d["documento"] for d in f["dados_poco"]["documentos"]} >= {"petrofisica_plugs", "petrofisica_gama"}
    assert "plug_testemunho" in f["dados_poco"]["tipos"] and "gama_testemunho" in f["dados_poco"]["tipos"]
