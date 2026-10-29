"""Pressões (0.38): estação do teste a cabo, DLIS por tempo, TFR (relatório + manômetros) e gradiente."""
import zipfile

import pytest

import pressoes_util as u
from motor import banco as mb
from motor import dados_poco as mdp
from motor import pocos as mpo
from motor import pressoes as pr


def test_reconhecimento_pelo_caminho():
    assert pr.tipo_pelo_nome("bruto/Rec/1-X-1-BA/Teste de Formacao a Cabo/1-x-1-ba_sft-2.dlis") == "wft"
    assert pr.tipo_pelo_nome("bruto/Pot/1-X-1-RN/Perfil Convencional/1-x-1-rn_mdt.dlis") == "wft"
    assert pr.tipo_pelo_nome("bruto/Pot/1-X-1-RN/Perfil Convencional/1-x-1-rn_raw-2.dlis") is None
    assert pr.tipo_pelo_nome("bruto/Rec/1-X-1-BA/Teste de Formacao/1X1BA_TFR.zip") == "tfr"
    assert pr.tipo_pelo_nome("bruto/Rec/1-X-1-BA/Outros/1X1BA_TFR.zip") == "tfr"
    assert pr.tipo_pelo_nome("bruto/Rec/1-X-1-BA/Outros/fotos.zip") is None
    assert pr.tipo_pelo_nome("bruto/Rec/1-X-1-BA/Teste de Formacao/registro.TPR") == "tfr"


def test_estacao_estabilizada_com_dois_pretestes():
    t, p = u.estacao(p_form=2500, hidro=3000)
    r = pr.analisar_estacao(t, p)
    assert r["pressao_psi"] == pytest.approx(2500, abs=0.5)
    assert r["hidrostatica_antes_psi"] == pytest.approx(3000, abs=0.5)
    assert r["n_pretestes"] == 2 and r["pressao_patamar_anterior_psi"] == pytest.approx(2500, abs=0.5)
    assert r["pressao_min_psi"] == pytest.approx(2100, abs=5) and r["qualidade"] == "estabilizada"
    # a subida lenta quando a sonda começa a soltar não entra no patamar
    assert abs(r["inclinacao_psi_min"]) < 0.5


def test_estacao_fechada_e_sem_vedacao():
    r = pr.analisar_estacao(*u.estacao(fechada=True))
    assert r["qualidade"].startswith("não estabilizou") and r["inclinacao_psi_min"] > 2
    r = pr.analisar_estacao(*u.estacao(sem_vedacao=True))
    assert r["pressao_psi"] is None and r["qualidade"] == "sem vedação ou sem pré-teste"
    assert pr.analisar_estacao([0, 1], [1, 2])["qualidade"] == "poucos dados"


def test_dlis_indexado_por_tempo():
    d = pr.estacoes_dlis(u.dlis_falso())
    assert d["cabecalho"]["poco"] == "1-SIAPP-1-RN" and d["cabecalho"]["peso_lama_lb_gal"] == "10.0"
    assert "bht_f" not in d["cabecalho"]                    # -999.25 = vazio
    e = d["estacoes"]
    assert [x["prof"] for x in e] == [1500.0, 1510.0, 1540.0, 1560.0]
    assert e[0]["pressao_psi"] == pytest.approx(2130, abs=0.5) and e[0]["canal"] == "FPRE"
    assert e[0]["pressao_kgf_cm2"] == pytest.approx(2130 / 14.2233, abs=0.05)
    assert len(e[0]["serie"]["t_s"]) <= 401 and e[0]["serie"]["t_s"][0] == 0
    assert pr._apelidos_wft(d["cabecalho"]) == ["1-ABC-1-RN"]


def test_tpr_e_relatorio_do_tfr_dentro_do_zip():
    d = pr.ler_tfr_zip(u.tfr_zip(), "1-SIAPP-1-RN_TFR.zip")
    r = d["relatorio"]
    assert (r["topo"], r["base"]) == (1395.0, 1400.0) and r["teste"] == "TFR-01" and r["formacao"] == "AÇU"
    assert r["pressao_estatica_kgf_cm2"] == 141.7 and r["pressao_fluxo_kgf_cm2"] == 130.4
    assert r["permeabilidade_md"] == 525.0 and r["skin"] == -1.5 and r["transmissibilidade"] == 1250.0
    assert r["ip"] == 4.1 and r["api"] == 31.2 and r["temp_max_c"] == 71.5 and r["prof_referencia"] == 1398.0
    assert [x["kgf_cm2"] for x in r["pressoes_estaticas"]] == [141.7, 141.52]
    assert r["conclusao"] == "Conclusivo\nIntervalo portador de óleo, produtividade média."
    assert r["modelo"] == "Fluxo radial homogêneo." and r["fluido_desc"] == "Óleo de 2,1 cp."
    f1, f2 = r["fluxos"]
    assert f1["abertura_64"] is None and f2["abertura_64"] == 16.0 and f2["vazao_liquido_m3_dia"] == 45.5
    m = {x["registrador"]: x for x in d["manometros"]}
    assert m["11111"]["interpretacao"] and not m["22222"]["interpretacao"]
    assert d["manometros"][0]["registrador"] == "11111"            # o da interpretação vem primeiro
    assert m["11111"]["profundidade"] == 1398.0 and m["11111"]["posicao"] == "INTERNO"
    assert m["22222"]["pressao_max_kgf_cm2"] == pytest.approx(152.0, abs=0.01)
    assert m["11111"]["n_amostras"] == 400 and m["11111"]["temperatura_max_c"] == pytest.approx(69.9)
    assert d["apelidos"] == ["1-ABC-1-RN"] and [o["arquivo"].rsplit("/", 1)[-1] for o in d["outros_arquivos"]] == ["leia-me.txt"]
    tipos = [i["tipo"] for i in pr.itens(d)]
    assert tipos == ["teste_tfr", "temperatura", "manometro", "manometro"]


def test_zip_sem_teste(tmp_path):
    import io
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr("nada.txt", "x")
    with pytest.raises(pr.ErroPressao, match="nem registros"):
        pr.ler_tfr_zip(b.getvalue())
    with pytest.raises(pr.ErroPressao, match="ZIP inválido"):
        pr.ler_tfr_zip(b"isto nao e zip")


def test_gradiente_densidade_e_contato():
    oleo = [(1500 + k, 150 + 0.07 * k) for k in range(5)]          # 0,7 g/cm³
    agua = [(1540 + k * 5, 0.104 * (1540 + k * 5) - 9.0) for k in range(4)]
    g1, g2 = pr.gradiente(oleo), pr.gradiente(agua)
    assert g1["densidade_g_cm3"] == pytest.approx(0.70, abs=1e-3) and g1["fluido_compativel"] == "óleo"
    assert g2["densidade_g_cm3"] == pytest.approx(1.04, abs=1e-3) and g2["fluido_compativel"] == "água"
    assert g1["gradiente_psi_ft"] == pytest.approx(0.07 * 14.2233 * 0.3048, abs=1e-4) and g1["r2"] == 1.0
    z = pr.contato(g1, g2)
    assert g1["gradiente_kgf_cm2_m"] * z + g1["intercepto_kgf_cm2"] == pytest.approx(
        g2["gradiente_kgf_cm2_m"] * z + g2["intercepto_kgf_cm2"], abs=0.01)
    with pytest.raises(pr.ErroPressao):
        pr.gradiente([(1500, 150)])


def _wft(banco, rel, poco="1-SIAPP-1-RN"):
    d = pr.estacoes_dlis(u.dlis_falso())
    dados = {"documento": "wft", "titulo": "Teste de formação a cabo", **d, "gerais": {"poco": d["cabecalho"]["poco"]},
             "apelidos": pr._apelidos_wft(d["cabecalho"])}
    return mdp.gravar(banco, rel, poco_id=poco, leitor="pressoes", dados=dados)


def test_painel_do_poco_e_serie(tmp_path):
    pasta = tmp_path / "p"
    rel_tfr = "bruto/Potiguar/1-SIAPP-1-RN/Teste de Formacao/1-SIAPP-1-RN_TFR.zip"
    (pasta / rel_tfr).parent.mkdir(parents=True)
    (pasta / rel_tfr).write_bytes(u.tfr_zip())
    b = mb.Banco(str(pasta / "projeto.sqlite"))
    b.registrar_arquivo(rel_tfr, bacia="Potiguar", poco_id="1-SIAPP-1-RN", tipo="outro")
    assert [a["rel"] for a in mdp.pendentes(b)] == [rel_tfr]
    r = mdp.ler_pendentes(b, str(pasta))[0]
    assert r["documento"] == "tfr" and r["confere"] == 1 and r["n"] == 4
    assert _wft(b, "bruto/Potiguar/1-SIAPP-1-RN/Teste de Formacao a Cabo/x_sft.dlis")["confere"] == 1
    assert mpo.resolver(b, "1-ABC-1-RN") == "1-SIAPP-1-RN"
    pn = pr.painel(mdp.do_poco(b, "1-SIAPP-1-RN"))
    origens = [p["origem"] for p in pn["pontos"]]
    assert origens.count("teste a cabo") == 4 and origens.count("TFR") == 1
    tfr = next(p for p in pn["pontos"] if p["origem"] == "TFR")
    assert tfr["prof"] == 1398.0 and tfr["pressao_kgf_cm2"] == 141.7
    assert pn["lama"] == [{"rel": "bruto/Potiguar/1-SIAPP-1-RN/Teste de Formacao a Cabo/x_sft.dlis",
                           "peso_lb_gal": 10.0, "tipo": "BASE AGUA"}]
    assert [s["qual"] for s in pn["series"]][0] == "manometro:11111" or len(pn["series"]) == 2
    assert pn["tfr"][0]["permeabilidade_md"] == 525.0 and len(pn["tfr"][0]["fluxos"]) == 2
    import json
    with b.conexao() as c:
        dados = json.loads(c.execute("SELECT dados FROM leituras WHERE rel = ?", (rel_tfr,)).fetchone()[0])
    s = pr.serie(dados, "manometro:11111")
    assert s["x_rotulo"] == "tempo (h)" and len(s["x"]) == len(s["y"]) == 400
    with pytest.raises(pr.ErroPressao):
        pr.serie(dados, "estacao:1")
    temps = mdp.itens_do_poco(b, "1-SIAPP-1-RN", "temperatura")
    assert {(t["valor"], t["unidade"]) for t in temps} == {(71.5, "°C"), (160.0, "°F")}


def test_ponte_serie_e_gradiente(api):
    import os
    api.escolher_pasta()
    rel = "bruto/Potiguar/1-SIAPP-1-RN/Teste de Formacao a Cabo/x_sft.dlis"
    _wft(api._banco, rel)
    os.makedirs(os.path.join(api._projeto.pasta, "bruto", "Potiguar", "1-SIAPP-1-RN"), exist_ok=True)
    api._banco.registrar_arquivo(rel, bacia="Potiguar", poco_id="1-SIAPP-1-RN", tipo="perfil")
    f = api.ficha_poco("1-SIAPP-1-RN")
    assert f["ok"] and len(f["dados_poco"]["pressoes"]["pontos"]) == 4
    s = api.serie_pressao(rel, "estacao:2")
    assert s["ok"] and s["titulo"].startswith("estação 2 · 1510.0 m") and s["linhas"]["pressao_kgf_cm2"]
    assert not api.serie_pressao(rel, "estacao:9")["ok"]
    pts = [[p["prof"], p["pressao_kgf_cm2"]] for p in f["dados_poco"]["pressoes"]["pontos"]]
    g = api.gradiente_pressoes({"A": pts[:2], "B": pts[2:]})
    assert g["ok"] and g["A"]["n"] == 2 and "contato" in g
    assert not api.gradiente_pressoes({"A": pts[:1]})["ok"]
    assert not api.gradiente_pressoes({})["ok"]
