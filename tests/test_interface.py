"""Interface de verdade num navegador sem tela (pulado sem Playwright)."""
import os

import pytest

pytestmark = pytest.mark.interface


def abrir_projeto(janela):
    janela.page.click("#ini-pasta")
    janela.esperar("document.getElementById('ini-pasta').disabled")


def test_abre_no_inicio_e_abre_projeto(janela):
    p = janela.page
    assert p.text_content("#versao").startswith("v0.")
    assert p.is_visible("#vista-inicio") and not p.is_visible("#vista-catalogo")
    abrir_projeto(janela)
    janela.esperar("!document.getElementById('panorama').hidden")
    assert "arquivo(s) baixado(s)" in p.text_content("#panorama")
    p.click("#aba-catalogo")
    assert not p.is_visible("#etapa-bacia.bloqueada")
    assert not janela.erros_js, janela.erros_js


def test_abas_trocam_de_vista(janela):
    p = janela.page
    p.click("#aba-docs")
    assert p.is_visible("#vista-docs") and not p.is_visible("#vista-inicio")
    assert "pasta do projeto" in p.text_content("#docs-resumo")
    p.click(".fluxo button[data-ir='comunidade']") if p.is_visible(".fluxo") else p.click("#aba-comunidade")
    p.click("#aba-comunidade")
    assert p.is_visible("#vista-comunidade")
    assert not janela.erros_js, janela.erros_js


def test_comunidade_autor_exportar_importar(janela):
    p = janela.page
    abrir_projeto(janela)
    api = janela.api
    api.corrigir_palavra("BARIGIRAS", "BARREIRAS")
    p.click("#aba-comunidade")
    janela.esperar("document.getElementById('com-local').textContent.includes('1 correção')")
    p.click("#btn-exportar")
    janela.esperar("document.querySelector('.rodape').classList.contains('erro')")
    assert "nome" in janela.status()
    p.fill("#autor-nome", "Ruan da Silva Nobre")
    p.fill("#autor-inst", "UFAL")
    p.click("#btn-autor")
    janela.esperar("document.getElementById('status').textContent.includes('Autoria salva')")
    p.click("#btn-exportar")
    janela.esperar("document.getElementById('com-exportado').textContent.includes('contribuicoes/')")
    rel = p.text_content("#com-exportado").split("em ")[1].split(" (")[0]
    # importar o próprio pacote como se fosse de outra pessoa
    api.remover_correcao("BARIGIRAS")
    api._janela.escolha = None
    original = api._janela.create_file_dialog
    api._janela.create_file_dialog = lambda tipo, **kw: (os.path.join(api._projeto.pasta, rel),)
    p.click("#btn-importar")
    janela.esperar("!document.getElementById('previa').hidden")
    assert "1 correção" in p.text_content("#previa")
    p.click("#previa .btn:not(.secundario)")
    janela.esperar("document.querySelectorAll('#lista-pacotes li button').length === 1")
    api._janela.create_file_dialog = original
    p.click("#aba-docs")
    janela.esperar("document.getElementById('n-com').textContent === '1'")
    assert not janela.erros_js, janela.erros_js


def test_mapa_com_cadastro_e_ficha(janela):
    from test_pocos import csv_exemplo
    p = janela.page
    abrir_projeto(janela)
    p.click("#aba-mapa")
    janela.esperar("!document.getElementById('mapa-vazio').hidden")
    janela.api._importar_cadastro(csv_exemplo(), "anp:teste")
    p.click("#aba-inicio")
    p.click("#aba-mapa")
    janela.esperar("document.getElementById('mapa-resumo').textContent.includes('2 poço')")
    assert p.is_hidden("#mapa-vazio")
    p.select_option("#f-bacia", "")
    janela.esperar("document.getElementById('mapa-resumo').textContent.includes('3 poço')")
    p.fill("#f-texto", "AURI")
    janela.esperar("document.querySelectorAll('#lista-mapa button').length === 1")
    p.click("#lista-mapa button")
    janela.esperar("document.getElementById('fi-corpo').textContent.includes('72100021414')")
    assert "Pioneiro" in p.text_content("#fi-corpo")
    p.keyboard.press("Escape")
    assert p.is_hidden("#ficha")
    assert not janela.erros_js, janela.erros_js


def test_perfis_inventario_grafico_intervalo_exportar(janela, tmp_path):
    from test_perfis import las_exemplo
    p = janela.page
    abrir_projeto(janela)
    pasta = tmp_path / "ambiente_teste" / "bruto" / "Potiguar" / "7-GMR-13-RN" / "Perfis"
    pasta.mkdir(parents=True)
    las_exemplo(pasta / "7gmr13.las")
    janela.api._abrir_projeto(str(tmp_path / "ambiente_teste"))
    p.click("#aba-perfis")
    janela.esperar("document.querySelectorAll('#lista-perfis button').length === 1")
    p.click("#lista-perfis button")
    janela.esperar("document.querySelectorAll('#pf-trilhas canvas').length === 3", 30)
    assert "7-GMR-13-RN" in p.text_content("#pf-titulo")
    # arrastar na trilha marca um intervalo
    cv = p.locator("#pf-trilhas canvas").nth(1)
    caixa = cv.bounding_box()
    p.mouse.move(caixa["x"] + 30, caixa["y"] + 100)
    p.mouse.down()
    p.mouse.move(caixa["x"] + 30, caixa["y"] + 200)
    p.mouse.up()
    assert p.input_value("#pf-int-topo") and p.input_value("#pf-int-base")
    p.fill("#pf-int-nome", "Reservatório A")
    p.click("#pf-form-int button")
    janela.esperar("document.getElementById('pf-fatos').textContent.includes('Reservatório A')")
    p.click("#pf-las")
    janela.esperar("document.getElementById('pf-exportado').textContent.includes('exportacoes/')")
    assert not janela.erros_js, janela.erros_js


def test_transcricao_com_caixa_e_sugestao(janela, tmp_path):
    import pymupdf
    p = janela.page
    abrir_projeto(janela)
    pasta = tmp_path / "ambiente_teste" / "bruto" / "Potiguar" / "7-GMR-13-RN" / "Pasta de Poco"
    pasta.mkdir(parents=True)
    doc = pymupdf.open()
    pg = doc.new_page()
    pg.insert_text((72, 100), "RELATORIO DE REVESTIMENTO - POCO 7-GMR-13-RN", fontsize=12)
    pg.insert_text((300, 200), "SAPATA: 1234,5 m", fontsize=14)
    doc.save(str(pasta / "rev.pdf"))
    api = janela.api
    api._abrir_projeto(str(tmp_path / "ambiente_teste"))
    rel = "bruto/Potiguar/7-GMR-13-RN/Pasta de Poco/rev.pdf"
    from motor import documentos as md
    r = md.processar_arquivo(str(pasta / "rev.pdf"), tessdata=str(tmp_path))
    api._projeto.salvar_texto(rel, r)
    api._indice.substituir_documento(rel, "Potiguar", "7-GMR-13-RN", "rev.pdf", r["paginas"], api._corretor)
    p.click("#aba-docs")
    janela.esperar("document.querySelectorAll('#lista-docs button').length === 1")
    p.click("#lista-docs button")
    janela.esperar("document.getElementById('pg-num').textContent.includes('1 de 1')")
    p.click("#tr-box summary")
    assert p.input_value("#tr-poco") == "7-GMR-13-RN"
    p.select_option("#tr-tipo", "revestimento")
    p.locator("#painel-pagina").evaluate("e => e.scrollTop = 0")
    img = p.locator("#pg-img").bounding_box()
    largura, altura = 595, 842                      # página A4 em pontos
    x0, y0 = img["x"] + img["width"] * 290 / largura, img["y"] + img["height"] * 180 / altura
    x1, y1 = img["x"] + img["width"] * 470 / largura, img["y"] + img["height"] * 210 / altura
    p.mouse.move(x0, y0)
    p.mouse.down()
    p.mouse.move(x1, y1)
    p.mouse.up()
    assert p.input_value("#tr-topo") == "1234,5"
    assert "SAPATA" in p.text_content("#tr-caixa-info")
    p.fill("#tr-nome", "Sapata 9 5/8 pol")
    p.click("#tr-form button[type=submit]")
    janela.esperar("document.getElementById('tr-n').textContent === '1'")
    f = api._banco.fatos("7-GMR-13-RN")[0]
    assert f["prof_topo"] == 1234.5 and f["pagina"] == 1 and len(f["caixa"]) == 4 and f["fonte_sha256"]
    assert p.locator("#pg-caixas .pg-caixa.salva").count() == 1
    assert not janela.erros_js, janela.erros_js


def test_tif_sem_processar_abre_amplia_e_arquivo_qualquer_abre_fora(janela, tmp_path, monkeypatch):
    from PIL import Image
    p = janela.page
    abrir_projeto(janela)
    pasta = tmp_path / "ambiente_teste" / "bruto" / "Potiguar" / "1-AURI-12-RN" / "Perfil Convencional"
    pasta.mkdir(parents=True)
    folhas = [Image.new("RGB", (500, 7000), "white"), Image.new("RGB", (500, 700), "gray")]
    folhas[0].save(str(pasta / "perfil.tif"), save_all=True, append_images=folhas[1:])
    p.click("#aba-docs")
    janela.esperar("document.querySelectorAll('#lista-docs button').length === 1")
    assert "sem texto" in p.text_content("#lista-docs")
    p.click("#lista-docs button")
    janela.esperar("document.getElementById('pg-num').textContent.includes('1 de 2')")
    assert p.is_visible("#pg-pendente") and not p.is_visible("#pg-texto-box")
    p.click("#pg-prox")
    janela.esperar("document.getElementById('pg-num').textContent.includes('2 de 2')")
    p.click("#pg-ant")
    janela.esperar("document.getElementById('pg-num').textContent.includes('1 de 2')")
    # visor ampliado: faixas sob demanda, zoom e Esc
    p.click("#pg-ampliar")
    janela.esperar("document.querySelectorAll('#v-folha .v-faixa').length === 14")
    janela.esperar("document.querySelectorAll('#v-folha .v-faixa img').length >= 1")
    carregadas = p.locator("#v-folha .v-faixa img").count()
    assert carregadas < 14                         # só o que está perto da tela
    antes = p.text_content("#v-zoom")
    p.click("#v-mais")
    assert p.text_content("#v-zoom") != antes
    p.locator("#v-area").evaluate("e => e.scrollTop = e.scrollHeight")
    janela.esperar("document.querySelector('#v-folha .v-faixa:last-child img') !== null")
    p.keyboard.press("Escape")
    assert not p.is_visible("#visor") and p.is_visible("#painel-pagina")
    # outro tipo de arquivo: programa do computador
    (pasta / "notas.txt").write_text("x")
    abertos = []
    monkeypatch.setattr("ponte.documentos.subprocess.Popen", lambda args: abertos.append(args))
    monkeypatch.setattr("ponte.documentos.sys.platform", "linux")
    p.evaluate("abrirBaixado('bruto/Potiguar/1-AURI-12-RN/Perfil Convencional/notas.txt')")
    janela.descarregar()
    janela.esperar("document.getElementById('status').textContent.includes('programa do computador')")
    assert abertos and abertos[0][1].endswith("notas.txt")
    assert not janela.erros_js, janela.erros_js


def test_levantamento_do_acervo_no_mapa(janela, monkeypatch):
    from test_levantamento import TIF_LIS, PDF, ClienteFalso
    from test_pocos import csv_exemplo
    from motor import reate
    falso = ClienteFalso({
        "/POCO/Categoria-1/1-AURI-12-RN/Perfil Convencional/1AURI.tif": TIF_LIS,
        "/POCO/Categoria-7/Categoria-7_parte1/7-GMR-13-RN/Pasta de Poco/pasta.pdf": PDF,
    })
    monkeypatch.setattr(reate.ClienteREATE, "da_bacia", classmethod(lambda cls, bacia, **kw: falso))
    p = janela.page
    abrir_projeto(janela)
    janela.api._importar_cadastro(csv_exemplo(), "anp:teste")
    p.click("#aba-mapa")
    janela.esperar("document.getElementById('mapa-resumo').textContent.includes('2 poço')")
    p.select_option("#lv-bacia", "Potiguar")
    janela.esperar("document.getElementById('lv-resumo').textContent.includes('Ainda não levantada')")
    p.click("#lv-carregar")
    janela.esperar("document.querySelectorAll('.lv-cat').length === 2")
    p.click("#lv-iniciar")
    janela.esperar("document.getElementById('lv-resumo').textContent.includes('2 pasta(s) de poço')", 30)
    assert "Levantamento concluído" in janela.status()
    texto = p.text_content("#lv-resumo")
    assert ".tif → LIS" in texto and "perfil digital" in texto
    assert p.is_visible("#legenda-acervo") and p.input_value("#f-cor") == "acervo"
    p.select_option("#f-acervo", "digital")
    janela.esperar("document.querySelectorAll('#lista-mapa button').length === 1")
    p.click("#lista-mapa button")
    janela.esperar("document.getElementById('fi-corpo').textContent.includes('No acervo do REATE')")
    assert "LIS em fita" in p.text_content("#fi-corpo")
    p.click("#lv-exportar")
    janela.esperar("document.getElementById('status').textContent.includes('_pocos.csv')")
    assert not janela.erros_js, janela.erros_js


def test_avaliacao_de_formacao_no_intervalo(janela, tmp_path):
    from test_avaliacao import las_reservatorio
    p = janela.page
    abrir_projeto(janela)
    pasta = tmp_path / "ambiente_teste" / "bruto" / "Potiguar" / "7-TST-1-RN" / "Perfil Convencional"
    pasta.mkdir(parents=True)
    las_reservatorio(pasta / "tst.las")
    janela.api._abrir_projeto(str(tmp_path / "ambiente_teste"))
    p.click("#aba-perfis")
    janela.esperar("document.querySelectorAll('#lista-perfis button').length === 1")
    p.click("#lista-perfis button")
    janela.esperar("document.querySelectorAll('#pf-trilhas canvas').length >= 3", 30)
    janela.esperar("document.querySelectorAll('.av-curva').length === 8")
    assert "Nenhum intervalo-alvo" in p.text_content("#av-intervalos")
    # sem intervalo, o cálculo é recusado com explicação
    p.click("#av-calcular")
    janela.esperar("document.getElementById('status').textContent.includes('intervalo-alvo')")
    # marca o intervalo pelo formulário (o arraste já é testado em outro teste)
    p.fill("#pf-int-nome", "Açu")
    p.fill("#pf-int-topo", "1005")
    p.fill("#pf-int-base", "1035")
    p.click("#pf-form-int button")
    janela.esperar("document.querySelectorAll('.av-int').length === 1")
    p.fill("#av-gr_limpo", "30")
    p.fill("#av-gr_argila", "120")
    p.fill("#av-rw", "0,05")
    p.click("#av-calcular")
    janela.esperar("document.querySelector('#av-resultado table') !== null", 30)
    linha = p.text_content("#av-resultado tbody tr")
    assert "Açu" in linha and "10" in p.text_content("#av-resultado td.destaque")
    # trilhas calculadas aparecem no gráfico
    janela.esperar("document.getElementById('pf-trilhas').textContent.includes('Net pay')")
    assert "SW" in p.text_content("#pf-trilhas")
    registros = list((tmp_path / "ambiente_teste" / "execucoes").glob("avaliacao_*.json"))
    assert len(registros) == 1
    p.click("#av-csv")
    janela.esperar("document.getElementById('status').textContent.includes('Avaliação exportada')")
    assert not p.is_hidden("#av-historico")
    assert not janela.erros_js, janela.erros_js


def test_agp_na_ficha_e_na_avaliacao(janela, monkeypatch, tmp_path):
    from test_avaliacao import las_reservatorio
    from test_levantamento import SUL_DLIS, ClienteFalso
    from test_pocos import csv_exemplo
    from motor import reate
    with open(os.path.join(os.path.dirname(__file__), "dados", "agp_sintetico.txt"), "rb") as f:
        agp = f.read().replace(b"7TST 0001  RN", b"1AURI0012  RN")
    falso = ClienteFalso({
        "/POCO/Categoria-1/1-AURI-12-RN/Perfil Convencional/1AURI.dlis": SUL_DLIS,
        "/POCO/Categoria-1/1-AURI-12-RN/AGP/1AURI0012RN_agp.txt": agp,
    })
    monkeypatch.setattr(reate.ClienteREATE, "da_bacia", classmethod(lambda cls, bacia, **kw: falso))
    p = janela.page
    abrir_projeto(janela)
    janela.api._importar_cadastro(csv_exemplo(), "anp:teste")
    p.click("#aba-mapa")
    janela.esperar("document.getElementById('mapa-resumo').textContent.includes('poço')")
    p.select_option("#lv-bacia", "Potiguar")
    assert p.is_checked("#lv-agp")
    p.click("#lv-iniciar")
    janela.esperar("document.getElementById('lv-resumo').textContent.includes('com topos de formação')", 30)
    assert "AGP(s) lidos" in janela.status()
    p.evaluate("abrirFicha('1-AURI-12-RN')")
    janela.esperar("document.getElementById('fi-corpo').textContent.includes('AGP — dados gerais')")
    corpo = p.text_content("#fi-corpo")
    assert "Formação Açu" in corpo and "Rmf 0,162 a 74,8 °F" in corpo and "salinidade 20.000 ppm" in corpo
    # perfil do mesmo poço: as unidades do AGP viram intervalos candidatos na avaliação
    pasta = tmp_path / "ambiente_teste" / "bruto" / "Potiguar" / "1-AURI-12-RN" / "Perfil Convencional"
    pasta.mkdir(parents=True)
    las_reservatorio(pasta / "auri.las")
    janela.api._abrir_projeto(str(tmp_path / "ambiente_teste"))
    p.click("#aba-perfis")
    janela.esperar("document.querySelectorAll('#lista-perfis button').length >= 1")
    p.click("#lista-perfis button")
    janela.esperar("document.querySelectorAll('.av-int').length >= 3", 30)
    assert "Formação Açu · 300–700 m" in p.text_content("#av-intervalos")
    assert "Rmf 0,162" in p.text_content("#av-lama")
    # litologia das amostras de calha vira uma trilha estreita no gráfico
    janela.esperar("document.querySelectorAll('.pf-trilha-lito canvas').length == 1")
    assert "Litol. (AGP)" in p.text_content(".pf-trilha-lito")
    assert not janela.erros_js, janela.erros_js
