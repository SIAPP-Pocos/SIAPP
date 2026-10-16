"""Texto de PDF, índice de busca e busca tolerante a erro de OCR."""
import pymupdf
import pytest

from motor import documentos as md
from motor import vocabulario as mv


def pdf_com_texto(caminho, paginas):
    doc = pymupdf.open()
    for t in paginas:
        pg = doc.new_page()
        pg.insert_text((72, 72), t, fontsize=11)
    doc.save(caminho)


def test_pdf_digital_usa_texto_embutido_sem_ocr(tmp_path):
    f = tmp_path / "cdpe.pdf"
    pdf_com_texto(str(f), ["NOTIFICACAO DE PERFURACAO DE POCO - Latitude -05:19:17,574 Cota 703,00 m"])
    r = md.processar_arquivo(str(f), tessdata=str(tmp_path / "sem_idioma"))
    assert r["n_paginas"] == 1 and r["paginas"][0]["metodo"] == "embutido"
    assert "Latitude" in r["paginas"][0]["texto"] and r["paginas"][0]["palavras"]


def test_pagina_imagem_sem_idioma_da_erro_claro(tmp_path):
    f = tmp_path / "scan.pdf"
    doc = pymupdf.open()
    doc.new_page()
    doc.save(str(f))
    assert md.precisa_ocr(str(f))
    with pytest.raises(md.ErroDocumento, match="Idioma"):
        md.processar_arquivo(str(f), tessdata=str(tmp_path / "sem_idioma"))


@pytest.fixture
def indice(tmp_path):
    ix = md.Indice(str(tmp_path / "indice.sqlite"))
    if not ix.fts:
        pytest.skip("SQLite sem FTS5")
    paginas = [
        {"pagina": 1, "metodo": "ocr", "titulo": "RELATÓRIO GEOLÓGICO QUINZENAL",
         "texto": "DESCRIÇÃO DE AMOSTRAS DE CALHA BARIGIRAS/JANDAIRA 234 AMOSTRAS CONTLMINDAS P/CIMENTO"},
        {"pagina": 2, "metodo": "ocr", "titulo": "TRANSA EEE EM IREEN CAS add ERASMO AAA",
         "texto": "PERDA DE CIRCULAÇÃO A 845 m - TAMPÃO DE CIMENTO"},
    ]
    corretor = mv.Corretor({}, mv.projeto_vazio())
    ix.substituir_documento("doc1", "Potiguar", "7-GMR-13-RN", "pasta.pdf", paginas, corretor)
    return ix


def test_busca_ignora_acento_e_caixa(indice):
    assert [r["pagina"] for r in indice.buscar("circulacao")["resultados"]] == [2]
    assert [r["pagina"] for r in indice.buscar("DESCRICAO calha")["resultados"]] == [1]


def test_busca_tolerante_acha_palavra_deformada_pelo_ocr(indice):
    assert indice.buscar("contaminadas", tolerante=False)["resultados"] == []
    r = indice.buscar("contaminadas")
    assert [x["pagina"] for x in r["resultados"]] == [1]
    assert r["expansoes"][0]["variacoes"] == ["contlmindas"]


def test_titulo_ruido_nao_entra_no_indice(indice):
    assert indice.titulos("doc1") == {1: "RELATÓRIO GEOLÓGICO QUINZENAL", 2: ""}


def test_reconstruir_aplica_correcoes_e_mantem_original(indice):
    c = mv.Corretor({}, {"palavras": [], "correcoes": {"BARIGIRAS": "BARREIRAS"}, "ignorar": []})
    paginas = [{"pagina": 1, "metodo": "ocr", "titulo": "", "texto": "BARIGIRAS"}]
    assert indice.reconstruir([("doc1", "P", "p", "a.pdf", paginas)], c) == 1
    assert indice.buscar("barreiras", tolerante=False)["resultados"]     # corrigido
    assert indice.buscar("barigiras", tolerante=False)["resultados"]     # original continua achável


def test_indice_de_versao_antiga_e_recriado(tmp_path):
    import sqlite3
    caminho = str(tmp_path / "velho.sqlite")
    with sqlite3.connect(caminho) as c:
        c.execute("CREATE TABLE paginas (texto)")
    assert md.Indice(caminho).recriado


# ------------------------------------------------- abrir sem processar e visor
def tif_paginas(caminho, tamanhos):
    from PIL import Image
    imgs = [Image.new("RGB", t, c) for t, c in zip(tamanhos, ["white", "lightblue", "pink"])]
    imgs[0].save(caminho, save_all=True, append_images=imgs[1:], dpi=(200, 200))


def test_tif_de_varias_paginas_abre_e_destaca(tmp_path):
    f = str(tmp_path / "perfil.tif")
    tif_paginas(f, [(800, 1000), (800, 1000)])
    assert md.n_paginas(f) == 2
    # destaque em TIF: antes falhava com "is no PDF" (PyMuPDF só desenha em PDF)
    url = md.imagem_pagina(f, 2, [[0.1, 0.1, 0.4, 0.2, "BARREIRAS"]], "barreiras")
    assert url.startswith("data:image/png;base64,")
    with pytest.raises(md.ErroDocumento):
        md.imagem_pagina(f, 3, [])


def test_visor_entrega_pagina_longa_em_faixas(tmp_path):
    f = str(tmp_path / "longo.tif")
    tif_paginas(f, [(500, 9000)])                       # perfil escaneado: 18× mais alto que largo
    i = md.visor_info(f, 1, largura=1000)
    assert i["largura"] == 1000 and i["altura"] == 18000 and i["faixas"] == 18
    assert md.visor_faixa(f, 1, 17, largura=1000).startswith("data:image/jpeg;base64,")
    with pytest.raises(md.ErroDocumento):
        md.visor_faixa(f, 1, 18, largura=1000)
    # a página no painel lateral nunca passa do limite de pixels
    import base64
    png = base64.b64decode(md.imagem_pagina(f, 1, []).split(",")[1])
    larg, alt = int.from_bytes(png[16:20], "big"), int.from_bytes(png[20:24], "big")
    assert larg * alt <= md.PIXELS_PAGINA and alt > larg * 15
