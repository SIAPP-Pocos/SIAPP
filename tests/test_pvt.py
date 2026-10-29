"""Análise PVT (0.39): planilhas sintéticas no formato do REATE, uso na ficha e na viabilidade."""
import pytest

from motor import banco as mb
from motor import dados_poco as mdp
from motor import economia as mec
from motor import fluidos as mfl
from motor import pocos as mpo
from motor import pvt

AMOSTRA_CAB = ["Nome do Poco\nPetrobras", "Nome do poço\nANP", "Tipo Amostragem", "Topo \n(m)", "Base \n(m)",
               "Temperatura (ºC)", "Dg liberado Tanque", "Grau API Tanque", "RGO Tanque \n(m³ Std/m³ Std)",
               "Dg Média Lib Dif", "Grau API Óleo Lib Dif", "Temperatura Lib Dif (°C)", "Fluido da Amostra"]
AMOSTRA = ["1-ABC-1-RN", "1-SIAPP-1-RN", "Amostra de fundo", "1395", "1400", "71,5", "0,9500", "31,20", "60,00",
           "0,850", "30,90", "71,5", "OLEO"]
DIF_CAB = ["Pressão (Kgf/cm²)", "Bo (m³/m³Std)", "Rs\n(m³Std/m³Std)", "Viscosidade do Óleo (cP)",
           "Massa específica do Óleo (g/cm³) ", "Bg (m³/m³Std)", "Dens. Gás (ar=1,00)", "Z do Gás Produzido",
           "Viscosidade do gás (cP)"]
# p, Bo, Rs, μo, ρo, Bg, dg, Z, μg — saturação a 120 kgf/cm² (maior Bo)
DIF = [("300", "1,2000", "70,00", "2,10", "0,7900", "-", "-", "-", "-"),
       ("200", "1,2100", "70,00", "2,00", "0,7850", "-", "-", "-", "-"),
       ("120", "1,2200", "70,00", "1,90", "0,7800", "-", "-", "-", "-"),
       ("90", "1,1800", "55,00", "2,20", "0,7900", "0,01200", "0,80", "0,89", "0,015"),
       ("50", "1,1300", "35,00", "2,60", "0,8000", "0,02200", "0,85", "0,93", "0,013"),
       ("0", "1,0400", "0", "4,00", "0,8200", "-", "1,30", "-", "-")]
FLASH_CAB = ["Densidade Ult Comp", "Massa Mol Ult Comp", "Componente", "Último Componente", "Óleo estabilizado (%)",
             "Componente Gás (%)", "Fluido Reservatório (%)"]
FLASH = [("-", "-", "C2", "-", "0", "12,0", "6,0"), ("0,8800", "420", "C20", "S", "40,0", "0", "18,0"),
         ("-", "-", "C1", "-", "0", "60,0", "30,0"), ("-", "-", "CO2", "-", "0", "1,0", "0,5"),
         ("-", "-", "N2", "-", "0", "0,5", "0,3"), ("-", "-", "C10", "-", "5,0", "0", "2,0")]


def diferencial():
    return [AMOSTRA_CAB + DIF_CAB] + [AMOSTRA + list(r) for r in DIF] + [[""] * 22]


def flash():
    return [AMOSTRA_CAB + FLASH_CAB] + [AMOSTRA + list(r) for r in FLASH]


def xlsx(caminho, linhas):
    import openpyxl
    wb = openpyxl.Workbook()
    for ln in linhas:
        wb.active.append(ln)
    wb.save(caminho)
    return caminho


def test_reconhece_e_numeros():
    assert pvt.reconhece("bruto/Rec/1-X-1-BA/Dados De Rochas e Fluidos/PVT/1-X-1-BA-PVT Liberação Diferencial .xls")
    assert pvt.reconhece("bruto/Rec/1-X-1-BA/Dados De Rochas e Fluidos/PVT/qualquer.xlsx")
    assert not pvt.reconhece("bruto/Rec/1-X-1-BA/Perfil de Acompanhamento Geologico/1-X_PAG_DAC.xls")
    assert pvt.numero("1,3678") == 1.3678 and pvt.numero("-") is None and pvt.numero(12) == 12.0
    assert pvt.numero("1.234,5") == 1234.5


def test_liberacao_diferencial_saturacao_e_interpolacao():
    d = pvt.ler_linhas(diferencial())
    assert d["documento"] == "pvt_diferencial" and d["apelidos"] == ["1-ABC-1-RN"]
    a = d["amostra"]
    assert a["poco"] == "1-SIAPP-1-RN" and (a["topo"], a["base"]) == (1395.0, 1400.0) and a["api_tanque"] == 31.2
    assert a["temp_lib_dif_c"] == 71.5 and a["dg_lib_dif"] == 0.85
    assert [r["p_kgf_cm2"] for r in d["tabela"]] == [300, 200, 120, 90, 50, 0]
    s = d["saturacao"]
    assert (s["p_kgf_cm2"], s["bo"], s["rs"]) == (120.0, 1.22, 70.0) and s["p_bar"] == pytest.approx(117.68, abs=0.01)
    assert s["co_por_kgf_cm2"] == pytest.approx(0.02 / 180 / 1.21, rel=1e-3)
    assert d["tabela"][3]["bg"] == 0.012 and d["tabela"][0]["bg"] is None
    assert pvt.interpolar(d["tabela"], "bo", 160) == pytest.approx(1.215)
    assert pvt.interpolar(d["tabela"], "bo", 999) == 1.2 and pvt.interpolar(d["tabela"], "bg", 70) == pytest.approx(0.017)
    it = pvt.itens(d)[0]
    assert it["tipo"] == "pvt" and it["valor"] == 120.0 and it["extra"]["n_estagios"] == 6


def test_flash_composicao():
    d = pvt.ler_linhas(flash())
    assert d["documento"] == "pvt_flash" and d["amostra"]["densidade_ultimo"] == 0.88
    assert [c["componente"] for c in d["componentes"]] == ["N2", "CO2", "C1", "C2", "C10", "C20"]
    assert d["componentes"][5]["ultimo"] == "S" and d["componentes"][0]["ultimo"] is None
    it = pvt.itens(d)[0]
    assert it["valor"] == 30.0 and it["extra"]["co2_pct"] == 0.5 and it["extra"]["massa_molar_ultimo"] == 420.0


def test_planilha_que_nao_e_pvt(tmp_path):
    with pytest.raises(pvt.ErroPVT, match="colunas"):
        pvt.ler_linhas([["A", "B"], [1, 2]])
    with pytest.raises(pvt.ErroPVT):
        pvt.ler_linhas([])
    (tmp_path / "x_PVT.xls").write_bytes(b"nao e planilha")
    with pytest.raises(pvt.ErroPVT):
        pvt.ler(str(tmp_path / "x_PVT.xls"))


def _projeto(tmp_path):
    pasta = tmp_path / "proj"
    rel_d = "bruto/Potiguar/1-SIAPP-1-RN/Dados De Rochas e Fluidos/PVT/1-SIAPP-1-RN-PVT Liberação Diferencial .xlsx"
    rel_f = "bruto/Potiguar/1-SIAPP-1-RN/Dados De Rochas e Fluidos/PVT/1-SIAPP-1-RN-PVT Liberação Flash .xlsx"
    (pasta / rel_d).parent.mkdir(parents=True)
    xlsx(str(pasta / rel_d), diferencial())
    xlsx(str(pasta / rel_f), flash())
    b = mb.Banco(str(pasta / "projeto.sqlite"))
    for rel in (rel_d, rel_f):
        b.registrar_arquivo(rel, bacia="Potiguar", poco_id="1-SIAPP-1-RN", tipo="outro")
    return str(pasta), b


def test_lido_no_projeto_e_na_viabilidade(tmp_path):
    pasta, b = _projeto(tmp_path)
    lidos = mdp.ler_pendentes(b, pasta)
    assert sorted(r["documento"] for r in lidos) == ["pvt_diferencial", "pvt_flash"]
    assert all(r["confere"] == 1 for r in lidos) and mpo.resolver(b, "1-ABC-1-RN") == "1-SIAPP-1-RN"
    med = mfl.medidos(b, ["1-SIAPP-1-RN"])
    assert len(med) == 1 and med[0]["api"] == 31.2 and med[0]["densidade_gas"] == 0.85
    assert len(med[0]["tabela"]) == 6 and med[0]["intervalo"] == "1395–1400 m"
    esc = mfl.escolher([], [{"grandeza": "api", "valor": 25.0, "metodo": "embutido", "poco": "X", "arquivo": "a",
                             "pagina": 1, "chave": "k"}], set(), med)
    assert esc["api"]["origem"] == "medido" and esc["api"]["valor"] == 31.2      # PVT antes da leitura automática
    assert esc["densidade_gas"]["valor"] == 0.85 and esc["pvt"]["saturacao"]["p_kgf_cm2"] == 120.0


def test_economia_usa_o_pvt_na_pressao_do_reservatorio(tmp_path):
    from test_economia import DIST, _banco
    b = _banco(tmp_path)
    med = mfl.medidos(b, [])
    assert med == []
    tab = pvt.ler_linhas(diferencial())
    sug = {"pvt": {"tabela": tab["tabela"], "saturacao": tab["saturacao"], "fonte": "PVT do poço 1-SIAPP-1-RN"}}
    p_bar = 160 * pvt.KGF_BAR
    av = mec.avaliar(b, "Campo Teste", DIST, {"pressao_bar": p_bar, "temperatura_c": 70, "api": 30}, sug)
    v = {e["simbolo"]: e for e in av["memoria"]["entradas"]}
    assert v["Bo"]["valor"] == pytest.approx(1.215) and v["Bo"]["fonte"].startswith("medido: PVT do poço 1-SIAPP-1-RN")
    assert v["Rs"]["valor"] == pytest.approx(70.0)
    assert av["metodos"]["poroso"]["estimados"] == ["Bg (Sutton + Papay)"]   # acima da saturação: Bg por correlação
    av = mec.avaliar(b, "Campo Teste", DIST, {"pressao_bar": 70 * pvt.KGF_BAR, "temperatura_c": 70, "api": 30}, sug)
    v = {e["simbolo"]: e for e in av["memoria"]["entradas"]}
    assert v["Bg"]["valor"] == pytest.approx(0.017) and av["metodos"]["poroso"]["estimados"] == []
    # o informado pelo usuário vale sobre o medido
    av = mec.avaliar(b, "Campo Teste", DIST, {"pressao_bar": p_bar, "temperatura_c": 70, "bo": 1.5}, sug)
    assert {e["simbolo"]: e["valor"] for e in av["memoria"]["entradas"]}["Bo"] == 1.5


def test_ficha_mostra_pvt_e_composicao(api, tmp_path):
    import os
    api.escolher_pasta()
    pasta = os.path.join(api._projeto.pasta, "bruto", "Potiguar", "1-SIAPP-1-RN", "Dados De Rochas e Fluidos", "PVT")
    os.makedirs(pasta)
    xlsx(os.path.join(pasta, "1-SIAPP-1-RN-PVT Liberação Diferencial .xlsx"), diferencial())
    xlsx(os.path.join(pasta, "1-SIAPP-1-RN-PVT Liberação Flash .xlsx"), flash())
    api._abrir_projeto(api._projeto.pasta)
    f = api.ficha_poco("1-SIAPP-1-RN")
    dp = f["dados_poco"]
    assert dp["pvt"][0]["saturacao"]["bo"] == 1.22 and len(dp["pvt"][0]["tabela"]) == 6
    assert [c["componente"] for c in dp["composicao"][0]["componentes"]][:3] == ["N2", "CO2", "C1"]
    assert dp["itens"]["pvt"][0]["valor"] == 120.0
