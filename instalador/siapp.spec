# -*- mode: python ; coding: utf-8 -*-
# SIAPP — receita do PyInstaller (0.67). Gera dist/SIAPP/SIAPP.exe (uma pasta, sem console).
# Rodar a partir da raiz do repositório:  pyinstaller instalador/siapp.spec --noconfirm
import os
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

RAIZ = os.path.abspath(os.path.join(SPECPATH, ".."))

dados = [
    (os.path.join(RAIZ, "ui"), "ui"),
    (os.path.join(RAIZ, "CHANGELOG.md"), "."),
    (os.path.join(RAIZ, "LICENSE"), "."),
    (os.path.join(RAIZ, "instalador", "AVISOS-DE-TERCEIROS.txt"), "."),
]
# recursos/ sem o modelo do OCR (tessdata é baixado na primeira vez, para a pasta de dados)
for raiz, _, arquivos in os.walk(os.path.join(RAIZ, "recursos")):
    if "tessdata" in raiz.split(os.sep):
        continue
    for a in arquivos:
        origem = os.path.join(raiz, a)
        dados.append((origem, os.path.relpath(raiz, RAIZ)))
dados += collect_data_files("dlisio") + collect_data_files("lasio") + collect_data_files("webview")

ocultos = collect_submodules("motor") + collect_submodules("ponte") + collect_submodules("lancador")
ocultos += collect_submodules("webview") + ["clr", "openpyxl", "xlrd"]

a = Analysis(
    [os.path.join(RAIZ, "siapp.py")],
    pathex=[RAIZ],
    datas=dados,
    hiddenimports=ocultos,
    # o PyMuPDF 2.x instala junto pymupdf4llm/pymupdf-layout/onnxruntime (licenças não declaradas; o SIAPP não usa e
    # o `import pymupdf` não os carrega): ficam fora do pacote
    excludes=["tkinter", "pytest", "playwright", "matplotlib", "IPython", "pymupdf4llm", "pymupdf_layout",
              "onnxruntime", "networkx", "tabulate", "yaml", "psutil", "qtpy", "PyQt5", "PyQt6", "PySide6"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="SIAPP",
    console=False,
    icon=os.path.join(RAIZ, "recursos", "icone", "siapp.ico"),
    version=os.path.join(RAIZ, "instalador", "versao.txt") if os.path.exists(os.path.join(RAIZ, "instalador", "versao.txt")) else None,
)
coll = COLLECT(exe, a.binaries, a.datas, name="SIAPP")
