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
from lancador import passos
from motor import registro
from ponte import base, icone
from ponte.api import API

__all__ = ["API", "main"]


def verificar() -> int:
    """`SIAPP.exe --verificar` (0.67): sem abrir janela, confere se o pacote tem tudo (módulos, interface, recursos) e
    se a pasta de dados é gravável. Usado pelo GitHub ao montar o instalador. Imprime um JSON; 0 = tudo certo."""
    import importlib
    import json
    import pkgutil
    import tempfile
    erros, mods = [], 0
    for pacote in ("motor", "ponte", "lancador"):
        pk = importlib.import_module(pacote)
        for m in pkgutil.iter_modules(pk.__path__):
            try:
                importlib.import_module(f"{pacote}.{m.name}")
                mods += 1
            except Exception as e:  # noqa: BLE001
                erros.append(f"{pacote}.{m.name}: {type(e).__name__}: {e}")
    for rel in ("ui/index.html", "ui/estilo.css", "recursos/ferramentas.json", "recursos/icone/siapp.ico", "CHANGELOG.md"):
        if not os.path.isfile(os.path.join(base.PASTA_APP, rel)):
            erros.append(f"falta {rel}")
    from importlib import metadata
    for lib, dist in (("dlisio", "dlisio"), ("lasio", "lasio"), ("pymupdf", "pymupdf"), ("numpy", "numpy"),
                      ("openpyxl", "openpyxl"), ("xlrd", "xlrd"), ("requests", "requests"), ("webview", "pywebview")):
        try:
            importlib.import_module(lib)
        except Exception as e:  # noqa: BLE001
            erros.append(f"{lib}: {e}")
        # 1.0.1: sem os metadados do pacote, o lasio procura a própria versão com "git describe" na pasta de onde o
        # SIAPP foi aberto, e quebra quando ela é um repositório com etiqueta (aconteceu na montagem da v1.0.0)
        try:
            metadata.version(dist)
        except Exception as e:  # noqa: BLE001
            erros.append(f"{dist}: sem metadados no pacote ({type(e).__name__})")
    try:
        os.makedirs(base.PASTA_DADOS, exist_ok=True)
        tempfile.NamedTemporaryFile(dir=base.PASTA_DADOS).close()
    except OSError as e:
        erros.append(f"pasta de dados: {e}")
    texto = json.dumps({"versao": mp.VERSAO_SIAPP, "instalado": base.INSTALADO, "app": base.PASTA_APP,
                        "dados": base.PASTA_DADOS, "modulos": mods, "erros": erros}, ensure_ascii=False, indent=1)
    try:                                       # o SIAPP.exe não tem console: o resultado também vai para um arquivo
        with open(os.path.join(base.PASTA_DADOS, "verificar.json"), "w", encoding="utf-8") as f:
            f.write(texto)
    except OSError:
        pass
    if sys.stdout is not None:
        print(texto)
    return 1 if erros else 0


def verificar_janela(espera: float = 90) -> int:
    """`SIAPP.exe --verificar-janela` (0.67): abre a janela de verdade, espera a interface pedir a versão ao motor (o
    caminho inteiro: WebView2 → página → scripts → ponte → Python → resposta) e fecha sozinha. Grava
    verificar-janela.json na pasta de dados; 0 = a janela abriu e a ponte respondeu."""
    import json
    import time
    os.makedirs(base.PASTA_PROJETO, exist_ok=True)
    registro.configurar(base.PASTA_PROJETO)
    api = API()
    janela = webview.create_window(f"SIAPP {mp.VERSAO_SIAPP} (verificação)", url=os.path.join(base.PASTA_APP, "ui", "index.html"),
                                   js_api=api, width=1280, height=820)
    api._janela = janela
    resultado = {"versao": mp.VERSAO_SIAPP, "ok": False, "tela": "", "segundos": 0.0, "erro": ""}

    def conferir():
        t0 = time.time()
        try:
            while time.time() - t0 < espera:
                try:
                    tela = janela.evaluate_js('(document.getElementById("versao") || {}).textContent || ""') or ""
                except Exception as e:  # noqa: BLE001  (a página ainda não carregou)
                    resultado["erro"] = f"{type(e).__name__}: {e}"
                    tela = ""
                if tela.strip() == "v" + mp.VERSAO_SIAPP:
                    resultado.update(ok=True, tela=tela.strip(), erro="")
                    break
                resultado["tela"] = tela
                time.sleep(1)
            else:
                resultado["erro"] = resultado["erro"] or "a interface não mostrou a versão a tempo"
        finally:
            resultado["segundos"] = round(time.time() - t0, 1)
            resultado["motor_da_janela"] = webview.renderer or ""
            janela.destroy()

    webview.start(conferir, http_server=True)
    texto = json.dumps(resultado, ensure_ascii=False, indent=1)
    try:
        with open(os.path.join(base.PASTA_DADOS, "verificar-janela.json"), "w", encoding="utf-8") as f:
            f.write(texto)
    except OSError:
        pass
    if sys.stdout is not None:
        print(texto)
    return 0 if resultado["ok"] else 1


def main():
    if "--verificar" in sys.argv:
        sys.exit(verificar())
    if "--verificar-janela" in sys.argv:
        sys.exit(verificar_janela())
    movidas = base.migrar_pastas_antigas() if base.INSTALADO else []    # 1.1: ambiente_teste → Projetos\Projeto principal
    os.makedirs(base.PASTA_PROJETO, exist_ok=True)
    icone.preparar_processo()        # identidade própria na barra de tarefas (Windows)
    icone.criar_atalho()             # SIAPP.lnk com o ícone, uma vez (em segundo plano)
    registro.configurar(base.PASTA_PROJETO)
    for m in movidas:
        registro.log.info("pasta reorganizada (1.1): %s", m)
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
    janela.events.shown += lambda *_: passos.avisar_abertura()    # a janelinha do lançador some
    api._vigiar_geometria(janela, "principal")
    janela.events.closing += api._ao_fechar_principal
    # http_server=True serve a pasta ui/ por um servidor local interno, o que
    # garante que index.html carregue estilo.css e os scripts em qualquer sistema.
    webview.start(http_server=True, debug="--debug" in sys.argv)


if __name__ == "__main__":
    # 0.67: no SIAPP.exe, o processo do OCR (multiprocessing "spawn") reabre o próprio executável; sem isto ele
    # abriria outra janela do SIAPP em vez de ler o documento
    import multiprocessing
    multiprocessing.freeze_support()
    main()
