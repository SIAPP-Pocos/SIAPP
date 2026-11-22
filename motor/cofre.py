"""
Guarda pequenos segredos do SIAPP (o acesso à conta do GitHub, 1.4) fora das pastas de projeto.

No Windows, o conteúdo é cifrado com a proteção de dados do próprio Windows (DPAPI, CryptProtectData): só a mesma
conta de usuário, no mesmo computador, consegue ler. Fora do Windows (testes, desenvolvimento), fica num arquivo
legível só pelo dono (permissão 600). O arquivo fica em %LOCALAPPDATA%\\SIAPP (ou ~/.local/share/SIAPP).
"""

from __future__ import annotations

import ctypes
import json
import os
import sys


def pasta_padrao() -> str:
    base = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), ".local", "share")
    return os.path.join(base, "SIAPP")


class _Blob(ctypes.Structure):
    _fields_ = [("cbData", ctypes.c_uint32), ("pbData", ctypes.POINTER(ctypes.c_char))]


def _dpapi(dados: bytes, cifrar: bool) -> bytes:
    crypt32, kernel32 = ctypes.windll.crypt32, ctypes.windll.kernel32          # type: ignore[attr-defined]
    funcao = crypt32.CryptProtectData if cifrar else crypt32.CryptUnprotectData
    funcao.argtypes = [ctypes.POINTER(_Blob), ctypes.c_wchar_p, ctypes.POINTER(_Blob), ctypes.c_void_p,
                       ctypes.c_void_p, ctypes.c_uint32, ctypes.POINTER(_Blob)]
    funcao.restype = ctypes.c_int
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    buf = ctypes.create_string_buffer(dados, len(dados))
    entrada = _Blob(len(dados), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))
    saida = _Blob()
    if not funcao(ctypes.byref(entrada), None, None, None, None, 0x1, ctypes.byref(saida)):   # 0x1: sem janela
        raise OSError("A proteção de dados do Windows recusou.")
    try:
        return ctypes.string_at(saida.pbData, saida.cbData)
    finally:
        kernel32.LocalFree(ctypes.cast(saida.pbData, ctypes.c_void_p))


CIFRADO, ABERTO = b"SIAPP-D1\n", b"SIAPP-P1\n"     # o começo do arquivo diz como ler o resto


class Cofre:
    def __init__(self, pasta: str | None = None, nome: str = "github.dat"):
        self.caminho = os.path.join(pasta or pasta_padrao(), nome)

    def ler(self) -> dict | None:
        try:
            with open(self.caminho, "rb") as f:
                dados = f.read()
            if dados.startswith(CIFRADO):
                dados = _dpapi(dados[len(CIFRADO):], cifrar=False)
            elif dados.startswith(ABERTO):
                dados = dados[len(ABERTO):]
            else:
                return None
            d = json.loads(dados.decode("utf-8"))
            return d if isinstance(d, dict) else None
        except (OSError, ValueError, AttributeError):
            return None

    def gravar(self, conteudo: dict) -> None:
        os.makedirs(os.path.dirname(self.caminho), exist_ok=True)
        dados = json.dumps(conteudo).encode("utf-8")
        saida = ABERTO + dados
        if sys.platform == "win32":
            try:
                saida = CIFRADO + _dpapi(dados, cifrar=True)
            except (OSError, AttributeError):
                pass                       # sem a proteção do Windows, fica como nos outros sistemas
        tmp = self.caminho + ".tmp"
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(saida)
        os.replace(tmp, self.caminho)

    def apagar(self) -> None:
        try:
            os.remove(self.caminho)
        except OSError:
            pass
