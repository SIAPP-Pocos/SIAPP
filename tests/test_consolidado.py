"""Dados consolidados (0.44): fontes de cada tipo de dado no projeto e num poço."""
import json
import os

import rfp_util as u
from motor import banco as mb
from motor import consolidado as mco
from motor import dados_poco as mdp

POCO = "1-SIAPP-1-RN"


def _banco(tmp_path):
    pasta = tmp_path / "proj"
    rel = f"bruto/Potiguar/{POCO}/Pasta de Poco/{POCO}_CDPE_7_RFP.pdf"
    (pasta / rel).parent.mkdir(parents=True)
    u.gerar(str(pasta / rel), u.RFP)
    b = mb.Banco(str(pasta / "projeto.sqlite"))
    b.registrar_arquivo(rel, bacia="Potiguar", poco_id=POCO, tipo="documento")
    mdp.ler_pendentes(b, str(pasta))
    with b.conexao() as c:
        c.execute("INSERT INTO agp_unidades (bacia, caminho, poco_id, tip, sigla, nome, topo, base, fonte) "
                  "VALUES ('Potiguar', 'a.txt', ?, 'L', 'ACU', 'Formação Açu', 800, 1400, 'AGP')", (POCO,))
        c.execute("INSERT INTO agp (bacia, caminho, poco_id, dados) VALUES ('Potiguar', 'a.txt', ?, ?)",
                  (POCO, json.dumps({"corridas": [{"corrida": 1, "rm": 0.5, "rmf": 0.4, "bht": 150,
                                                   "prof_alcancada": 1800}]})))
    b.salvar_fato({"poco_id": POCO, "tipo": "topo_formacao", "nome": "Açu", "prof_topo": 802, "autor": "Ruan"})
    return b


def test_projeto_conta_cada_fonte(tmp_path):
    b = _banco(tmp_path)
    r = mco.projeto(b)
    tm = {t["chave"]: {f["rotulo"]: (f["pocos"], f["registros"]) for f in t["fontes"]} for t in r["temas"]}
    assert tm["topos"]["AGP da ANP"] == (1, 1) and tm["topos"]["RFP (topos constatados)"] == (1, 4)
    assert tm["topos"]["Transcritos (você e a comunidade)"] == (1, 1)
    assert tm["temperatura"]["AGP — corridas de perfilagem (BHT)"] == (1, 1)
    assert tm["temperatura"]["RFP, teste a cabo e TFR"] == (1, 2) and tm["pressao"]["Testes do RFP"] == (1, 3)
    assert tm["tempo"]["Checkshot (SEG-Y da sísmica de poço)"] == (0, 0)
    assert r["leituras"] == [{"leitor": "cdpe", "documento": "rfp", "n": 1, "erros": 0, "de_outro_poco": 0}]
    assert all(t["usos"] for t in r["temas"])
    assert any("só os topos do AGP" in x for x in next(t for t in r["temas"] if t["chave"] == "topos")["usos"])


def test_poco_lado_a_lado(tmp_path):
    b = _banco(tmp_path)
    r = mco.poco(b, POCO)
    topos = next(t for t in r["temas"] if t["chave"] == "topos")
    por = {f["rotulo"]: f["linhas"] for f in topos["fontes"]}
    assert [(x["nome"], x["topo"]) for x in por["AGP da ANP"]] == [("Formação Açu", 800.0)]
    assert [x["topo"] for x in por["RFP (topos constatados)"]] == [0.0, 162.0, 801.5, 1402.0]
    assert por["Transcritos (você e a comunidade)"][0]["detalhe"] == "local · Ruan"
    assert topos["com_dado"] == 3
    lama = next(t for t in r["temas"] if t["chave"] == "lama")
    corr = lama["fontes"][0]["linhas"][0]
    assert corr["nome"] == "corrida 1" and "RMF 0,4" in corr["valor"] and corr["detalhe"] == "BHT 150 °F"
    vazio = mco.poco(b, "7-NADA-1-RN")
    assert all(t["com_dado"] == 0 for t in vazio["temas"])


def test_ponte(api):
    api.escolher_pasta()
    pasta = os.path.join(api._projeto.pasta, "bruto", "Potiguar", POCO, "Pasta de Poco")
    os.makedirs(pasta)
    u.gerar(os.path.join(pasta, f"{POCO}_CDPE_8_RFCP_1.pdf"), u.RFCP)
    api._abrir_projeto(api._projeto.pasta)
    r = api.consolidado_projeto()
    assert r["ok"] and r["leituras"][0]["documento"] == "rfcp"
    p = api.consolidado_poco("1-ABC-1-RN")                       # pelo apelido do RFCP
    assert p["ok"] and p["poco"] == POCO
    inter = next(t for t in p["temas"] if t["chave"] == "intervalos")
    assert next(f for f in inter["fontes"] if f["rotulo"] == "Canhoneados (RFCP)")["n"] == 1
    assert "Informe o poço" in api.consolidado_poco("  ")["erro"]
