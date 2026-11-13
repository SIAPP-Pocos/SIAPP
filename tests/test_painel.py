"""Painel de preenchimento e contribuição (0.35), com um banco montado à mão."""
import pytest

from motor import banco as mb
from motor import painel


@pytest.fixture
def banco(tmp_path):
    b = mb.Banco(str(tmp_path / "p.sqlite"))
    with b.conexao() as c:
        for poco, bacia, n_perfil, sit in (("A", "Potiguar", 2, "digital"), ("B", "Potiguar", 0, "sem_perfil"),
                                           ("C", "Potiguar", 1, "digital"), ("D", "Alagoas", 1, "digital")):
            c.execute("INSERT INTO acervo_pocos (bacia, caminho, poco_id, n_perfil, situacao) VALUES (?, ?, ?, ?, ?)",
                      (bacia, f"/POCO/{poco}", poco, n_perfil, sit))
        c.execute("INSERT INTO agp_unidades (bacia, caminho, poco_id, topo) VALUES ('Potiguar', 'x', 'A', 500)")
        c.execute("INSERT INTO producao_poco (campo, poco_anp, poco_id, periodo) VALUES ('X', 'A', 'A', '2020-01')")
    for rel, poco, bacia, tipo in (("a.pdf", "A", "Potiguar", "documento"), ("a.las", "A", "Potiguar", "perfil"),
                                   ("b1.pdf", "B", "Potiguar", "documento"), ("b2.pdf", "B", "Potiguar", "documento"),
                                   ("d.pdf", "D", "Alagoas", "documento")):
        b.registrar_arquivo(rel, bacia=bacia, poco_id=poco, tipo=tipo)
    b.salvar_fato({"poco_id": "C", "tipo": "topo_formacao", "nome": "Açu", "prof_topo": 800,
                   "criado_em": "2026-09-10T10:00:00-03:00"})
    b.salvar_fato({"poco_id": "B", "tipo": "revestimento", "prof_topo": 300, "autor": "Ana",
                   "origem": "pacote", "pacote": "p1", "criado_em": "2026-10-02T10:00:00-03:00"})
    b.vocab_definir("correcao", "BARIGIRAS", "BARREIRAS")
    b.vocab_definir("correcao", "AREN1TO", "ARENITO", origem="base", pacote="base:v1", autor="Beto")
    b.salvar_revisao("d.pdf", 1, "texto corrigido", autor="Ruan")
    b.salvar_interpretacao({"poco_id": "A", "dados": {"intervalos": []}, "autor": "Beto", "origem": "base",
                            "pacote": "base:v1", "criado_em": "2026-10-05T10:00:00-03:00"})
    return b


def test_cobertura_por_indicador_e_por_bacia(banco):
    r = painel.indicadores(banco, "Ruan")
    assert r["total"] == 4 and r["levantamento"]
    n = {i["chave"]: (i["n"], i["pct"]) for i in r["indicadores"]}
    assert n["documentos"] == (3, 75.0) and n["perfil"] == (3, 75.0)      # D: perfil no portal, não baixado
    assert n["topos"] == (2, 50.0) and n["topos_transcritos"] == (1, 25.0)
    assert n["transcricoes"] == (2, 50.0) and n["revisadas"] == (1, 25.0)
    assert n["interpretacoes"] == (1, 25.0) and n["producao"] == (1, 25.0)
    pb = {x["bacia"]: x for x in r["por_bacia"]}
    assert pb["Potiguar"]["total"] == 3 and pb["Potiguar"]["topos"] == 2 and pb["Alagoas"]["revisadas"] == 1
    assert r["bacias"] == ["Alagoas", "Potiguar"]


def test_contribuidores_atividade_e_onde_ajudar(banco):
    r = painel.indicadores(banco, "Ruan")
    por = {d["autor"]: d for d in r["contribuidores"]}
    assert por["Ruan"]["total"] == 3 and por["Ruan"]["voce"]               # topo + correção + página
    assert por["Ruan"]["topos"] == 1 and por["Ruan"]["correcoes"] == 1 and por["Ruan"]["paginas"] == 1
    assert por["Ana"]["fatos"] == 1 and por["Ana"]["origens"] == ["pacote"] and not por["Ana"]["voce"]
    assert por["Beto"]["interpretacoes"] == 1 and por["Beto"]["correcoes"] == 1
    assert r["contribuidores"][0]["autor"] == "Ruan"
    assert r["global"] == {"correcoes": 2, "palavras": 0, "autores": 3}
    meses = {m["mes"]: m for m in r["atividade"]}
    assert meses["2026-09"]["topos"] == 1 and meses["2026-10"]["fatos"] == 1
    aj = {a["chave"]: a for a in r["ajudar"]}
    assert [p["poco"] for p in aj["perfil_sem_topo"]["pocos"]] == ["D"]
    assert [p["poco"] for p in aj["docs_sem_dado"]["pocos"]] == ["A", "D"]


def test_filtro_por_bacia_e_banco_vazio(banco, tmp_path):
    r = painel.indicadores(banco, "Ruan", "Alagoas")
    assert r["total"] == 1 and r["bacia"] == "Alagoas"
    assert [d["autor"] for d in r["contribuidores"]] == ["Ruan"]           # só a página revisada do D
    vazio = painel.indicadores(mb.Banco(str(tmp_path / "v.sqlite")))
    assert vazio["total"] == 0 and all(i["pct"] is None for i in vazio["indicadores"])
    assert vazio["contribuidores"] == [] and not vazio["levantamento"]


def test_ponte_painel(api):
    api.escolher_pasta()
    api.definir_autor("Ruan da Silva Nobre")
    api._banco.salvar_fato({"poco_id": "1-X-1-RN", "tipo": "topo_formacao", "nome": "Açu", "prof_topo": 10})
    r = api.painel_comunidade()
    assert r["ok"] and r["contribuidores"][0]["autor"] == "Ruan da Silva Nobre"
    assert r["avaliacoes_nao_compartilhadas"] == 0
    assert api.painel_comunidade("Alagoas")["total"] == 0


def test_pasta_so_com_imagem_nao_conta_como_perfil_digital(banco):
    """0.63 (A13): o painel contava n_perfil > 0, que inclui pasta de perfil só com imagem; agora é o mesmo critério
    de Configurações › Fontes e prioridade (baixado ou conferido pelo conteúdo)."""
    with banco.conexao() as c:
        c.execute("UPDATE acervo_pocos SET situacao = 'imagem' WHERE poco_id = 'D'")
    n = {i["chave"]: i["n"] for i in painel.indicadores(banco, "Ruan")["indicadores"]}
    assert n["perfil"] == 2
