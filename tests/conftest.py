"""Configuração comum dos testes. Nenhum teste acessa a internet."""
import enum
import os
import sys
import types

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)


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


@pytest.fixture
def api(tmp_path, monkeypatch):
    """API da janela com a pasta de projeto apontando para um diretório temporário."""
    import siapp

    pasta = tmp_path / "ambiente_teste"
    monkeypatch.setattr(siapp, "PASTA_PROJETO", str(pasta))

    class Janela:
        escolha = None
        eventos: list = []

        def create_file_dialog(self, tipo, directory=""):
            return self.escolha if self.escolha is not None else (str(pasta),)

        def evaluate_js(self, codigo):
            self.eventos.append(codigo)

    a = siapp.API()
    a._janela = Janela()
    return a
