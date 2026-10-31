"""Procurar poços por tipo de dado (0.49): a partir do levantamento (acervo_arquivos), sem tocar no portal."""
import csv
import io
import os

import pytest

from motor import tipos_dado as td

POCOS = [  # (bacia, pasta do poço no portal, nome, categoria)
    ("Potiguar", "/POCO/Categoria-1/Categoria-1_parte1/1-AAA-1-RN/", "1-AAA-1-RN", "Categoria-1"),
    ("Potiguar", "/POCO/Categoria-1/Categoria-1_parte1/1-BBB-2-RN/", "1-BBB-2-RN", "Categoria-1"),
    ("Potiguar", "/POCO/Categoria-3/7-CCC-3-RN/", "7-CCC-3-RN", "Categoria-3"),
    ("Alagoas", "/POCO/Categoria-1/1-DDD-4-AL/", "1-DDD-4-AL", "Categoria-1"),
]
ARQS = [  # (índice do poço, pasta dentro do poço, nome, tamanho)
    (0, "Dados de Rochas e Fluidos/PETROFISICABASICA", "a_COREGAMA.xls", 1000),
    (0, "Dados de Rochas e Fluidos/PETROFISICABASICA", "a_plugs.xls", 500),
    (0, "Dados de Rochas e Fluidos/PVT", "pvt.xls", 300),
    (0, "Perfis Digitais", "a.dlis", 90000),
    (1, "Petrofisica_basica", "b_COREGAMA.xls", 2000),
    (1, "Dados de Rochas e Fluidos/PETROFISICAAVANCADA", "b_PressaoCapilar.xls", 700),
    (2, "Petrofica_basica", "c_plugs.xls", 400),                       # erro de grafia que existe no REATE
    (2, "Teste de Formacao", "tfr.pdf", 50),
    (2, "Teste de Formacao a Cabo", "cabo.dlis", 60),
    (3, "Dados de Rochas e Fluidos/PETROFISICA_BASICA", "d_plugs.xlsx", 800),
]


@pytest.fixture
def banco(api):
    api.escolher_pasta()
    with api._banco.conexao() as c:
        for bacia, cam, nome, cat in POCOS:
            c.execute("INSERT INTO acervo_pocos(bacia, caminho, nome_pasta, poco_id, categoria) VALUES (?,?,?,?,?)",
                      (bacia, cam, nome, nome, cat))
        for i, pasta, nome, tam in ARQS:
            bacia, cam, _, _ = POCOS[i]
            c.execute("INSERT INTO acervo_arquivos(bacia, caminho, poco_caminho, nome, pasta, tamanho) VALUES (?,?,?,?,?,?)",
                      (bacia, f"{cam}{pasta}/{nome}", cam, nome, pasta, tam))
    return api._banco


def test_tipo_pelo_nome_da_pasta_em_todas_as_grafias():
    pb = "petrofisica_basica"
    for pasta in ("Dados de Rochas e Fluidos/PETROFISICABASICA", "Petrofisica_basica", "Petrofica_basica",
                  "Petrofisicabasica", "PETROFISICA_BASICA", "Dados de Rochas de Fluidos/PETROFISICABASICA"):
        assert td.tipos_da_pasta(pasta) == {pb}, pasta
    assert td.tipos_da_pasta("Dados de Rochas e Fluidos/PETROFISICAAVANCADA") == {"petrofisica_avancada"}
    assert td.tipos_da_pasta("Teste de Formacao") == {"teste_formacao"}              # não confunde com o a cabo
    assert td.tipos_da_pasta("Teste de Formacao a Cabo") == {"teste_formacao_cabo"}
    assert td.tipos_da_pasta("Perfil Digital Processado") == {"perfil_processado", "perfis_digitais"} \
        or td.tipos_da_pasta("Perfil Digital Processado") == {"perfil_processado"}
    assert td.tipos_da_pasta("AGP") == {"agp"} and td.tipos_da_pasta("Dados Direcionais") == {"direcionais"}
    assert td.tipos_da_pasta("Dados de Rochas e Fluidos/PVT") == {"pvt"}
    assert td.tipos_da_pasta("") == set() and td.tipos_da_pasta(None) == set()
    assert td.tipos_da_pasta("Pasta aleatória/Outra") == set()


def test_contar_poços_arquivos_e_bytes(banco):
    r = td.contar(banco)
    por = {t["chave"]: t for t in r["tipos"]}
    assert r["pocos_levantados"] == 4 and r["bacias"] == ["Alagoas", "Potiguar"]
    pb = por["petrofisica_basica"]
    assert (pb["n_pocos"], pb["n_arquivos"], pb["bytes"]) == (4, 5, 1000 + 500 + 2000 + 400 + 800)
    assert por["petrofisica_avancada"]["n_pocos"] == 1 and por["pvt"]["n_pocos"] == 1
    assert por["teste_formacao"]["n_pocos"] == 1 and por["teste_formacao_cabo"]["n_pocos"] == 1
    assert por["geoquimica"]["n_pocos"] == 0
    assert td.contar(banco, "Alagoas")["pocos_levantados"] == 1
    assert {t["chave"]: t["n_pocos"] for t in td.contar(banco, "Alagoas")["tipos"]}["petrofisica_basica"] == 1


def test_buscar_todos_e_algum_e_so_os_arquivos_do_tipo(banco):
    r = td.buscar(banco, ["petrofisica_basica"])
    assert [p["poco"] for p in r["pocos"]] == ["1-DDD-4-AL", "1-AAA-1-RN", "1-BBB-2-RN", "7-CCC-3-RN"] or \
        sorted(p["poco"] for p in r["pocos"]) == ["1-AAA-1-RN", "1-BBB-2-RN", "1-DDD-4-AL", "7-CCC-3-RN"]
    a = next(p for p in r["pocos"] if p["poco"] == "1-AAA-1-RN")
    assert sorted(x["nome"] for x in a["arquivos"]) == ["a_COREGAMA.xls", "a_plugs.xls"]      # sem o PVT nem o perfil
    assert a["arquivos"][0]["caminho"].startswith("/POCO/Categoria-1/") and a["arquivos"][0]["pasta_relativa"]
    assert r["n_arquivos"] == 5 and r["bytes"] == 4700

    ambos = td.buscar(banco, ["petrofisica_basica", "pvt"])
    assert [p["poco"] for p in ambos["pocos"]] == ["1-AAA-1-RN"]
    algum = td.buscar(banco, ["petrofisica_basica", "pvt"], modo="algum")
    assert algum["n_pocos"] == 4
    so_al = td.buscar(banco, ["petrofisica_basica"], "Alagoas")
    assert [p["poco"] for p in so_al["pocos"]] == ["1-DDD-4-AL"]
    assert td.buscar(banco, ["geoquimica"])["n_pocos"] == 0
    assert td.buscar(banco, ["teste_formacao", "teste_formacao_cabo"])["n_pocos"] == 1


def test_busca_invalida(banco):
    with pytest.raises(ValueError, match="pelo menos um"):
        td.buscar(banco, [])
    with pytest.raises(ValueError, match="pelo menos um"):
        td.buscar(banco, ["tipo_que_nao_existe"])
    with pytest.raises(ValueError, match="Modo"):
        td.buscar(banco, ["pvt"], modo="qualquer")


def test_csv_um_arquivo_por_linha(banco):
    r = td.buscar(banco, ["petrofisica_basica", "pvt"], modo="algum")
    linhas = list(csv.reader(io.StringIO(td.csv_da_busca(r)), delimiter=";"))
    assert linhas[0] == ["bacia", "poco", "categoria", "tipos_de_dado", "pasta", "arquivo", "tamanho_bytes",
                         "caminho_no_portal"]
    assert len(linhas) == 1 + r["n_arquivos"]
    pvt = next(l for l in linhas if l[5] == "pvt.xls")
    assert pvt[:4] == ["Potiguar", "1-AAA-1-RN", "Categoria-1", "PVT"] and pvt[6] == "300"


def test_exportar_grava_arquivo(banco, tmp_path):
    r = td.buscar(banco, ["pvt"])
    caminho = td.exportar(r, str(tmp_path / "saida"))
    assert os.path.basename(caminho).startswith("busca_pvt_") and caminho.endswith(".csv")
    assert "pvt.xls" in open(caminho, encoding="utf-8-sig").read()


def test_pela_ponte(api, banco):
    t = api.tipos_de_dado("")
    assert t["ok"] and t["pocos_levantados"] == 4
    b = api.buscar_por_tipo(["petrofisica_basica"], "Potiguar", "todos")
    assert b["ok"] and b["n_pocos"] == 3
    assert "pelo menos um" in api.buscar_por_tipo([], "", "todos")["erro"]
    e = api.exportar_busca_por_tipo(["pvt"], "", "todos")
    assert e["ok"] and e["n_pocos"] == 1 and e["arquivo"].startswith("exportacoes/tipos_de_dado/")
    assert os.path.isfile(os.path.join(api._projeto.pasta, e["arquivo"]))
