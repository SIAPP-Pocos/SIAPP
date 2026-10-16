"""AGP da ANP: leitura das seções e gravação no banco.

O arquivo de exemplo (tests/dados/agp_sintetico.txt) tem o MESMO leiaute do AGP
real, com poço e valores inventados — arquivos do REATE não entram no repositório.
"""
import os

import pytest

from motor import agp
from motor.banco import Banco

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXEMPLO = os.path.join(RAIZ, "tests", "dados", "agp_sintetico.txt")


@pytest.fixture
def texto():
    with open(EXEMPLO, "rb") as f:
        return agp.decodificar(f.read())


@pytest.fixture
def est():
    return agp.ler_estratigrafia(os.path.join(RAIZ, "recursos", "estratigrafia.json"))


def test_cabecalho(texto):
    c = agp.ler(texto)["cabecalho"]
    assert c["poco_id"] == "7-TST-1-RN" and c["bacia"] == "POTIGUAR (T)"
    assert c["mesa_rotativa"] == 50.0 and c["prof_final"] == 1200.0
    assert c["lat"] == pytest.approx(-5.2) and c["lon"] == pytest.approx(-36.5)
    assert c["formacao_pf"] == "F PENDEN" and c["direcional"] == "VERTICAL"


def test_unidades_verticalizadas(texto, est):
    us = agp.ler(texto, est)["unidades"]
    porsig = {u["sigla"]: u for u in us}
    acu = porsig["ACU"]
    assert (acu["nome"], acu["nivel"], acu["codigo"], acu["topo"], acu["base"]) == ("Açu", "F", "312010", 300.0, 700.0)
    assert acu["cota_topo"] == -250.0 and acu["fonte"] == "A.G.P. ANTIGO" and acu["data"] == "01/01/1900"
    assert porsig["MORCHA"]["nivel"] == "M" and porsig["MORCHA"]["nome"] == "Morro do Chaves"
    assert porsig["ALAGAM"]["desc_topo"] == "DISCORDANCIA" and porsig["ALAGAM"]["desc_base"] == "FALH.INTERNA"
    assert porsig["PENDEN"]["base"] is None                       # última unidade: sem base
    assert porsig["MARCO L"]["tip"] == "M" and porsig["MARCO L"]["nivel"] == ""
    assert porsig["BFL  PEN"]["fonte"] == "E&P RNCE GEXP/GEINT" and porsig["BFL  PEN"]["data"] == "27/07/1993"
    assert len(us) == 8


def test_linha_sem_letra_de_nivel_e_topo_sem_zero():
    # visto em AGPs reais: 4 espaços antes do nome e topo ".1"
    u = agp.unidades([" L   B    SPA    010004      .1(   50.0)                 3.0 (   47.)"
                      "                E        A.G.P.  ANTIGO               01/01/1900"])[0]
    assert (u["sigla"], u["nivel"], u["topo"], u["base"]) == ("SPA", "", 0.1, 3.0)


def test_corridas_temperaturas_e_zonas(texto):
    r = agp.ler(texto)
    assert len(r["corridas"]) == 1                                 # repetições do mesmo dado viram uma
    c = r["corridas"][0]
    assert (c["rm"], c["t_rm"], c["rmf"], c["t_rmf"], c["bht"]) == (0.156, 102.9, 0.162, 74.8, 136.0)
    assert c["tipo_lama"] == "NACL C/ ACRILAMIDA" and c["data"] == "04/04/1990" and c["prof_alcancada"] == 1200.0
    assert r["temperaturas"] == [{"corrida": "01", "metodo": "DADO NAO REVISTO", "temperatura_f": 144.0,
                                  "prof": 1200.0, "gradiente_f_m": 0.053}]
    assert [(z["codigo"], z["topo"], z["base"]) for z in r["zonas"]] == [("751/ACU0210", 520.0, 548.0),
                                                                       ("757/ACU0230", 560.0, 570.0)]
    assert [(p["tipo"], p["topo"], p["base"]) for p in r["perfis"]] == [("IEL", 100.0, 1199.0), ("CDL", 100.0, 1199.0)]


def test_revestimentos_indicios_testes(texto):
    r = agp.ler(texto)
    assert [(x["tipo"], x["prof"], x["diametro"]) for x in r["revestimentos"]] == [
        ("REV. SUPERFICIE", 100.0, "13 3/8"), ("REV. PRODUCAO", 1195.0, "5 1/2")]
    assert [(i["fluido"], i["topo"], i["base"]) for i in r["indicios"]] == [("óleo", 529.0, 546.0), ("gás", 565.0, 568.0)]
    t = r["testes"][0]
    assert (t["topo"], t["base"], t["salinidade_ppm"]) == (668.5, 684.0, 20000.0)
    assert "AGUA DE FORMACAO" in t["observacoes"]


def test_gravar_no_banco_e_agp_de_outro_poco(tmp_path, texto, est):
    b = Banco(str(tmp_path / "p.sqlite"))
    agp.gravar(b, bacia="Potiguar", caminho="/POCO/x/7-TST-1-RN/AGP/7TST0001RN_agp.txt", poco_caminho="/POCO/x/7-TST-1-RN/",
               poco_pasta="7-TST-1-RN", tamanho=len(texto), texto=texto, estratigrafia=est)
    assert [u["sigla"] for u in agp.unidades_do_poco(b, "7-TST-1-RN")][:3] == ["JANDAI", "A.JIQUIA", "ACU"]
    g = agp.do_poco(b, "7-TST-1-RN")[0]
    assert g["confere"] == 1 and g["dados"]["corridas"][0]["rmf"] == 0.162
    # o portal às vezes guarda na pasta de um poço o AGP de outro
    agp.gravar(b, bacia="Potiguar", caminho="/POCO/x/3-AP-10-RN/AGP/7TST0001RN_agp.txt", poco_caminho="/POCO/x/3-AP-10-RN/",
               poco_pasta="3-AP-10-RN", tamanho=len(texto), texto=texto, estratigrafia=est)
    assert agp.unidades_do_poco(b, "3-AP-10-RN") == []
    assert [x["confere"] for x in agp.do_poco(b, "7-TST-1-RN")] == [1, 0]
    freq = {u["sigla"]: u["pocos"] for u in agp.unidades_frequentes(b)}
    assert freq["ACU"] == 1


def test_texto_que_nao_e_agp(tmp_path):
    b = Banco(str(tmp_path / "p.sqlite"))
    agp.gravar(b, bacia="P", caminho="/x/lixo_agp.txt", poco_caminho="/x/", poco_pasta="1-A-1-RN", tamanho=3,
               texto="qualquer coisa\nsem formato")
    with b.conexao() as c:
        assert c.execute("SELECT erro FROM agp").fetchone()[0].startswith("Não parece um AGP")


def test_eh_agp():
    assert agp.eh_agp("1FL0001RN_agp.txt") and agp.eh_agp("dados.txt", "AGP")
    assert agp.eh_agp("x.txt", "Arquivo_geral_de_poco") and not agp.eh_agp("x.pdf", "AGP")
    assert not agp.eh_agp("leia-me.txt", "Pasta de Poco")


def test_campo_vazio_no_cabecalho_e_litologia(texto):
    r = agp.ler(texto)
    assert r["cabecalho"]["bap"] == 45.0 and r["cabecalho"]["campos"]["QUADRICULA"] == ""
    assert [(x["topo"], x["base"], x["rocha"]) for x in r["litologia"]] == [
        (5.0, 8.0, "CALCARENITO"), (8.0, 13.5, "ARENITO"), (13.5, 20.0, "ARGILITO")]
