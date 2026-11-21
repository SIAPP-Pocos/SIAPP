"""Contribuições: exportar, importar (com prévia e conflitos), desfazer e base."""
import functools
import http.server
import json
import os
import threading

import pytest

from base_util import montar_base
from motor import banco as mb
from motor import comunidade as mc

AUTOR = {"nome": "Ruan da Silva Nobre", "instituicao": "UFAL", "orcid": ""}


@pytest.fixture
def banco(tmp_path):
    return mb.Banco(str(tmp_path / "a.sqlite"))


def fazer_trabalho(b):
    b.vocab_definir("correcao", "BARIGIRAS", "BARREIRAS", autor="Ruan")
    b.vocab_definir("palavra", "Açu")
    b.vocab_definir("ignorar", "AMOSTRAS")
    b.registrar_arquivo("bruto/Potiguar/7-GMR-13-RN/Pasta de Poco/x.pdf", bacia="Potiguar",
                        poco_id="7-GMR-13-RN", caminho_remoto="/POCO/C7/7-GMR-13-RN/Pasta de Poco/x.pdf",
                        sha256="ab" * 32, tipo="documento")
    return b.salvar_fato({"poco_id": "7-GMR-13-RN", "tipo": "topo_formacao", "nome": "Açu",
                          "prof_topo": 512.5, "fonte_rel": "bruto/Potiguar/7-GMR-13-RN/Pasta de Poco/x.pdf",
                          "pagina": 3, "caixa": [0.1, 0.2, 0.4, 0.25]})


def test_exportar_exige_autor(banco):
    fazer_trabalho(banco)
    with pytest.raises(mc.ErroComunidade, match="nome"):
        mc.montar_pacote(banco, {}, "0.7.0")


def test_pacote_valido_cita_fonte_sem_arquivo(banco, tmp_path):
    fazer_trabalho(banco)
    p = mc.montar_pacote(banco, AUTOR, "0.7.0")
    assert mc.validar_pacote(p) == []
    f = p["fatos"][0]
    assert f["poco"] == "7-GMR-13-RN" and f["fonte"]["sha256"] == "ab" * 32
    assert f["fonte"]["caminho_remoto"].endswith("x.pdf") and f["fonte"]["pagina"] == 3
    assert p["vocabulario"] == {"palavras": ["Açu"], "correcoes": [{"de": "BARIGIRAS", "para": "BARREIRAS"}],
                                "manter_original": ["AMOSTRAS"]}
    caminho = mc.gravar_pacote(banco, p, str(tmp_path / "contrib"))
    assert os.path.basename(caminho).endswith("_nobre_siapp.json")
    # segunda exportação "só novidades": nada novo
    assert mc.pacote_vazio(mc.montar_pacote(banco, AUTOR, "0.7.0"))
    assert not mc.pacote_vazio(mc.montar_pacote(banco, AUTOR, "0.7.0", apenas_novos=False))


def test_validador_recusa_numero_e_profundidade_absurda():
    p = {"formato": mc.FORMATO, "versao_formato": 2, "id": "x" * 36, "autor": {"nome": "A"},
         "licenca": mc.LICENCA, "vocabulario": {"correcoes": [{"de": "87", "para": "83"}]},
         "fatos": [{"id": "f", "poco": "P", "tipo": "topo_formacao", "prof_topo": 50000}]}
    erros = mc.validar_pacote(p)
    assert any("87" in e for e in erros) and any("prof_topo" in e for e in erros)


def test_importar_previa_conflito_e_desfazer(banco, tmp_path):
    fazer_trabalho(banco)
    p = mc.montar_pacote(banco, AUTOR, "0.7.0")
    outro = mb.Banco(str(tmp_path / "b.sqlite"))
    outro.vocab_definir("correcao", "BARIGIRAS", "BARREIRA")          # discorda
    pv = mc.previa(outro, p)
    assert pv["conflitos"] == [{"de": "BARIGIRAS", "atual": "BARREIRA", "origem_atual": "local",
                                "proposta": "BARREIRAS"}]
    r = mc.importar(outro, p, "x.json")
    assert r["fatos_novos"] == 1
    ef = outro.vocab_efetivo()
    assert ef["correcoes"]["BARIGIRAS"] == "BARREIRA"                    # o local continua valendo
    f = outro.fatos("7-GMR-13-RN")[0]
    assert f["origem"] == "pacote" and f["caixa"] == [0.1, 0.2, 0.4, 0.25] and f["autor"] == AUTOR["nome"]
    assert mc.previa(outro, p)["ja_importado"]
    assert mc.importar(outro, p)["fatos_novos"] == 0                     # reimportar não duplica
    outro.desfazer_pacote(p["id"])
    assert outro.fatos() == [] and "Açu" not in outro.vocab_efetivo()["palavras"]


def test_aplicar_base_substitui_a_anterior(banco, tmp_path):
    fazer_trabalho(banco)
    p = mc.montar_pacote(banco, AUTOR, "0.7.0")
    alvo = mb.Banco(str(tmp_path / "c.sqlite"))
    montar_base(str(tmp_path / "base1.sqlite"), [p], "v2026.10.0")
    r = mc.aplicar_base(alvo, str(tmp_path / "base1.sqlite"))
    assert r == {"versao": "v2026.10.0", "contribuicoes": 1, "vocabulario": 3, "fatos": 1, "apelidos": 0,
                 "interpretacoes": 0}
    assert alvo.vocab_efetivo()["origens"] == {"BARIGIRAS": "base"}
    assert alvo.fatos()[0]["caixa"] == [0.1, 0.2, 0.4, 0.25]
    montar_base(str(tmp_path / "base2.sqlite"), [], "v2026.11.0")         # base nova, vazia
    mc.aplicar_base(alvo, str(tmp_path / "base2.sqlite"))
    assert alvo.fatos() == [] and alvo.vocab_efetivo()["correcoes"] == {}
    assert [x["id"] for x in alvo.pacotes("base")] == ["base:v2026.11.0"]


def test_base_invalida(banco, tmp_path):
    f = tmp_path / "x.sqlite"
    f.write_bytes(b"isto nao e sqlite" * 100)
    with pytest.raises(mc.ErroComunidade):
        mc.aplicar_base(banco, str(f))


class _GitHubFalso(http.server.BaseHTTPRequestHandler):
    base_bytes = b""
    publicada = True

    def log_message(self, *a):
        pass

    def do_GET(self):
        porta = self.server.server_port
        if self.path == "/latest":
            if not self.publicada:
                self.send_response(404)
                self.end_headers()
                return
            corpo = json.dumps({"tag_name": "v2026.10.0", "published_at": "2026-10-16T10:00:00Z",
                                "assets": [{"name": "siapp-dados.sqlite",
                                            "browser_download_url": f"http://127.0.0.1:{porta}/b"}]})
            self.send_response(200)
            self.end_headers()
            self.wfile.write(corpo.encode())
        elif self.path == "/b":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(self.base_bytes)


def test_baixar_base_do_github(tmp_path, banco):
    fazer_trabalho(banco)
    montar_base(str(tmp_path / "pub.sqlite"), [mc.montar_pacote(banco, AUTOR, "0.7.0")])
    _GitHubFalso.base_bytes = (tmp_path / "pub.sqlite").read_bytes()
    srv = http.server.HTTPServer(("127.0.0.1", 0), _GitHubFalso)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_port}/latest"
    try:
        info = mc.baixar_base(str(tmp_path / "baixada.sqlite"), url=url)
        assert info["versao"] == "v2026.10.0"
        assert mc.aplicar_base(mb.Banco(str(tmp_path / "d.sqlite")), str(tmp_path / "baixada.sqlite"))["fatos"] == 1
        _GitHubFalso.publicada = False
        with pytest.raises(mc.ErroComunidade, match="ainda não foi publicada"):
            mc.baixar_base(str(tmp_path / "x.sqlite"), url=url)
    finally:
        _GitHubFalso.publicada = True
        srv.shutdown()


def test_ponte_exportar_importar(api, tmp_path):
    api.escolher_pasta()
    assert "nome" in api.exportar_contribuicao()["erro"]
    assert not api.definir_autor("Ru")["ok"]
    assert not api.definir_autor("Ruan Nobre", orcid="123")["ok"]
    assert api.definir_autor("Ruan da Silva Nobre", "UFAL", "0000-0002-1825-0097")["ok"]
    assert api.corrigir_palavra("BARIGIRAS", "BARREIRAS")["ok"]
    r = api.exportar_contribuicao()
    assert r["ok"] and r["arquivo"].startswith("contribuicoes/") and r["itens"]["correcoes"] == 1
    assert "Nada novo" in api.exportar_contribuicao()["erro"]
    # outra pessoa importa o pacote
    arquivo = os.path.join(api._projeto.pasta, r["arquivo"])
    api.remover_correcao("BARIGIRAS")
    api._janela.arquivo = (arquivo,)
    pv = api.escolher_contribuicao()
    assert pv["ok"] and pv["previa"]["itens"]["correcoes"] == 1
    assert api.confirmar_importacao("outro-id")["ok"] is False
    assert api.confirmar_importacao(pv["previa"]["id"])["ok"]
    assert api.dicionario()["correcoes_comunidade"] == [{"de": "BARIGIRAS", "para": "BARREIRAS",
                                                         "origem": "pacote"}]
    c = api.comunidade()
    assert c["autor"]["instituicao"] == "UFAL" and len(c["importados"]) == 1
    assert api.desfazer_pacote(pv["previa"]["id"])["ok"]
    assert api.dicionario()["correcoes_comunidade"] == []


# ------------------------------------------------------------------ 1.3: ligar à página, novidades da base
def _pacote_e_outro_projeto(banco, tmp_path, *, mesmo_sha=True):
    fazer_trabalho(banco)
    p = mc.montar_pacote(banco, AUTOR, "1.3.0")
    outro = mb.Banco(str(tmp_path / "outro.sqlite"))
    montar_base(str(tmp_path / "b.sqlite"), [p], "v2026.11.0")
    mc.aplicar_base(outro, str(tmp_path / "b.sqlite"))
    return p, outro


def test_fato_da_comunidade_aparece_na_pagina_do_mesmo_documento(banco, tmp_path):
    p, outro = _pacote_e_outro_projeto(banco, tmp_path)
    rel = "bruto/Potiguar/outra pasta/x.pdf"        # o mesmo documento, guardado noutro lugar
    assert outro.fatos(documento=rel, pagina=3) == []
    outro.registrar_arquivo(rel, bacia="Potiguar", poco_id="7-GMR-13-RN", sha256="ab" * 32, tipo="documento")
    f = outro.fatos(documento=rel, pagina=3)
    assert len(f) == 1 and f[0]["origem"] == "base" and f[0]["fonte_rel"] is None
    assert outro.anotar_documentos(outro.fatos())[0]["doc_local"] == rel
    # sem o hash, vale o caminho no portal
    rel2 = "bruto/Potiguar/y/x.pdf"
    outro2 = mb.Banco(str(tmp_path / "outro2.sqlite"))
    mc.aplicar_base(outro2, str(tmp_path / "b.sqlite"))
    outro2.registrar_arquivo(rel2, bacia="Potiguar", poco_id="7-GMR-13-RN",
                             caminho_remoto="/POCO/C7/7-GMR-13-RN/Pasta de Poco/x.pdf", tipo="documento")
    assert len(outro2.fatos(documento=rel2, pagina=3)) == 1
    assert outro2.fatos(documento=rel2, pagina=4) == []
    # o seu continua aparecendo pelo caminho local
    assert len(banco.fatos(documento="bruto/Potiguar/7-GMR-13-RN/Pasta de Poco/x.pdf")) == 1


def test_pocos_com_dados_da_comunidade(banco, tmp_path):
    _, outro = _pacote_e_outro_projeto(banco, tmp_path)
    assert banco.comunidade_por_poco() == {}                  # o que é seu não conta como comunidade
    assert outro.comunidade_por_poco() == {"7-GMR-13-RN": {"fatos": 1, "interpretacoes": 0,
                                                           "autores": ["Ruan da Silva Nobre"]}}
    from motor import pocos as mpo
    with outro.conexao() as c:
        c.execute("INSERT INTO pocos (id, lat, lon) VALUES ('7-GMR-13-RN', -5.1, -36.5), ('1-X-1-RN', -5.2, -36.6)")
    linhas = {d["id"]: d for d in mpo.linhas_mapa(mpo.pocos_mapa(outro))}
    assert linhas["7-GMR-13-RN"]["comunidade"] == 1 and linhas["1-X-1-RN"]["comunidade"] == 0


def test_previa_lista_pocos_e_documentos_que_faltam(banco, tmp_path):
    fazer_trabalho(banco)
    p = mc.montar_pacote(banco, AUTOR, "1.3.0")
    outro = mb.Banco(str(tmp_path / "outro.sqlite"))
    pv = mc.previa(outro, p)
    assert pv["pocos"] == ["7-GMR-13-RN"]
    assert pv["documentos_faltando"] == [{"poco": "7-GMR-13-RN", "bacia": "Potiguar", "nome": "x.pdf",
                                          "caminho_remoto": "/POCO/C7/7-GMR-13-RN/Pasta de Poco/x.pdf"}]
    outro.registrar_arquivo("bruto/a/x.pdf", bacia="Potiguar", poco_id="7-GMR-13-RN", sha256="ab" * 32)
    assert mc.previa(outro, p)["documentos_faltando"] == []


class _GitHubComResumo(http.server.BaseHTTPRequestHandler):
    versao = "v2026.11.1"
    resumo = {}
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
            corpo = {"tag_name": self.versao, "published_at": "2026-11-21T10:00:00Z",
                     "assets": [{"name": "siapp-dados.sqlite", "browser_download_url": f"http://127.0.0.1:{porta}/b"},
                                {"name": "resumo.json", "browser_download_url": f"http://127.0.0.1:{porta}/r"}]}
        else:
            corpo = self.resumo
        self.send_response(200)
        self.end_headers()
        self.wfile.write(json.dumps(corpo).encode())


def test_novidades_da_base(banco, tmp_path):
    p, outro = _pacote_e_outro_projeto(banco, tmp_path)            # outro aplicou a v2026.11.0, com o pacote p
    novo = {"id": "outro-pacote", "autor": "Maria Souza", "instituicao": "UFRN", "criado_em": "2026-11-20",
            "correcoes": 2, "palavras": 0, "fatos": 5, "interpretacoes": 1, "pocos": ["1-X-1-RN"]}
    _GitHubComResumo.resumo = {"formato": "siapp-dados-resumo", "versao_base": "v2026.11.1",
                               "contagens": {"contribuicoes": 2, "fatos": 6, "pocos": 2},
                               "pacotes": [{"id": p["id"], "autor": "Ruan da Silva Nobre", "pocos": ["7-GMR-13-RN"]},
                                           novo]}
    srv = http.server.HTTPServer(("127.0.0.1", 0), _GitHubComResumo)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_port}/latest"
    try:
        info = mc.consultar_base(url)
        assert info["versao"] == "v2026.11.1" and info["resumo"]["contagens"]["pocos"] == 2
        n = mc.novidades(outro, info)
        assert n["ha_novidade"] and n["local"] == "v2026.11.0"
        assert [x["autor"] for x in n["pacotes_novos"]] == ["Maria Souza"]
        assert n["pacotes_novos"][0]["pocos"] == ["1-X-1-RN"]
        # quem nunca aplicou a base vê todos os pacotes como novos
        vazio = mb.Banco(str(tmp_path / "vazio.sqlite"))
        assert len(mc.novidades(vazio, info)["pacotes_novos"]) == 2
        _GitHubComResumo.versao = "v2026.11.0"
        assert mc.novidades(outro, mc.consultar_base(url))["ha_novidade"] is False
        _GitHubComResumo.publicada = False
        assert mc.consultar_base(url) is None
        assert mc.novidades(outro, None) == {"publicada": False, "local": "v2026.11.0", "ha_novidade": False}
    finally:
        _GitHubComResumo.publicada = True
        _GitHubComResumo.versao = "v2026.11.1"
        srv.shutdown()


def test_ponte_verifica_a_base_uma_vez_por_dia(api, monkeypatch):
    api.escolher_pasta()
    chamadas = []

    def falso(url=mc.URL_ULTIMA_BASE, timeout=10):
        chamadas.append(url)
        return {"versao": "v2026.11.0", "publicada_em": "2026-11-21T10:00:00Z", "resumo": None}
    monkeypatch.setattr(mc, "consultar_base", falso)
    r = api.verificar_base()
    assert r["ok"] and r["ha_novidade"] and r["versao"] == "v2026.11.0" and r["local"] is None
    assert api.verificar_base()["ha_novidade"] and len(chamadas) == 1            # no mesmo dia, não consulta de novo
    assert api.verificar_base(True)["ok"] and len(chamadas) == 2                 # "Procurar agora"
    assert api.comunidade()["verificar_sozinho"] is True
    assert api.comunidade_verificar_sozinho(False)["ok"]
    assert api.verificar_base() == {"ok": True, "desligado": True} and len(chamadas) == 2
    assert api.verificar_base(True)["ok"] and len(chamadas) == 3                 # o botão funciona mesmo desligado
