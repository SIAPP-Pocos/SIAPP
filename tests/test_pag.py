"""Perfil de Acompanhamento Geológico (0.40): curvas de lama e gás e descrição de calha, sintéticas."""
import os

import lasio
import numpy as np
import pytest

from motor import banco as mb
from motor import dados_poco as mdp
from motor import pag
from motor import perfis as mpf

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POCO = "1-SIAPP-1-RN"
PASTA = f"bruto/Potiguar/{POCO}/Perfil de Acompanhamento Geologico"

# cabeçalho como o da planilha do REATE (duas linhas: grupos e subcolunas)
CAB1 = ["PROF. (m)", "TIPO DE \nROCHA", "PERC. NA \nAMOSTRA (%)", "COR", "TONALIDADE", "TEXTURA", "", "",
        "COMPOSIÇÃO", "", "ESTR.", "MATRIZ / CIMENTO", "", "POR", "COESÃO", "MODO", "", "", "FLUOREC0ÊNCIA", "", "",
        "", "CORTE", "", "DESCRIÇÕES E OBSERVAÇÕES", "FORMAÇÃO GEOLÓGICA"]
CAB2 = ["", "", "", "", "", "GRAN", "ARRED", "SEL", "PRINC", "ACESS", "", "MTZ", "CMT", "(APAR)", "", "MCH", "IMP",
        "ODR", "TIPO", "PERC. (%)", "COR", "TON ", "VELOC", "MD. DISSEM.", "", ""]


def _linha(prof="", rocha="", pct="", fluor=("", "", "", ""), corte=("", ""), desc="", formacao=""):
    ln = [""] * 26
    ln[0], ln[1], ln[2], ln[24], ln[25] = prof, rocha, pct, desc, formacao
    ln[18:22] = list(fluor)
    ln[22:24] = list(corte)
    return ln


def linhas_dac():
    vazio = [""] * 26
    return [CAB1, CAB2, vazio,
            _linha("9", "ARN", "100", desc="AMR / MED", formacao="Barreiras"), vazio,
            _linha("18", "ARN", "70", desc="AMR", formacao="Barreiras"),
            _linha("", "FLH", "30"),
            _linha("27", "CLU", "100", formacao="Jandaira"),
            _linha("30", "ARN", "80", fluor=("EP", "20", "AMR", "OUR"), corte=("66", "RD"), formacao="Acu"),
            _linha("", "XYZ", "20"),
            _linha("33", "FLH", "100", formacao="Acu")]


def las_pag(caminho):
    prof = np.arange(1.0, 301.0, 1.0)
    gas = np.full_like(prof, 1000.0)
    gas[(prof >= 100) & (prof <= 110)] = 8000.0          # zona de gás de 11 m
    gas[200] = 9000.0                                     # pico isolado (1 m): não é zona
    c1, c2, c3 = gas * 0.7, gas * 0.15, gas * 0.1
    sal = np.full_like(prof, np.nan)
    sal[[49, 149]] = [150000.0, 200000.0]
    las = lasio.LASFile()
    las.well["WELL"].value = POCO
    las.append_curve("DEPT", prof, unit="M")
    for nome, v, u in (("HYDC", gas, "ppm"), ("METH", c1, "ppm"), ("ETH", c2, "ppm"), ("PRP", c3, "ppm"),
                       ("SAL", sal, "ppm"), ("DENS", np.full_like(prof, 9.4), "lb/gal"), ("ROP", np.full_like(prof, 5.0), "min/m")):
        las.append_curve(nome, v, unit=u)
    las.write(str(caminho), version=2.0)


def xlsx(caminho, linhas):
    import openpyxl
    wb = openpyxl.Workbook()
    wb.active.title = "Header"
    ws = wb.create_sheet("Descrição")
    for ln in linhas:
        ws.append(ln)
    wb.save(caminho)


def test_reconhece_pelo_caminho():
    assert pag.tipo_pelo_nome(f"{PASTA}/{POCO}_PAG_curvas.las") == "pag_curvas"
    assert pag.tipo_pelo_nome(f"{PASTA}/{POCO}_PAG_DAC.xls") == "pag_dac"
    assert pag.tipo_pelo_nome(f"{PASTA}/{POCO}_PAG_ANP.pdf") is None
    assert pag.tipo_pelo_nome(f"bruto/P/{POCO}/Perfil Convencional/x.las") is None
    assert mdp.leitor_para(f"{PASTA}/{POCO}_PAG_DAC.xlsx") == "pag"


def test_zonas_de_gas_e_razoes_de_haworth():
    prof = np.arange(0.0, 100.0)
    gas = np.full_like(prof, 500.0)
    gas[40:46] = 5000.0
    gas[43] = 1000.0                       # uma leitura baixa no meio não parte a zona
    z = pag.zonas_gas(prof, gas)
    assert z["fundo"] == 500.0 and [(x["topo"], x["base"]) for x in z["zonas"]] == [(40.0, 45.0)]
    assert z["zonas"][0]["vezes_fundo"] == 10.0
    seco = pag.razoes_haworth({"C1": 990.0, "C2": 3.0, "C3": 1.0})
    assert seco["wh"] < 0.5 and seco["haworth"] == "gás muito seco"
    oleo = pag.razoes_haworth({"C1": 60.0, "C2": 20.0, "C3": 15.0, "C4": 4.0, "C5": 1.0})
    assert oleo["wh"] == 40.0 and oleo["haworth"] == "óleo residual ou pesado"
    assert pag.razoes_haworth({"C1": 70.0, "C2": 15.0, "C3": 10.0})["haworth"].startswith("óleo")
    assert pag.razoes_haworth({"C2": 1.0}) == {}


def test_rw_de_nacl_pela_salinidade():
    assert pag.rw_salinidade(200000) == pytest.approx(0.0443, abs=0.002)        # ~0,045 Ω·m a 75 °F
    assert pag.rw_salinidade(20000) > 0.25 and pag.rw_salinidade(0) is None
    assert pag.rw_salinidade(200000, 200.0) < pag.rw_salinidade(200000)         # mais quente, menor


def test_curvas_las(tmp_path):
    las_pag(tmp_path / "p.las")
    d = pag.ler_curvas(str(tmp_path / "p.las"))
    assert d["documento"] == "pag_curvas" and d["cromatografia"] == ["C1", "C2", "C3"]
    zs = d["gas"]["zonas"]
    assert [(z["topo"], z["base"]) for z in zs] == [(100.0, 110.0)] and zs[0]["vezes_fundo"] == 8.0
    assert zs[0]["haworth"].startswith("óleo")                                   # Wh = 25
    assert [(s["prof"], s["ppm"]) for s in d["salinidade"]] == [(50.0, 150000.0), (150.0, 200000.0)]
    assert d["lama"] == {"peso_min_lb_gal": 9.4, "peso_max_lb_gal": 9.4}
    tipos = [i["tipo"] for i in pag.itens(d)]
    assert tipos == ["gas_lama", "salinidade_lama", "salinidade_lama"]


def test_familias_novas_e_unidade_que_desempata():
    cl = mpf.Classificador(mpf.ler_familias(os.path.join(RAIZ, "recursos", "mnemonicos.json")))
    assert cl.familia("HYDC", "ppm") == "GAS_TOTAL" and cl.familia("METH", "ppm") == "GAS_C1"
    assert cl.familia("DENS", "lb/gal") == "LAMA_PESO" and cl.familia("ROP", "min/m") == "ROP"
    assert cl.familia("DENS", "g/cm3") != "LAMA_PESO"          # densidade em g/cm³ não é o peso da lama
    assert cl.familia("RHOB", "g/cm3") == "RHOB"
    inv = {"quadros": [{"curvas": [{"mnemonico": "HYDC", "unidade": "ppm", "familia": None}]}]}
    assert cl.reclassificar(inv)["quadros"][0]["curvas"][0]["familia"] == "GAS_TOTAL"


def test_descricao_de_calha():
    d = pag.ler_dac_linhas(linhas_dac())
    a = d["amostras"]
    assert [x["prof"] for x in a] == [9.0, 18.0, 27.0, 30.0, 33.0]
    assert [x["base"] for x in a] == [18.0, 27.0, 30.0, 33.0, 33.0]
    assert [(r["codigo"], r["pct"]) for r in a[1]["rochas"]] == [("ARN", 70.0), ("FLH", 30.0)]
    assert a[2]["principal"]["nome"] == "CALCILUTITO" and a[3]["rochas"][1]["nome"] == "XYZ"   # código desconhecido fica
    assert a[3]["fluorescencia"] == {"fluor_tipo": "EP", "fluor_pct": "20", "fluor_cor": "AMR", "fluor_ton": "OUR"}
    assert a[3]["corte"] == {"velocidade": "66", "modo": "RD"} and a[0]["descricao"] == "AMR / MED"
    assert [(t["formacao"], t["prof"], t["acima"]) for t in d["topos"]] == [
        ("Barreiras", 9.0, None), ("Jandaira", 27.0, 18.0), ("Acu", 30.0, 27.0)]
    its = pag.itens(d)
    assert sum(i["tipo"] == "litologia_calha" for i in its) == 5
    ind = [i for i in its if i["tipo"] == "indicio_calha"]
    assert len(ind) == 1 and ind[0]["valor"] == 20.0 and ind[0]["nome"] == "Acu"
    with pytest.raises(pag.ErroPAG):
        pag.ler_dac_linhas([["x"], ["y"], ["z"]])


def _projeto(tmp_path):
    pasta = tmp_path / "proj"
    (pasta / PASTA).mkdir(parents=True)
    las_pag(pasta / PASTA / f"{POCO}_PAG_curvas.las")
    xlsx(str(pasta / PASTA / f"{POCO}_PAG_DAC.xlsx"), linhas_dac())
    b = mb.Banco(str(pasta / "projeto.sqlite"))
    for nome, tipo in ((f"{POCO}_PAG_curvas.las", "perfil"), (f"{POCO}_PAG_DAC.xlsx", "outro")):
        b.registrar_arquivo(f"{PASTA}/{nome}", bacia="Potiguar", poco_id=POCO, tipo=tipo)
    return str(pasta), b


def test_lido_no_projeto(tmp_path):
    pasta, b = _projeto(tmp_path)
    lidos = mdp.ler_pendentes(b, pasta)
    assert sorted(r["documento"] for r in lidos) == ["pag_curvas", "pag_dac"] and not any(r["erro"] for r in lidos)
    assert [t["nome"] for t in mdp.itens_do_poco(b, POCO, "topo_calha")] == ["Barreiras", "Jandaira", "Acu"]
    assert len(mdp.itens_do_poco(b, POCO, "gas_lama")) == 1
    assert mdp.pendentes(b) == []


def test_biblioteca_que_falta_nao_grava(tmp_path, monkeypatch):
    pasta, b = _projeto(tmp_path)

    def sem_openpyxl(caminho):
        raise ModuleNotFoundError("No module named 'openpyxl'", name="openpyxl")
    monkeypatch.setattr(pag, "ler_dac", sem_openpyxl)
    r = mdp.ler_arquivo(b, pasta, f"{PASTA}/{POCO}_PAG_DAC.xlsx", poco_id=POCO)
    assert "openpyxl" in r["erro"] and b.contar("leituras") == 0     # fica pendente para a próxima abertura
    assert len(mdp.pendentes(b)) == 2


def test_ponte_perfis_e_avaliacao(api):
    api.escolher_pasta()
    pasta = os.path.join(api._projeto.pasta, *PASTA.split("/"))
    os.makedirs(pasta)
    las_pag(os.path.join(pasta, f"{POCO}_PAG_curvas.las"))
    xlsx(os.path.join(pasta, f"{POCO}_PAG_DAC.xlsx"), linhas_dac())
    api._abrir_projeto(api._projeto.pasta)
    fp = api._formularios_perfil(POCO)
    assert [c["rocha"] for c in fp["litologia_calha"]][:3] == ["ARENITO", "ARENITO", "CALCILUTITO"]
    assert fp["topos_calha"][1] == {"nome": "Jandaira", "topo": 27.0}
    ints = {i["id"]: i for i in api._intervalos_formularios(POCO)}
    z = ints["rfp:gas_lama:100-110"]
    assert z["origem"] == "PAG" and z["nome"].startswith("Gás na lama · 8,0 × o fundo")
    f = api.ficha_poco(POCO)
    assert {d["documento"] for d in f["dados_poco"]["documentos"]} == {"pag_curvas", "pag_dac"}
    assert len(f["dados_poco"]["itens"]["salinidade_lama"]) == 2
