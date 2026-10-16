"""Formato real de um arquivo, pelo conteúdo — não pelo nome.

No acervo REATE a extensão engana:

- `.tif` quase nunca é imagem. Na perfilagem, TIF é o **Tape Image Format**: um
  envelope de fita (cabeçalhos de 12 bytes) em volta de um **LIS** — curvas
  digitais. Ex.: `7CS__0016__AL_7CS__0016__AL.tif`, pasta `Perfis_digitais`.
- `5PX__0011__RN_5PX__0011__RN.tif` (5-PX-11-RN) é um **DLIS** sem envelope.
- `.lis` também vem dentro do envelope TIF.

Por isso o SIAPP olha os primeiros bytes (1 KB basta) antes de decidir em que
aba o arquivo abre — e o levantamento do acervo lê só esse pedaço do portal.
"""

from __future__ import annotations

import os
import struct

DOCUMENTO = ("pdf", "tiff", "png", "jpg")
PERFIL = ("dlis", "lis", "las")
BYTES_NECESSARIOS = 1024
_POR_EXTENSAO = {".pdf": "pdf", ".tif": "tiff", ".tiff": "tiff", ".png": "png", ".jpg": "jpg",
                 ".jpeg": "jpg", ".dlis": "dlis", ".lis": "lis", ".las": "las"}
# tipos de registro lógico do LIS 79 que abrem um arquivo: cabeçalho de arquivo,
# de fita, de rolo (128–133)
_LIS_ABERTURA = range(128, 134)
NOMES = {"tiff": "imagem TIFF", "pdf": "PDF", "png": "imagem PNG", "jpg": "imagem JPEG",
         "dlis": "DLIS", "lis": "LIS", "las": "LAS"}


def pela_extensao(nome: str) -> str:
    return _POR_EXTENSAO.get(os.path.splitext(nome)[1].lower(), "")


def _sul_dlis(c: bytes) -> bool:
    # DLIS (RP66 v1): rótulo da unidade de armazenamento, 80 bytes em ASCII:
    # nº de sequência (4), "V1.00", "RECORD", tamanho máximo do registro, id do conjunto
    return c[4:9] == b"V1.00" and c[9:15] == b"RECORD"


def _lis(c: bytes) -> bool:
    # registro físico LIS: tamanho (2, big-endian), atributos (2), e o registro
    # lógico começa com o tipo (1) e um byte reservado
    if len(c) < 6:
        return False
    tamanho = struct.unpack(">H", c[:2])[0]
    return 6 <= tamanho <= 16384 and c[4] in _LIS_ABERTURA and c[5] == 0


def pelos_bytes(c: bytes) -> dict:
    """{'formato': ..., 'envelope': 'tif' ou ''} a partir do começo do arquivo.
    formato vazio = não reconhecido."""
    sem = {"envelope": ""}
    if c[:4] in (b"II*\x00", b"MM\x00*", b"II+\x00", b"MM\x00+"):
        return {"formato": "tiff", **sem}
    if c.startswith(b"\x89PNG"):
        return {"formato": "png", **sem}
    if c.startswith(b"\xff\xd8\xff"):
        return {"formato": "jpg", **sem}
    if b"%PDF" in c[:1024]:
        return {"formato": "pdf", **sem}
    if _sul_dlis(c):
        return {"formato": "dlis", **sem}
    # Tape Image Format: cada bloco começa com tipo (4, 0 = dados), posição do
    # cabeçalho anterior (4, 0 no primeiro) e do próximo (4), little-endian
    if len(c) >= 24 and c[:8] == b"\x00" * 8:
        proximo = struct.unpack("<I", c[8:12])[0]
        if proximo > 12:
            dentro = c[12:]
            return {"formato": "dlis" if _sul_dlis(dentro) else "lis", "envelope": "tif"}
    if _lis(c):
        return {"formato": "lis", **sem}
    for linha in c.lstrip(b"\xef\xbb\xbf").splitlines():   # LAS: 1ª linha útil é ~V(ersion)
        linha = linha.strip()
        if not linha or linha.startswith(b"#"):
            continue
        return {"formato": "las" if linha[:2].upper() == b"~V" else "", **sem}
    return {"formato": "", **sem}


def pelo_conteudo(caminho: str) -> str:
    try:
        with open(caminho, "rb") as f:
            return pelos_bytes(f.read(BYTES_NECESSARIOS))["formato"]
    except OSError:
        return ""


def formato(caminho: str) -> str:
    """Pelo conteúdo; se não reconhecer, pela extensão."""
    return pelo_conteudo(caminho) or pela_extensao(caminho)


def tipo_de(fmt: str) -> str:
    return "documento" if fmt in DOCUMENTO else "perfil" if fmt in PERFIL else "outro"


def tipo(caminho: str) -> str:
    """'documento' (abre no visor), 'perfil' (aba Perfis) ou 'outro'."""
    return tipo_de(formato(caminho) if os.path.isfile(caminho) else pela_extensao(caminho))
