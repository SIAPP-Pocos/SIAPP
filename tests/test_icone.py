"""Ícone do SIAPP (0.46): o .ico tem todos os tamanhos, cada um desenhado para o seu; a troca nunca derruba o app."""

import os
import struct
import sys
import types

from ponte import base, icone

PASTA = os.path.join(base.PASTA_RECURSOS, "icone")
TAMANHOS = {16, 20, 24, 32, 40, 48, 64, 256}


def _entradas_ico(caminho):
    dados = open(caminho, "rb").read()
    reservado, tipo, n = struct.unpack_from("<HHH", dados, 0)
    assert (reservado, tipo) == (0, 1)
    saida = []
    for i in range(n):
        w, h, _, _, planos, bpp, tam, off = struct.unpack_from("<BBBBHHII", dados, 6 + 16 * i)
        png = dados[off:off + tam]
        assert png[:8] == b"\x89PNG\r\n\x1a\n"
        pw, ph = struct.unpack(">II", png[16:24])          # IHDR
        saida.append(((w or 256), (h or 256), pw, ph, bpp))
    return saida


def test_ico_tem_todos_os_tamanhos_e_cada_png_bate_com_a_entrada():
    ents = _entradas_ico(icone.CAMINHO_ICO)
    assert {e[0] for e in ents} == TAMANHOS
    for w, h, pw, ph, bpp in ents:
        assert (w, h) == (pw, ph) and w == h and bpp == 32


def test_fontes_svg_do_icone_e_icone_da_interface_existem():
    for nome in ("siapp.svg", "siapp-40.svg", "siapp-32.svg", "siapp-24.svg", "siapp-20.svg", "siapp-16.svg"):
        txt = open(os.path.join(PASTA, nome), encoding="utf-8").read()
        assert txt.lstrip().startswith("<svg") and 'viewBox="0 0 256 256"' in txt
    ui = os.path.join(base.PASTA_APP, "ui", "img", "siapp.svg")
    assert os.path.exists(ui)
    html = open(os.path.join(base.PASTA_APP, "ui", "index.html"), encoding="utf-8").read()
    assert 'src="img/siapp.svg"' in html and 'rel="icon"' in html


def test_fora_do_windows_nao_faz_nada(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    assert icone.preparar_processo() is False
    assert icone.aplicar(types.SimpleNamespace()) is False


def test_no_windows_liga_ao_evento_shown_e_erro_nao_escapa(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    chamados = []

    class Evento(list):
        def __iadd__(self, f):
            self.append(f)
            return self

    janela = types.SimpleNamespace(title="SIAPP 0.46.0", events=types.SimpleNamespace(shown=Evento()))
    monkeypatch.setattr(icone, "_hwnd", lambda j: 1234)
    monkeypatch.setattr(icone, "aplicar_no_hwnd", lambda h: chamados.append(h) or 2)
    assert icone.aplicar(janela) is True
    janela.events.shown[0]()
    assert chamados == [1234]

    def explode(h):
        raise OSError("sem user32")
    monkeypatch.setattr(icone, "aplicar_no_hwnd", explode)
    janela.events.shown[0]()                                # não levanta


def test_janela_sem_eventos_nao_quebra(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    assert icone.aplicar(types.SimpleNamespace(title="x")) is False


def _lnk_falso(caminho, *textos):
    """Um .lnk de mentira: o que importa é que os caminhos aparecem em UTF-16, como no formato real."""
    caminho.write_bytes(b"L\x00\x00\x00" + b"".join(t.encode("utf-16-le") for t in textos))


def test_atalho_so_no_windows_e_so_se_estiver_desatualizado(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "platform", "linux")
    assert icone.criar_atalho(sincrono=True) is False
    monkeypatch.setattr(sys, "platform", "win32")
    lnk = tmp_path / "SIAPP.lnk"
    monkeypatch.setattr(icone, "CAMINHO_ATALHO", str(lnk))
    _lnk_falso(lnk, os.path.join(base.PASTA_APP, icone.NOME_LANCADOR), base.PASTA_APP)
    assert icone.criar_atalho(sincrono=True) is False      # aponta para esta pasta: não recria


def test_atalho_de_pasta_antiga_ou_do_bat_e_recriado(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "platform", "win32")
    lnk = tmp_path / "SIAPP.lnk"
    monkeypatch.setattr(icone, "CAMINHO_ATALHO", str(lnk))
    rodou = []
    import subprocess
    monkeypatch.setattr(subprocess, "run", lambda cmd, **kw: rodou.append(cmd))
    _lnk_falso(lnk, r"C:\x\pasta_antiga\SIAPP.vbs", r"C:\x\pasta_antiga")            # pasta com o nome antigo
    assert icone.criar_atalho(sincrono=True) is True
    _lnk_falso(lnk, os.path.join(base.PASTA_APP, "iniciar.bat"), base.PASTA_APP)   # atalho da 0.46
    assert icone.criar_atalho(sincrono=True) is True
    assert len(rodou) == 2


def test_atalho_atual_ignora_maiusculas_e_arquivo_ausente(tmp_path):
    lnk = tmp_path / "a.lnk"
    assert icone.atalho_atual(str(lnk), r"C:\SIAPP\SIAPP.vbs", r"C:\SIAPP") is False
    _lnk_falso(lnk, r"c:\siapp\siapp.vbs", r"c:\siapp")
    assert icone.atalho_atual(str(lnk), r"C:\SIAPP\SIAPP.vbs", r"C:\SIAPP") is True


def test_comando_do_atalho_aponta_para_o_lancador_silencioso_e_escapa_aspas():
    cmd = icone._comando_atalho(r"C:\x\SIAPP.lnk", r"C:\Ana's\SIAPP.vbs", r"C:\x\recursos\icone\siapp.ico", r"C:\x")
    assert cmd[0] == "powershell" and cmd[-2] == "-Command"
    s = cmd[-1]
    assert r"System32\wscript.exe" in s and "iniciar.bat" not in s
    assert "Arguments='//nologo \"C:\\Ana''s\\SIAPP.vbs\"'" in s
    assert "IconLocation='C:\\x\\recursos\\icone\\siapp.ico,0'" in s


def test_atalho_dispara_powershell_no_windows(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(icone, "CAMINHO_ATALHO", str(tmp_path / "SIAPP.lnk"))
    rodou = []
    import subprocess
    monkeypatch.setattr(subprocess, "run", lambda cmd, **kw: rodou.append(cmd))
    assert icone.criar_atalho(sincrono=True) is True
    assert rodou and rodou[0][0] == "powershell"
