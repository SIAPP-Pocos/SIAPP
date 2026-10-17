"""Validação cruzada (deixar um poço de fora) e prognóstico num ponto. Poços sintéticos."""
import math

import numpy as np
import pytest

from motor import bloco as mb
from motor import bloco_figura as mbf
from motor import bloco_solido as mbs
from motor import bloco_validacao as mbv
from test_bloco_solido import IDS, _pos, banco  # noqa: F401  (banco é fixture)


def test_tirar_um_ponto_e_igual_a_refazer_a_triangulacao():
    rng = np.random.default_rng(7)
    for rep in range(8):
        n = int(rng.integers(6, 40))
        pts = rng.uniform(0, 10, (n, 2))
        pts[1] = pts[0]                                   # dois poços no mesmo ponto (pad)
        val = rng.normal(0, 50, n)
        obs = [(pts[i, 0], pts[i, 1], val[i], f"P{i}") for i in range(n)]
        f = mbv.Interpolador(obs)
        for i in range(n):
            g = mbv.Interpolador([o for o in obs if o[3] != f"P{i}"])
            for q in [pts[i]] + list(rng.uniform(-2, 12, (3, 2))):
                a, b = f.valor(q[0], q[1], f"P{i}"), g.valor(q[0], q[1])
                assert a[0] == pytest.approx(b[0], abs=1e-6) and a[1] == b[1] and a[2] == pytest.approx(b[2])


def test_ponto_e_grade_seguem_as_mesmas_regras(banco):
    m = mb.montar(banco, IDS)
    s, g = m["solido"], m["grade"]
    emp = mbv.Empilhamento(m)
    lims = [np.array(z) for z in s["limites"]]
    com_cob = s["camadas"][0]["chave"] == mbs.CHAVE_COBERTURA
    for j, i in [(3, 4), (10, 20), (g["ny"] // 2, g["nx"] // 2), (g["ny"] - 4, g["nx"] - 6)]:
        x, y = g["x0"] + i * g["passo"], g["y0"] + j * g["passo"]
        L = emp.limites(x, y)
        bordas = ([L["terreno"]] if com_cob else []) + L["lim"]
        for k, v in enumerate(bordas):
            assert v == pytest.approx(lims[k][j, i], abs=0.15)


def test_validacao_cruzada(banco):
    m = mb.montar(banco, IDS)
    v = mbv.validar(m)
    assert v["n_pocos"] == 5 and v["n_comparacoes"] == len(v["linhas"])
    por = {(l["poco"], l["chave"]): l for l in v["linhas"]}
    # poço do meio: Jandaíra plana e Açu num plano — a interpolação acerta, nos dois modos
    for ch in ("JANDAI", "ACU"):
        l = por[("1-AA-5-RN", ch)]
        assert l["interpolado"] is True and abs(l["erro_fechado"]) < 1.0 and abs(l["erro_superficie"]) < 1.0
        assert l["dist_km"] == pytest.approx(math.hypot(2.2, 2.2), rel=0.1)
    # canto: sem ele, o ponto fica fora do contorno dos outros — extrapolado; superfícies não preveem
    canto = por[("1-AA-4-RN", "ACU")]
    assert canto["interpolado"] is False and canto["superficie"] is None and canto["fechado"] is not None
    acu = next(u for u in v["unidades"] if u["chave"] == "ACU")
    assert acu["n"] == 5 and acu["fechado"]["n"] == 5 and acu["superficie"]["n_fora"] == 4
    assert {"n", "vies", "mediana", "p68", "reqm", "max", "max_poco"} <= set(acu["fechado"])
    assert sum(f["n"] for f in v["faixas"]) == v["n_comparacoes"]
    # espessura medida (com zeros onde a unidade falta) comparada com a prevista
    assert any(l["esp_obs"] == 0 for l in v["linhas"] if l["chave"] == "ALAGAM") or \
        next(u for u in v["unidades"] if u["chave"] == "ALAGAM")["espessura"]["n"] > 0
    assert len(mbv.linhas_csv(v)) == len(v["linhas"]) and len(mbv.linhas_csv(v)[0]) == len(mbv.COLUNAS_CSV)


def test_figura_da_validacao(banco, tmp_path):
    v = mbv.validar(mb.montar(banco, IDS))
    svg = mbv.figura(v, titulo="Validação", autor="Fulano", data="17/10/2026", versao="0.21.0")
    assert "(a)" in svg and "(b)" in svg and "(c)" in svg and ("JANDAI" in svg or "Jandaíra" in svg)
    assert "68% dos erros" in svg and "<pattern" not in svg and "1:1" in svg
    saida = mbf.exportar(svg, str(tmp_path / "v.pdf"), "pdf")
    assert open(saida, "rb").read(4) == b"%PDF"


def test_poucos_pocos(tmp_path):
    from motor.banco import Banco
    from test_secao import poco
    b = Banco(str(tmp_path / "p.sqlite"))
    for k, (la, lo) in enumerate([(-5.0, -37.0), (-5.0, -36.97), (-5.03, -36.985)]):
        poco(b, f"1-BB-{k}-RN", la, lo, 60.0, [("F", "JANDAI", 5, 200)], prof_final=300)
    with pytest.raises(mbv.ErroValidacao):
        mbv.validar(mb.montar(b, [f"1-BB-{k}-RN" for k in range(3)]))


def test_prognostico(banco):
    m = mb.montar(banco, IDS)
    x, y = _pos(m, "1-AA-5-RN")
    p = mbv.prognostico(m, x, y)
    assert [c["chave"] for c in p["camadas"]] == [c["chave"] for c in m["solido"]["camadas"]]
    cam = {c["chave"]: c for c in p["camadas"]}
    leste = next(q for q in m["pocos"] if q["id"] == "1-AA-5-RN")["lon"] + 37.0
    assert cam["ACU"]["topo"] == pytest.approx(50 - (300 + 10 * leste * 111.0), abs=1.0)
    assert cam["JANDAI"]["prof_topo"] == pytest.approx(45 - 30, abs=1.0)        # terreno 45, topo a cota 30
    assert cam["JANDAI"]["interpolado"] and p["dentro_bloco"] and p["proximos"][0]["poco"] == "1-AA-5-RN"
    assert cam["JANDAI"]["incerteza_m"] is None and any("Validar" in a for a in p["avisos"])
    soma = sum(c["espessura"] for c in p["camadas"])
    assert soma == pytest.approx(p["terreno"] - p["base"], abs=0.5)               # a coluna fecha
    v = mbv.validar(m)
    p2 = mbv.prognostico(m, x, y, v)
    assert p2["camadas"][1]["incerteza_m"] is not None and "68%" in p2["camadas"][1]["incerteza_fonte"]
    g = m["grade"]
    with pytest.raises(mbv.ErroValidacao):
        mbv.prognostico(m, g["x0"] - 50, g["y0"])
    # com margem, o canto da grade fica fora do contorno do bloco
    mm = mb.montar(banco, IDS, margem_km=1.0)
    gm = mm["grade"]
    canto = mbv.prognostico(mm, gm["x0"] + 0.01, gm["y0"] + 0.01)
    assert not canto["dentro_bloco"] and any("fora do contorno" in a for a in canto["avisos"])
    assert not any(c["interpolado"] for c in canto["camadas"])


def test_incerteza_cai_para_faixa_ou_geral():
    val = {"por_unidade_faixa": {"A": [{"n": 2, "p68": 5.0}] + [{"n": 0, "p68": None}] * 4},
           "faixas": [{"n_fechado": 9, "p68_fechado": 12.0}] + [{"n_fechado": 0, "p68_fechado": None}] * 4,
           "unidades": [{"chave": "A", "fechado": {"n": 2, "p68": 5.0}}], "global": {"fechado": {"n": 9, "p68": 12.0}}}
    assert mbv.incerteza(val, "A", 0.5)[0] == 12.0                        # unidade com poucos: a faixa inteira
    assert mbv.incerteza(val, "A", 3.0)[0] == 12.0                        # faixa vazia: o geral
    assert mbv.incerteza(None, "A", 1.0) == (None, "")
