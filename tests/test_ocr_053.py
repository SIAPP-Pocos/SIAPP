"""OCR 0.53: segunda passada nas páginas ruins (resolução maior, outro limiar) e escolha pela legibilidade."""
import os

import numpy as np
import pymupdf
import pytest

from motor import documentos as md
from ponte import base

BOM = ("O relatório geológico descreve a perfuração do poço, a formação arenito com porosidade regular, "
       "perfilagem concluída, testemunho recuperado e amostras descritas pelo geólogo responsável. "
       "A perfilagem confirma arenito, formação regular e porosidade; o relatório descreve amostras e testemunho.")
RUIM = ("Qrelat6rio geol6gico descr1ve aperfura9ao dopo9o formaqao arenlto porosldade regu1ar perfl1agem concl8ida "
        "testemunh0 recuperadd amostr4s descritqs geol0go respons4vel perfi1agem confinma arenlto formaqao regu1ar")


def pagina_de_imagem(tmp_path, texto="Sem texto embutido"):
    """Página de PDF só com imagem (sem texto embutido): obriga o OCR."""
    doc = pymupdf.open()
    pg = doc.new_page()
    pix = pymupdf.Pixmap(pymupdf.csRGB, 300, 100, b"\xff" * (300 * 100 * 3), False)
    pg.insert_image(pymupdf.Rect(50, 50, 350, 150), pixmap=pix)
    return doc[0]


def conhecida_falsa(w):
    return w.lower() in {"relatório", "geológico", "descreve", "perfuração", "formação", "arenito", "porosidade",
                         "regular", "perfilagem", "concluída", "testemunho", "recuperado", "amostras", "descritas",
                         "geólogo", "responsável", "poço", "relatorio", "geologico"}


class OcrFalso:
    """Substitui a passada de OCR: devolve um texto por (dpi, limiar) e conta as chamadas."""

    def __init__(self, textos):
        self.textos, self.chamadas = textos, []

    def __call__(self, page, tessdata, dpi=md.DPI_OCR, limiar="fixo"):
        self.chamadas.append((dpi, limiar))
        t = self.textos[(dpi, limiar)]
        doc = pymupdf.open()
        pg = doc.new_page()
        pg.insert_text((40, 80), t[:60])
        palavras = [(40.0, 70.0, 80.0, 82.0, w, 0, i, i) for i, w in enumerate(t.split())]
        return pg, t, palavras


@pytest.fixture
def tessdata(tmp_path, monkeypatch):
    monkeypatch.setattr(md, "idioma_disponivel", lambda td: True)
    return str(tmp_path)


def test_pagina_ruim_ganha_segunda_passada_e_ela_vence_quando_melhora(tmp_path, tessdata, monkeypatch):
    falso = OcrFalso({(300, "fixo"): RUIM, (450, "otsu"): BOM})
    monkeypatch.setattr(md, "_ocr_pagina", falso)
    r = md.extrair_pagina(pagina_de_imagem(tmp_path), tessdata, conhecida=conhecida_falsa)
    assert falso.chamadas == [(300, "fixo"), (450, "otsu")]
    assert r["metodo"] == "ocr" and r["texto"] == BOM and r["ocr"]["escolhida"] == 2
    p1, p2 = r["ocr"]["passadas"]
    assert (p1["dpi"], p1["limiar"]) == (300, "fixo") and (p2["dpi"], p2["limiar"]) == (450, "otsu")
    assert p2["legibilidade"] > p1["legibilidade"] + md.GANHO_MINIMO_SEGUNDA - 1


def test_segunda_passada_que_nao_melhora_nao_troca_o_texto(tmp_path, tessdata, monkeypatch):
    falso = OcrFalso({(300, "fixo"): RUIM, (450, "otsu"): RUIM + " xyz"})
    monkeypatch.setattr(md, "_ocr_pagina", falso)
    r = md.extrair_pagina(pagina_de_imagem(tmp_path), tessdata, conhecida=conhecida_falsa)
    assert len(falso.chamadas) == 2 and r["texto"] == RUIM and r["ocr"]["escolhida"] == 1
    assert len(r["ocr"]["passadas"]) == 2                                       # a tentativa fica registrada


def test_pagina_boa_ou_curta_nao_gasta_segunda_passada(tmp_path, tessdata, monkeypatch):
    boa = OcrFalso({(300, "fixo"): BOM})
    monkeypatch.setattr(md, "_ocr_pagina", boa)
    r = md.extrair_pagina(pagina_de_imagem(tmp_path), tessdata, conhecida=conhecida_falsa)
    assert boa.chamadas == [(300, "fixo")] and r["ocr"]["escolhida"] == 1 and len(r["ocr"]["passadas"]) == 1
    curta = OcrFalso({(300, "fixo"): "poço 7-GMR-13"})                          # poucas palavras: sem julgamento
    monkeypatch.setattr(md, "_ocr_pagina", curta)
    r2 = md.extrair_pagina(pagina_de_imagem(tmp_path), tessdata, conhecida=conhecida_falsa)
    assert curta.chamadas == [(300, "fixo")] and r2["ocr"]["passadas"][0]["legibilidade"] is None


def test_segunda_passada_pode_ser_desligada(tmp_path, tessdata, monkeypatch):
    falso = OcrFalso({(300, "fixo"): RUIM})
    monkeypatch.setattr(md, "_ocr_pagina", falso)
    r = md.extrair_pagina(pagina_de_imagem(tmp_path), tessdata, segunda_passada=False, conhecida=conhecida_falsa)
    assert falso.chamadas == [(300, "fixo")] and r["texto"] == RUIM


def test_pdf_com_texto_embutido_nao_faz_ocr_e_nao_tem_campo_ocr(tmp_path, tessdata):
    doc = pymupdf.open()
    doc.new_page().insert_text((50, 100), "Relatório diário de perfuração com texto embutido suficiente para dispensar o OCR.")
    r = md.extrair_pagina(doc[0], tessdata)
    assert r["metodo"] == "embutido" and "ocr" not in r


def test_limiar_de_otsu_separa_tinta_e_papel_e_respeita_os_limites():
    rng = np.random.default_rng(0)
    escuro = rng.normal(60, 12, 4000).clip(0, 255)
    claro = rng.normal(215, 10, 40000).clip(0, 255)
    a = np.concatenate([escuro, claro]).astype(np.uint8).reshape(-1, 100)
    t = md.limiar_otsu(a)
    assert 100 <= t <= 200 and 80 < t < 200
    assert md.limiar_otsu(np.full((10, 10), 255, np.uint8)) in range(100, 201)           # página em branco: não quebra
    assert md.limiar_otsu(np.zeros((0, 0), np.uint8)) == 150


def test_imagem_para_ocr_padrao_continua_a_mesma_e_a_nova_e_maior(tmp_path):
    doc = pymupdf.open()
    pg = doc.new_page(width=200, height=100)
    pg.insert_text((10, 50), "TESTE", fontsize=30)
    antiga = md._imagem_para_ocr(pg)
    assert abs(antiga.width - 200 / 72 * md.DPI_OCR) <= 1 and antiga.colorspace.name == pymupdf.csRGB.name
    nova = md._imagem_para_ocr(pg, md.DPI_OCR_SEGUNDA, "otsu")
    assert abs(nova.width - 200 / 72 * md.DPI_OCR_SEGUNDA) <= 1 and nova.width > antiga.width
    amostras = np.frombuffer(nova.samples, np.uint8)
    assert set(np.unique(amostras)) <= {0, 255}                                          # só preto e branco


@pytest.mark.skipif(not os.path.exists(os.path.join(base.PASTA_TESSDATA, "por.traineddata")),
                    reason="idioma do OCR não instalado")
def test_ocr_de_verdade_le_uma_pagina_so_de_imagem(tmp_path):
    texto = ("Relatório geológico da perfuração do poço. A formação apresenta arenito com porosidade regular "
             "e testemunho recuperado, descrito pelo geólogo responsável.")
    origem = pymupdf.open()
    origem.new_page(width=595, height=400).insert_textbox(pymupdf.Rect(30, 30, 565, 380), texto, fontsize=14)
    pix = origem[0].get_pixmap(dpi=200, colorspace=pymupdf.csRGB)
    doc = pymupdf.open()
    pg = doc.new_page(width=595, height=400)
    pg.insert_image(pg.rect, pixmap=pix)                                                  # só imagem, sem texto
    r = md.extrair_pagina(doc[0], base.PASTA_TESSDATA)
    assert r["metodo"] == "ocr" and "perfuração" in r["texto"] and "arenito" in r["texto"]
    assert r["ocr"]["passadas"][0]["legibilidade"] is not None and r["ocr"]["escolhida"] == 1


def test_processar_arquivo_repassa_a_opcao_da_segunda_passada(tmp_path, tessdata, monkeypatch):
    doc = pymupdf.open()
    pg = doc.new_page()
    pg.insert_image(pymupdf.Rect(50, 50, 350, 150), pixmap=pymupdf.Pixmap(pymupdf.csRGB, 30, 10, b"\xff" * 900, False))
    pdf = tmp_path / "scan.pdf"
    doc.save(str(pdf))
    vistas = []
    monkeypatch.setattr(md, "extrair_pagina", lambda page, td, segunda=True, conhecida=None:
                        vistas.append(segunda) or {"metodo": "ocr", "texto": "", "titulo": "", "palavras": []})
    md.processar_arquivo(str(pdf), tessdata)
    md.processar_arquivo(str(pdf), tessdata, segunda_passada=False)
    assert vistas == [True, False]
    assert md.VERSAO_EXTRACAO == 2


def test_ponte_e_interface_tem_a_opcao(api):
    import inspect
    assert inspect.signature(type(api).processar_documentos).parameters["segunda_passada"].default is True
