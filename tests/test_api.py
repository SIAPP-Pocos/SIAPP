"""Regras da janela: pasta de projeto fixa e travas de segurança."""


def test_pasta_fixa_recusa_outras(api, tmp_path):
    api._janela.escolha = (str(tmp_path),)
    assert not api.escolher_pasta()["ok"]
    api._janela.escolha = (str(tmp_path / "ambiente_teste" / "catalogo"),)
    assert not api.escolher_pasta()["ok"]
    api._janela.escolha = None
    assert api.escolher_pasta()["ok"]


def test_cancelar_dialogo_nao_e_erro(api):
    api._janela.escolha = ()
    assert api.escolher_pasta() == {"ok": True, "cancelado": True}


def test_acoes_exigem_projeto_e_conexao(api):
    assert "pasta do projeto" in api.conectar("Sergipe")["erro"]
    api.escolher_pasta()
    assert "Conecte-se" in api.listar_pocos("Categoria-7")["erro"]


def test_correcao_global_de_numero_e_bloqueada(api):
    api.escolher_pasta()
    r = api.corrigir_palavra("87", "83")
    assert not r["ok"] and "Números" in r["erro"]
    assert api.corrigir_palavra("BARIGIRAS", "BARREIRAS")["ok"]
    assert api.dicionario()["correcoes"] == {"BARIGIRAS": "BARREIRAS"}


def test_caminho_fora_da_bacia_e_recusado(api):
    api.escolher_pasta()
    api._cliente, api._cliente_dl, api._base_remota, api._bacia = object(), object(), "/POCO/", "X"
    assert not api.explorar_poco("x", "/OUTRA/x/")["ok"]
    assert not api.baixar("x", [{"caminho": "/OUTRA/a", "nome": "a"}])["ok"]
