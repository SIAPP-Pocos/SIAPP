"""Interface de verdade num navegador sem tela (pulado sem Playwright)."""
import pytest

pytestmark = pytest.mark.interface


def test_abre_sem_erro_e_escolhe_pasta(janela):
    p = janela.page
    assert p.text_content("#versao").startswith("v0.")
    p.click("#btn-pasta")
    janela.esperar("!document.getElementById('etapa-bacia').classList.contains('bloqueada')")
    assert "Projeto" in janela.status()
    assert not janela.erros_js


def test_abas_trocam_de_vista(janela):
    p = janela.page
    p.click("#aba-docs")
    assert p.is_visible("#vista-docs") and not p.is_visible("#vista-catalogo")
    assert "pasta do projeto" in p.text_content("#docs-resumo")
    p.click("#aba-catalogo")
    assert p.is_visible("#vista-catalogo")
    assert not janela.erros_js
