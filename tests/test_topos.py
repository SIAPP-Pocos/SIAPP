"""Topos de várias fontes (0.45): candidatos, diferenças, escolha do usuário e uso na seção."""
import os

import pytest

import rfp_util as u
from motor import agp as magp
from motor import banco as mb
from motor import dados_poco as mdp
from motor import secao as msc
from motor import topos as mtp

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOMES = magp.ler_estratigrafia(os.path.join(RAIZ, "recursos", "estratigrafia.json"))
POCO = "1-SIAPP-1-RN"


def test_nome_nivel_e_chave():
    assert mtp.nome_e_nivel("FM. AÇU") == ("ACU", "F") and mtp.nome_e_nivel("Membro Mossoró") == ("MOSSORO", "M")
    assert mtp.nome_e_nivel("Agua Grande") == ("AGUA GRANDE", "")
    sig = mtp.mapa_siglas(NOMES)
    assert mtp.chave_de("FM AÇU", sig)[0] == "ACU" and mtp.chave_de("Formação Jandaíra", sig) == ("JANDAI", "F")
    assert mtp.chave_de("Fm Sergi", sig)[0] == mtp.chave_de("SERGI", sig)[0]


def _banco(tmp_path, com_agp=True):
    pasta = tmp_path / "proj"
    rel = f"bruto/Potiguar/{POCO}/Pasta de Poco/{POCO}_CDPE_7_RFP.pdf"
    (pasta / rel).parent.mkdir(parents=True)
    u.gerar(str(pasta / rel), u.RFP)                    # Barreiras 0, Jandaíra 162, Açu 801,5, Pendência 1.402
    b = mb.Banco(str(pasta / "projeto.sqlite"))
    b.registrar_arquivo(rel, bacia="Potiguar", poco_id=POCO, tipo="documento")
    mdp.ler_pendentes(b, str(pasta))
    with b.conexao() as c:
        c.execute("INSERT INTO pocos (id, bacia, lat, lon, mesa_rotativa) VALUES (?, 'Potiguar', -5.5, -37.26, 112.2)",
                  (POCO,))
        if com_agp:
            c.execute("INSERT INTO agp (bacia, caminho, poco_id, dados, tamanho) VALUES ('Potiguar', 'a.txt', ?, '{}', 1)",
                      (POCO,))
            c.execute("""INSERT INTO agp_unidades (bacia, caminho, poco_id, ordem, tip, nivel, sigla, codigo, nome, topo,
                         cota_topo, base, fonte) VALUES ('Potiguar', 'a.txt', ?, 1, 'L', 'F', 'ACU', '312010', 'Açu',
                         795, -682.8, 1400, 'AGP')""", (POCO,))
    b.salvar_fato({"poco_id": POCO, "tipo": "topo_formacao", "nome": "Formação Açu", "prof_topo": 812.0, "autor": "Ruan"})
    return b


def test_comparar_mostra_fontes_e_diferenca(tmp_path):
    b = _banco(tmp_path)
    c = mtp.comparar(b, POCO, NOMES)
    acu = next(x for x in c["unidades"] if x["chave"] == "ACU")
    assert {f: v["topo"] for f, v in acu["fontes"].items()} == {"agp": 795.0, "transcrito": 812.0, "rfp": 801.5}
    assert acu["diferenca_m"] == 17.0 and acu["usada"] == "agp" and acu["por"] == "precedência"
    assert c["divergentes"] == 1 and c["precedencia"] == ["agp", "transcrito", "rfp", "calha"]
    jand = next(x for x in c["unidades"] if x["chave"] == "JANDAI")
    assert jand["usada"] == "rfp" and jand["nome"] == "Jandaíra"           # só o RFP tem: vale ele


def test_escolher_e_precedencia(tmp_path):
    b = _banco(tmp_path)
    mtp.escolher(b, POCO, "ACU", "rfp", autor="Ruan")
    lito = {x["sigla"]: x for x in mtp.efetivas(b, POCO, NOMES)[0]}
    assert lito["ACU"]["topo"] == 801.5 and lito["ACU"]["fonte"] == "RFP" and lito["ACU"]["cota_topo"] == -689.3
    mtp.escolher(b, POCO, "ACU", "nenhuma")
    assert "ACU" not in {x["sigla"] for x in mtp.efetivas(b, POCO, NOMES)[0]}
    mtp.escolher(b, POCO, "ACU", "padrao")
    assert next(x for x in mtp.efetivas(b, POCO, NOMES)[0] if x["sigla"] == "ACU")["fonte"] == "AGP"
    assert mtp.definir_precedencia(b, ["transcrito", "x", "agp"]) == ["transcrito", "agp", "rfp", "calha"]
    assert next(x for x in mtp.efetivas(b, POCO, NOMES)[0] if x["sigla"] == "ACU")["topo"] == 812.0
    with pytest.raises(ValueError):
        mtp.escolher(b, POCO, "ACU", "chute")


def test_poco_sem_agp_entra_na_secao(tmp_path):
    b = _banco(tmp_path, com_agp=False)
    assert POCO in mtp.pocos_com_topos(b)
    assert [p["id"] for p in msc.pocos_com_topos(b)] == [POCO]
    d = msc.dados_poco(b, POCO, NOMES)
    assert [x["sigla"] for x in d["lito"]][1:3] == ["JANDAI", "ACU"]       # na ordem da profundidade
    col = msc.coluna_poco(d, msc.NIVEIS_SECAO["formacoes"])
    acu = next(x for x in col["unidades"] if x["chave"] == "ACU")
    assert acu["topo"] == 812.0 and acu["fonte"] == "Transcrito" and col["mesa"] == 112.2   # transcrito antes do RFP
    jand = next(x for x in col["unidades"] if x["chave"] == "JANDAI")
    assert jand["fonte"] == "RFP" and jand["cota_topo"] == -49.8


def test_ponte(api, tmp_path):
    api.escolher_pasta()
    pasta = os.path.join(api._projeto.pasta, "bruto", "Potiguar", POCO, "Pasta de Poco")
    os.makedirs(pasta)
    u.gerar(os.path.join(pasta, f"{POCO}_CDPE_7_RFP.pdf"), u.RFP)
    api._abrir_projeto(api._projeto.pasta)
    api._banco.salvar_fato({"poco_id": POCO, "tipo": "topo_formacao", "nome": "Açu", "prof_topo": 790.0})
    f = api.ficha_poco(POCO)
    acu = next(x for x in f["topos"]["unidades"] if x["chave"] == "ACU")
    assert acu["usada"] == "transcrito"                                   # sem AGP: transcrito antes do RFP
    r = api.topos_escolher(POCO, "ACU", "rfp")
    assert r["ok"] and next(x for x in r["unidades"] if x["chave"] == "ACU")["usada"] == "rfp"
    assert "desconhecida" in api.topos_escolher(POCO, "ACU", "chute")["erro"]
    p = api.topos_precedencia(["rfp"])
    assert p["ordem"][0] == "rfp" and api.topos_precedencia()["ordem"][0] == "rfp"
