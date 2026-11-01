"""Identidade na barra de tarefas (0.53.1): atalho e janelas com o mesmo AppUserModelID, nome e reabertura do SIAPP.

Os testes de COM rodam só no Windows (usam o Shell de verdade, com um atalho e uma janela Win32 invisíveis)."""
import ctypes
import os
import shutil
import subprocess
import sys
import types
from ctypes import wintypes

import pytest

from lancador import identidade as idn
from lancador import janela
from ponte import base, icone

windows = pytest.mark.skipif(sys.platform != "win32", reason="usa o Shell do Windows")


def test_a_identidade_e_uma_so_para_janelinha_janela_e_atalho():
    assert idn.APP_ID == icone.APP_ID == janela.APP_ID == "SIAPP.Pocos.SIAPP"


def test_fora_do_windows_nao_faz_nada(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "platform", "linux")
    lnk = tmp_path / "a.lnk"
    lnk.write_bytes(b"x")
    assert idn.aplicar_na_janela(1234, str(tmp_path)) is False
    assert idn.aplicar_no_atalho(str(lnk)) is False
    assert idn.ler_da_janela(1234, "id") is None and idn.ler_do_atalho(str(lnk)) is None


def test_valores_da_janela_reabrem_pelo_lancador_silencioso_e_nunca_pelo_python():
    v = idn.valores_da_janela(r"C:\Programas\SIAPP")
    assert v["id"] == "SIAPP.Pocos.SIAPP" and v["nome"] == "SIAPP"
    assert v["comando"].lower().endswith(r'wscript.exe" //nologo "c:\programas\siapp\siapp.vbs"')
    assert "python" not in v["comando"].lower()
    assert v["icone"] == r"C:\Programas\SIAPP\recursos\icone\siapp.ico,0"


def test_janela_principal_recebe_a_identidade_ao_aparecer(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    chamadas = []

    class Evento(list):
        def __iadd__(self, f):
            self.append(f)
            return self

    j = types.SimpleNamespace(title="SIAPP", events=types.SimpleNamespace(shown=Evento()))
    monkeypatch.setattr(icone, "_hwnd", lambda _j: 4321)
    monkeypatch.setattr(icone, "aplicar_no_hwnd", lambda h: 2)
    monkeypatch.setattr(idn, "aplicar_na_janela", lambda h, pasta: chamadas.append((h, pasta)) or True)
    assert icone.aplicar(j) is True
    j.events.shown[0]()
    assert chamadas == [(4321, base.PASTA_APP)]


def test_atalho_criado_recebe_a_identidade_depois_do_powershell(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "platform", "win32")
    lnk = tmp_path / "SIAPP.lnk"
    monkeypatch.setattr(icone, "CAMINHO_ATALHO", str(lnk))
    ordem = []
    monkeypatch.setattr(subprocess, "run", lambda cmd, **kw: ordem.append("powershell"))
    monkeypatch.setattr(idn, "aplicar_no_atalho", lambda c: ordem.append(("id", c)) or True)
    assert icone.criar_atalho(sincrono=True) is True
    assert ordem == ["powershell", ("id", str(lnk))]


@windows
def test_atalho_real_ganha_a_identidade_e_nao_perde_o_destino(tmp_path):
    lnk = tmp_path / "SIAPP.lnk"
    cmd = icone._comando_atalho(str(lnk), os.path.join(base.PASTA_APP, "SIAPP.vbs"), icone.CAMINHO_ICO, base.PASTA_APP)
    r = subprocess.run(cmd, capture_output=True, timeout=60, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    assert r.returncode == 0 and lnk.exists(), r.stderr
    assert idn.ler_do_atalho(str(lnk)) is None                                   # como o da 0.47
    assert icone.atalho_atual(str(lnk), os.path.join(base.PASTA_APP, "SIAPP.vbs"), base.PASTA_APP) is False
    assert idn.aplicar_no_atalho(str(lnk)) is True
    assert idn.ler_do_atalho(str(lnk)) == "SIAPP.Pocos.SIAPP"
    assert icone.atalho_atual(str(lnk), os.path.join(base.PASTA_APP, "SIAPP.vbs"), base.PASTA_APP) is True
    # ainda é um atalho que abre o lançador, com o ícone
    ps = ("$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%s'); "
          "$s.TargetPath; $s.Arguments; $s.IconLocation" % str(lnk).replace("'", "''"))
    saida = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True, timeout=60,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout.lower()
    assert "wscript.exe" in saida and "siapp.vbs" in saida and "siapp.ico" in saida


@windows
def test_janela_real_ganha_id_nome_icone_e_comando_de_reabertura():
    u = ctypes.windll.user32
    u.CreateWindowExW.restype = wintypes.HWND
    u.CreateWindowExW.argtypes = [wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD, ctypes.c_int,
                                  ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.HWND, wintypes.HMENU,
                                  wintypes.HINSTANCE, wintypes.LPVOID]
    hwnd = u.CreateWindowExW(0, "STATIC", "teste siapp", 0x00CF0000, 0, 0, 100, 100, None, None, None, None)
    assert hwnd
    try:
        assert idn.aplicar_na_janela(hwnd, base.PASTA_APP) is True
        assert idn.ler_da_janela(hwnd, "id") == "SIAPP.Pocos.SIAPP"
        assert idn.ler_da_janela(hwnd, "nome") == "SIAPP"
        assert idn.ler_da_janela(hwnd, "icone").endswith("siapp.ico,0")
        cmd = idn.ler_da_janela(hwnd, "comando")
        assert cmd.lower().endswith('wscript.exe" //nologo "' + os.path.join(base.PASTA_APP, "SIAPP.vbs").lower() + '"') \
            or "siapp.vbs" in cmd.lower()
        assert "pythonw" not in cmd.lower()
    finally:
        u.DestroyWindow(hwnd)


@windows
def test_janela_invalida_nao_levanta_erro():
    assert idn.aplicar_na_janela(0, base.PASTA_APP) is False
    assert idn.aplicar_na_janela(999999999, base.PASTA_APP) is False
    assert idn.ler_do_atalho(r"C:\nao\existe.lnk") is None and idn.aplicar_no_atalho(r"C:\nao\existe.lnk") is False


@windows
def test_caminho_relativo_tambem_funciona(tmp_path, monkeypatch):
    lnk = tmp_path / "SIAPP.lnk"
    cmd = icone._comando_atalho(str(lnk), os.path.join(base.PASTA_APP, "SIAPP.vbs"), icone.CAMINHO_ICO, base.PASTA_APP)
    subprocess.run(cmd, capture_output=True, timeout=60, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    monkeypatch.chdir(tmp_path)
    assert idn.aplicar_no_atalho("SIAPP.lnk") is True and idn.ler_do_atalho("SIAPP.lnk") == "SIAPP.Pocos.SIAPP"
