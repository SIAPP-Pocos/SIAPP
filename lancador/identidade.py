"""Identidade do SIAPP na barra de tarefas do Windows (0.53.1): o atalho e as janelas são "o mesmo programa".

O que o Windows faz: agrupa os botões da barra de tarefas pelo **AppUserModelID**. Antes da 0.53.1, as janelas do SIAPP
tinham o ID `SIAPP.Pocos.SIAPP`, mas o atalho (`SIAPP.lnk`, que chama o `wscript` e o `SIAPP.vbs`) não tinha ID nenhum.
Resultado: o atalho fixado virava um botão e a janela aberta outro, rotulado "Python" (o nome do `pythonw.exe` que a abriu).

Aqui se grava a mesma identidade nos dois lados, só com `ctypes` (esta pasta não pode depender de nada instalado):

- `aplicar_no_atalho(lnk)`: põe o `System.AppUserModel.ID` no arquivo `.lnk`; o atalho fixado passa a ser o mesmo botão da
  janela aberta;
- `aplicar_na_janela(hwnd, pasta)`: põe na janela o ID e também o **comando de reabertura**, o **ícone** e o **nome** ("SIAPP").
  Com isso o grupo se chama SIAPP (e não "Python") e, se você fixar a janela aberta na barra, o atalho criado abre o SIAPP
  pelo lançador silencioso, não o `pythonw.exe`.

Fora do Windows, ou se algo falhar, não faz nada e devolve False: identidade é cosmética e nunca pode impedir o SIAPP de abrir.
"""

from __future__ import annotations

import ctypes
import ntpath
import os
import sys
from ctypes import wintypes

APP_ID = "SIAPP.Pocos.SIAPP"
NOME = "SIAPP"
NOME_LANCADOR = "SIAPP.vbs"

_FMTID_APPUSERMODEL = "{9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3}"
# System.AppUserModel.* : número da propriedade dentro do conjunto acima
PROPRIEDADES = {"id": 5, "comando": 2, "icone": 3, "nome": 4}
_VT_LPWSTR = 31


def _no_windows() -> bool:
    return sys.platform == "win32"


class _GUID(ctypes.Structure):
    _fields_ = [("Data1", ctypes.c_ulong), ("Data2", ctypes.c_ushort), ("Data3", ctypes.c_ushort),
                ("Data4", ctypes.c_ubyte * 8)]


class _PROPERTYKEY(ctypes.Structure):
    _fields_ = [("fmtid", _GUID), ("pid", ctypes.c_ulong)]


def _guid(texto: str) -> _GUID:
    g = _GUID()
    if ctypes.windll.ole32.CLSIDFromString(ctypes.c_wchar_p(texto), ctypes.byref(g)) != 0:
        raise OSError(f"GUID inválido: {texto}")
    return g


def _chave(campo: str) -> _PROPERTYKEY:
    return _PROPERTYKEY(_guid(_FMTID_APPUSERMODEL), PROPRIEDADES[campo])


def _iniciar_com() -> None:
    # S_OK, S_FALSE (já iniciado) e RPC_E_CHANGED_MODE (outro modo na mesma thread) servem igual para o que fazemos
    ctypes.windll.ole32.CoInitializeEx(None, 2)


def _metodo(objeto, indice: int, *tipos):
    """Método de número `indice` da tabela virtual de um objeto COM; devolve HRESULT."""
    vtbl = ctypes.cast(ctypes.cast(objeto, ctypes.POINTER(ctypes.c_void_p))[0], ctypes.POINTER(ctypes.c_void_p))
    return ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, *tipos)(vtbl[indice])


def _soltar(objeto) -> None:
    if objeto:
        _metodo(objeto, 2)(objeto)                                  # IUnknown::Release


def _propvariant_texto(texto: str):
    """PROPVARIANT do tipo VT_LPWSTR. (InitPropVariantFromString é função inline do cabeçalho do Windows, não existe
    na DLL; por isso o valor é montado aqui: tipo nos 2 primeiros bytes e, no deslocamento 8, o ponteiro para a string
    na memória COM, que o PropVariantClear libera.)"""
    pv = ctypes.create_string_buffer(24)                            # PROPVARIANT (16 bytes em 32 bits, 24 em 64)
    alocar = ctypes.windll.ole32.CoTaskMemAlloc
    alocar.restype = ctypes.c_void_p
    alocar.argtypes = [ctypes.c_size_t]
    dados = (texto + "\0").encode("utf-16-le")
    memoria = alocar(len(dados))
    if not memoria:
        raise OSError("sem memória para o valor da propriedade")
    ctypes.memmove(memoria, dados, len(dados))
    ctypes.memmove(ctypes.addressof(pv), _VT_LPWSTR.to_bytes(2, "little"), 2)
    ctypes.memmove(ctypes.addressof(pv) + 8, ctypes.byref(ctypes.c_void_p(memoria)), ctypes.sizeof(ctypes.c_void_p))
    return pv


def _gravar(loja, valores: dict) -> None:
    """IPropertyStore::SetValue de cada (campo → texto) e Commit."""
    for campo, texto in valores.items():
        pv = _propvariant_texto(texto)
        try:
            h = _metodo(loja, 6, ctypes.POINTER(_PROPERTYKEY), ctypes.c_void_p)(loja, ctypes.byref(_chave(campo)), pv)
        finally:
            ctypes.windll.ole32.PropVariantClear(pv)
        if h != 0:
            raise OSError(f"SetValue({campo}) falhou: 0x{h & 0xFFFFFFFF:08X}")
    h = _metodo(loja, 7)(loja)                                      # Commit
    if h != 0:
        raise OSError(f"Commit falhou: 0x{h & 0xFFFFFFFF:08X}")


def _ler(loja, campo: str) -> str | None:
    pv = ctypes.create_string_buffer(24)
    h = _metodo(loja, 5, ctypes.POINTER(_PROPERTYKEY), ctypes.c_void_p)(loja, ctypes.byref(_chave(campo)), pv)
    if h != 0:
        return None
    try:
        if int.from_bytes(pv.raw[:2], "little") != _VT_LPWSTR:
            return None
        saida = ctypes.c_void_p()
        if ctypes.windll.propsys.PropVariantToStringAlloc(pv, ctypes.byref(saida)) != 0:
            return None
        try:
            return ctypes.wstring_at(saida.value)
        finally:
            ctypes.windll.ole32.CoTaskMemFree(saida)
    finally:
        ctypes.windll.ole32.PropVariantClear(pv)


# ------------------------------------------------------------------------------------------------------ a janela
def comando_de_reabertura(pasta_app: str) -> str:
    """Linha de comando que reabre o SIAPP pelo lançador silencioso (a mesma do atalho); instalado, o SIAPP.exe."""
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'

    # o comando é sempre do Windows: ntpath usa a barra invertida também quando os testes rodam no Linux
    wscript = ntpath.join(os.environ.get("WINDIR") or os.environ.get("SystemRoot") or r"C:\Windows", "System32", "wscript.exe")
    return f'"{wscript}" //nologo "{ntpath.join(pasta_app, NOME_LANCADOR)}"'


def valores_da_janela(pasta_app: str) -> dict:
    return {"id": APP_ID, "comando": comando_de_reabertura(pasta_app),
            "icone": ntpath.join(pasta_app, "recursos", "icone", "siapp.ico") + ",0", "nome": NOME}


def _loja_da_janela(hwnd: int):
    iid = _guid("{886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99}")           # IID_IPropertyStore
    f = ctypes.windll.shell32.SHGetPropertyStoreForWindow
    f.argtypes = [wintypes.HWND, ctypes.POINTER(_GUID), ctypes.POINTER(ctypes.c_void_p)]
    f.restype = ctypes.c_long
    loja = ctypes.c_void_p()
    h = f(hwnd, ctypes.byref(iid), ctypes.byref(loja))
    if h != 0 or not loja.value:
        raise OSError(f"SHGetPropertyStoreForWindow falhou: 0x{h & 0xFFFFFFFF:08X}")
    return loja


def aplicar_na_janela(hwnd: int, pasta_app: str) -> bool:
    """Grava na janela o ID, o comando de reabertura, o ícone e o nome. True se deu certo."""
    if not _no_windows() or not hwnd:
        return False
    loja = None
    try:
        _iniciar_com()
        loja = _loja_da_janela(hwnd)
        _gravar(loja.value, valores_da_janela(pasta_app))
        return True
    except Exception:
        return False
    finally:
        if loja is not None:
            _soltar(loja.value)


def ler_da_janela(hwnd: int, campo: str) -> str | None:
    if not _no_windows():
        return None
    loja = None
    try:
        _iniciar_com()
        loja = _loja_da_janela(hwnd)
        return _ler(loja.value, campo)
    except Exception:
        return None
    finally:
        if loja is not None:
            _soltar(loja.value)


# ------------------------------------------------------------------------------------------------------ o atalho
def _abrir_atalho(caminho: str):
    """(IShellLinkW, IPersistFile, IPropertyStore) do .lnk, carregado para leitura e escrita. O caminho tem de ser absoluto."""
    caminho = os.path.abspath(caminho)
    _iniciar_com()
    clsid = _guid("{00021401-0000-0000-C000-000000000046}")        # CLSID_ShellLink
    iid_link = _guid("{000214F9-0000-0000-C000-000000000046}")     # IID_IShellLinkW
    link = ctypes.c_void_p()
    h = ctypes.windll.ole32.CoCreateInstance(ctypes.byref(clsid), None, 1, ctypes.byref(iid_link), ctypes.byref(link))
    if h != 0:
        raise OSError(f"CoCreateInstance(ShellLink) falhou: 0x{h & 0xFFFFFFFF:08X}")
    arquivo, loja = ctypes.c_void_p(), ctypes.c_void_p()
    try:
        for iid, destino in (("{0000010B-0000-0000-C000-000000000046}", arquivo),          # IPersistFile
                             ("{886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99}", loja)):             # IPropertyStore
            g = _guid(iid)
            h = _metodo(link.value, 0, ctypes.POINTER(_GUID), ctypes.POINTER(ctypes.c_void_p))(
                link.value, ctypes.byref(g), ctypes.byref(destino))
            if h != 0:
                raise OSError(f"QueryInterface falhou: 0x{h & 0xFFFFFFFF:08X}")
        h = _metodo(arquivo.value, 5, ctypes.c_wchar_p, ctypes.c_ulong)(arquivo.value, caminho, 2)   # Load(READWRITE)
        if h != 0:
            raise OSError(f"Load falhou: 0x{h & 0xFFFFFFFF:08X}")
    except Exception:
        for o in (loja, arquivo, link):
            _soltar(o.value)
        raise
    return link, arquivo, loja


def aplicar_no_atalho(caminho: str) -> bool:
    """Grava a identidade do SIAPP (System.AppUserModel.ID) no arquivo `.lnk`. True se deu certo."""
    if not _no_windows() or not os.path.isfile(caminho):
        return False
    link = arquivo = loja = None
    caminho = os.path.abspath(caminho)
    try:
        link, arquivo, loja = _abrir_atalho(caminho)
        _gravar(loja.value, {"id": APP_ID})
        h = _metodo(arquivo.value, 6, ctypes.c_wchar_p, ctypes.c_long)(arquivo.value, caminho, 1)     # Save(fRemember)
        return h == 0
    except Exception:
        return False
    finally:
        for o in (loja, arquivo, link):
            if o is not None:
                _soltar(o.value)


def ler_do_atalho(caminho: str, campo: str = "id") -> str | None:
    if not _no_windows() or not os.path.isfile(caminho):
        return None
    link = arquivo = loja = None
    try:
        link, arquivo, loja = _abrir_atalho(caminho)
        return _ler(loja.value, campo)
    except Exception:
        return None
    finally:
        for o in (loja, arquivo, link):
            if o is not None:
                _soltar(o.value)
