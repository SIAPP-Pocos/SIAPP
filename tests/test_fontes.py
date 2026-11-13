"""Fontes e prioridade do projeto e critérios de contagem de "perfil digital" (0.63). Só dados sintéticos."""

import pytest

from motor import banco as mb
from motor import fontes as mfo
from motor import zonas as mzo


@pytest.fixture
def banco(tmp_path):
    b = mb.Banco(str(tmp_path / "p.sqlite"))
    with b.conexao() as c:
        # A: perfil digital, pasta de perfis digitais, em duas categorias do portal (conta uma vez)
        # B: pasta "Perfis digitais" só com imagem; C: DLIS numa pasta sem esse nome; D: nada
        for bacia, cam, pid, sit in (("Potiguar", "/C1/A", "A", "digital"), ("Potiguar", "/C7/A", "A", "digital"),
                                     ("Potiguar", "/C1/B", "B", "imagem"), ("Potiguar", "/C1/C", "C", "digital"),
                                     ("Alagoas", "/C1/D", "D", "sem_perfil")):
            c.execute("INSERT INTO acervo_pocos(bacia, caminho, nome_pasta, poco_id, situacao) VALUES (?,?,?,?,?)",
                      (bacia, cam, pid, pid, sit))
        for bacia, poco_cam, pasta in (("Potiguar", "/C1/A", "Perfis digitais"), ("Potiguar", "/C7/A", "PERFIL_DIGITAL"),
                                       ("Potiguar", "/C1/B", "Perfis digitais"), ("Potiguar", "/C1/C", "Outros"),
                                       ("Alagoas", "/C1/D", "Pasta de poco")):
            c.execute("INSERT INTO acervo_arquivos(bacia, caminho, poco_caminho, nome, pasta, tamanho) VALUES (?,?,?,?,?,?)",
                      (bacia, poco_cam + "/" + pasta + "/x", poco_cam, "x", pasta, 10))
    b.registrar_arquivo("bruto/Potiguar/A/a.dlis", bacia="Potiguar", poco_id="A", tipo="perfil")
    return b


def test_zonas_padrao_ordem_ligar_e_guardar(banco):
    z = mfo.zonas(banco)
    assert z["ordem"] == mzo.PRIORIDADE_PADRAO and "tabela" not in z["ligadas"]       # padrão de antes, na janela
    z = mfo.definir_zonas(banco, ["fluido", "canhoneado", "inventada"], ["fluido", "canhoneado"])
    assert z["ordem"][:2] == ["fluido", "canhoneado"] and set(z["ordem"]) == set(mzo.FONTES)   # o resto vem atrás
    assert z["ligadas"] == ["fluido", "canhoneado"]
    z = mfo.ligar_zona(banco, "tabela")
    assert z["ordem"][:2] == ["fluido", "canhoneado"] and "tabela" in z["ligadas"]       # ligar não mexe na ordem
    assert mfo.fontes_zona_em_uso(banco) == ["fluido", "canhoneado", "tabela"]
    banco.definir_meta(mfo.CHAVE_ZONAS, "{quebrado")
    assert mfo.zonas(banco)["ordem"] == mzo.PRIORIDADE_PADRAO                           # meta estragada: padrão


def test_ler_junta_topos_e_zonas_com_rotulos(banco):
    r = mfo.ler(banco, tem_tabela=True)
    assert r["topos"]["ordem"] == ["agp", "transcrito", "rfp", "calha"] and r["topos"]["rotulos"]["calha"] == "Calha (PAG)"
    assert r["zonas"]["tem_tabela"] and r["zonas"]["rotulos"]["tabela"].startswith("Tabela sua")


def test_tres_criterios_de_perfil_digital(banco):
    r = mfo.contar_perfil(banco)
    n = {c["chave"]: c["n"] for c in r["criterios"]}
    assert n == {"conteudo": 2, "pasta": 2, "baixado": 1}       # A conta uma vez, apesar das duas pastas
    assert r["so_pasta"] == 1 and r["so_conteudo"] == 1          # B: pasta só com imagem; C: perfil fora da pasta
    assert r["baixado_ou_conteudo"] == 2
    assert all(c["rotulo"] and c["explicacao"] for c in r["criterios"])
    assert {c["chave"]: c["n"] for c in mfo.contar_perfil(banco, "Alagoas")["criterios"]} == \
        {"conteudo": 0, "pasta": 0, "baixado": 0}
    with pytest.raises(ValueError):
        mfo.pocos_com_perfil(banco, "inventado")


def test_resumo_do_levantamento_traz_poços_e_criterio(banco):
    from motor import levantamento as mlv
    r = mlv.resumo(banco, "Potiguar")
    assert r["pocos"] == 4 and r["pocos_distintos"] == 3          # 4 pastas, 3 poços
    assert r["situacoes"]["digital"] == 3                           # a tabela conta pastas…
    assert r["perfil_digital"]["n"] == 2 and r["perfil_digital"]["chave"] == "conteudo"   # …o número conta poços


def test_api_fontes_e_bloco_usa_as_do_projeto(api):
    api.escolher_pasta()
    r = api.fontes_prioridade()
    assert r["ok"] and r["zonas"]["tem_tabela"] is False
    r = api.fontes_prioridade_salvar("zonas", ["teste", "canhoneado"], ["teste"])
    assert r["ok"] and r["zonas"]["ligadas"] == ["teste"]
    assert api._config_zonas({})["fontes"] == ["teste"]                    # sem escolha da janela: as do projeto
    assert api._config_zonas({"fontes": ["fluido"]})["fontes"] == ["fluido"]
    r = api.fontes_prioridade_salvar("topos", ["rfp"])
    assert r["topos"]["ordem"][0] == "rfp" and api.topos_precedencia()["ordem"][0] == "rfp"
    assert not api.fontes_prioridade_salvar("outro", [])["ok"]
    assert api.contagens_perfil()["ok"]
    eventos = [e["evento"] for e in api._projeto.historico()]
    assert "definiu_fontes_zonas" in eventos and "definiu_precedencia_topos" in eventos
