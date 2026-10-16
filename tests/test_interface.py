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
