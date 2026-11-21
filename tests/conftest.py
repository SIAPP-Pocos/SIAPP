"""Configuração comum dos testes. Nenhum teste acessa a internet."""
import enum
import json
import os
import sys
import types

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _webview_falso():
    """O pywebview precisa de interface gráfica; nos testes, um substituto mínimo."""
    m = types.ModuleType("webview")

    class FileDialog(enum.IntEnum):
        OPEN = 10
        FOLDER = 20
        SAVE = 30

    m.FileDialog = FileDialog
    return m


sys.modules.setdefault("webview", _webview_falso())


def item(nome, pasta=False, tamanho=0):
    return {"nome": nome, "pasta": pasta, "tamanho": tamanho, "modificado": ""}


class ArvoreFalsa:
    """Substitui ClienteREATE.listar por uma árvore de pastas em memória."""

    def __init__(self, arvore: dict):
        self.arvore = arvore
        self.lidas: list[str] = []

    def __call__(self, caminho):
        caminho = "/" + caminho.strip("/") + "/" if caminho.strip("/") else "/"
        self.lidas.append(caminho)
        return [dict(i, caminho=caminho + i["nome"] + ("/" if i["pasta"] else ""))
                for i in self.arvore[caminho]]


def _sem_github(monkeypatch):
    """1.3: ao abrir o projeto, o SIAPP procura base nova no GitHub. Nos testes, nunca vai à internet: a base
    "ainda não foi publicada" (quem testa a novidade troca esta função)."""
    from motor import atualizacao as mat
    from motor import comunidade as mc
    monkeypatch.setattr(mc, "consultar_base", lambda *a, **k: None)
    monkeypatch.setattr(mat, "consultar", lambda *a, **k: None)          # e versão nova do SIAPP, também não


@pytest.fixture
def api(tmp_path, monkeypatch):
    """API da janela com a pasta de projeto apontando para um diretório temporário."""
    import siapp
    from ponte import base

    pasta = tmp_path / "ambiente_teste"
    monkeypatch.setattr(base, "PASTA_PROJETO", str(pasta))
    _sem_github(monkeypatch)

    class Janela:
        escolha = None          # resposta do diálogo de pasta (None = a pasta do projeto)
        arquivo = None          # resposta do diálogo de abrir arquivo
        eventos: list = []

        def create_file_dialog(self, tipo, directory="", **kw):
            if tipo != siapp.webview.FileDialog.FOLDER:
                return self.arquivo
            return self.escolha if self.escolha is not None else (str(pasta),)

        def evaluate_js(self, codigo):
            self.eventos.append(codigo)

    a = siapp.API()
    a._janela = Janela()
    return a


# ------------------------------------------------------------ interface
def _playwright_disponivel():
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
        return True
    except Exception:
        return False


@pytest.fixture(scope="session")
def navegador():
    if not _playwright_disponivel():
        pytest.skip("Playwright não instalado")
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        try:
            b = p.chromium.launch(args=["--enable-unsafe-swiftshader"])   # WebGL do bloco 3D
        except Exception as e:  # Chromium não baixado
            pytest.skip(f"Chromium indisponível: {e}")
        yield b
        b.close()


@pytest.fixture
def janela(tmp_path, monkeypatch, navegador, request):
    """Interface real (ui/) num Chromium sem tela, ligada à API Python."""
    import siapp
    from ponte import base
    from interface_util import JanelaFalsa, abrir

    pasta = tmp_path / "ambiente_teste"
    monkeypatch.setattr(base, "PASTA_PROJETO", str(pasta))
    _sem_github(monkeypatch)
    # os avisos de primeira vez (OCR, avaliação, modelo 3D) já vistos: os testes clicam direto nos botões;
    # test_avisos_de_primeira_vez apaga a marca para conferir o aviso
    pasta.mkdir(parents=True, exist_ok=True)
    pref = {"avisos_vistos": {"ocr": True, "avaliacao": True, "bloco": True}}
    if os.environ.get("SIAPP_ESCURO"):
        pref.update({"tema": "escuro", "abrir_ao_iniciar": False})
    (pasta / "preferencias.json").write_text(json.dumps(pref), encoding="utf-8")
    a = siapp.API()
    a._janela = JanelaFalsa(str(pasta))
    jt, srv = abrir(a, navegador)
    yield jt
    if os.environ.get("SIAPP_ESCURO"):
        try:
            jt.page.screenshot(path=os.path.join(os.environ["SIAPP_ESCURO"], request.node.name + ".png"))
        except Exception:
            pass
    jt.page.close()
    srv.httpd.shutdown()
