"""Formato real de um arquivo, pelo conteúdo — não pelo nome.

O acervo REATE tem arquivos com extensão trocada: na pasta "Perfil Convencional"
do 5-PX-11-RN, `5PX__0011__RN_5PX__0011__RN.tif` é um **DLIS** (recuperação
digital da Petrobras de 2020), não uma imagem. Por isso o SIAPP olha os primeiros
bytes antes de decidir em que aba o arquivo abre.
"""

from __future__ import annotations

import os

DOCUMENTO = ("pdf", "tif", "png", "jpg")
PERFIL = ("dlis", "lis", "las")
_POR_EXTENSAO = {".pdf": "pdf", ".tif": "tif", ".tiff": "tif", ".png": "png", ".jpg": "jpg",
                 ".jpeg": "jpg", ".dlis": "dlis", ".lis": "lis", ".las": "las"}


def pela_extensao(nome: str) -> str:
    return _POR_EXTENSAO.get(os.path.splitext(nome)[1].lower(), "")


def pelo_conteudo(caminho: str) -> str:
    """'pdf', 'tif', 'png', 'jpg', 'dlis', 'las' ou '' (não reconhecido)."""
    try:
        with open(caminho, "rb") as f:
            c = f.read(1024)
    except OSError:
        return ""
    if c[:4] in (b"II*\x00", b"MM\x00*", b"II+\x00", b"MM\x00+"):
        return "tif"
    if c.startswith(b"\x89PNG"):
        return "png"
    if c.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if b"%PDF" in c:
        return "pdf"
    # DLIS (RP66 v1): rótulo da unidade de armazenamento, 80 bytes em ASCII:
    # nº de sequência (4), "V1.00", "RECORD", tamanho máximo do registro, id do conjunto
    if c[4:9] == b"V1.00" and c[9:15] == b"RECORD":
        return "dlis"
    # LAS: a primeira linha útil é a seção ~V(ersion)
    for linha in c.lstrip(b"\xef\xbb\xbf").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith(b"#"):
            continue
        return "las" if linha[:2].upper() == b"~V" else ""
    return ""


def formato(caminho: str) -> str:
    """Pelo conteúdo; se não reconhecer (LIS não tem assinatura), pela extensão."""
    return pelo_conteudo(caminho) or pela_extensao(caminho)


def tipo(caminho: str) -> str:
    """'documento' (abre no visor), 'perfil' (aba Perfis) ou 'outro'."""
    f = formato(caminho) if os.path.isfile(caminho) else pela_extensao(caminho)
    return "documento" if f in DOCUMENTO else "perfil" if f in PERFIL else "outro"
