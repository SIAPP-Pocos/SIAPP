"""Biblioteca de interpretações de perfil (0.35): compartilhar uma avaliação, levar no
pacote (formato v3), importar, aplicar pela base, comparar e refazer no próprio SIAPP.
Perfil sintético (test_avaliacao.las_reservatorio): nada do REATE entra nos testes."""
import json
import os

import pytest

from base_util import montar_base
from motor import banco as mb
from motor import biblioteca as mbib
from motor import comunidade as mc
from test_avaliacao import las_reservatorio

POCO = "7-TST-1-RN"
REL = f"bruto/Potiguar/{POCO}/Perfil Convencional/tst.las"
AUTOR = "Ruan da Silva Nobre"


def intervalo(nome, topo, base, net, phi=0.2, sw=0.25, **extra):
    return {"nome": nome, "topo": topo, "base": base, "bruto_m": base - topo, "com_dados_m": base - topo,
            "reservatorio_m": net, "net_pay_m": net, "phi_media_pay": phi, "sw_media_pay": sw,
            "vsh_medio": 0.3, "hpv_m": net * phi * (1 - sw), **extra}


def dados(intervalos, rw=0.05, vsh="linear"):
    return {"intervalos": intervalos, "metodos": {"vsh": vsh, "phi": "densidade_neutrao", "sw": "archie"},
            "parametros": {"rw": rw, "a": 1.0, "m": 2.0, "n": 2.0, "gr_limpo": 30.0},
            "parametros_automaticos": {"gr_limpo": "percentil 5 do GR nos intervalos"},
            "curvas_usadas": {"GR": {"quadro": "LAS", "mnemonico": "GR", "unidade": "gAPI"}}}


# ------------------------------------------------------------ motor
def test_totais_ponderam_pelo_net_pay():
    t = mbib.totais({"intervalos": [intervalo("A", 1000, 1010, 8, phi=0.20, sw=0.30),
                                    intervalo("B", 1100, 1104, 2, phi=0.10, sw=0.50)]})
    assert t["net_pay_m"] == 10 and t["bruto_m"] == 14
    assert t["phi_pay"] == pytest.approx(0.18) and t["sw_pay"] == pytest.approx(0.34)


def test_comparar_casa_intervalos_pela_profundidade_e_mostra_o_que_difere():
    a = {"id": "a", "rotulo": "Ana", "poco": POCO, "dados": dados([intervalo("Açu", 1000, 1020, 10),
                                                                   intervalo("Pendência", 1500, 1510, 3)])}
    b = {"id": "b", "rotulo": "Beto", "poco": POCO,
         "dados": dados([intervalo("Açu superior", 1002, 1018, 7)], rw=0.08, vsh="larionov_terciario")}
    r = mbib.comparar([a, b])
    acu, pend = r["intervalos"]
    assert acu["nomes"] == ["Açu", "Açu superior"] and acu["net_pay_amplitude_m"] == 3
    assert pend["por_item"][1] is None                     # o Beto não avaliou a Pendência
    assert "Rw (ohm·m)" in r["diferencas"] and "Vsh" in r["diferencas"]
    rw = next(p for p in r["parametros"] if p["chave"] == "rw")
    assert [v["valor"] for v in rw["valores"]] == [0.05, 0.08] and rw["difere"]
    gr = next(p for p in r["parametros"] if p["chave"] == "gr_limpo")
    assert gr["valores"][0]["auto"] and not gr["difere"]
    assert not r["avisos"]
    with pytest.raises(mbib.ErroBiblioteca):
        mbib.comparar([a])


def test_validar_item_de_pacote():
    bom = {"id": "i" * 36, "poco": POCO, **dados([intervalo("Açu", 1000, 1020, 10)])}
    assert mbib.validar(bom) == []
    ruim = {**bom, "intervalos": [{"nome": "x", "topo": 1020, "base": 1000}],
            "metodos": {"sw": "magia"}, "parametros": {"chute": 1}}
    erros = " ".join(mbib.validar(ruim))
    assert "topo e base" in erros and "magia" in erros and "chute" in erros
    assert "sem intervalos" in " ".join(mbib.validar({**bom, "intervalos": []}))


# ------------------------------------------------------------ ponta a ponta
@pytest.fixture
def projeto(api, tmp_path):
    api.escolher_pasta()
    pasta = tmp_path / "ambiente_teste" / "bruto" / "Potiguar" / POCO / "Perfil Convencional"
    pasta.mkdir(parents=True)
    las_reservatorio(pasta / "tst.las")
    api._abrir_projeto(str(tmp_path / "ambiente_teste"))
    r = api.inventariar_perfil(REL)
    assert r["ok"], r
    s = api.salvar_intervalo(REL, {"tipo": "intervalo_alvo", "nome": "Açu", "prof_topo": "1005", "prof_base": "1035"})
    assert s["ok"]
    info = api.avaliacao_info(REL)
    curvas = {p: d["padrao"] for p, d in info["papeis"].items() if d["padrao"]}
    return api, curvas, s["fato"]["id"]


def avaliar(api, curvas, ints, **par):
    r = api.avaliar_formacao(REL, curvas, ints, {"gr_limpo": "30", "gr_argila": "120", "rw": "0,05", **par})
    assert r["ok"], r
    return r


def test_compartilhar_exportar_importar_e_desfazer(projeto, tmp_path):
    api, curvas, fid = projeto
    ex = avaliar(api, curvas, [fid])
    assert api.biblioteca()["nao_compartilhadas"][0]["id"] == ex["id"]
    assert "nome" in api.publicar_interpretacao(ex["id"], "Açu com Archie")["erro"]      # sem autor
    assert api.definir_autor(AUTOR, "UFAL")["ok"]
    assert "longo" in api.publicar_interpretacao(ex["id"], "x" * 200)["erro"]
    p = api.publicar_interpretacao(ex["id"], "Açu com Archie", "Rw da\n\n\n\nlama do AGP.")
    assert p["ok"] and not p["atualizada"]
    b = api.biblioteca()
    assert b["nao_compartilhadas"] == [] and len(b["interpretacoes"]) == 1
    it = b["interpretacoes"][0]
    assert it["poco"] == POCO and it["autor"] == AUTOR and it["origem"] == "local" and it["tem_arquivo"]
    assert it["totais"]["net_pay_m"] == pytest.approx(10.0, abs=0.5)
    assert api.biblioteca({"texto": "archie"})["interpretacoes"] and not api.biblioteca({"texto": "xyz"})["interpretacoes"]
    d = api.interpretacao(p["id"])
    assert d["comentario"] == "Rw da\n\nlama do AGP." and d["arquivo_local"] == REL and d["pode_remover"]
    assert any(x["chave"] == "rw" and x["valor"] == 0.05 for x in d["parametros"])
    assert api.publicar_interpretacao(ex["id"], "Açu (revisto)")["atualizada"]           # mesma execução
    assert api.biblioteca()["interpretacoes"][0]["titulo"] == "Açu (revisto)"
    assert api.avaliacao_info(REL)["publicadas"] == {ex["id"]: p["id"]}

    # exportar: a interpretação vai no pacote v3, sem curvas
    r = api.exportar_contribuicao()
    assert r["ok"] and r["itens"]["interpretacoes"] == 1
    pacote = json.load(open(os.path.join(api._projeto.pasta, r["arquivo"]), encoding="utf-8"))
    assert pacote["versao_formato"] == 3 and mc.validar_pacote(pacote) == []
    pi = pacote["interpretacoes"][0]
    assert pi["poco"] == POCO and pi["arquivo"]["nome"] == "tst.las" and pi["arquivo"]["sha256"]
    assert "curvas" not in pi and pi["intervalos"][0]["nome"] == "Açu"
    assert api.comunidade()["local"]["interpretacoes_nao_exportadas"] == 0

    # outra pessoa importa e desfaz
    outro = mb.Banco(str(tmp_path / "outro.sqlite"))
    assert mc.previa(outro, pacote)["itens"]["interpretacoes"] == 1
    assert mc.importar(outro, pacote)["interpretacoes_novas"] == 1
    assert mc.previa(outro, pacote)["interpretacoes_repetidas"] == 1
    assert mc.importar(outro, pacote)["interpretacoes_novas"] == 0
    i = outro.interpretacoes()[0]
    assert i["origem"] == "pacote" and i["autor"] == AUTOR and i["dados"]["parametros"]["rw"] == 0.05
    assert outro.remover_interpretacao(i["id"]) == 0                   # da comunidade: só desfazendo o pacote
    assert outro.desfazer_pacote(pacote["id"])["interpretacoes"] == 1

    # pela base comunitária (e base antiga, sem a tabela, continua valendo)
    montar_base(str(tmp_path / "b.sqlite"), [pacote])
    assert mc.aplicar_base(outro, str(tmp_path / "b.sqlite"))["interpretacoes"] == 1
    assert outro.interpretacoes()[0]["origem"] == "base"
    montar_base(str(tmp_path / "velha.sqlite"), [pacote], "v2026.11.0", com_interpretacoes=False)
    assert mc.aplicar_base(outro, str(tmp_path / "velha.sqlite"))["interpretacoes"] == 0
    assert outro.interpretacoes() == []

    # pacote v2 com interpretações é recusado
    assert any("formato 3" in e for e in mc.validar_pacote({**pacote, "versao_formato": 2}))

    # remover a sua
    rm = api.remover_interpretacao(p["id"])
    assert rm["ok"] and rm["removidas"] == 1 and rm["ja_exportada"]


def test_comparar_com_avaliacao_nao_compartilhada_e_refazer(projeto):
    api, curvas, fid = projeto
    api.definir_autor(AUTOR)
    ex1 = avaliar(api, curvas, [fid])
    pid = api.publicar_interpretacao(ex1["id"], "Archie, Rw 0,05")["id"]
    ex2 = avaliar(api, curvas, [fid], rw="0,02")
    c = api.comparar_interpretacoes([pid, "exec:" + ex2["id"]])
    assert c["ok"], c
    assert c["itens"][1]["origem"] == "não compartilhada"
    assert "Rw (ohm·m)" in c["diferencas"] and len(c["intervalos"]) == 1
    assert all(x is not None for x in c["intervalos"][0]["por_item"])
    assert not api.comparar_interpretacoes([pid])["ok"]

    # refazer: o arquivo é achado pelo hash; os intervalos vêm da biblioteca
    r = api.interpretacao_refazer(pid)
    assert r["ok"] and r["rel"] == REL and r["conferido_por"] == "sha256"
    info = api.avaliacao_info(REL, pid)
    bib = info["biblioteca"]
    assert bib["mesmo_arquivo"] and bib["intervalos"][0]["id"] == f"bib:{pid}:0"
    assert bib["parametros"]["rw"] == 0.05 and info["na_biblioteca"] == 1
    refeita = avaliar(api, curvas, [bib["intervalos"][0]["id"]])
    assert refeita["intervalos"][0]["net_pay_m"] == ex1["intervalos"][0]["net_pay_m"]
    assert refeita["intervalos"][0]["origem"] == "biblioteca"
    assert api.avaliacao_info(REL, "nao-existe")["biblioteca"] is None
    assert not api.interpretacao_refazer("nao-existe")["ok"]


def test_refazer_sem_o_arquivo_explica_onde_baixar(api, tmp_path):
    api.escolher_pasta()
    api._banco.salvar_interpretacao({"poco_id": "1-XYZ-1-AL", "titulo": "t", "arquivo_nome": "xyz.dlis",
                                     "arquivo_caminho": "/POCO/C1/1-XYZ-1-AL/Perfis/xyz.dlis",
                                     "dados": dados([intervalo("A", 10, 20, 5)]), "autor": "Ana",
                                     "origem": "base", "pacote": "base:v1"})
    pid = api._banco.interpretacoes()[0]["id"]
    r = api.interpretacao_refazer(pid)
    assert not r["ok"] and "xyz.dlis" in r["erro"] and "Catálogo" in r["erro"]
    b = api.biblioteca({"origem": "base"})
    assert len(b["interpretacoes"]) == 1 and not b["interpretacoes"][0]["tem_arquivo"]
    assert api.biblioteca({"origem": "local"})["interpretacoes"] == []
    assert not api.remover_interpretacao(pid)["ok"]
