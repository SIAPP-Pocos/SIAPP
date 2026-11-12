"""Projetos em pastas separadas (0.58)."""
import os

from motor import banco as mb
from motor import projetos as mpj
from motor.projeto import Projeto


def test_criar_nomear_e_listar(tmp_path):
    principal = tmp_path / "ambiente_teste"
    principal.mkdir()
    Projeto.abrir_ou_criar(str(principal))
    a = mpj.criar(str(tmp_path), "Guamaré — modelo 3D", ["Potiguar"])
    b = mpj.criar(str(tmp_path), "Guamaré — modelo 3D")                   # mesmo nome: outra pasta
    assert os.path.basename(a) == "guamare-modelo-3d" and os.path.basename(b) == "guamare-modelo-3d-2"
    assert mpj.nome_do_projeto(str(principal), str(principal)) == mpj.NOME_PRINCIPAL
    assert mpj.nome_do_projeto(a) == "Guamaré — modelo 3D"
    lista = mpj.conhecidos(str(principal), [a, a, str(tmp_path / "sumiu")], str(tmp_path))
    assert lista[0] == str(principal) and lista.count(a) == 1 and b in lista     # b achado em projetos/
    assert mpj.renomear(a, "Guamaré") == "Guamaré" and mpj.nome_do_projeto(a) == "Guamaré"
    r = mpj.resumo(str(tmp_path / "sumiu"))
    assert r["existe"] is False and r["pocos"] == 0


def test_resumo_le_o_banco_sem_travar(tmp_path):
    from test_pocos import csv_exemplo
    from motor import pocos as mpo
    pasta = mpj.criar(str(tmp_path), "Teste", [])
    b = mb.Banco(os.path.join(pasta, "projeto.sqlite"))
    mpo.importar_cadastro(b, mpo.ler_cadastro(csv_exemplo()), "anp:teste")
    mpo.registrar_reate(b, "Potiguar", "Categoria-1", [{"caminho": "/a/1-AURI-12-RN", "nome": "1-AURI-12-RN"},
                                                       {"caminho": "/a/7-GMR-13-RN", "nome": "7-GMR-13-RN"}])
    r = mpj.resumo(pasta)
    assert r["pocos"] == 2 and r["bacias"] == ["Potiguar"] and len(r["pontos"]) == 2
    assert mpj.resumo(pasta)["nome"] == "Teste"


def test_nome_vazio_recusado(tmp_path):
    import pytest
    with pytest.raises(mpj.ErroProjeto):
        mpj.criar(str(tmp_path), " ")


def test_api_abrir_outro_projeto_e_resumo_dos_modulos(api, tmp_path, monkeypatch):
    assert api.escolher_pasta()["ok"]
    r = api.inicio_resumo()
    assert r["ok"] and r["docs"]["total"] == 0 and r["secao"]["ultima"] is None and r["bloco"]["ultimo"] is None
    novo = api.projeto_criar("Sergipe", ["Sergipe"])
    assert novo["ok"] and os.path.isdir(novo["pasta"])
    lista = api.projetos()
    assert [p["nome"] for p in lista["projetos"]] == [mpj.NOME_PRINCIPAL, "Sergipe"]
    assert lista["projetos"][0]["aberto"] and lista["projetos"][1]["bacias"] == ["Sergipe"]
    # com downloads em andamento, não troca
    monkeypatch.setattr(type(api._fila), "ativa", property(lambda self: True))
    r = api.projeto_abrir(novo["pasta"])
    assert not r["ok"] and "downloads" in r["erro"]
    monkeypatch.setattr(type(api._fila), "ativa", property(lambda self: False))
    reaberto = []
    monkeypatch.setattr(type(api), "_reiniciar", lambda self: reaberto.append(1))
    assert api.projeto_abrir(novo["pasta"])["reiniciando"] and reaberto == [1]
    assert api._projeto_inicial() == novo["pasta"]
    assert not api.projeto_abrir(str(tmp_path / "qualquer"))["ok"]                    # só projetos conhecidos
    assert api.projeto_renomear(novo["pasta"], "SE")["nome"] == "SE"


def test_abre_o_ultimo_projeto_escolhido(api, tmp_path):
    from ponte import base
    os.makedirs(base.PASTA_PROJETO, exist_ok=True)
    pasta = mpj.criar(str(tmp_path), "Outro")
    api._preferencias().atualizar({"projeto_atual": pasta})
    r = api.abrir_projeto_padrao()
    assert r["ok"] and r["pasta"] == pasta
    assert api.estado()["existe_projeto"] is True


def test_abertura_reconfere_o_tipo_so_quando_precisa(api, tmp_path):
    """0.59 (A16 da revisão): a conferência do tipo pelo conteúdo roda inteira uma vez; depois, só arquivo que mudou."""
    from ponte import base
    assert api.escolher_pasta()["ok"]
    bruto = os.path.join(base.PASTA_PROJETO, "bruto", "Potiguar", "1-AA-1-RN")
    os.makedirs(bruto, exist_ok=True)
    arq = os.path.join(bruto, "perfil.tif")
    with open(arq, "wb") as f:
        f.write(b"texto qualquer, nao e imagem nem DLIS" * 10)
    api._migrar_downloads()
    tipo = api._banco.arquivos()[0]["tipo"]
    assert api._banco.meta("tipo_conferido") == "1"
    with api._banco.conexao() as c:
        c.execute("UPDATE arquivos SET tipo = 'documento'")
    api._migrar_downloads()                                   # mesma regra, mesmo tamanho: não reabre o arquivo
    assert api._banco.arquivos()[0]["tipo"] == "documento"
    with open(arq, "ab") as f:
        f.write(b"mais")                                      # mudou: confere de novo
    api._migrar_downloads()
    assert api._banco.arquivos()[0]["tipo"] == tipo


def test_nenhum_nome_publico_repetido_entre_as_partes_da_api():
    """A API é uma classe feita de 17 partes (mixins): um nome público repetido faria uma parte esconder a outra."""
    from ponte.api import API
    vistos = {}
    for parte in API.__mro__[1:]:
        if parte is object:
            continue
        for nome, valor in vars(parte).items():
            if nome.startswith("_") or not callable(valor):
                continue
            assert nome not in vistos, f"{nome} está em {vistos[nome]} e em {parte.__name__}"
            vistos[nome] = parte.__name__
    assert len(vistos) > 150
