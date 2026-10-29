"""Dados do poço lidos de documentos (0.37): leituras, itens, apelidos e a ponte."""
import os

import pytest

import rfp_util as u
from motor import banco as mb
from motor import dados_poco as mdp
from motor import pocos as mpo
from motor import rfp

POCO = "1-SIAPP-1-RN"
PASTA = f"bruto/Potiguar/{POCO}/Pasta de Poco"


def _projeto(tmp_path, docs=("RFP", "RFCP", "Perfuracao")):
    pasta = tmp_path / "proj"
    (pasta / PASTA).mkdir(parents=True)
    b = mb.Banco(str(pasta / "projeto.sqlite"))
    for k, nome in enumerate(docs, 1):
        rel = f"{PASTA}/{POCO}_CDPE_{k}_{nome}.pdf"
        u.gerar(str(pasta / rel), getattr(u, nome.upper()))
        b.registrar_arquivo(rel, bacia="Potiguar", poco_id=POCO, tipo="documento", sha256=f"h{k}")
    b.registrar_arquivo(f"{PASTA}/outro.pdf", bacia="Potiguar", poco_id=POCO, tipo="documento")
    return str(pasta), b


def test_pendentes_ler_e_versao_do_leitor(tmp_path, monkeypatch):
    pasta, b = _projeto(tmp_path)
    assert [a["rel"].rsplit("_", 1)[1] for a in mdp.pendentes(b)] == ["RFP.pdf", "RFCP.pdf", "Perfuracao.pdf"]
    lidos = mdp.ler_pendentes(b, pasta)
    assert {r["documento"] for r in lidos} == {"rfp", "rfcp", "perfuracao"} and all(r["confere"] == 1 for r in lidos)
    assert mdp.pendentes(b) == []
    monkeypatch.setattr(rfp, "VERSAO", rfp.VERSAO + 1)           # leitor melhor: relê tudo
    assert len(mdp.pendentes(b)) == 3
    monkeypatch.setattr(rfp, "VERSAO", rfp.VERSAO - 1)
    b.registrar_arquivo(f"{PASTA}/{POCO}_CDPE_1_RFP.pdf", bacia="Potiguar", poco_id=POCO, tipo="documento",
                        sha256="outro")                          # o arquivo mudou
    assert [a["sha256"] for a in mdp.pendentes(b)] == ["outro"]


def test_itens_por_tipo_gerais_e_apelidos(tmp_path):
    pasta, b = _projeto(tmp_path)
    mdp.ler_pendentes(b, pasta)
    dp = mdp.do_poco(b, POCO)
    assert len(dp["leituras"]) == 3
    it = dp["itens"]
    assert [t["prof_topo"] for t in it["topo"]] == [0.0, 162.0, 801.5, 1402.0]
    assert it["canhoneado"][0]["prof_topo"] == 1396.0 and it["canhoneado"][0]["documento"] == "rfcp"
    assert [t["valor"] for t in it["temperatura"]] == [80.0, 158.0]
    g = mdp.gerais(b, POCO)
    assert g["prof_sondador"] == 1850.0 and g["termino_completacao"] == "10/04/2010"   # RFP + RFCP juntos
    assert g["cadastro"] == "99999999999" and g["mesa_rotativa"] == 112.2
    # a sigla antiga do RFCP e o nome na operadora viram apelidos
    assert mpo.resolver(b, "1-ABC-1-RN") == POCO and mpo.resolver(b, "1ABC1RN") == POCO
    r = mdp.resumo(b)
    assert r["documentos"] == {"rfp": 1, "rfcp": 1, "perfuracao": 1} and r["pocos"] == 1 and r["itens"]["topo"] == 4


def test_ler_de_novo_substitui_e_erro_fica_registrado(tmp_path):
    pasta, b = _projeto(tmp_path, docs=("RFP",))
    rel = f"{PASTA}/{POCO}_CDPE_1_RFP.pdf"
    mdp.ler_arquivo(b, pasta, rel, poco_id=POCO)
    n = b.contar("dados_poco")
    mdp.ler_arquivo(b, pasta, rel, poco_id=POCO)
    assert b.contar("dados_poco") == n                            # não duplica
    with open(os.path.join(pasta, rel), "wb") as f:
        f.write(b"corrompido")
    r = mdp.ler_arquivo(b, pasta, rel, poco_id=POCO)
    assert r["erro"] and r["n"] == 0 and b.contar("dados_poco") == 0
    assert mdp.ler_arquivo(b, pasta, f"{PASTA}/outro.pdf", poco_id=POCO) is None   # nenhum leitor


def test_formulario_de_outro_poco_nao_entra(tmp_path):
    pasta, b = _projeto(tmp_path, docs=("RFCP",))
    rel = f"{PASTA}/{POCO}_CDPE_1_RFCP.pdf"
    r = mdp.ler_arquivo(b, pasta, rel, poco_id="7-OUTRO-1-RN")
    assert r["confere"] == 0
    assert mdp.itens_do_poco(b, "7-OUTRO-1-RN", "canhoneado") == []     # dado de outro poço: fora
    assert mpo.resolver(b, "1-ABC-1-RN") == mpo.chave("1-ABC-1-RN")     # e nenhum apelido criado


def test_apelido_nao_sequestra_poco_do_cadastro(tmp_path):
    pasta, b = _projeto(tmp_path, docs=("RFCP",))
    with b.conexao() as c:
        c.execute("INSERT INTO pocos (id, bacia) VALUES ('1-ABC-1-RN', 'Potiguar')")
    mdp.ler_pendentes(b, pasta)
    assert mpo.resolver(b, "1-ABC-1-RN") == "1-ABC-1-RN"


# ------------------------------------------------------------------ ponte
@pytest.fixture
def api_com_formularios(api):
    api.escolher_pasta()
    pasta = os.path.join(api._projeto.pasta, *PASTA.split("/"))
    os.makedirs(pasta)
    for k, nome in enumerate(("RFP", "RFCP", "Perfuracao"), 1):
        u.gerar(os.path.join(pasta, f"{POCO}_CDPE_{k}_{nome}.pdf"), getattr(u, nome.upper()))
    return api


def test_abertura_le_os_formularios_e_ficha_mostra(api_com_formularios):
    api = api_com_formularios
    api._abrir_projeto(api._projeto.pasta)          # reabrir: os arquivos novos entram e são lidos
    f = api.ficha_poco(POCO)
    assert f["ok"]
    dp = f["dados_poco"]
    assert {d["documento"] for d in dp["documentos"]} == {"rfp", "rfcp", "perfuracao"}
    assert next(d for d in dp["documentos"] if d["documento"] == "rfp")["titulo"] == "Relatório Final de Poço"
    assert dp["gerais"]["prof_sondador"] == 1850.0 and len(dp["itens"]["topo"]) == 4
    assert "1-ABC-1-RN" in f["apelidos"]
    r = api.reler_dados_poco(POCO)
    assert r["ok"] and r["lidos"] == 3 and r["erros"] == [] and r["dados_poco"]["itens"]["fase"]


def test_download_le_na_hora(api):
    api.escolher_pasta()
    destino = api._projeto.destino_bruto("Potiguar", POCO, "Pasta de Poco", f"{POCO}_CDPE_8_RFCP_1.pdf")
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    u.gerar(destino, u.RFCP)
    api._ao_terminar_download({"arquivo_local": destino, "bacia": "Potiguar", "poco": POCO, "caminho": "/x"})
    assert [i["prof_topo"] for i in mdp.itens_do_poco(api._banco, POCO, "canhoneado")] == [1396.0]


def test_intervalos_e_temperaturas_na_avaliacao(api_com_formularios):
    api = api_com_formularios
    api._abrir_projeto(api._projeto.pasta)
    ints = api._intervalos_formularios(POCO)
    nomes = {i["id"]: i["nome"] for i in ints}
    assert nomes == {"rfp:analise_perfil:1392-1406.5": "Análise de perfis · ARENITO · FM AÇU",
                     "rfp:canhoneado:1396-1401": "Canhoneado · FM. AÇU",
                     "rfp:teste_formacao:1395-1400": "Teste TFR · ÓLEO"}
    assert {i["origem"] for i in ints} == {"RFP", "RFCP"}
    fp = api._formularios_perfil(POCO)
    assert [t["nome"] for t in fp["topos"]][:2] == ["FM BARREIRAS", "FM JANDAÍRA"] and fp["topos"][0]["com_nome"]
    assert fp["canhoneados"] == [{"nome": "FM. AÇU", "topo": 1396.0, "base": 1401.0}]


def test_mesmo_dado_em_dois_formularios_aparece_uma_vez(tmp_path):
    pasta, b = _projeto(tmp_path, docs=("RFP",))
    rel = f"{PASTA}/{POCO}_CDPE_3_ND_1.pdf"
    u.gerar(os.path.join(pasta, rel), u.ND)
    b.registrar_arquivo(rel, bacia="Potiguar", poco_id=POCO, tipo="documento")
    mdp.ler_pendentes(b, pasta)
    ap = mdp.itens_do_poco(b, POCO, "analise_perfil")
    assert len(ap) == 1 and ap[0]["documento"] == "rfp" and ap[0]["tambem_em"] == ["nd"]
    ind = {i["prof_topo"]: i for i in mdp.itens_do_poco(b, POCO, "indicio")}
    assert ind[812.0]["documento"] == "rfp" and ind[1450.0]["documento"] == "nd"   # só no ND: entra
    pts = [t for t in mdp.itens_do_poco(b, POCO, "teste_formacao") if t["prof_topo"] == 1420.0]
    assert len(pts) == 1 and pts[0]["documento"] == "rfp"
    docs = [le["documento"] for le in mdp.do_poco(b, POCO)["leituras"]]
    assert docs == ["rfp", "nd"]                                  # em ordem de prioridade
    assert mdp.gerais(b, POCO)["prof_sondador"] == 1850.0
