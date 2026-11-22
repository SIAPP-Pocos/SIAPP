"""Enviar a contribuição pelo GitHub (1.4): entrada por código, envio em partes, acompanhamento e o cofre."""
import base64
import gzip
import hashlib
import http.server
import json
import re
import threading
import urllib.parse

import pytest

from motor import envio as me
from motor.cofre import Cofre
from test_comunidade import fazer_trabalho


class _GitHub(http.server.BaseHTTPRequestHandler):
    estado = {}

    def log_message(self, *a):
        pass

    def _responder(self, corpo, codigo=200):
        dados = json.dumps(corpo).encode()
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)

    def do_POST(self):
        e = self.estado
        tam = int(self.headers.get("Content-Length") or 0)
        bruto = self.rfile.read(tam).decode()
        if self.path == "/login/device/code":
            return self._responder({"device_code": "dc", "user_code": "ABCD-1234",
                                    "verification_uri": "https://github.com/login/device", "expires_in": 900,
                                    "interval": 1})
        if self.path == "/login/oauth/access_token":
            d = dict(urllib.parse.parse_qsl(bruto))
            assert d["client_id"] == me.CLIENT_ID
            if d["grant_type"] == "refresh_token":
                e["renovou"] = e.get("renovou", 0) + 1
                return self._responder({"access_token": "tok2", "expires_in": 28800, "refresh_token": "ref2",
                                        "refresh_token_expires_in": 15897600})
            e["perguntas"] = e.get("perguntas", 0) + 1
            if e.get("negar"):
                return self._responder({"error": "access_denied"})
            if e["perguntas"] < 3:
                return self._responder({"error": "authorization_pending" if e["perguntas"] == 1 else "slow_down",
                                        "interval": 1})
            return self._responder({"access_token": "tok1", "expires_in": 28800, "refresh_token": "ref1",
                                    "refresh_token_expires_in": 15897600})
        if self.path == "/repos/SIAPP-Pocos/Comunidade/issues":
            assert self.headers["Authorization"].startswith("Bearer ")
            e["issue"] = json.loads(bruto)
            e["comentarios"] = []
            return self._responder({"number": 5, "html_url": "https://github.com/SIAPP-Pocos/Comunidade/issues/5"},
                                   201)
        if self.path == "/repos/SIAPP-Pocos/Comunidade/issues/5/comments":
            if e.get("falhar_comentario"):
                return self._responder({"message": "erro"}, 500)
            e["comentarios"].append(json.loads(bruto)["body"])
            return self._responder({"id": len(e["comentarios"])}, 201)
        self._responder({"message": "?"}, 404)

    def do_PATCH(self):
        self.estado["fechou"] = True
        self._responder({})

    def do_GET(self):
        e = self.estado
        if self.path == "/user":
            return self._responder({"login": "maria", "name": "Maria Souza", "id": 9})
        if self.path == "/repos/SIAPP-Pocos/Comunidade/issues/5":
            return self._responder({"number": 5, "state": e.get("issue_estado", "open"),
                                    "comments": len(e.get("robo", [])), "html_url": "https://x/issues/5"})
        if self.path.startswith("/repos/SIAPP-Pocos/Comunidade/issues/5/comments"):
            return self._responder([{"user": {"login": "github-actions[bot]", "type": "Bot"}, "body": b}
                                    for b in e.get("robo", [])])
        if self.path == "/repos/SIAPP-Pocos/Comunidade/pulls/9":
            return self._responder({"html_url": "https://x/pull/9", "state": e.get("pr_estado", "open"),
                                    "merged_at": e.get("merged_at")})
        if self.path == "/repos/SIAPP-Pocos/Comunidade/pulls/9/reviews":
            return self._responder(e.get("revisoes", []))
        self._responder({"message": "?"}, 404)


@pytest.fixture
def github(monkeypatch):
    _GitHub.estado = {}
    srv = http.server.HTTPServer(("127.0.0.1", 0), _GitHub)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    raiz = f"http://127.0.0.1:{srv.server_port}"
    monkeypatch.setattr(me, "API", raiz)
    monkeypatch.setattr(me, "URL_CODIGO", raiz + "/login/device/code")
    monkeypatch.setattr(me, "URL_TOKEN", raiz + "/login/oauth/access_token")
    yield _GitHub.estado
    srv.shutdown()


def _sem_espera(monkeypatch):
    monkeypatch.setattr(me.time, "sleep", lambda s: None)


# ------------------------------------------------------------------ motor
def test_entrar_por_codigo(github):
    info = me.iniciar_login()
    assert info["codigo"] == "ABCD-1234" and info["url"] == "https://github.com/login/device"
    dormidas = []
    t = me.aguardar_login(info["device_code"], 1, 900, dormir=dormidas.append)
    assert t["access_token"] == "tok1" and t["refresh_token"] == "ref1" and github["perguntas"] == 3
    assert dormidas == [1, 1, 1]
    assert me.usuario("tok1") == {"login": "maria", "nome": "Maria Souza", "id": 9}
    assert me.renovar("ref1")["access_token"] == "tok2"


def test_entrar_negado_ou_cancelado(github):
    github["negar"] = True
    with pytest.raises(me.ErroEnvio, match="negada"):
        me.aguardar_login("dc", 1, 900, dormir=lambda s: None)
    with pytest.raises(me.ErroEnvio, match="cancelada"):
        me.aguardar_login("dc", 1, 900, cancelado=lambda: True, dormir=lambda s: None)
    relogio = iter([0, 1000])
    with pytest.raises(me.ErroEnvio, match="expirou"):
        me.aguardar_login("dc", 1, 900, dormir=lambda s: None, relogio=lambda: next(relogio))


def test_codificar_no_formato_do_robo(monkeypatch):
    """O contrato com o repositório Comunidade (ferramentas/receber_pacote.py): cabeçalho, partes e SHA-256."""
    monkeypatch.setattr(me, "TAMANHO_PARTE", 50)
    pacote = {"id": "abc-123-def", "autor": {"nome": "Maria Souza", "instituicao": "UFRN"}, "siapp_versao": "1.4.0",
              "fatos": [{"poco": "7-GMR-13-RN", "nome": "Açu"}] * 20}
    sha, partes = me.codificar(pacote)
    assert len(partes) > 3
    titulo, corpo = me.texto_issue(pacote, {"correcoes": 2, "fatos": 20}, ["7-GMR-13-RN"], sha, len(partes))
    assert titulo == "[pacote] Maria Souza: 2 correções, 20 dados transcritos" and "Maria Souza (UFRN)" in corpo
    cab = re.search(r"<!--\s*siapp-pacote\s+id=([0-9A-Za-z-]{8,64})\s+partes=(\d{1,3})\s+sha256=([0-9a-f]{64})\s*-->",
                    corpo)
    assert cab and cab.group(1) == "abc-123-def" and int(cab.group(2)) == len(partes)
    re_parte = re.compile(r"<!--\s*siapp-parte\s+(\d{1,3})/(\d{1,3})\s*-->\s*```[a-z]*\s*([A-Za-z0-9+/=\s]+?)\s*```",
                          re.S)
    juntos = "".join(re_parte.search(me.comentario_parte(i, len(partes), p)).group(3)
                     for i, p in enumerate(partes, 1))
    dados = gzip.decompress(base64.b64decode(juntos))
    assert hashlib.sha256(dados).hexdigest() == sha and json.loads(dados) == pacote


def test_enviar_e_acompanhar(github, monkeypatch):
    monkeypatch.setattr(me, "TAMANHO_PARTE", 40)
    pacote = {"id": "abc-123-def", "autor": {"nome": "Maria"}, "fatos": []}
    vistos = []
    r = me.enviar("tok1", pacote, {"correcoes": 1}, [], progresso=lambda i, n: vistos.append((i, n)))
    assert r["numero"] == 5 and r["partes"] == len(github["comentarios"]) == vistos[-1][1]
    assert github["issue"]["title"].startswith("[pacote] Maria")
    assert me.situacao(5)["estado"] == "conferindo"
    github["robo"] = ["<!-- siapp-erro -->\nO pacote não pôde ser recebido:\n\nO pacote não passou na validação:\n- x\n"
                      "\nNada foi gravado. Corrija no SIAPP e envie de novo."]
    s = me.situacao(5)
    assert s["estado"] == "recusado" and "validação" in s["detalhe"]
    github["robo"] = ["<!-- siapp-pr: 9 -->\nRecebido e conferido."]
    assert me.situacao(5)["estado"] == "revisao"
    github["revisoes"] = [{"state": "CHANGES_REQUESTED"}]
    assert me.situacao(5)["estado"] == "mudanca"
    github["merged_at"], github["pr_estado"] = "2026-11-23T10:00:00Z", "closed"
    assert me.situacao(5) == {"estado": "aceito", "rotulo": "Aceito: entra na próxima base",
                              "url": "https://x/pull/9", "aceito_em": "2026-11-23T10:00:00Z"}
    github["merged_at"] = None
    assert me.situacao(5)["estado"] == "nao_aceito"


def test_envio_pela_metade_fecha_a_issue(github):
    github["falhar_comentario"] = True
    with pytest.raises(me.ErroEnvio, match="parou no meio"):
        me.enviar("tok1", {"id": "abc-123-def", "autor": {"nome": "M"}}, {}, [])
    assert github["fechou"] is True


def test_cofre_guarda_e_apaga(tmp_path):
    c = Cofre(str(tmp_path))
    assert c.ler() is None
    c.gravar({"access_token": "x", "login": "maria"})
    assert c.ler() == {"access_token": "x", "login": "maria"}
    c.apagar()
    assert c.ler() is None


# ------------------------------------------------------------------ ponte
def test_ponte_entrar_enviar_e_acompanhar(api, github, monkeypatch):
    _sem_espera(monkeypatch)
    api.escolher_pasta()
    assert api.github_conta() == {"ok": True, "conectado": False, "login": "", "nome": ""}
    assert not api.enviar_comunidade()["ok"]                                  # sem conta, não envia
    assert api.github_entrar()["codigo"] == "ABCD-1234"
    assert api.github_aguardar() == {"ok": True, "login": "maria", "nome": "Maria Souza"}
    assert api.github_conta()["login"] == "maria"
    assert "Preencha seu nome" in api.previa_envio()["erro"]                  # toda contribuição tem autor
    assert api.definir_autor("Maria Souza", "UFRN")["ok"]
    assert "Nada novo" in api.previa_envio()["erro"]
    fazer_trabalho(api._banco)
    pv = api.previa_envio()
    assert pv["itens"]["fatos"] == 1 and pv["pocos"] == ["7-GMR-13-RN"] and pv["conta"]["login"] == "maria"
    r = api.enviar_comunidade()
    assert r["ok"] and r["numero"] == 5 and r["arquivo"].startswith("contribuicoes")
    assert "Maria Souza (UFRN)" in github["issue"]["body"]
    assert "Nada novo" in api.previa_envio()["erro"]                          # o que foi não vai de novo
    e = api.envios_comunidade()
    assert e["envios"][0]["numero"] == 5 and e["envios"][0]["estado"] == "conferindo" and e["mudou"] == []
    github["robo"] = ["<!-- siapp-pr: 9 -->\nok"]
    assert api.envios_comunidade()["mudou"] == []                             # consultou há pouco: espera
    envios = api._envios()
    envios[0]["verificado_em"] = 0
    api._guardar_envios(envios)
    m = api.envios_comunidade()["mudou"]
    assert m and m[0]["estado"] == "revisao" and m[0]["numero"] == 5
    assert api.github_sair()["ok"] and not api.github_conta()["conectado"]


def test_ponte_renova_o_acesso_vencido(api, github):
    api._cofre_github().gravar({"access_token": "velho", "expira_em": 0, "refresh_token": "ref1",
                                "renovar_ate": 9e12, "login": "maria"})
    assert api._token_github() == "tok2" and github["renovou"] == 1
    assert api._cofre_github().ler()["refresh_token"] == "ref2"
    api._cofre_github().gravar({"access_token": "velho", "expira_em": 0, "refresh_token": "r", "renovar_ate": 0})
    assert api._token_github() is None                                         # venceu de vez: entrar de novo
