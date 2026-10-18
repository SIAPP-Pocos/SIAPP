"""Produção da ANP por campo e camadas geográficas (IBGE, EPE, ANP) — servidores falsos,
arquivos sintéticos nos formatos reais (nenhum arquivo original da ANP/IBGE/EPE no git)."""
import json
import os

import pytest

from motor import camadas as mca
from motor import producao as mpr
from motor.banco import Banco
from externos_util import (CAMPOS, PT_ANTIGO, PT_NOVO, URL_PT_NOVO, VERTICES, ZONA, SessaoFalsa, _dbf, _shp,
                           pdf_pd, shapefile_campos, zipar)


# ------------------------------------------------------------------ leitores
def test_numeros_e_chaves():
    assert mpr.numero("2.619,83") == 2619.83 and mpr.numero(",0035") == 0.0035 and mpr.numero("7") == 7
    assert mpr.numero("") is None and mpr.numero("abc") is None and mpr.numero("0,000") == 0
    assert mpr.chave_campo("Guamaré") == mpr.chave_campo("GUAMARÉ") == "GUAMARE"
    assert mpr.chave_campo("Canto do Amaro") == "CANTO DO AMARO"


def test_producao_por_poco_nos_dois_cabecalhos():
    novo = mpr.ler_producao_poco(PT_NOVO.encode("utf-8"), "campo teste")
    assert len(novo) == 4 and {r["periodo"] for r in novo} == {"2026-05", "2026-06"}
    r = next(x for x in novo if x["poco"] == "1-AA-1-RN" and x["periodo"] == "2026-05")
    assert r["oleo_m3"] == 186.18 and r["gas_assoc_mil_m3"] == 0.23 and r["agua_m3"] == 2619.83
    assert r["inj_agua_rec_m3"] is None and r["instalacao"] == "Estação Coletora A"
    inj = next(x for x in novo if x["poco"] == "8-AA-9-RN")
    assert inj["oleo_m3"] is None and inj["inj_agua_rec_m3"] == 1500 and inj["inj_agua_desc_m3"] == 8.9
    antigo = mpr.ler_producao_poco(PT_ANTIGO.encode("utf-8"))
    assert len(antigo) == 2 and antigo[0]["oleo_m3"] == 858.1 and antigo[0]["periodo"] == "1983-01"
    # cp1252 sem BOM (como alguns arquivos da ANP)
    cp = mpr.ler_producao_poco(PT_NOVO.replace("﻿", "").encode("cp1252"), "CAMPO TESTE")
    assert len(cp) == 4 and cp[0]["instalacao"] == "Estação Coletora A"
    with pytest.raises(mpr.ErroProducao):
        mpr.ler_producao_poco(b"a,b,c\n1,2,3\n")


def test_producao_por_zona_vira_volume_do_mes():
    z = mpr.ler_producao_zona(ZONA.encode("utf-8"), "Campo Teste")
    assert len(z) == 2 and z[0]["zona"] == "AÇU0250 FSP-2" and z[0]["dias"] == 31
    assert z[0]["oleo_m3"] == pytest.approx(62.0) and z[0]["agua_m3"] == pytest.approx(310.0)


def test_ficha_e_poligono_do_campo():
    f = {c["chave"]: c for c in mpr.ler_campos(CAMPOS.encode("utf-8"))}
    assert f["CAMPO TESTE"]["inicio_producao"] == "31/01/1983" and f["CAMPO MAR"]["ambiente"] == "Mar"
    v = mpr.ler_vertices(VERTICES.encode("utf-8"), "Campo Teste")
    assert v == [[-5.0, -37.0], [-5.0, -36.95], [-5.05, -36.95]]                # na ordem dos vértices


def test_sumario_do_pd():
    d = mpr.ler_pd(pdf_pd())
    assert d["titulo"] == "Campo Teste" and d["ano"] == 2023 and d["resolucao"] == "0030/2023"
    assert d["area_km2"] == 70.17 and d["inicio_producao"] == "01/1983" and d["bacia"] == "Potiguar"
    assert d["pocos"] == {"data": "12/2022", "perfurados": 148, "produtores": 77, "injetores": 5}
    assert d["in_place"] == {"data": "31/12/2021", "oleo_milhoes_m3": 13.8, "gas_total_milhoes_m3": 596.38}
    assert d["acumulada"]["oleo_milhoes_m3"] == 1.4 and d["acumulada"]["gas_total_milhoes_m3"] == 251.72
    assert d["fonte"] == "BAR/2021" and "Formação Açu" in d["reservatorios"]


def test_lista_de_arquivos_e_periodos():
    from externos_util import pagina_producao
    a = mpr.arquivos_producao(pagina_producao())
    tipos = sorted((x["tipo"], x["ambiente"], x["ano_ini"], x["ano_fim"]) for x in a)
    assert ("poco", "terra", 1983, 1983) in tipos and ("poco", "terra", 2015, 2015) in tipos
    assert ("poco", "mar", 2026, 2026) in tipos and sum(1 for t in tipos if t[0] == "zona") == 2
    assert [x["ano_ini"] for x in mpr.escolher(a, "poco", "terra", 2010, 2026)] == [2015, 2026]
    assert mpr._anos("x/pt/2024/producao-por-poco-terra-trim-3.csv") == (2024, 2024)
    assert mpr._anos("x/pt/2019/producaoterra20191trim.csv") == (2019, 2019)
    assert mpr._anos("x/pt/1982-1941/producao-terra-1981-1982.csv") == (1981, 1982)
    assert mpr.url_pd('<a href="/anp/pd/guamare_sudeste.pdf">x</a>', "Guamaré Sudeste").endswith("guamare_sudeste.pdf")


# ------------------------------------------------------------------ baixar e guardar
def test_baixar_producao_guarda_no_banco_e_reaproveita(tmp_path):
    b = Banco(str(tmp_path / "p.sqlite"))
    s = SessaoFalsa()
    msgs = []
    f = mpr.baixar(b, str(tmp_path), "Campo Teste", progresso=msgs.append, sessao=s)
    assert f["ambiente"] == "terra" and f["ano_ini"] == 1983 and f["pd"] is True
    assert f["linhas_poco"] == 1 + 1 + 4 and f["linhas_zona"] == 4 and f["arquivos"] == 5 and not f["avisos"]
    r = mpr.resumo(b, "CAMPO TESTE")
    assert r["poco"]["de"] == "1983-01" and r["poco"]["ate"] == "2026-06" and r["poco"]["pocos"] == 3
    assert r["poco"]["oleo_m3"] == pytest.approx(858.1 + 100.5 + 186.18 + 36.08 + 180)
    assert r["ultimo_mes"]["periodo"] == "2026-06" and r["ultimo_mes"]["produtores"] == 1
    assert r["ultimo_mes"]["injetores"] == 1
    assert r["zona"]["zonas"] == 2 and r["zona"]["de"] == "2026-04"
    assert r["ficha"]["pd"]["in_place"]["oleo_milhoes_m3"] == 13.8 and len(r["ficha"]["poligono"]) == 3
    assert [a["ano"] for a in r["anos"]] == ["1983", "2015", "2026"]
    with b.conexao() as c:
        assert c.execute("SELECT poco_id FROM producao_poco WHERE poco_anp = '1-AA-1-RN' LIMIT 1").fetchone()[0] == "1-AA-1-RN"
    # cópia local: baixar de novo não pede os CSVs da ANP outra vez, nem duplica linhas
    n_antes = len([p for p in s.pedidos if p.endswith(".csv") and "/pt/" in p])
    f2 = mpr.baixar(b, str(tmp_path), "Campo Teste", sessao=s)
    assert f2["mb_baixados"] < 0.01
    assert len([p for p in s.pedidos if p.endswith(".csv") and "/pt/" in p]) == n_antes
    assert mpr.resumo(b, "Campo Teste")["poco"]["linhas"] == 6
    assert os.path.exists(tmp_path / mpr.PASTA_CACHE)
    cols, linhas = mpr.linhas_csv(b, "Campo Teste")
    assert len(linhas) == 6 and cols[0] == "poco_anp"


def test_baixar_periodo_mar_e_erros(tmp_path):
    b = Banco(str(tmp_path / "p.sqlite"))
    f = mpr.baixar(b, str(tmp_path), "Campo Teste", ano_ini=2020, zona=False, pd=False, sessao=SessaoFalsa())
    assert f["ano_ini"] == 2020 and f["arquivos"] == 1 and f["linhas_zona"] == 0
    m = mpr.baixar(b, str(tmp_path), "Campo Mar", zona=False, sessao=SessaoFalsa())
    assert m["ambiente"] == "mar" and m["linhas_poco"] == 3
    assert any("Plano de Desenvolvimento" in a for a in m["avisos"])
    with pytest.raises(mpr.ErroProducao):
        mpr.baixar(b, str(tmp_path), "Campo Inexistente", sessao=SessaoFalsa())
    # cancelar no meio
    with pytest.raises(mpr.Cancelado):
        mpr.baixar(b, str(tmp_path / "outro"), "Campo Teste", sessao=SessaoFalsa(), cancelar=lambda: True)


def test_arquivo_que_falha_vira_aviso(tmp_path):
    s = SessaoFalsa()
    del s.arquivos[URL_PT_NOVO]
    f = mpr.baixar(Banco(str(tmp_path / "p.sqlite")), str(tmp_path), "Campo Teste", sessao=s)
    assert any("404" in a for a in f["avisos"]) and f["linhas_poco"] == 2


# ------------------------------------------------------------------ camadas
def test_shapefile_poligono_com_buraco_e_dbf():
    a = shapefile_campos()
    g = mca.shapefile_geojson(a["CAMPOS.shp"], a["CAMPOS.dbf"])
    assert len(g["features"]) == 1
    f = g["features"][0]
    assert f["geometry"]["type"] == "Polygon" and len(f["geometry"]["coordinates"]) == 2      # externo + buraco
    assert f["properties"] == {"NOM_CAMPO": "CAMPO TESTE", "AREA": 70}
    assert mca.caixa(g) == [-37.0, -5.05, -36.95, -5.0]
    pts = mca.shapefile_geojson(_shp(1, [(-36.5, -5.5)]), _dbf([("nome", "C", 20)], [{"nome": "Usina Açu"}]))
    assert pts["features"][0]["geometry"] == {"type": "Point", "coordinates": [-36.5, -5.5]}
    assert pts["features"][0]["properties"]["nome"] == "Usina Açu"                          # cp1252 pelo LDID


def test_zip_remoto_le_so_os_pedacos():
    s = SessaoFalsa()
    z = mca.ZipRemoto(s.zip_ibge_url, s)
    nome = z.procurar("/dut_trecho_duto_l.dbf")
    assert nome == "bc250/dut_trecho_duto_l.dbf"
    dbf = z.ler(nome)
    assert mca.ler_dbf(dbf)[0]["nome"] == "Gasoduto Nordestão"
    assert all("[bytes=" in p or p.startswith("HEAD") for p in s.pedidos if s.zip_ibge_url in p)


def test_epe_em_paginas():
    s = SessaoFalsa()
    g = mca.epe_feicoes(55, s)
    assert len(g["features"]) == 1500 and sum(1 for p in s.pedidos if "/55/query" in p) == 2
    assert "OBJECTID" not in g["features"][0]["properties"] and g["features"][0]["properties"]["Diam_Pol_x"] == "14"


def test_baixar_camadas_guarda_geojson_shapefile_e_indice(tmp_path):
    s = SessaoFalsa()
    r = mca.baixar(str(tmp_path), ["epe_gasodutos_transporte", "anp_campos_producao", "ibge_dutos",
                                   "anp_blocos_exploratorios", "ibge_rodovias"], sessao=s)
    feitos = {f["id"]: f for f in r["feitos"]}
    assert set(feitos) == {"epe_gasodutos_transporte", "anp_campos_producao", "ibge_dutos"}
    assert {e["id"] for e in r["erros"]} == {"anp_blocos_exploratorios", "ibge_rodovias"}
    assert feitos["ibge_dutos"]["feicoes"] == 2 and feitos["epe_gasodutos_transporte"]["feicoes"] == 1500
    g = json.load(open(tmp_path / "sig" / "ibge" / "ibge_dutos.geojson", encoding="utf-8"))
    assert g["features"][1]["geometry"]["type"] == "MultiLineString"
    assert g["features"][0]["properties"]["nome"] == "Gasoduto Nordestão"
    assert (tmp_path / "sig" / "ibge" / "ibge_dutos" / "dut_trecho_duto_l.shp").exists()
    assert (tmp_path / "sig" / "anp" / "anp_campos_producao" / "CAMPOS.prj").exists()
    idx = mca.indice(str(tmp_path))
    assert set(idx["camadas"]) == set(feitos) and idx["camadas"]["ibge_dutos"]["caixa"]
    cat = {c["id"]: c for c in mca.catalogo_com_estado(str(tmp_path))}
    assert cat["ibge_dutos"]["baixada"]["feicoes"] == 2 and cat["ibge_estados"]["baixada"] is None
    with pytest.raises(mca.ErroCamadas):
        mca.baixar(str(tmp_path), ["nao_existe"], sessao=s)


def test_zip_sem_range_da_erro_claro():
    class SemRange(SessaoFalsa):
        def _get(self, url, params=None, headers=None):
            r = super()._get(url, params, None)
            return r
    s = SemRange()
    with pytest.raises(mca.ErroCamadas, match="pedaço"):
        mca.ZipRemoto(s.zip_ibge_url, s)
    assert zipar({"a": b"1"})[:2] == b"PK"
