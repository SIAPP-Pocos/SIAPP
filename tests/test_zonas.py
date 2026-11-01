"""Zonas produtoras no bloco 3D (0.55): intervalos de várias fontes, reservatórios, regras, tabela do usuário e bloco completo."""
import json

import numpy as np
import pytest

from motor import bloco as mb
from motor import utm as mutm
from motor import zonas as mz
from motor.banco import Banco

# 6 poços num retângulo de ~4 x 4,4 km; mesa a 50 m. Reservatório raso (todos): topo a 1.000 m no oeste, mergulhando 5 m/km
# para leste; fundo (só 4 poços) uns 500 m abaixo.
POCOS = [("1-ZZ-1-RN", -5.00, -37.00), ("1-ZZ-2-RN", -5.00, -36.96), ("1-ZZ-3-RN", -5.04, -37.00),
         ("1-ZZ-4-RN", -5.04, -36.96), ("1-ZZ-5-RN", -5.02, -36.98), ("1-ZZ-6-RN", -5.02, -36.94)]
LESTE_KM = {pid: (lo + 37.00) * 111.0 for pid, _, lo in POCOS}
MESA = 50.0


def topo_raso(pid):
    return 1000.0 + 5 * LESTE_KM[pid]


@pytest.fixture
def banco(tmp_path):
    return popular(Banco(str(tmp_path / "projeto.sqlite")))


def popular(b):
    """Seis poços com canhoneado, análise de perfis e fluido (reservatório raso) e teste de formação (fundo, em quatro)."""
    n = 0
    for pid, la, lo in POCOS:
        with b.conexao() as c:
            c.execute("INSERT INTO pocos(id, lat, lon, mesa_rotativa, prof_sondador, campo) VALUES (?,?,?,?,?,?)",
                      (pid, la, lo, MESA, 1800.0, "CAMPO TESTE"))

        def item(rel, tipo, topo, base, nome="", documento="rfp", leitor="cdpe", pagina=2):
            nonlocal n
            n += 1
            with b.conexao() as c:
                c.execute("INSERT OR IGNORE INTO leituras(rel, poco_id, leitor, versao, documento, n, lido_em) VALUES (?,?,?,?,?,?,?)",
                          (rel, pid, leitor, 1, documento, 1, "2026-10-31"))
                c.execute("INSERT INTO dados_poco VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                          (rel, pid, tipo, n, nome, topo, base, None, None, None, None, "{}", pagina))
        t = topo_raso(pid)
        item(f"bruto/{pid}/rfcp.pdf", "canhoneado", t + 2, t + 8, "canhoneio", "rfcp")           # fonte de maior prioridade
        item(f"bruto/{pid}/rfp.pdf", "analise_perfil", t, t + 14, "arenito", "rfp")                # envelope maior
        item(f"bruto/{pid}/pvt.xls", "pvt", t + 3, t + 5, "amostra", "pvt_diferencial", "pvt", None)
        if pid not in ("1-ZZ-5-RN", "1-ZZ-6-RN"):
            item(f"bruto/{pid}/tfr.pdf", "teste_formacao", 1500.0, 1520.0, "TFR", "tfr", "pressoes")   # reservatório fundo
    return b


def conversores(banco, ids):
    return {p: mz.Conversor(lambda md: MESA - np.asarray(md, float), 2500) for p in ids}


def candidatos(banco, fontes=None):
    fontes = fontes or ["canhoneado", "teste", "analise_perfil", "fluido"]
    return {pid: mz.coletar(banco, pid, fontes) for pid, _, _ in POCOS}


# ------------------------------------------------------------------------------------------------------- coletar / agrupar
def test_coleta_por_fonte_e_ids_estaveis(banco):
    c = mz.coletar(banco, "1-ZZ-1-RN", ["canhoneado", "analise_perfil", "fluido", "teste"])
    assert {x["fonte"] for x in c} == {"canhoneado", "analise_perfil", "fluido", "teste"}
    can = next(x for x in c if x["fonte"] == "canhoneado")
    assert (can["topo"], can["base"], can["ref"]) == (1002.0, 1008.0, "md") and can["id"] == "1-ZZ-1-RN|canhoneado|1002-1008"
    assert can["fonte_rotulo"] == mz.FONTES["canhoneado"] and can["pagina"] == 2
    assert mz.coletar(banco, "1-ZZ-1-RN", ["canhoneado"])[0]["id"] == can["id"]
    assert mz.coletar(banco, "1-ZZ-1-RN", []) == []
    leitura = lambda rel, pag: "ocr" if rel.endswith("rfcp.pdf") else "digital"                  # noqa: E731
    c2 = mz.coletar(banco, "1-ZZ-1-RN", ["canhoneado", "analise_perfil"], leitura=leitura)
    assert {x["fonte"]: x["leitura"] for x in c2} == {"canhoneado": "ocr", "analise_perfil": "digital"}


def test_intervalo_invalido_nao_vira_candidato(banco):
    with banco.conexao() as c:
        c.execute("INSERT INTO dados_poco VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                  ("bruto/1-ZZ-1-RN/rfcp.pdf", "1-ZZ-1-RN", "canhoneado", 999, "ruim", 1200.0, 1100.0, None, None, None, None, "{}", 1))
    c = mz.coletar(banco, "1-ZZ-1-RN", ["canhoneado"])
    assert len(c) == 1 and c[0]["topo"] == 1002.0


def test_agrupar_em_reservatorios_pela_profundidade():
    mk = lambda t, b: {"cota_topo": 50 - t, "cota_base": 50 - b}                                # noqa: E731
    g = mz.agrupar([mk(1000, 1010), mk(1005, 1020), mk(1500, 1510), mk(1012, 1030), mk(1900, 1910)], 20)
    assert [len(x) for x in g] == [3, 1, 1]
    assert [round(50 - x[0]["cota_topo"]) for x in g] == [1000, 1500, 1900]                     # do mais raso ao mais fundo
    g2 = mz.agrupar([mk(1000, 1010), mk(1040, 1050)], 20)
    assert len(g2) == 2
    assert len(mz.agrupar([mk(1000, 1010), mk(1040, 1050)], 40)) == 1                           # a tolerância junta
    assert mz.agrupar([], 20) == []


# ------------------------------------------------------------------------------------------------------- planejar
def test_dois_reservatorios_e_regra_de_prioridade(banco):
    ids = [p for p, _, _ in POCOS]
    plano = mz.planejar(candidatos(banco), conversores(banco, ids), {"fontes": ["canhoneado", "teste", "analise_perfil", "fluido"]})
    assert [z["chave"] for z in plano["zonas"]] == ["ZP1", "ZP2"]
    z1, z2 = plano["zonas"]
    assert (z1["n_pocos"], z2["n_pocos"]) == (6, 4) and z1["nome"] == "Reservatório 1" and z1["ativa"] and z2["ativa"]
    assert z1["cota_media"] > z2["cota_media"] > -1500                                           # o 1 é o mais raso
    e = plano["por_poco"]["1-ZZ-1-RN"]
    assert [x["zona"] for x in e] == ["ZP1", "ZP2"]
    # prioridade: o canhoneado (1002–1008) vence a análise de perfis (1000–1014) e a amostra de fluido
    assert (e[0]["topo"], e[0]["base"]) == (1002.0, 1008.0) and e[0]["fonte"] == mz.FONTES["canhoneado"]
    assert (e[0]["cota_topo"], e[0]["cota_base"]) == (MESA - 1002.0, MESA - 1008.0) and e[0]["n_candidatos"] == 3
    assert (e[1]["topo"], e[1]["base"]) == (1500.0, 1520.0)
    assert sum(c["usado"] for c in plano["candidatos"] if c["poco"] == "1-ZZ-1-RN") == 2
    assert [x["zona"] for x in plano["por_poco"]["1-ZZ-5-RN"]] == ["ZP1"]                         # só o raso


def test_regra_do_envelope_e_ordem_das_fontes(banco):
    ids = [p for p, _, _ in POCOS]
    env = mz.planejar(candidatos(banco), conversores(banco, ids), {"regra": "envelope"})
    e = env["por_poco"]["1-ZZ-1-RN"][0]
    assert (e["topo"], e["base"]) == (1000.0, 1014.0)                                            # do menor topo ao maior fim
    outra = mz.planejar(candidatos(banco), conversores(banco, ids), {"fontes": ["analise_perfil", "canhoneado"]})
    assert (outra["por_poco"]["1-ZZ-1-RN"][0]["topo"], outra["por_poco"]["1-ZZ-1-RN"][0]["base"]) == (1000.0, 1014.0)
    so_fluido = mz.planejar(candidatos(banco), conversores(banco, ids), {"fontes": ["fluido"]})
    assert (so_fluido["por_poco"]["1-ZZ-1-RN"][0]["topo"],) == (1003.0,) and len(so_fluido["zonas"]) == 1
    with pytest.raises(mz.ErroZonas, match="Regra desconhecida"):
        mz.planejar({}, {}, {"regra": "media"})
    with pytest.raises(mz.ErroZonas, match="negativa"):
        mz.planejar({}, {}, {"tolerancia_m": -1})


def test_ajustes_do_usuario_ignorar_editar_e_mover(banco):
    ids = [p for p, _, _ in POCOS]
    base = mz.planejar(candidatos(banco), conversores(banco, ids), {})
    can = next(c for c in base["candidatos"] if c["poco"] == "1-ZZ-1-RN" and c["fonte"] == "canhoneado")
    teste = next(c for c in base["candidatos"] if c["poco"] == "1-ZZ-1-RN" and c["fonte"] == "teste")
    aj = {can["id"]: {"zona": "ignorar"}, teste["id"]: {"topo": 1495, "base": 1530}}
    plano = mz.planejar(candidatos(banco), conversores(banco, ids), {"ajustes": aj})
    e = plano["por_poco"]["1-ZZ-1-RN"]
    assert (e[0]["topo"], e[0]["base"]) == (1000.0, 1014.0)                                       # sem o canhoneado: a análise de perfis
    assert (e[1]["topo"], e[1]["base"]) == (1495.0, 1530.0)                                       # número corrigido à mão
    ed = next(c for c in plano["candidatos"] if c["id"] == teste["id"])
    assert ed["editado"] and (ed["topo_orig"], ed["base_orig"]) == (1500.0, 1520.0)
    ig = next(c for c in plano["candidatos"] if c["id"] == can["id"])
    assert ig["ignorado"] and not ig["usado"]
    # mover o teste do fundo para o reservatório raso: vira o mesmo grupo e a prioridade escolhe o canhoneado (se não ignorado)
    mv = mz.planejar(candidatos(banco), conversores(banco, ids), {"ajustes": {teste["id"]: {"zona": "ZP1"}}})
    assert len(mv["por_poco"]["1-ZZ-1-RN"]) == 1 and mv["por_poco"]["1-ZZ-1-RN"][0]["zona"] == "ZP1"
    invalido = mz.planejar(candidatos(banco), conversores(banco, ids), {"ajustes": {teste["id"]: {"topo": 1600, "base": 1500}}})
    assert [c["aviso"] for c in invalido["candidatos"] if c["id"] == teste["id"]][0].startswith("topo e base inválidos")


def test_avisos_poucos_pocos_e_sem_intervalos(banco):
    ids = [p for p, _, _ in POCOS]
    cands = candidatos(banco)
    cands["1-ZZ-6-RN"] = []                                                                      # um poço sem nenhum intervalo
    plano = mz.planejar(cands, conversores(banco, ids), {})
    assert any("Sem nenhum intervalo" in a and "1-ZZ-6-RN" in a for a in plano["avisos"])
    so_dois = {p: cands[p] for p in ("1-ZZ-1-RN", "1-ZZ-2-RN")}
    p2 = mz.planejar(so_dois, conversores(banco, ids), {})
    assert any("só 2 poço(s)" in a for a in p2["avisos"])
    sem_conv = mz.planejar({"1-ZZ-1-RN": cands["1-ZZ-1-RN"]}, {}, {})
    assert any("nenhum utilizável" in a for a in sem_conv["avisos"])


# ------------------------------------------------------------------------------------------------------- unidades do bloco
def test_unidades_topo_e_base_de_cada_reservatorio():
    esc = [{"zona": "ZP1", "topo": 1000.0, "base": 1010.0, "cota_topo": -950.0, "cota_base": -960.0},
           {"zona": "ZP2", "topo": 1500.0, "base": 1520.0, "cota_topo": -1450.0, "cota_base": -1470.0}]
    nomes = {"ZP1": "Raso", "ZP2": "Fundo"}
    u = mz.unidades_do_poco(esc, None, nomes, 1800.0, -1750.0)
    assert [x["chave"] for x in u] == ["ZP1", "ZP1_B", "ZP2", "ZP2_B"]
    assert (u[0]["topo"], u[0]["base"]) == (1000.0, 1010.0) and u[0]["nome"] == "Raso"
    assert (u[1]["topo"], u[1]["base"], u[1]["cota_topo"], u[1]["cota_base"]) == (1010.0, 1500.0, -960.0, -1450.0)     # base até o próximo
    assert u[1]["nome"] == "Base do Raso" and u[1]["base_atingida"] is True
    assert (u[3]["topo"], u[3]["base"], u[3]["cota_base"], u[3]["base_atingida"]) == (1520.0, 1800.0, -1750.0, False)  # até o fundo
    so1 = mz.unidades_do_poco(esc, ["ZP2"], nomes, 1800.0, -1750.0)
    assert [x["chave"] for x in so1] == ["ZP2", "ZP2_B"]                                          # reservatório escolhido
    assert mz.unidades_do_poco([], None, {}, 1800.0, -1750.0) == []
    sem_fundo = mz.unidades_do_poco(esc[:1], None, nomes, None, None)
    assert sem_fundo[1]["base"] == 1010.0 and sem_fundo[1]["base_atingida"] is False


# ------------------------------------------------------------------------------------------------------- bloco completo
def test_montar_bloco_de_zonas(banco):
    ids = [p for p, _, _ in POCOS]
    m = mb.montar(banco, ids, nivel="zonas", zonas={"fontes": ["canhoneado", "teste", "analise_perfil", "fluido"]})
    assert [u["chave"] for u in m["legenda"]] == ["ZP1", "ZP1_B", "ZP2", "ZP2_B"]
    s = {x["chave"]: x for x in m["superficies"]}
    assert s["ZP1"]["n_pocos"] == 6 and s["ZP2"]["n_pocos"] == 4 and s["ZP1"]["z"] and s["ZP1_B"]["z"]
    # topo do reservatório raso: canhoneado a topo_raso + 2; cota = 50 − (…); a 6,7 km a leste, ~33 m mais fundo
    cmax = s["ZP1"]["cota_max"]
    assert cmax == pytest.approx(MESA - (1000.0 + 2.0), abs=1.5)
    assert s["ZP1"]["cota_min"] == pytest.approx(cmax - 5 * 6.66, abs=2.0)
    # a base é 6 m abaixo do topo, sempre: espessura constante
    for lt, lb in zip(s["ZP1"]["z"], s["ZP1_B"]["z"]):
        for a, b in zip(lt, lb):
            if a is not None and b is not None:
                assert a - b == pytest.approx(6.0, abs=0.01)
    assert m["parametros"]["nivel"] == "zonas" and m["zonas"]["config"]["regra"] == "prioridade"
    assert [z["chave"] for z in m["zonas"]["zonas"]] == ["ZP1", "ZP2"] and m["solido"]
    cores = {u["chave"]: u["cor"] for u in m["legenda"]}
    assert cores["ZP1"] == "#2a78d6" and cores["ZP2"] == "#eb6834"                                 # cada reservatório com a sua cor
    assert m["zonas"]["candidatos"] and {"id", "poco", "fonte", "topo", "base", "zona", "usado"} <= set(m["zonas"]["candidatos"][0])
    json.dumps(m, default=float)                                                                   # o modelo precisa ser gravável


def test_montar_so_com_um_reservatorio_e_nome_proprio(banco):
    ids = [p for p, _, _ in POCOS]
    m = mb.montar(banco, ids, nivel="zonas", zonas={"ativas": ["ZP2"], "nomes": {"ZP2": "Açu fundo"}})
    assert [u["chave"] for u in m["legenda"]] == ["ZP2", "ZP2_B"]
    assert m["legenda"][0]["nome"] == "Açu fundo" and m["legenda"][1]["nome"] == "Base do Açu fundo"
    assert [z["ativa"] for z in m["zonas"]["zonas"]] == [False, True]                              # a outra continua listada
    raso = mb.montar(banco, ids, nivel="zonas", zonas={"ativas": ["ZP1"]})
    assert [u["chave"] for u in raso["legenda"]] == ["ZP1", "ZP1_B"]


def test_montar_sem_intervalos_avisa_e_nivel_antigo_continua(banco):
    ids = [p for p, _, _ in POCOS]
    with pytest.raises(mb.ErroBloco, match="Nenhum poço tem intervalo de zona produtora"):
        mb.montar(banco, ids, nivel="zonas", zonas={"fontes": ["marcado"]})              # nenhuma unidade: sem nada para desenhar
    assert "zonas" in mb.NIVEIS and "formacoes" in mb.NIVEIS


# ------------------------------------------------------------------------------------------------------- tabela do usuário
def csv_tabela(tmp_path, ref="md", utm=False, sep=";"):
    linhas = ["Poço;Topo;Base;Reservatório" + (";X;Y" if utm else "")]
    for pid, la, lo in POCOS:
        t = topo_raso(pid) + 1
        topo, base = (t, t + 12) if ref == "md" else (MESA - t, MESA - t - 12)
        extra = ""
        if utm:
            x, y = mutm.para_utm(la, lo, 24, True)
            extra = f";{float(np.ravel(x)[0]):.2f}".replace(".", ",") + f";{float(np.ravel(y)[0]):.2f}".replace(".", ",")
        linhas.append(f"{pid};{str(round(topo, 2)).replace('.', ',')};{str(round(base, 2)).replace('.', ',')};Raso{extra}")
    caminho = tmp_path / "manual.csv"
    caminho.write_text("\n".join(linhas).replace(";", sep) if sep != ";" else "\n".join(linhas), encoding="latin-1")
    return str(caminho)


def test_ler_tabela_csv_com_virgula_decimal_e_utm(banco, tmp_path):
    t = mz.ler_tabela(csv_tabela(tmp_path, utm=True), banco, utm_zona=24)
    assert len(t["linhas"]) == 6 and t["n_pocos"] == 6 and t["com_coordenadas"] and not t["avisos"]
    r = t["linhas"][0]
    assert r["poco_id"] == "1-ZZ-1-RN" and r["zona"] == "Raso" and r["ref"] == "md" and r["base"] - r["topo"] == pytest.approx(12.0)
    assert (r["lat"], r["lon"]) == pytest.approx((POCOS[0][1], POCOS[0][2]), abs=2e-5)           # UTM de volta para graus
    assert t["colunas"]["poco"] == "Poço" and t["colunas"]["x"] == "X"
    assert mz.coordenadas_da_tabela(t)["1-ZZ-2-RN"] == pytest.approx((POCOS[1][1], POCOS[1][2]), abs=2e-5)
    with pytest.raises(mz.ErroZonas, match="zona UTM"):
        mz.ler_tabela(csv_tabela(tmp_path, utm=True), banco)


def test_ler_tabela_formatos_e_erros(banco, tmp_path):
    virg_arq = tmp_path / "virgula.csv"                                        # vírgula como separador, ponto decimal
    virg_arq.write_text("poco,topo,base\n1-ZZ-1-RN,1001.5,1013.5\n1-ZZ-2-RN,1005.5,1017.5\n", encoding="utf-8")
    virg = mz.ler_tabela(str(virg_arq), banco)
    assert [(r["topo"], r["base"]) for r in virg["linhas"]] == [(1001.5, 1013.5), (1005.5, 1017.5)]
    tab = tmp_path / "t.csv"
    tab.write_text("Well\ttop\tbottom\n1-ZZ-1-RN\t1.010,5\t1.020,5\n1-ZZ-2-RN\t1100\t1000\n1-OUTRO-9-RN\t900\t910\n;;\n", encoding="utf-8")
    t = mz.ler_tabela(str(tab), banco)
    assert [(r["poco_id"], r["topo"], r["base"]) for r in t["linhas"]] == [("1-ZZ-1-RN", 1010.5, 1020.5), ("1-OUTRO-9-RN", 900.0, 910.0)]
    assert any("não é maior que o topo" in a for a in t["avisos"]) and any("não reconheceu" in a and "1-OUTRO-9-RN" in a for a in t["avisos"])
    ruim = tmp_path / "r.csv"
    ruim.write_text("a;b\n1;2\n", encoding="utf-8")
    with pytest.raises(mz.ErroZonas, match="coluna de: poco, topo, base"):
        mz.ler_tabela(str(ruim), banco)
    vazia = tmp_path / "v.csv"
    vazia.write_text("poco;topo;base\n", encoding="utf-8")
    with pytest.raises(mz.ErroZonas, match="cabeçalho e ao menos uma linha"):
        mz.ler_tabela(str(vazia), banco)
    with pytest.raises(mz.ErroZonas, match="md ou cota"):
        mz.ler_tabela(str(tab), banco, ref="tvd")


def test_tabela_em_cota_vira_profundidade_medida(banco, tmp_path):
    ids = [p for p, _, _ in POCOS]
    t = mz.ler_tabela(csv_tabela(tmp_path, ref="cota"), banco, ref="cota")
    assert all(r["base"] < r["topo"] for r in t["linhas"])
    cands = {pid: mz.coletar(banco, pid, ["tabela"], t["linhas"]) for pid in ids}
    plano = mz.planejar(cands, conversores(banco, ids), {"fontes": ["tabela"]})
    e = plano["por_poco"]["1-ZZ-1-RN"][0]
    assert e["topo"] == pytest.approx(topo_raso("1-ZZ-1-RN") + 1, abs=1.5) and e["base"] - e["topo"] == pytest.approx(12.0, abs=2.0)
    assert e["cota_topo"] == pytest.approx(MESA - e["topo"])


def test_tabela_como_fonte_no_bloco_e_comparacao_com_o_siapp(banco, tmp_path):
    ids = [p for p, _, _ in POCOS]
    t = mz.ler_tabela(csv_tabela(tmp_path, utm=True), banco, utm_zona=24)
    m = mb.montar(banco, ids, nivel="zonas", zonas={"fontes": ["tabela"], "tabela": t, "usar_coordenadas_da_tabela": True})
    s = {x["chave"]: x for x in m["superficies"]}
    assert [u["chave"] for u in m["legenda"]] == ["ZP1", "ZP1_B"] and s["ZP1"]["n_pocos"] == 6
    assert s["ZP1"]["cota_max"] == pytest.approx(MESA - (1000.0 + 1.0), abs=1.5)               # a tabela: topo_raso + 1
    assert m["zonas"]["com_tabela"] and m["zonas"]["usar_coordenadas_da_tabela"]
    # comparação: o SIAPP (sem a tabela) escolhe o canhoneado (+2…+8); a tabela diz +1…+13
    plano = mz.planejar(candidatos(banco), conversores(banco, ids), {})
    cmp = mz.comparar(plano, t)
    r = next(x for x in cmp if x["poco_id"] == "1-ZZ-1-RN")
    assert r["situacao"] == "comparado" and r["zona_siapp"] == "ZP1"
    assert (r["dif_topo"], r["dif_base"]) == pytest.approx((1.0, -5.0), abs=0.05)               # SIAPP − tabela, em metros
    assert len(cmp) == 6 and all(x["situacao"] == "comparado" for x in cmp)
    fora = mz.comparar({"por_poco": {}, "zonas": []}, t)
    assert all(x["situacao"] == "o SIAPP não achou intervalo neste poço" for x in fora)


def test_tabela_guardada_no_projeto(banco, tmp_path):
    t = mz.ler_tabela(csv_tabela(tmp_path), banco)
    assert mz.tabela_guardada(str(tmp_path / "proj")) is None
    mz.guardar_tabela(str(tmp_path / "proj"), t, "manual.csv")
    lida = mz.tabela_guardada(str(tmp_path / "proj"))
    assert lida["origem"] == "manual.csv" and len(lida["linhas"]) == 6
    assert mz.apagar_tabela(str(tmp_path / "proj")) and mz.tabela_guardada(str(tmp_path / "proj")) is None
    assert mz.apagar_tabela(str(tmp_path / "proj")) is False


# ------------------------------------------------------------------------------------------------------- saídas do bloco
def test_saidas_do_bloco_aceitam_o_modelo_de_zonas(banco, tmp_path):
    """Mapas (topo, base e espessura de cada reservatório), CSV, validação cruzada, volumetria, ECLIPSE e modelo 3D."""
    import os

    from motor import bloco_eclipse as mbe
    from motor import bloco_glb as mbg
    from motor import bloco_mapas as mbm
    from motor import bloco_validacao as mbv
    from motor import bloco_volumetria as mbvol
    ids = [p for p, _, _ in POCOS]
    m = mb.montar(banco, ids, nivel="zonas", zonas={"fontes": ["canhoneado", "teste", "analise_perfil", "fluido"]})
    mbm.exportar(m, str(tmp_path / "mapas"), "bloco_z")
    arqs = {f for _, _, fs in os.walk(tmp_path / "mapas") for f in fs}
    # topo e base de cada reservatório (a "base" é o topo da unidade ZPn_B) e a espessura (isópaca) de cada um
    assert {"topo_zp1.tif", "topo_zp1_b.tif", "topo_zp2.tif", "topo_zp2_b.tif", "isopaca_zp1.tif", "isopaca_zp2.tif",
            "bloco_z_mapas_xyz.csv"} <= arqs
    csvs = mb.exportar_csv(m, str(tmp_path / "csv"), "bloco_z")
    assert csvs and all(os.path.getsize(c) > 0 for c in csvs)
    topos = open([c for c in csvs if c.endswith("_topos.csv")][0], encoding="utf-8").read()
    assert "Reservatório 1" in topos and "Base do Reservatório 1" in topos and "Reservatório 2" in topos
    v = mbv.validar(m)
    assert v and ("ZP1" in json.dumps(v, default=float) or "Reservat" in json.dumps(v, default=float))
    vol = mbvol.calcular(m)
    assert vol is not None
    eclipse = mbe.exportar(m, str(tmp_path / "ecl"), "bloco_z")
    assert eclipse
    glb = mbg.exportar(m, str(tmp_path / "bloco.glb"))
    assert glb["bytes"] > 0 and os.path.getsize(glb["arquivo"]) == glb["bytes"]
