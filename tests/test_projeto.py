"""Pasta de projeto: criação, reabertura, nomes e caminhos seguros."""
import json
import os

import pytest

from motor import projeto as mp


def test_criar_e_reabrir_sem_sobrescrever(tmp_path):
    p = mp.Projeto.abrir_ou_criar(str(tmp_path))
    assert set(mp.SUBPASTAS) <= set(os.listdir(tmp_path))
    p.registrar("conectou", bacia="Sergipe", categorias=3)
    p2 = mp.Projeto.abrir_ou_criar(str(tmp_path))
    assert p2.config["bacia"] == "Sergipe" and len(p2.config["historico"]) == 1
    assert not any(f.endswith(".tmp") for _, _, fs in os.walk(tmp_path) for f in fs)


def test_arquivo_no_lugar_de_pasta(tmp_path):
    (tmp_path / "x").write_text("a")
    with pytest.raises(NotADirectoryError):
        mp.Projeto.abrir_ou_criar(str(tmp_path / "x"))


def test_nome_seguro():
    assert mp.nome_seguro("Categoria 7 - Pioneiro: Adj?") == "Categoria_7_-_Pioneiro_Adj"


def test_destino_bruto_reproduz_portal_e_nunca_sai_do_projeto(tmp_path):
    p = mp.Projeto.abrir_ou_criar(str(tmp_path))
    d = p.destino_bruto("Alagoas", "7-ANB-9-AL", "Perfis_digitais", "a.dlis")
    assert d == os.path.join(str(tmp_path), "bruto", "Alagoas", "7-ANB-9-AL", "Perfis_digitais", "a.dlis")
    malicioso = p.destino_bruto("..", "..", "../../x", "y.dlis")
    assert os.path.commonpath([malicioso, str(tmp_path)]) == str(tmp_path)


def test_caminho_seguro_recusa_sair_de_bruto(tmp_path):
    p = mp.Projeto.abrir_ou_criar(str(tmp_path))
    with pytest.raises(ValueError):
        p.caminho_seguro("bruto/../../siapp.py")


def test_registro_de_downloads(tmp_path):
    p = mp.Projeto.abrir_ou_criar(str(tmp_path))
    p.registrar_download("Alagoas", "7-ANB-9-AL", "/POCO/x/a.dlis", str(tmp_path / "bruto" / "a.dlis"), 10)
    reg = json.loads((tmp_path / "bruto" / "registro_downloads.json").read_text(encoding="utf-8"))
    assert reg["Alagoas:/POCO/x/a.dlis"]["bytes"] == 10
