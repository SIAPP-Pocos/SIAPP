"""0.65: "Ver arquivos" da ficha — conecta se preciso e usa a lista salva da categoria (dados sintéticos)."""

import pytest

from motor import reate


class Falso:
    def descobrir_categorias(self):
        return "/POCO/", [{"nome": "Categoria-7", "modificado": ""}, {"nome": "Categoria-1", "modificado": ""}]


@pytest.fixture
def api_conectavel(api, monkeypatch):
    conexoes = []
    monkeypatch.setattr(reate.ClienteREATE, "da_bacia", classmethod(lambda cls, b, **kw: conexoes.append(b) or Falso()))
    api.escolher_pasta()
    api.conexoes = conexoes
    return api


def test_sem_lista_salva_mostra_so_o_poco(api_conectavel):
    r = api_conectavel.catalogo_abrir_poco("Potiguar", "Categoria-7", "7-X-1-RN", "/POCO/Categoria-7/7-X-1-RN/")
    assert r["ok"] and r["lista"]["parcial"] and r["lista"]["pocos"] == [r["poco"]]
    assert [c["nome"] for c in r["conexao"]["categorias"]] == ["Categoria-7", "Categoria-1"]
    assert api_conectavel.conexoes == ["Potiguar", "Potiguar"]          # uma conexão = 2 clientes (um para downloads)


def test_com_lista_salva_usa_ela_e_nao_reconecta(api_conectavel):
    api = api_conectavel
    api.conectar("Potiguar")
    pocos = [{"nome": "7-A-1-RN", "caminho": "/POCO/Categoria-7/7-A-1-RN/", "parte": None},
             {"nome": "7-X-1-RN", "caminho": "/POCO/Categoria-7/p1/7-X-1-RN/", "parte": "p1"}]
    api._projeto.salvar_pocos("Potiguar", "Categoria-7", pocos, [])
    r = api.catalogo_abrir_poco("Potiguar", "Categoria-7", "7-X-1-RN", "/POCO/Categoria-7/p1/7-X-1-RN/", "p1")
    assert r["ok"] and not r["lista"]["parcial"] and len(r["lista"]["pocos"]) == 2
    assert r["poco"]["parte"] == "p1" and r["conexao"]["ja_conectado"]
    assert api.conexoes == ["Potiguar", "Potiguar"]           # só a conexão do começo
    r = api.catalogo_abrir_poco("Alagoas", "Categoria-7", "7-X-1-RN", "/OUTRA/7-X-1-RN/")
    assert not r["ok"] and "não é da bacia" in r["erro"]
