"""
SIAPP — janela principal.

Abre uma janela nativa que exibe a interface HTML (pasta ui/) e expõe ao
JavaScript as funções da classe ponte.api.API. O JS chama, por exemplo:

    await window.pywebview.api.conectar("Sergipe")

Toda lógica fica em motor/; a ponte (ponte/) só traduz chamadas da janela.

Uso:  python siapp.py            (ou dois cliques em iniciar.bat)
      python siapp.py --debug    (habilita o inspetor do navegador: F12)
"""

from __future__ import annotations

import os
import sys

import webview

from motor import projeto as mp
from motor import registro
from ponte import base, icone
from ponte.api import API

__all__ = ["API", "main"]


def main():
    os.makedirs(base.PASTA_PROJETO, exist_ok=True)
    icone.preparar_processo()        # identidade própria na barra de tarefas (Windows)
    icone.criar_atalho()             # SIAPP.lnk com o ícone, uma vez (em segundo plano)
    registro.configurar(base.PASTA_PROJETO)
    api = API()
    # posição e tamanho da última vez (se a tela ainda existir; senão, centralizada)
    geometria = api._kwargs_geometria(api._preferencias().ler()["principal"], padrao=(1280, 820))
    janela = webview.create_window(
        f"SIAPP {mp.VERSAO_SIAPP}",
        url=os.path.join(base.PASTA_APP, "ui", "index.html"),
        js_api=api, min_size=(980, 640), **geometria,
    )
    api._janela = janela
    icone.aplicar(janela)            # ícone do SIAPP no lugar do ícone do python.exe
    api._vigiar_geometria(janela, "principal")
    janela.events.closing += api._ao_fechar_principal
    # http_server=True serve a pasta ui/ por um servidor local interno, o que
    # garante que index.html carregue estilo.css e os scripts em qualquer sistema.
    webview.start(http_server=True, debug="--debug" in sys.argv)


if __name__ == "__main__":
    main()
