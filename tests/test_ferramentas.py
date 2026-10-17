"""Esquemas de ferramentas: nome do arquivo, texto/OCR, vínculo com os perfis, banco.

Os PDFs são sintéticos (gerados aqui, no leiaute dos esquemas da Schlumberger e da
Tucker); nenhum arquivo do REATE entra no repositório."""
import glob
import os

import pymupdf
import pytest

from motor import ferramentas as mf
from motor.banco import Banco

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIC = mf.ler_dicionario(os.path.join(RAIZ, "recursos", "ferramentas.json"))


def tessdata_ingles():
    for d in [os.environ.get("TESSDATA_PREFIX", "")] + glob.glob("/usr/share/tesseract-ocr/*/tessdata"):
        if d and mf.idioma_disponivel(d):
            return d
    return None


TESSDATA = tessdata_ingles()
precisa_ocr = pytest.mark.skipif(TESSDATA is None, reason="sem o modelo de OCR em inglês")

LINHAS_SLB = [
    "SURFACE EQUIPMENT", "NCT-B", "WITM (DTS)-A", "DOWNHOLE EQUIPMENT",
    "LEH-QT", "DTC-H", "ECH-KC", "HILTB-FTB", "HGNSD-B", "HRMS-B", "MCFL Device", "Gamma-Ray", "Neutron",
    "DSLT-H", "HAIT-H", "Induction", "TOOL ZERO",
    "MAXIMUM STRING DIAMETER 4.63 IN", "MEASUREMENTS RELATIVE TO TOOL ZERO", "ALL LENGTHS IN METERS",
]
CARIMBO = ["DATA: 10/05/2008", "POCO: 7-XX-1-RN", "CADASTRO: 72100099999", "OPERADORA: PETROBRAS"]


def esquema_pdf(caminho, linhas=LINHAS_SLB, carimbo=CARIMBO, raster_dpi=None, girar=0):
    """Esquema sintético: texto vetorial, ou (raster_dpi) só uma imagem escaneada."""
    doc = pymupdf.open()
    pg = doc.new_page(width=612, height=792)
    y = 40
    for ln in linhas:
        pg.insert_text((40, y), ln, fontsize=11, fontname="helv")
        y += 17
    for k, ln in enumerate(carimbo):
        pg.insert_text((300, 300 + 26 * k), ln, fontsize=16, fontname="helv")
    if raster_dpi:
        pix = pg.get_pixmap(dpi=raster_dpi, colorspace=pymupdf.csRGB)
        img = pymupdf.open()
        p2 = img.new_page(width=612, height=792)
        p2.insert_image(p2.rect, pixmap=pix, rotate=girar)
        doc = img
    doc.save(str(caminho))
    return str(caminho)


# ================================================================ nome
@pytest.mark.parametrize("nome, tipo, corrida, passada, fase, tokens", [
    ("7-xx-1-rn_raw_toolstring.pdf", "convencional", None, None, None, ["raw"]),
    ("7-xx-1-rn_raw1-10028.dlis", "convencional", 1, None, None, ["raw"]),
    ("3-xx-12-rn_sft_1_toolstring.pdf", "testador", 1, None, None, ["sft"]),
    ("1xx12rn_sft_gr_875_run3.dlis", "testador", 3, None, 8.75, ["sft", "gr"]),
    ("1-XX-12-RN_AIT_P.DLIS", "resistividade", None, "principal", None, ["ait"]),
    ("1-XX-12-RN_AIT_R.DLIS", "resistividade", None, "repetida", None, ["ait"]),
    ("1-XX-12-RN_RFT7.DLIS", "testador", 7, None, None, ["rft"]),
    ("7-xx-1-rn_cbl_gr_ccl_run1-13319.dlis", "cimentacao", 1, None, None, ["cbl", "gr", "ccl"]),
    ("1-XX-8-RN_AIT-SDT-MCFL-TDD-HGNS-GR_ToolString.pdf", "convencional", None, None, None,
     ["ait", "sdt", "mcfl", "tdd", "hgns", "gr"]),
    ("7xx1585rn_esq.pdf", None, None, None, None, []),
    ("7_XX_640_RN_7_XX_640_RN.lis", None, None, None, None, []),          # nome do poço duas vezes
    ("RUN_1_AIT-MCFL_7-XX-20-RN_Toolstring.pdf", "resistividade", 1, None, None, ["ait", "mcfl"]),
])
def test_ler_nome(nome, tipo, corrida, passada, fase, tokens):
    r = mf.ler_nome(nome, DIC)
    assert (r["tipo"], r["corrida"], r["passada"], r["fase"], r["tokens"]) == (tipo, corrida, passada, fase, tokens)


def test_pasta_do_perfil_diz_o_tipo_quando_o_nome_nao_diz():
    assert mf.ler_nome("7-xx-1-rn_estacao_12.dlis", DIC, "Teste de Formacao a Cabo")["tipo"] == "testador"


def test_eh_esquema():
    assert mf.eh_esquema("7-xx-1-rn_raw.pdf", "Esquema de Ferramentas")
    assert mf.eh_esquema("x.PDF", "Esquema_ferramentas")
    assert not mf.eh_esquema("7-xx-1-rn_raw.dlis", "Esquema de Ferramentas")
    assert not mf.eh_esquema("7-xx-1-rn_raw.pdf", "Perfil Composto")


# ============================================================ vínculos
def nomes(*ns):
    return [{"nome": n} for n in ns]


def test_vincula_esquema_ao_perfil_pela_corrida():
    v = mf.vincular(
        nomes("7-xx-1-rn_raw1_toolstring.pdf", "7-xx-1-rn_raw2_toolstring.pdf", "7-xx-1-rn_raw2_fmi-gpit_toolstring.pdf", "7-xx-1-rn_rft_toolstring.pdf"),
        nomes("7-xx-1-rn_raw1.dlis", "7-xx-1-rn_raw2.dlis", "7-xx-1-rn_raw2_fmi-gpit.dlis", "7-xx-1-rn_rft.dlis"), DIC)
    assert v == {"7-xx-1-rn_raw1_toolstring.pdf": ["7-xx-1-rn_raw1.dlis"], "7-xx-1-rn_raw2_toolstring.pdf": ["7-xx-1-rn_raw2.dlis"],
                 "7-xx-1-rn_raw2_fmi-gpit_toolstring.pdf": ["7-xx-1-rn_raw2_fmi-gpit.dlis"], "7-xx-1-rn_rft_toolstring.pdf": ["7-xx-1-rn_rft.dlis"]}


def test_esquema_sem_numero_cobre_todas_as_corridas_e_passadas():
    v = mf.vincular(nomes("1-xx-12-rn_AIT_tool.pdf", "1-xx-12-rn_RFT_tool.pdf"),
                    nomes("1-XX-12-RN_AIT_P.DLIS", "1-XX-12-RN_AIT_R.DLIS", "1-XX-12-RN_RFT1.DLIS",
                          "1-XX-12-RN_RFT2.DLIS"), DIC)
    assert v["1-xx-12-rn_AIT_tool.pdf"] == ["1-XX-12-RN_AIT_P.DLIS", "1-XX-12-RN_AIT_R.DLIS"]
    assert v["1-xx-12-rn_RFT_tool.pdf"] == ["1-XX-12-RN_RFT1.DLIS", "1-XX-12-RN_RFT2.DLIS"]


def test_corrida_diferente_nao_liga_e_gr_sozinho_nao_liga():
    v = mf.vincular(nomes("7-xx-1-rn_cbl_gr_ccl_run1_toolstring.pdf", "7-xx-1-rn_ccl_run2_toolstring.pdf", "7-xx-1-rn_dipmeter_gr.pdf"),
                    nomes("7-xx-1-rn_cbl_gr_ccl_run1-13319.dlis", "7-xx-1-rn_ccl_run2-13320.dlis", "7-xx-1-rn_sft_gr_875_run3.dlis"), DIC)
    assert v == {"7-xx-1-rn_cbl_gr_ccl_run1_toolstring.pdf": ["7-xx-1-rn_cbl_gr_ccl_run1-13319.dlis"],
                 "7-xx-1-rn_ccl_run2_toolstring.pdf": ["7-xx-1-rn_ccl_run2-13320.dlis"], "7-xx-1-rn_dipmeter_gr.pdf": []}


def test_segunda_passada_pelo_tipo():
    # CONV_PRIN e RAW: os dois "convencional", e é o único esquema desse tipo
    v = mf.vincular(nomes("1-xx-5-rn_RAW_ToolString.pdf", "1-xx-5-rn_RFT-GR_ToolString.pdf"),
                    nomes("1-XX-5-RN_CONV_PRIN.DLIS"), DIC)
    assert v["1-xx-5-rn_RAW_ToolString.pdf"] == ["1-XX-5-RN_CONV_PRIN.DLIS"]
    # um esquema só no poço e o perfil sem nada no nome
    v = mf.vincular(nomes("7-xx-640-rn_raw_toolstring.pdf"), nomes("7_XX_640_RN_7_XX_640_RN.lis"), DIC)
    assert v["7-xx-640-rn_raw_toolstring.pdf"] == ["7_XX_640_RN_7_XX_640_RN.lis"]
    # esquema genérico (_esq) se liga quando a leitura deu o tipo
    esq = [{"nome": "7xx1622rn_esq.pdf", "tipo": "convencional"}, {"nome": "7-xx-1622-rn_ccl_run2.pdf"}]
    v = mf.vincular(esq, nomes("7-xx-1622-rn_conv.las", "7-xx-1622-rn_ccl_run2-1.dlis"), DIC)
    assert v["7xx1622rn_esq.pdf"] == ["7-xx-1622-rn_conv.las"]
    assert mf.vincular(esq[:1] + [{"nome": "b_esq.pdf", "tipo": "convencional"}],
                       nomes("7-xx-1622-rn_conv.las"), DIC)["7xx1622rn_esq.pdf"] == []   # dois do mesmo tipo: ambíguo


# ================================================================ texto
def test_codigos_com_trocas_do_ocr():
    r = lambda t, s=True: (mf.reconhecer_codigo(t, s, DIC) or {}).get("codigo")  # noqa: E731
    assert r("OTC") == "DTC"           # O no lugar de D
    assert r("HILTE") == "HILTB"       # E no lugar de B
    assert r("HGNSD") == "HGNS"        # uma letra a mais, com sufixo de peça
    assert r("HGNSD", False) is None   # sem sufixo, não
    assert r("NGT") == "NGT" and r("NCT") == "NCT"   # grafia exata antes das trocas
    assert r("TOOL") is None and r("ZERO") is None


def test_analisar_texto_schlumberger():
    a = mf.analisar_texto("\n".join(LINHAS_SLB + CARIMBO), DIC)
    codigos = [f["codigo"] for f in a["ferramentas"]]
    assert codigos == ["LEH", "DTC", "ECH", "HILTB", "HGNS", "HRMS", "MCFL", "DSLT", "HAIT"]
    assert "NCT" not in codigos            # equipamento de superfície fica de fora
    assert set(a["familias"]) >= {"gr", "neutron", "densidade", "micro", "sonico", "inducao"}
    assert a["fabricante"] == "Schlumberger" and a["diametro_max_pol"] == 4.63
    assert mf.tipo_pelas_familias(a["familias"]) == "convencional"
    assert mf.carimbo("\n".join(CARIMBO)) == {"data": "10/05/2008", "poco": "7-XX-1-RN",
                                              "cadastro": "72100099999", "operadora": "PETROBRAS"}


def test_nome_do_poco_nao_vira_ferramenta():
    a = mf.analisar_texto("POCO: 1-STAR-11-RN\nOPERADORA: STARFISH\nSGT-N\nXPT-BA\nHydrostat", DIC)
    assert [f["codigo"] for f in a["ferramentas"]] == ["SGT", "XPT"]
    assert mf.tipo_pelas_familias(a["familias"]) == "testador"


def test_analisar_texto_tucker():
    t = ("Companhia: PETROBRAS\nPoco: 8-XX-14-RN\nData: 14/09/2012\nTool String Schematic\n"
         "Total Tool Length - 6.24 (M)\nMaximum Outside diameter - 133.35 (mm)\n"
         "Tool: GRT-B Length: 1.04 (M)\nGamma Ray Controller\nTool: FTT-CA Length: 5.21 (M)\nFormation Test Tool")
    a = mf.analisar_texto(t, DIC)
    assert [f["codigo"] for f in a["ferramentas"]] == ["GRT", "FTT"]
    assert a["fabricante"] == "Tucker" and a["comprimento_m"] == 6.24 and a["diametro_max_pol"] == 5.25
    assert mf.tipo_pelas_familias(a["familias"]) == "testador"


@pytest.mark.parametrize("familias, tipo", [
    (["gr", "testador"], "testador"), (["gr", "imagem", "inclinometria"], "imagem"),
    (["gr", "neutron", "densidade"], "convencional"), (["inducao"], "resistividade"), (["sonico", "gr"], "sonico"),
    (["gr", "ccl"], "correlacao"), ([], None),
])
def test_tipo_pelas_familias(familias, tipo):
    assert mf.tipo_pelas_familias(familias) == tipo


def test_le_pdf_com_texto_embutido(tmp_path):
    f = esquema_pdf(tmp_path / "7-xx-1-rn_raw_toolstring.pdf")
    d = mf.ler_esquema(f, "7-xx-1-rn_raw_toolstring.pdf", DIC, poco_id="7-XX-1-RN", tessdata=None)
    assert d["metodo"] == "embutido" and d["tipo"] == "convencional" and d["fabricante"] == "Schlumberger"
    assert d["carimbo"]["confere"] is True and d["pelo_nome"]["tipo"] == "convencional"
    assert not d["aviso"]


def test_imagem_sem_modelo_de_ocr_usa_so_o_nome(tmp_path):
    f = esquema_pdf(tmp_path / "e.pdf", raster_dpi=100)
    d = mf.ler_esquema(f, "7-xx-1-rn_sft_toolstring.pdf", DIC, tessdata=str(tmp_path / "sem_modelo"))
    assert d["metodo"] == "vazio" and d["tipo"] == "testador" and d["ferramentas"] == []
    assert "OCR" in d["aviso"]


@precisa_ocr
@pytest.mark.parametrize("girar", [0, 90])
def test_ocr_de_esquema_escaneado_em_baixa_resolucao(tmp_path, girar):
    # 100 dpi, como os esquemas de 768 px de largura do acervo; girado como alguns
    f = esquema_pdf(tmp_path / "e.pdf", raster_dpi=100, girar=girar)
    d = mf.ler_esquema(f, "7xx1esq.pdf", DIC, poco_id="7-XX-1-RN", tessdata=TESSDATA)
    assert d["metodo"] == "ocr"
    codigos = {fe["codigo"] for fe in d["ferramentas"]}
    assert {"HILTB", "DSLT", "HAIT"} <= codigos, codigos
    assert d["tipo"] == "convencional" and d["carimbo"].get("data") == "10/05/2008"


def test_pdf_corrompido(tmp_path):
    f = tmp_path / "ruim.pdf"
    f.write_bytes(b"%PDF-1.4 lixo")
    with pytest.raises(mf.ErroEsquema):
        mf.ler_esquema(str(f), "ruim.pdf", DIC)


# ================================================================ banco
P = "/POCO/Categoria-7/7-XX-1-RN/"


def acervo(banco, arquivos):
    """Poço 7-XX-1-RN no levantamento, com os arquivos {caminho: (pasta, tamanho, candidato, formato)}."""
    with banco.conexao() as c:
        c.execute("INSERT INTO acervo_pocos (bacia, caminho, nome_pasta, poco_id, categoria) VALUES (?,?,?,?,?)",
                  ("Potiguar", P, "7-XX-1-RN", "7-XX-1-RN", "Categoria-7"))
        for cam, (pasta, tam, cand, fmt) in arquivos.items():
            c.execute("""INSERT INTO acervo_arquivos (bacia, caminho, poco_caminho, nome, pasta, ext, tamanho,
                         candidato, formato) VALUES (?,?,?,?,?,?,?,?,?)""",
                      ("Potiguar", cam, P, cam.rsplit("/", 1)[1], pasta, os.path.splitext(cam)[1].lower(),
                       tam, cand, fmt))


class Portal:
    def __init__(self, arquivos):
        self.arquivos, self.lidos = arquivos, []

    def ler_inicio(self, caminho, n=1024):
        self.lidos.append(caminho)
        return self.arquivos[caminho][:n]


def test_ler_do_portal_gravar_e_rotular(tmp_path):
    banco = Banco(str(tmp_path / "projeto.sqlite"))
    pdf = open(esquema_pdf(tmp_path / "x.pdf"), "rb").read()
    acervo(banco, {
        P + "Esquema de Ferramentas/7-xx-1-rn_raw_toolstring.pdf": ("Esquema de Ferramentas", len(pdf), 0, None),
        P + "Esquema de Ferramentas/7xx1rn_esq.pdf": ("Esquema de Ferramentas", len(pdf), 0, None),
        P + "Esquema de Ferramentas/7-xx-1-rn_fmi.pdf": ("Esquema de Ferramentas", 90_000_000, 0, None),
        P + "Perfil Convencional/7-xx-1-rn_raw-1234.dlis": ("Perfil Convencional", 10, 1, "dlis"),
        P + "Teste de Formacao a Cabo/7-xx-1-rn_estacao_3.dlis": ("Teste de Formacao a Cabo", 10, 1, "dlis"),
        P + "Pasta de Poco/relatorio.pdf": ("Pasta de Poco", 10, 0, None),
    })
    antes = mf.do_poco(banco, "7-XX-1-RN", DIC)
    assert [e["nome"] for e in antes["esquemas"]] == ["7-xx-1-rn_fmi.pdf", "7-xx-1-rn_raw_toolstring.pdf",
                                                      "7xx1rn_esq.pdf"]
    assert not any(e["lido"] for e in antes["esquemas"])
    assert antes["perfis"]["7-xx-1-rn_raw-1234.dlis"]["fonte"] == "nome do esquema"
    assert antes["perfis"]["7-xx-1-rn_estacao_3.dlis"]["rotulo"] == "Teste de formação a cabo · corrida 3"

    pend = mf.pendentes(banco, "Potiguar", ["Categoria-7"])
    assert len(pend) == 3
    portal = Portal({k: pdf for k in [P + "Esquema de Ferramentas/7-xx-1-rn_raw_toolstring.pdf",
                                      P + "Esquema de Ferramentas/7xx1rn_esq.pdf"]})
    n = mf.ler_do_portal(banco, portal, "Potiguar", pend, DIC, pasta_projeto=str(tmp_path), tessdata=None)
    assert n == 3 and len(portal.lidos) == 2                  # o de 90 MB nem é baixado
    assert mf.pendentes(banco, "Potiguar") == []
    d = mf.do_poco(banco, "7-XX-1-RN", DIC)
    por_nome = {e["nome"]: e for e in d["esquemas"]}
    assert "grande demais" in por_nome["7-xx-1-rn_fmi.pdf"]["erro"]
    raw = por_nome["7-xx-1-rn_raw_toolstring.pdf"]
    assert raw["lido"] and raw["dados"]["tipo"] == "convencional"
    assert raw["arquivo_local"] == "esquemas/Potiguar/7-XX-1-RN/7-xx-1-rn_raw_toolstring.pdf"
    assert os.path.isfile(tmp_path / raw["arquivo_local"])
    perfil = d["perfis"]["7-xx-1-rn_raw-1234.dlis"]
    assert perfil["fonte"] == "esquema lido" and perfil["tipo"] == "convencional"
    assert perfil["ferramentas"][:3] == ["HILTB", "HGNS", "HRMS"]       # sem as de apoio (LEH, DTC…)
    # cópia local reaproveitada: não baixa de novo ao reler
    with banco.conexao() as c:
        c.execute("UPDATE esquemas SET leitor = 0")
    portal.lidos.clear()
    mf.ler_do_portal(banco, portal, "Potiguar", mf.pendentes(banco, "Potiguar"), DIC, pasta_projeto=str(tmp_path),
                     tessdata=None)
    assert portal.lidos == []
    r = mf.resumo(banco, "Potiguar")
    assert r["esquemas_disponiveis"] == 3 and r["esquemas_lidos"] == 3 and r["esquemas_com_ferramentas"] == 2
    assert r["esquemas_por_tipo"] == {"convencional": 2}


def test_levantamento_com_esquemas(tmp_path):
    from test_levantamento import SUL_DLIS, ClienteFalso, rodar
    pdf = open(esquema_pdf(tmp_path / "x.pdf"), "rb").read()
    banco = Banco(str(tmp_path / "projeto.sqlite"))
    falso = ClienteFalso({
        P + "Perfil Convencional/7-xx-1-rn_raw.dlis": SUL_DLIS,
        P + "Esquema de Ferramentas/7-xx-1-rn_raw_toolstring.pdf": pdf,
    })
    r, eventos = rodar(banco, falso, ["Categoria-7"], esquemas=True, pasta_projeto=str(tmp_path),
                       ferramentas=DIC, tessdata=None)
    assert r["esquemas_lidos"] == 1
    assert any(e["tipo"] == "esquema" for e in eventos)
    assert r["resumo"]["esquemas_lidos"] == 1
    d = mf.do_poco(banco, "7-XX-1-RN", DIC)
    assert d["perfis"]["7-xx-1-rn_raw.dlis"]["fonte"] == "esquema lido"
