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
