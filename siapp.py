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
from ponte import base
from ponte.api import API

__all__ = ["API", "main"]


def main():
    os.makedirs(base.PASTA_PROJETO, exist_ok=True)
    registro.configurar(base.PASTA_PROJETO)
    api = API()
    janela = webview.create_window(
        f"SIAPP {mp.VERSAO_SIAPP}",
        url=os.path.join(base.PASTA_APP, "ui", "index.html"),
        js_api=api,
        width=1280, height=820, min_size=(980, 640),
    )
    api._janela = janela
    # http_server=True serve a pasta ui/ por um servidor local interno, o que
    # garante que index.html carregue estilo.css e os scripts em qualquer sistema.
    webview.start(http_server=True, debug="--debug" in sys.argv)


if __name__ == "__main__":
    main()
