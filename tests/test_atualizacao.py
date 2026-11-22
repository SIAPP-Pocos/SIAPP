"""Versão nova do SIAPP (1.3): consultar o GitHub, baixar o instalador conferido e instalar."""
import hashlib
import http.server
import json
import os
import threading

import pytest

from motor import atualizacao as mat
from motor import projeto as mp

CONTEUDO = b"MZ instalador de mentira " * 4000
SHA = hashlib.sha256(CONTEUDO).hexdigest()


class _GitHub(http.server.BaseHTTPRequestHandler):
    versao = "9.1.0"
    digest = "sha256:" + SHA
    corpo_arquivo = CONTEUDO
    publicada = True

    def log_message(self, *a):
        pass

    def do_GET(self):
        porta = self.server.server_port
        if not self.publicada:
            self.send_response(404)
            self.end_headers()
            return
        if self.path == "/latest":
            nome = f"SIAPP-{self.versao}-instalador.exe"
            corpo = json.dumps({
                "tag_name": "v" + self.versao, "published_at": "2026-12-01T10:00:00Z",
                "html_url": f"https://github.com/SIAPP-Pocos/SIAPP/releases/tag/v{self.versao}",
                "body": "### Adicionado\n- **Coisa nova** na `aba`.\n  continua aqui.\n\n---\n**Instalar:** baixe…",
                "assets": [{"name": f"SIAPP-{self.versao}-codigo-fonte.zip", "size": 1, "browser_download_url": "x"},
                           {"name": nome, "size": len(CONTEUDO), "digest": self.digest,
                            "browser_download_url": f"http://127.0.0.1:{porta}/inst"}]}).encode()
        else:
            corpo = self.corpo_arquivo
        self.send_response(200)
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)


@pytest.fixture
def github():
    srv = http.server.HTTPServer(("127.0.0.1", 0), _GitHub)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_port}/latest"
    srv.shutdown()
    _GitHub.versao, _GitHub.digest, _GitHub.corpo_arquivo, _GitHub.publicada = "9.1.0", "sha256:" + SHA, CONTEUDO, True


def test_comparar_versoes():
    assert mat.mais_nova("1.10.0", "1.9.9") and mat.mais_nova("v2.0.0", "1.99.99")
    assert not mat.mais_nova("1.3.0", "1.3.0") and not mat.mais_nova("1.2.9", "1.3.0")
    assert mat.versao_tupla("lixo") == (0, 0, 0) and mat.versao_tupla("1.4") == (1, 4, 0)


def test_consultar_acha_o_instalador_e_limpa_as_notas(github):
    info = mat.consultar("1.3.0", github)
    assert info["nova"] and info["versao"] == "9.1.0" and info["atual"] == "1.3.0"
    assert info["instalador"] == {"nome": "SIAPP-9.1.0-instalador.exe", "url": github.replace("latest", "inst"),
                                  "bytes": len(CONTEUDO), "sha256": SHA}
    assert info["notas"].startswith("### Adicionado") and "Instalar" not in info["notas"]
    assert mat.consultar("9.1.0", github)["nova"] is False
    _GitHub.publicada = False
    assert mat.consultar("1.3.0", github) is None


def test_baixar_confere_o_sha256(github, tmp_path):
    info = mat.consultar("1.3.0", github)
    vistos = []
    caminho = mat.baixar(info, str(tmp_path), lambda feito, total: vistos.append((feito, total)))
    assert open(caminho, "rb").read() == CONTEUDO and vistos[-1] == (len(CONTEUDO), len(CONTEUDO))
    assert mat.baixar(info, str(tmp_path)) == caminho                   # já baixado e conferido: reaproveita
    # arquivo adulterado no caminho: recusa e não deixa nada para trás
    os.remove(caminho)
    _GitHub.corpo_arquivo = CONTEUDO[:-1] + b"!"
    with pytest.raises(mat.ErroAtualizacao, match="não confere"):
        mat.baixar(info, str(tmp_path))
    assert os.listdir(tmp_path) == []
    assert mat.comando_instalar("C:/x/i.exe")[1:] == list(mat.PARAMETROS_INSTALADOR)


def test_sem_instalador_anexado():
    with pytest.raises(mat.ErroAtualizacao, match="ainda não tem o instalador"):
        mat.baixar({"versao": "9.0.0", "instalador": None}, "/tmp/nada")


# ------------------------------------------------------------------ ponte
def _info(versao="9.1.0", **inst):
    return {"versao": versao, "atual": mp.VERSAO_SIAPP, "nova": mat.mais_nova(versao, mp.VERSAO_SIAPP),
            "publicada_em": "2026-12-01T10:00:00Z", "notas": "- nova", "pagina": "https://github.com/x",
            "instalador": {"nome": f"SIAPP-{versao}-instalador.exe", "url": "u", "bytes": 10, "sha256": "", **inst}}


def test_ponte_procura_uma_vez_por_dia_e_respeita_pular_e_desligar(api, monkeypatch):
    chamadas = []
    monkeypatch.setattr(mat, "consultar", lambda atual, *a, **k: chamadas.append(atual) or _info())
    r = api.verificar_versao()
    assert r["ok"] and r["nova"] and r["versao"] == "9.1.0" and r["atual"] == mp.VERSAO_SIAPP
    assert r["pode_instalar"] is False and r["instalado"] is False          # rodando do código: só avisa
    assert api.verificar_versao()["nova"] and len(chamadas) == 1             # no mesmo dia, não consulta de novo
    assert api.verificar_versao(True)["ok"] and len(chamadas) == 2
    assert api.pular_versao("9.1.0")["ok"] and api.verificar_versao()["pulada"] is True
    assert api.salvar_preferencias({"avisar_versao_nova": False})["ok"]
    assert api.verificar_versao() == {"ok": True, "desligado": True}
    assert api.verificar_versao(True)["nova"]                                # o menu Ajuda procura mesmo desligado
    assert not api.baixar_versao()["ok"]                                     # rodando do código, não instala


def test_ponte_baixa_instala_e_fecha(api, monkeypatch, tmp_path):
    from ponte import atualizacao as pa
    from ponte import base
    monkeypatch.setattr(base, "INSTALADO", True)
    monkeypatch.setattr(pa.sys, "platform", "win32")
    monkeypatch.setattr(mat, "consultar", lambda *a, **k: _info())
    instalador = tmp_path / "SIAPP-9.1.0-instalador.exe"

    def baixar(info, pasta, progresso):
        progresso(5, 10)
        progresso(10, 10)
        instalador.write_bytes(b"x" * 10)
        return str(instalador)
    monkeypatch.setattr(mat, "baixar", baixar)
    abertos, timers = [], []
    monkeypatch.setattr(pa.subprocess, "Popen", lambda cmd, **k: abertos.append(cmd))
    monkeypatch.setattr(pa.threading, "Timer", lambda s, f: timers.append(f) or type("T", (), {"start": lambda self: None})())
    assert not api.instalar_versao()["ok"]                                    # sem baixar antes, não instala
    assert api.verificar_versao(True)["pode_instalar"] is True
    assert api.trabalho_em_andamento() == {"ok": True, "downloads": False, "leitura": False}
    assert api.baixar_versao() == {"ok": True, "pronto": True, "versao": "9.1.0"}
    assert api.instalar_versao() == {"ok": True, "fechando": True}
    assert abertos == [[str(instalador), *mat.PARAMETROS_INSTALADOR]] and len(timers) == 1
    assert api._estado_versao()["instalando"] == {"de": mp.VERSAO_SIAPP, "para": "9.1.0"}


def test_aviso_depois_que_o_instalador_trocou_a_versao(api):
    assert api.aviso_atualizacao() == {"ok": True, "aviso": None}            # primeira vez: só guarda a versão
    api._guardar_estado_versao(ultima_aberta="1.2.0", instalando={"de": "1.2.0", "para": mp.VERSAO_SIAPP})
    assert api.aviso_atualizacao()["aviso"] == {"de": "1.2.0", "para": mp.VERSAO_SIAPP}
    assert api.aviso_atualizacao()["aviso"] is None                          # uma vez só
    assert "instalando" not in api._estado_versao()


def test_canal_de_teste_ve_a_pre_release_mais_nova(monkeypatch):
    """1.4.1: com "Receber versões de teste", vale a de número maior entre as normais e as de teste."""
    lista = [{"tag_name": "v1.4.0", "prerelease": False, "assets": [], "body": "normal"},
             {"tag_name": "v1.4.2", "prerelease": True, "assets": [], "body": "teste"},
             {"tag_name": "v9.9.9", "draft": True, "assets": []}]

    class R:
        status_code = 200

        def __init__(self, dados):
            self.dados = dados

        def json(self):
            return self.dados
    pedidos = []
    monkeypatch.setattr(mat.requests, "get", lambda url, **k: pedidos.append(url) or R(lista))
    info = mat.consultar("1.4.0", teste=True)
    assert info["versao"] == "1.4.2" and info["de_teste"] is True and info["nova"] is True
    assert pedidos == [mat.URL_VERSOES]
    monkeypatch.setattr(mat.requests, "get", lambda url, **k: pedidos.append(url) or R(lista[0]))
    info = mat.consultar("1.4.0")
    assert info["nova"] is False and info["de_teste"] is False and pedidos[-1] == mat.URL_ULTIMA


def test_ponte_respeita_o_canal_de_teste(api, monkeypatch):
    canais = []
    monkeypatch.setattr(mat, "consultar", lambda atual, *a, teste=False, **k: canais.append(teste) or _info())
    api.verificar_versao()
    assert canais == [False]
    assert api.salvar_preferencias({"versoes_de_teste": True})["ok"]
    api.verificar_versao()                                     # mudou o canal: consulta de novo no mesmo dia
    assert canais == [False, True]
