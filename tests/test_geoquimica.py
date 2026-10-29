"""Geoquímica (0.43): planilha XML 2003 sintética com isótopos de gás e geoquímica de rocha."""
import os

import pytest

from motor import dados_poco as mdp
from motor import geoquimica as mgq
from motor import pocos as mpo

POCO = "1-SIAPP-1-RN"
PASTA = f"bruto/Potiguar/{POCO}/Dados De Rochas e Fluidos/GEOQUIMICADEFLUIDO"


def _celula(v, formula=None, html=False, idx=None):
    a = (f' ss:Formula="{formula}"' if formula else "") + (f' ss:Index="{idx}"' if idx else "")
    if html:
        return (f'<Cell{a}><ss:Data ss:Type="String" xmlns="http://www.w3.org/TR/REC-html40"><B><Font>d</Font>'
                f'<Sup><Font>13</Font></Sup><Font>{v}</Font></B></ss:Data></Cell>')
    tipo = "Number" if isinstance(v, (int, float)) else "String"
    return f'<Cell{a}><Data ss:Type="{tipo}">{v}</Data></Cell>'


def xml_geoquimica(caminho, *, metano=("47.39", "=--47.39"), rocha=True):
    linhas1 = [
        [_celula(x) for x in ("Poço ANP", "Registro (BR)", "Poço", "Prof. (m)", "Tipo de Amostra", "Bacia")],
        [_celula(x) for x in (POCO, "123", "1-ABC-0001-RN", "1395/1400", "Gás", "Potiguar")],
        [_celula("Anexo")],
        [_celula("Poço (Sigla)"), _celula("Prof. (m)"), _celula("C Metano (‰)", html=True),
         _celula("C Etano (‰)", html=True), _celula("C Propano (‰)", html=True)],
        [_celula(POCO), _celula("1395/1400"), _celula(float(metano[0]), formula=metano[1]), _celula(-31.61), _celula(-27.38)],
    ]
    linhas2 = [[_celula(x) for x in ("Prof. (m)", "COT (%)", "S1 (mg HC/g)", "S2 (mg HC/g)", "Tmax (°C)", "IH")],
               [_celula(x) for x in ("1.200", 2.5, 1.1, 8.2, 438, 328)],
               [_celula("1250"), _celula(1.8), _celula(0.5), _celula(4.0), _celula(440, idx=5)]]
    def aba(nome, linhas):
        return (f'<Worksheet ss:Name="{nome}"><Table>' + "".join("<Row>" + "".join(ln) + "</Row>" for ln in linhas)
                + "</Table></Worksheet>")
    xml = ('<?xml version="1.0"?><?mso-application progid="Excel.Sheet"?>'
           '<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" '
           'xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">' + aba("Amostra", linhas1)
           + (aba("Rocha", linhas2) if rocha else "") + "</Workbook>")
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(xml)
    return caminho


def test_reconhece_e_numeros():
    assert mgq.reconhece(f"{PASTA}/Envio de Resultados_ANP_d13C_GC-IR2_x.xml")
    assert not mgq.reconhece(f"bruto/P/{POCO}/Dados De Rochas e Fluidos/PVT/x.xls")
    assert mdp.leitor_para(f"{PASTA}/x.xml") == "geoquimica"
    assert mgq.numero("--47,39") == -47.39 and mgq.numero("47.39") == 47.39 and mgq.numero("-") is None
    assert mgq._prof("1680/1684") == (1680.0, 1684.0) and mgq._prof("1.682,5") == (1682.5, None)
    assert mgq._prof("1.200") == (1200.0, None) and mgq._prof("1.680/1.684") == (1680.0, 1684.0)


def test_leitura_dos_isotopos():
    assert mgq.leitura_isotopos(-47.4, -31.6, -27.4) == "gás termogênico; ordem normal (C1 < C2 < C3)"
    assert mgq.leitura_isotopos(-70.0, None, None) == "gás biogênico"
    assert mgq.leitura_isotopos(-55.0, -40.0, -42.0).startswith("gás misto ou de transição; ordem invertida")
    assert mgq.leitura_isotopos(None, -30, -28) is None


def test_planilha_xml(tmp_path):
    d = mgq.ler(xml_geoquimica(str(tmp_path / "g.xml")))
    iso = d["isotopos"][0]
    assert (iso["topo"], iso["base"], iso["C1"], iso["C2"], iso["C3"]) == (1395.0, 1400.0, -47.39, -31.61, -27.38)
    assert "sinal duplo" in d["avisos"][0] and "−47,39" in d["avisos"][0]
    assert d["amostra"]["tipo_amostra"] == "Gás" and d["apelidos"] == ["1-ABC-0001-RN"]
    assert [(r["topo"], r["cot"], r["s2"], r["tmax"], r["ih"]) for r in d["rocha"]] == [
        (1200.0, 2.5, 8.2, 438.0, 328.0), (1250.0, 1.8, 4.0, 440.0, None)]     # ss:Index pula a coluna IH
    tipos = [i["tipo"] for i in mgq.itens(d)]
    assert tipos == ["isotopo_gas", "geoquimica_rocha", "geoquimica_rocha"]


def test_positivo_sem_sinal_duplo_fica_com_aviso(tmp_path):
    d = mgq.ler(xml_geoquimica(str(tmp_path / "g.xml"), metano=("47.39", None), rocha=False))
    assert d["isotopos"][0]["C1"] == 47.39 and "confira" in d["avisos"][0]


def test_nao_e_geoquimica(tmp_path):
    (tmp_path / "x.xml").write_text("<a/>", encoding="utf-8")
    with pytest.raises(mgq.ErroGeoquimica):
        mgq.ler(str(tmp_path / "x.xml"))
    (tmp_path / "y.xml").write_text("<a", encoding="utf-8")
    with pytest.raises(mgq.ErroGeoquimica):
        mgq.ler(str(tmp_path / "y.xml"))


def test_ficha_e_apelido_com_origem(api):
    api.escolher_pasta()
    pasta = os.path.join(api._projeto.pasta, *PASTA.split("/"))
    os.makedirs(pasta)
    xml_geoquimica(os.path.join(pasta, "Envio de Resultados_ANP_d13C.xml"))
    api._abrir_projeto(api._projeto.pasta)
    f = api.ficha_poco(POCO)
    it = f["dados_poco"]["itens"]
    assert it["isotopo_gas"][0]["valor"] == -47.39 and len(it["geoquimica_rocha"]) == 2
    doc = f["dados_poco"]["documentos"][0]
    assert doc["documento"] == "geoquimica" and "sinal duplo" in doc["avisos"][0]
    assert mpo.resolver(api._banco, "1-ABC-1-RN") == POCO
    assert {"chave": mpo.chave("1-ABC-0001-RN"), "origem": "geoquimica"} in f["apelidos_origem"]
