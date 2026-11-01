"""Ícone do SIAPP nas janelas (Windows).

O pywebview, no Windows, põe em cada janela o ícone do executável que a abriu — o `python.exe` da `.venv`. Aqui:

- `preparar_processo()` dá ao processo uma identidade própria na barra de tarefas (AppUserModelID), para o SIAPP
  não se agrupar com outros programas em Python nem herdar o ícone deles;
- `aplicar(janela)` troca o ícone da janela pelo `recursos/icone/siapp.ico` assim que ela aparece, no tamanho
  pequeno (barra de título, 16 px a 100 %) e no grande (barra de tarefas e Alt+Tab);
- `criar_atalho()` cria `SIAPP.lnk` na pasta do SIAPP, com o ícone e apontando para o lançador silencioso
  (`SIAPP.vbs`), para copiar para a Área de Trabalho ou fixar no Iniciar; recria se o destino ou a pasta mudaram.

Fora do Windows, ou se algo falhar, não faz nada: o ícone é cosmético e nunca pode impedir o SIAPP de abrir.
"""

from __future__ import annotations

import os
import sys

from lancador import identidade
from ponte import base

CAMINHO_ICO = os.path.join(base.PASTA_RECURSOS, "icone", "siapp.ico")
APP_ID = identidade.APP_ID

_WM_SETICON = 0x0080
_ICON_SMALL, _ICON_BIG = 0, 1
_IMAGE_ICON, _LR_LOADFROMFILE = 1, 0x0010
_SM_CXICON, _SM_CXSMICON = 11, 49


def _no_windows() -> bool:
    return sys.platform == "win32"


def preparar_processo() -> bool:
    """Chamar antes de criar a primeira janela. Devolve True se a identidade foi definida."""
    if not _no_windows():
        return False
    try:
        import ctypes
        return ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID) == 0
    except Exception:
        return False


def _hwnd(janela) -> int | None:
    """Identificador da janela nativa: pelo formulário do pywebview ou, se não der, pelo título."""
    try:
        h = janela.native.Handle
        h = h.ToInt64() if hasattr(h, "ToInt64") else int(h)
        if h:
            return h
    except Exception:
        pass
    try:
        import ctypes
        h = ctypes.windll.user32.FindWindowW(None, janela.title)
        return h or None
    except Exception:
        return None


def aplicar_no_hwnd(hwnd: int, caminho: str = CAMINHO_ICO) -> int:
    """Põe o ícone nos dois tamanhos que o Windows pede. Devolve quantos foram aplicados (0, 1 ou 2)."""
    import ctypes
    from ctypes import wintypes
    u = ctypes.windll.user32
    u.LoadImageW.restype = wintypes.HANDLE
    u.LoadImageW.argtypes = [wintypes.HINSTANCE, wintypes.LPCWSTR, wintypes.UINT, ctypes.c_int, ctypes.c_int,
                             wintypes.UINT]
    u.SendMessageW.restype = ctypes.c_ssize_t
    u.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    feitos = 0
    for tipo, metrica in ((_ICON_SMALL, _SM_CXSMICON), (_ICON_BIG, _SM_CXICON)):
        lado = u.GetSystemMetrics(metrica) or (16 if tipo == _ICON_SMALL else 32)
        h = u.LoadImageW(None, caminho, _IMAGE_ICON, lado, lado, _LR_LOADFROMFILE)
        if h:
            u.SendMessageW(hwnd, _WM_SETICON, tipo, h)
            feitos += 1
    return feitos


CAMINHO_ATALHO = os.path.join(base.PASTA_APP, "SIAPP.lnk")
NOME_LANCADOR = "SIAPP.vbs"


def _comando_atalho(atalho: str, vbs: str, ico: str, pasta: str) -> list[str]:
    """PowerShell que cria um atalho para o lançador silencioso (wscript + SIAPP.vbs, sem console)."""
    q = lambda s: s.replace("'", "''")      # noqa: E731  (aspas simples no PowerShell)
    script = ("$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{a}');"
              "$s.TargetPath=$env:windir+'\\System32\\wscript.exe';"
              "$s.Arguments='//nologo \"{b}\"';"
              "$s.WorkingDirectory='{p}';"
              "$s.IconLocation='{i},0';"
              "$s.Description='SIAPP';"
              "$s.Save()").format(a=q(atalho), b=q(vbs), p=q(pasta), i=q(ico))
    return ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", script]


def atalho_atual(atalho: str, vbs: str, pasta: str) -> bool:
    """True se o .lnk existe, aponta para este lançador nesta pasta e tem a identidade do SIAPP (0.53.1). O .lnk guarda
    os caminhos e o ID em UTF-16."""
    try:
        with open(atalho, "rb") as f:
            dados = f.read().lower()
    except OSError:
        return False
    return all(t.lower().encode("utf-16-le") in dados for t in (vbs, pasta, APP_ID))      # destino, pasta e identidade


def criar_atalho(sincrono: bool = False) -> bool:
    """Cria (ou recria, se o destino ou a pasta mudaram) `SIAPP.lnk`, em segundo plano. True = disparou."""
    vbs = os.path.join(base.PASTA_APP, NOME_LANCADOR)
    if not _no_windows() or not os.path.exists(CAMINHO_ICO) or not os.path.exists(vbs)             or atalho_atual(CAMINHO_ATALHO, vbs, base.PASTA_APP):
        return False
    cmd = _comando_atalho(CAMINHO_ATALHO, vbs, CAMINHO_ICO, base.PASTA_APP)

    def rodar():
        try:
            import subprocess
            subprocess.run(cmd, timeout=30, capture_output=True,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            # a mesma identidade das janelas: o atalho fixado e a janela aberta viram um botão só (0.53.1)
            identidade.aplicar_no_atalho(CAMINHO_ATALHO)
        except Exception:
            pass

    if sincrono:
        rodar()
    else:
        import threading
        threading.Thread(target=rodar, name="siapp-atalho", daemon=True).start()
    return True


def aplicar(janela) -> bool:
    """Liga a troca do ícone ao evento "shown" da janela. Devolve True se ligou."""
    if not _no_windows() or not os.path.exists(CAMINHO_ICO):
        return False

    def ao_mostrar(*_):
        try:
            h = _hwnd(janela)
            if h:
                aplicar_no_hwnd(h)
                identidade.aplicar_na_janela(h, base.PASTA_APP)      # grupo "SIAPP" (e não "Python") e reabertura certa
        except Exception:
            pass

    try:
        janela.events.shown += ao_mostrar
        return True
    except AttributeError:
        return False
