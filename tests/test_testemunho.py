"""Testemunho × perfil (0.50): comparação de porosidade e deslocamento de profundidade pelo gama (dados sintéticos)."""
import numpy as np
import pytest

from motor import testemunho as tm


def gr_sintetico(prof):
    # gama com estrutura (folhelho/arenito) para a correlação ter um pico claro
    return 60 + 40 * np.sin(prof / 1.7) + 25 * np.sin(prof / 0.6 + 1) + 8 * np.cos(prof * 3.1)


def test_valor_em_interpola_e_recusa_buraco():
    prof = np.array([100.0, 100.5, 101.0, 103.0, 103.5])
    v = np.array([0.10, 0.20, 0.30, 0.10, 0.20])
    assert tm.valor_em(prof, v, 100.25) == pytest.approx(0.15)
    assert tm.valor_em(prof, v, 101.1, 0.3) == pytest.approx(0.29, abs=1e-3)
    assert tm.valor_em(prof, v, 102.0, 0.3) is None                 # buraco de 2 m na curva
    assert tm.valor_em(prof, v, 99.0, 0.3) is None and tm.valor_em(prof, v, 105.0, 0.3) is None
    assert tm.valor_em([1.0], [1.0], 1.0) is None
    assert tm.valor_em(prof, [np.nan] * 5, 100.0) is None


def test_deslocamento_conhecido_e_recuperado():
    prof_log = np.arange(2000.0, 2040.0, 0.2)
    gr_log = gr_sintetico(prof_log)
    # o testemunho está 1,6 m mais fundo no registro do perfil do que na profundidade que o testemunho declara:
    # perfil = testemunho + d  →  testemunho = perfil − d. Aqui d = +1,6 m.
    prof_core = np.arange(2012.0, 2024.0, 0.2)
    gr_core = np.interp(prof_core + 1.6, prof_log, gr_log)
    r = tm.deslocamento_gama(prof_core, gr_core, prof_log, gr_log)
    assert r["deslocamento_m"] == pytest.approx(1.6, abs=0.06)
    assert r["correlacao"] > 0.99 and r["confiavel"] is True and r["motivo"] is None
    assert r["correlacao_sem_deslocamento"] < r["correlacao"]
    assert r["n"] == len(prof_core) and r["curva"]


def test_deslocamento_nao_confiavel_com_ruido_ou_poucos_pontos():
    prof_log = np.arange(2000.0, 2040.0, 0.2)
    gr_log = gr_sintetico(prof_log)
    prof_core = np.arange(2012.0, 2024.0, 0.2)
    rng = np.random.default_rng(1)
    ruido = tm.deslocamento_gama(prof_core, rng.normal(60, 30, len(prof_core)), prof_log, gr_log)
    assert ruido["confiavel"] is False and ruido["motivo"]
    pouco = tm.deslocamento_gama(prof_core[:5], gr_log[:5], prof_log, gr_log)
    assert pouco["deslocamento_m"] is None and "poucos pontos" in pouco["motivo"]
    fora = tm.deslocamento_gama(np.arange(10.0, 20.0, 0.2), np.arange(50.0), prof_log, gr_log)
    assert fora["deslocamento_m"] is None and "não se sobrepõe" in fora["motivo"]
    constante = tm.deslocamento_gama(prof_core, np.full(len(prof_core), 50.0), prof_log, gr_log)
    assert constante["deslocamento_m"] is None


def test_comparar_plugs_diferenca_e_estatistica():
    prof = np.arange(1000.0, 1010.0, 0.5)
    phi = np.full(len(prof), 0.20)
    plugs = [{"prof": 1002.0, "phi_pct": 18.0}, {"prof": 1004.0, "phi_pct": 22.0}, {"prof": 1006.0, "phi_pct": 20.0},
             {"prof": 1500.0, "phi_pct": 15.0}]                                  # fora do perfil
    r = tm.comparar_plugs(prof, phi, plugs)
    ln = r["plugs"]
    assert [x["diferenca_pp"] for x in ln[:3]] == [2.0, -2.0, 0.0] and ln[3]["perfil_pct"] is None
    e = r["estatisticas"]
    assert e["n"] == 3 and e["diferenca_media_pp"] == 0.0 and e["erro_absoluto_medio_pp"] == pytest.approx(1.33, abs=0.01)
    assert e["rmse_pp"] == pytest.approx(1.63, abs=0.01)
    assert "correlacao" not in e                                                 # perfil constante: sem correlação
    assert tm.comparar_plugs(prof, phi, [{"prof": 9999.0, "phi_pct": 10.0}])["estatisticas"] == {"n": 0}


def test_comparar_com_deslocamento_melhora_a_concordancia():
    prof_log = np.arange(2000.0, 2040.0, 0.2)
    gr_log = gr_sintetico(prof_log)
    phi_log = 0.10 + 0.08 * (gr_log - gr_log.min()) / (gr_log.max() - gr_log.min())     # φ amarrada ao gama
    prof_core = np.arange(2012.0, 2024.0, 0.2)
    gama = [{"prof": float(p), "gr": float(g)} for p, g in zip(prof_core, np.interp(prof_core + 1.6, prof_log, gr_log))]
    plugs = [{"prof": float(p), "phi_pct": float(np.interp(p + 1.6, prof_log, phi_log) * 100)}
             for p in (2013.0, 2015.0, 2017.0, 2019.0, 2021.0)]
    r = tm.comparar(prof_log, phi_log, plugs, gama, prof_log, gr_log)
    assert r["deslocamento"]["confiavel"] and r["deslocamento"]["deslocamento_m"] == pytest.approx(1.6, abs=0.06)
    sem, com = r["sem_deslocamento"]["estatisticas"], r["com_deslocamento"]["estatisticas"]
    assert com["erro_absoluto_medio_pp"] < 0.2 < sem["erro_absoluto_medio_pp"]
    assert r["curva_deslocamento"]
    assert tm.comparar(prof_log, phi_log, plugs)["deslocamento"] is None


def test_deslocamento_pequeno_nao_vira_segunda_tabela():
    prof_log = np.arange(2000.0, 2040.0, 0.2)
    gr_log = gr_sintetico(prof_log)
    prof_core = np.arange(2012.0, 2024.0, 0.2)
    gama = [{"prof": float(p), "gr": float(g)} for p, g in zip(prof_core, np.interp(prof_core, prof_log, gr_log))]
    r = tm.comparar(prof_log, np.full(len(prof_log), 0.15), [{"prof": 2015.0, "phi_pct": 15.0}], gama, prof_log, gr_log)
    assert abs(r["deslocamento"]["deslocamento_m"]) < 0.05 and r["com_deslocamento"] is None


def test_pela_ponte_com_plugs_lidos(api):
    import json
    import os

    import petrofisica_util as pu
    POCO = "1-SIAPP-1-RN"
    api.escolher_pasta()
    pasta = os.path.join(api._projeto.pasta, "bruto", "Potiguar", POCO, "Dados de Rochas e Fluidos", "PETROFISICABASICA")
    os.makedirs(pasta)
    pu.plugs(os.path.join(pasta, "1SIAPP 0001  RN-Petrofisica Basica.xlsx"),
             linhas=[("1000,5", "18,0", "2,66", "10,5", "VH1", "1"), ("1001,5", "12,0", "2,70", "1,2", "VH1", "2")])
    pu.coregama(os.path.join(pasta, f"{POCO}_COREGAMA.xlsx"))
    api._abrir_projeto(api._projeto.pasta)
    # avaliação fabricada: φ = 16 % de 995 a 1010 m
    exe = api._pasta_execucoes()
    os.makedirs(exe, exist_ok=True)
    ident = "avaliacao_1-SIAPP-1-RN_20261031-120000"
    prof = np.arange(995.0, 1010.0, 0.2)
    np.savez_compressed(os.path.join(exe, ident + ".npz"), prof=prof, PHI=np.full(len(prof), 0.16, np.float32))
    json.dump({"id": ident, "tipo": "avaliacao_formacao", "poco": POCO, "arquivo": "bruto/x.las", "curvas_usadas": {},
               "intervalos": [], "criado_em": "2026-10-31"}, open(os.path.join(exe, ident + ".json"), "w"))
    r = api.comparar_testemunho(ident)
    assert r["ok"] and r["poco"] == POCO and r["n_gama"] == 4
    e = r["sem_deslocamento"]["estatisticas"]
    assert e["n"] == 2 and e["diferenca_media_pp"] == pytest.approx(1.0, abs=0.01)     # (16−18 + 16−12)/2
    assert r["deslocamento"] is None and r["com_deslocamento"] is None
    assert "não encontrada" in api.comparar_testemunho("nao_existe")["erro"]
