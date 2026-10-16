"""Seção estratigráfica a partir dos topos do AGP (motor/secao.py).

Poços e topos inventados, gravados direto nas tabelas que o leitor do AGP preenche.
"""
import json
import os
import re

import pytest

from motor import agp as magp
from motor import secao as ms
from motor.banco import Banco

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SLOTS = ms.ler_slots(os.path.join(RAIZ, "recursos", "estratigrafia.json"))
NOMES = magp.ler_estratigrafia(os.path.join(RAIZ, "recursos", "estratigrafia.json"))


def poco(b, pid, lat, lon, mesa, unidades, prof_final=None, desviado_km=0.0, litologia=()):
    """unidades: [(nivel, sigla, topo, base)] em profundidade medida. desviado_km
    simula poço desviado: a cota do AGP fica 10 m acima de mesa − prof por 100 m."""
    with b.conexao() as c:
        c.execute("INSERT INTO pocos (id, lat, lon, mesa_rotativa, campo, prof_sondador) VALUES (?, ?, ?, ?, ?, ?)",
                  (pid, lat, lon, mesa, "CAMPO TESTE", prof_final))

    def cota(p):
        return None if p is None else mesa - p + (p / 100 * 10 if desviado_km else 0)
    caminho = f"/POCO/Categoria-1/{pid}/AGP/{pid}_agp.txt"
    dados = {"formato": "novo", "cabecalho": {"poco_id": pid, "poco_agp": pid, "mesa_rotativa": mesa,
                                              "prof_final": prof_final},
             "unidades": [], "litologia": [{"topo": a, "base": z, "rocha": r, "descricao": ""} for a, z, r in litologia]}
    with b.conexao() as c:
        c.execute("""INSERT INTO agp (bacia, caminho, poco_caminho, poco_pasta, poco_id, poco_agp, confere, tamanho,
                     arquivo_local, lido_em, dados, erro, leitor) VALUES ('Potiguar', ?, '', ?, ?, ?, 1, 100, '', '', ?, NULL, 2)""",
                  (caminho, pid, pid, pid, json.dumps(dados)))
        for k, (nivel, sigla, topo, base) in enumerate(unidades):
            c.execute("""INSERT INTO agp_unidades (bacia, caminho, poco_id, ordem, tip, ql, nivel, sigla, codigo, nome,
                         topo, cota_topo, desc_topo, base, cota_base, desc_base, metodo, fonte, data)
                         VALUES ('Potiguar', ?, ?, ?, 'L', 'B', ?, ?, '', ?, ?, ?, '', ?, ?, '', 'PERFIL', 'UN-TESTE', '01/01/2005')""",
                      (caminho, pid, k, nivel, sigla, sigla, topo, cota(topo), base, cota(base)))


@pytest.fixture
def banco(tmp_path):
    b = Banco(str(tmp_path / "p.sqlite"))
    # três poços numa linha oeste→leste (~5,5 km entre eles), um fora da linha
    poco(b, "1-OES-1-RN", -5.30, -36.80, 50.0, [("F", "JANDAI", 10, 300), ("F", "ACU", 300, 700),
                                                 ("F", "ALAGAM", 700, 900), ("", "EMBASA", 900, None)],
         prof_final=950, litologia=[(10, 300, "CALCARENITO"), (300, 700, "ARENITO")])
    poco(b, "1-MEI-1-RN", -5.30, -36.75, 40.0, [("F", "JANDAI", 8, 320), ("F", "ACU", 320, 760),
                                                 ("M", "ACU 4", 320, 400), ("F", "PENDEN", 760, None)],
         prof_final=1200)
    poco(b, "1-LES-1-RN", -5.30, -36.70, 30.0, [("F", "JANDAI", 5, 330), ("F", "ACU", 330, 900)],
         prof_final=1000)
    poco(b, "1-LON-1-RN", -5.40, -36.75, 30.0, [("F", "ACU", 300, 600)], prof_final=700)   # 11 km ao sul
    return b


def test_ordenar_linha_pca_lista():
    coords = [{"id": "B", "lat": -5.30, "lon": -36.75}, {"id": "C", "lat": -5.30, "lon": -36.70},
              {"id": "A", "lat": -5.30, "lon": -36.80}]
    lin = ms.ordenar(coords, "linha")             # do 1º (B) ao último (A): para oeste
    assert lin["ordem"] == ["C", "B", "A"] and lin["pontas"] == ("E", "W")
    pca = ms.ordenar(coords, "pca")               # direção principal, de oeste para leste
    assert pca["ordem"] == ["A", "B", "C"] and pca["pontas"] == ("W", "E")
    assert pca["x_km"]["C"] == pytest.approx(11.07, abs=0.05)
    lista = ms.ordenar(coords, "lista")
    assert lista["ordem"] == ["B", "C", "A"] and lista["x_km"]["A"] == pytest.approx(16.6, abs=0.1)


def test_corredor(banco):
    r = ms.corredor(banco, "1-OES-1-RN", "1-LES-1-RN", largura_km=2.0)
    assert [p["id"] for p in r["pocos"]] == ["1-OES-1-RN", "1-MEI-1-RN", "1-LES-1-RN"]
    assert r["comprimento_km"] == pytest.approx(11.07, abs=0.05)
    r = ms.corredor(banco, "1-OES-1-RN", "1-LES-1-RN", largura_km=12)
    assert "1-LON-1-RN" in [p["id"] for p in r["pocos"]]
    with pytest.raises(ms.ErroSecao):
        ms.corredor(banco, "1-OES-1-RN", "1-NAO-1-RN")


def test_montar_em_cota(banco):
    m = ms.montar(banco, ["1-LES-1-RN", "1-OES-1-RN", "1-MEI-1-RN"], ordem="pca", slots=SLOTS, nomes=NOMES)
    assert [p["id"] for p in m["pocos"]] == ["1-OES-1-RN", "1-MEI-1-RN", "1-LES-1-RN"]
    oes = m["pocos"][0]
    acu = next(u for u in oes["unidades"] if u["chave"] == "ACU")
    assert (acu["nome"], acu["cota_topo"], acu["cota_base"], acu["y_topo"]) == ("Formação Açu", -250.0, -650.0, -250.0)
    emb = oes["unidades"][-1]                      # sem base: vai até o fundo do poço
    assert emb["nome"] == "Embasamento" and emb["cota_base"] == -900.0 and not emb["base_atingida"]
    assert oes["litologia"][1] == {"cota_topo": -250.0, "cota_base": -650.0, "rocha": "ARENITO", "descricao": "",
                                   "topo": 300, "base": 700, "y_topo": -250.0, "y_base": -650.0}
    # só formações: o membro Açu 4 não entra
    assert "ACU 4" not in [u["chave"] for p in m["pocos"] for u in p["unidades"]]
    # legenda na ordem do empilhamento, cor fixa da unidade
    assert [u["chave"] for u in m["legenda"]] == ["JANDAI", "ACU", "ALAGAM", "PENDEN", "EMBASA"]
    assert next(u for u in m["legenda"] if u["chave"] == "JANDAI")["cor"] == ms.CORES[SLOTS["JANDAI"]]
    assert m["pontas"] == ["W", "E"] and m["comprimento_km"] == pytest.approx(11.07, abs=0.05)
    # topo do Açu: −280 (MEI) → −300 (LES): 20 m, abaixo do limiar
    assert not m["saltos"]
    m2 = ms.montar(banco, ["1-OES-1-RN", "1-MEI-1-RN", "1-LES-1-RN"], ordem="linha", limiar_salto_m=15)
    assert {(s["de"], s["para"]) for s in m2["saltos"]} >= {("1-MEI-1-RN", "1-LES-1-RN")}
    assert any("confira" in a for a in m2["avisos"])


def test_montar_nivelado_e_membros(banco):
    m = ms.montar(banco, ["1-OES-1-RN", "1-MEI-1-RN", "1-LES-1-RN", "1-LON-1-RN"], ordem="lista", eixo="nivelado",
                  datum="JANDAI", nomes=NOMES)
    assert [p["id"] for p in m["pocos"]] == ["1-OES-1-RN", "1-MEI-1-RN", "1-LES-1-RN"]    # LON não tem Jandaíra
    assert any("1-LON-1-RN" in a and "datum" in a for a in m["avisos"])
    assert m["datum_nome"] == "Formação Jandaíra"
    for p in m["pocos"]:
        assert next(u for u in p["unidades"] if u["chave"] == "JANDAI")["y_topo"] == 0.0
    mem = ms.montar(banco, ["1-OES-1-RN", "1-MEI-1-RN"], nivel="membros", nomes=NOMES)
    assert [u["nome"] for p in mem["pocos"] for u in p["unidades"]] == ["Membro Açu 4"]
    with pytest.raises(ms.ErroSecao):
        ms.montar(banco, ["1-OES-1-RN"])


def test_gr_em_cota_vertical_e_desviado(banco):
    poco(banco, "7-DES-1D-RN", -5.30, -36.72, 100.0, [("F", "JANDAI", 100, 400), ("F", "ACU", 400, 800)],
         prof_final=900, desviado_km=1)

    def gr_de(pid):
        return {"arquivo": f"bruto/{pid}.las", "mnemonico": "GR", "prof": [100.0, 400.0, 800.0, 900.0],
                "valores": [50.0, None, 80.0, 90.0]}
    m = ms.montar(banco, ["1-LES-1-RN", "7-DES-1D-RN"], ordem="lista", gr_de=gr_de)
    les, des = m["pocos"]
    assert les["gr"]["cota"] == [-70.0, -370.0, -770.0, -870.0] and les["gr"]["valores"][1] is None
    assert not les["desviado"] and des["desviado"]
    # desviado: pelos pontos do AGP (cota = mesa − prof + 10 % da prof)
    assert des["gr"]["cota"][:3] == [10.0, -260.0, -620.0]
    assert des["gr"]["cota"][3] == pytest.approx(-710.0)      # prolonga a última inclinação
    assert any("desviado" in a for a in m["avisos"])

    def falha(pid):
        raise ValueError("arquivo corrompido")
    m = ms.montar(banco, ["1-LES-1-RN", "1-OES-1-RN"], gr_de=falha)
    assert all(p["gr"] is None for p in m["pocos"]) and any("GR não lido" in a for a in m["avisos"])


def test_desenhar_registrar_exportar(banco, tmp_path):
    m = ms.montar(banco, ["1-OES-1-RN", "1-MEI-1-RN", "1-LES-1-RN"], slots=SLOTS, nomes=NOMES, gr_de=lambda p: None)
    svg = ms.desenhar(m, "Seção <teste> & cia", estilo="moderno")
    assert svg.startswith("<svg") and "Seção &lt;teste&gt; &amp; cia" in svg
    for txt in ("1-OES-1-RN", "Formação Açu", "Cota (m)", "Calha:", "AGP da ANP"):
        assert txt in svg
    pasta = str(tmp_path / "execucoes")
    ident, caminho = ms.registrar(pasta, m, svg, autor="Teste")
    assert ms.execucoes(pasta)[0]["pocos"] == ["1-OES-1-RN", "1-MEI-1-RN", "1-LES-1-RN"]
    with open(caminho, encoding="utf-8") as f:
        reg = json.load(f)
    assert reg["tipo"] == "secao_estratigrafica" and reg["autor"] == "Teste" and reg["parametros"]["eixo"] == "cota"
    for fmt in ("svg", "png", "pdf", "csv"):
        saida = str(tmp_path / "exp" / f"{ident}.{fmt}")
        ms.exportar(pasta, ident, saida, fmt)
        assert os.path.getsize(saida) > 200
    with open(str(tmp_path / "exp" / f"{ident}.csv"), encoding="utf-8-sig") as f:
        linhas = f.read().splitlines()
    assert linhas[0].startswith("poco;distancia_km") and any("1-MEI-1-RN;" in x and ";Formação Açu;" in x for x in linhas)
    with open(str(tmp_path / "exp" / f"{ident}.png"), "rb") as f:
        assert f.read(4) == b"\x89PNG"


def test_unidade_lida_por_leitor_antigo():
    u = {"tip": "L", "nivel": "", "sigla": "C PONTUB", "codigo": "325042", "nome": "C PONTUB"}
    n = ms._normalizar(u, NOMES)
    assert (n["nivel"], n["sigla"], n["nome"]) == ("C", "PONTUB", "Ponta do Tubarão")
    assert ms._rotulo_unidade(n) == "Camadas Ponta do Tubarão"
    n = ms._normalizar({"tip": "L", "nivel": "", "sigla": "XPTO", "codigo": "", "nome": "XPTO"}, NOMES)
    assert n["nome"] == "XPTO"


def test_estilo_classico(banco):
    from motor import secao_classica as cl
    m = ms.montar(banco, ["1-OES-1-RN", "1-MEI-1-RN", "1-LES-1-RN"], slots=SLOTS, nomes=NOMES, eixo="nivelado",
                  datum="ACU")
    assert m["parametros"]["estilo"] == "classico"
    svg = ms.desenhar(m, "Teste", autor="Fulana de Tal", data="16/10/2026")
    for txt in ("SEÇÃO ESTRATIGRÁFICA A–A′", "A′", "Fm. Açu", "DATUM: topo da Formação Açu", "Localização",
                "Litologia (calha)", "Calcário", "Arenito", "Elaboração: Fulana de Tal · 16/10/2026",
                "Sem descrição de calha", "Topo de unidade (AGP)"):
        assert txt in svg, txt
    assert "<pattern" not in svg and "clip-path" not in svg        # o PyMuPDF não entende
    # a mesma seção no outro estilo
    assert "Calha:" in ms.desenhar(m, estilo="moderno")


def test_padroes_litologicos():
    from motor import secao_classica as cl
    assert cl.litologia("CALCARENITO")[0] == "calcario"         # não é arenito
    assert cl.litologia("ARENITO")[0] == "arenito" and cl.litologia("FOLHELHO")[0] == "folhelho"
    assert cl.litologia("GNAISSE")[0] == "embasamento" and cl.litologia("XYZ")[0] == "outra"
    tr, pt = cl.marcas("pontos", 10, 10, 26, 40)
    assert pt and not tr
    for pat in ("tracos", "tijolo", "grade", "cruzes", "vees", "seixos", "marga", "silte", "tijolo_obliquo", "sem"):
        tr, _ = cl.marcas(pat, 10, 10, 26, 40)
        assert tr, pat
        # nada começa fora do retângulo
        for x, y in re.findall(r"M(-?[\d.]+) (-?[\d.]+)", tr):
            assert 10 <= float(x) <= 36 and 10 <= float(y) <= 50, (pat, x, y)
    assert cl.marcas("pontos", 0, 0, 26, 1.0) == ("", "")       # camada fina: só a cor
    assert cl.simbolo_poco(0, 0, "seco").count("<line") == 4 and cl.simbolo_poco(0, 0, "gas").count("<line") == 8
    assert ms._classe_poco("PRODUTOR DE OLEO E GAS") == "oleo_gas" and ms._classe_poco("SECO") == "seco"
