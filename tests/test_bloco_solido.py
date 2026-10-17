"""Bloco fechado: malha do contorno, empilhamento por espessuras (nunca cruza, respeita os
poços), base plana, terreno, extrapolação, perfil da seção A–A′ e a figura. Poços
sintéticos (tests/test_secao.poco), nenhum arquivo do REATE."""
import numpy as np
import pytest

from motor import bloco as mb
from motor import bloco_figura as mbf
from motor import bloco_solido as mbs
from motor.banco import Banco
from test_secao import poco

IDS = ["1-AA-1-RN", "1-AA-2-RN", "1-AA-3-RN", "1-AA-4-RN", "1-AA-5-RN"]


# ============================================================== malha
def test_malha_cobre_o_poligono_com_borda_reta():
    g = {"x0": 0.0, "y0": 0.0, "passo": 1.0, "nx": 11, "ny": 11}
    pol = mb.contorno_convexo([(0.5, 0.5), (9.3, 1.0), (8.0, 9.7), (1.0, 8.0)])
    m = mbs.malha_contorno(g, pol)
    # soma das áreas = área do polígono: nada sobrando, nada sobreposto
    assert mbs._areas(m).sum() == pytest.approx(mb.area_shoelace(pol))
    b = mbs.borda(g, pol)
    assert np.allclose(b[0], b[-1])
    # os pontos da borda são vértices da malha (as paredes casam com o topo)
    vert = {(round(x, 6), round(y, 6)) for x, y in m["pts"]}
    assert all((round(x, 6), round(y, 6)) in vert for x, y in b)
    # corte: o mesmo polígono menos um semiplano
    meio = mbs.malha_contorno(g, pol, extra=[(1.0, 0.0, -5.0)])          # x ≥ 5
    assert mbs._areas(meio).sum() < mbs._areas(m).sum() and meio["pts"][:, 0].min() >= 5 - 1e-9


def test_bilinear_exata_num_plano_e_borda_continua():
    g = {"x0": 0.0, "y0": 0.0, "passo": 0.5, "nx": 21, "ny": 21}
    gx, gy = np.meshgrid(np.arange(21) * 0.5, np.arange(21) * 0.5)
    z = 10 + 2 * gx - 3 * gy
    assert mbs.bilinear(z, g, [1.23, 7.7], [4.4, 0.1]) == pytest.approx([10 + 2.46 - 13.2, 10 + 15.4 - 0.3])
    # fora do contorno dos dados: o valor da borda (contínuo), não um degrau
    pts = np.array([[2, 2], [8, 2], [8, 8], [2, 8], [5, 5]], float)
    val = 100 + 3 * pts[:, 0]
    zz, ctl = mbs.interpolar_grade(pts, val, g)
    assert zz[8, 0] == pytest.approx(106) and zz[8, 20] == pytest.approx(124)       # x=0 → x=2; x=10 → x=8
    assert ctl[10, 10] and not ctl[0, 0]
    assert np.abs(np.diff(zz, axis=1)).max() <= 3 * 0.5 + 1e-9                     # sem salto


# ============================================================== bloco fechado
@pytest.fixture
def banco(tmp_path):
    """5 poços num quadrado de ~4 km; mesa 50 m. Jandaíra a 20 m (cobertura de 20 m);
    Jandaíra engrossa para leste (10 m/km), Açu termina a 700 m; Alagamar só em 3 poços;
    Pendência (com base) só em 2 — embaixo dela, a camada "abaixo da última unidade"."""
    b = Banco(str(tmp_path / "projeto.sqlite"))
    for pid, la, lo in [("1-AA-1-RN", -5.00, -37.00), ("1-AA-2-RN", -5.00, -36.96), ("1-AA-3-RN", -5.04, -37.00),
                        ("1-AA-4-RN", -5.04, -36.96), ("1-AA-5-RN", -5.02, -36.98)]:
        leste = (lo + 37.00) * 111.0
        un = [("F", "JANDAI", 20, 300 + 10 * leste), ("F", "ACU", 300 + 10 * leste, 700)]
        if pid in ("1-AA-1-RN", "1-AA-2-RN", "1-AA-3-RN"):
            un.append(("F", "ALAGAM", 700, 900))
        if pid in ("1-AA-1-RN", "1-AA-4-RN"):
            un.append(("F", "PENDEN", 900, 1100))
        poco(b, pid, la, lo, 50.0, un, prof_final=1200)
    with b.conexao() as c:
        c.execute("UPDATE pocos SET cota_altimetrica = 45.0")
    return b


def _pos(m, pid):
    p = next(p for p in m["pocos"] if p["id"] == pid)
    return p["x"], p["y"]


def test_bloco_fechado_empilha_sem_cruzar_e_respeita_os_pocos(banco):
    m = mb.montar(banco, IDS, slots={"JANDAI": 1, "ACU": 2})
    s = m["solido"]
    assert s["ok"], s["avisos"]
    chaves = [c["chave"] for c in s["camadas"]]
    assert chaves == ["_cobertura", "JANDAI", "ACU", "ALAGAM", "PENDEN", "_abaixo"]
    lims = [np.array(z) for z in s["limites"]]
    assert len(lims) == len(chaves) + 1
    for a, b in zip(lims, lims[1:]):
        assert (a >= b - 1e-6).all()                       # nunca cruzam
    assert lims[0].max() == pytest.approx(45.0, abs=0.2)   # terreno = cota altimétrica
    assert (lims[-1] == s["base"]).all() and s["base"] < -1150 + 50   # base plana abaixo do mais fundo
    g = m["grade"]
    for pid in IDS:
        x, y = _pos(m, pid)
        leste = next(p for p in m["pocos"] if p["id"] == pid)["lon"] + 37.0
        topo_acu = 50 - (300 + 10 * leste * 111.0)
        # topo do Açu (limite 2) no poço = o do AGP (a interpolação passa pelo dado)
        assert float(mbs.bilinear(lims[2], g, x, y)) == pytest.approx(topo_acu, abs=1.0)
        assert float(mbs.bilinear(lims[1], g, x, y)) == pytest.approx(30.0, abs=1.0)   # topo da Jandaíra
    # Alagamar ausente nos poços 4 e 5: espessura zero lá (passaram pela posição dela)
    x4, y4 = _pos(m, "1-AA-4-RN")
    assert float(mbs.bilinear(lims[3] - lims[4], g, x4, y4)) == pytest.approx(0, abs=1.0)
    al = next(c for c in s["camadas"] if c["chave"] == "ALAGAM")
    assert 0 < al["area_km2"] <= s["area_km2"] and al["volume_km3"] > 0
    assert s["area_km2"] == pytest.approx(m["area_km2"], rel=1e-6)          # sem margem: o contorno dos poços
    fr = {c["chave"]: c["fracao_extrapolada"] for c in s["camadas"]}
    assert fr["JANDAI"] < 0.05 and fr["ACU"] < 0.05
    assert fr["PENDEN"] == 1.0                             # só 2 poços com a espessura: toda extrapolada


def test_margem_extrapola_e_base_pedida(banco):
    m = mb.montar(banco, IDS, margem_km=1.0, base_cota=-1500)
    s = m["solido"]
    assert s["base"] == -1500 and s["area_km2"] > m["area_km2"] * 1.5
    ja = next(c for c in s["camadas"] if c["chave"] == "JANDAI")
    assert ja["fracao_extrapolada"] > 0.2 and ja["controle"]
    acima = mb.montar(banco, IDS, base_cota=-500)["solido"]
    assert any("acima do ponto mais fundo" in a for a in acima["avisos"])
    assert np.array(acima["limites"]).min() >= -500


def test_ordem_trocada_vira_espessura_zero_com_aviso(banco):
    # num poço, o Açu vem acima da Jandaíra: espessura negativa → zero, com aviso
    poco(banco, "1-AA-6-RN", -5.03, -36.99, 50.0, [("F", "ACU", 20, 100), ("F", "JANDAI", 100, 400),
                                                    ("F", "ALAGAM", 700, 900)], prof_final=1000)
    s = mb.montar(banco, IDS + ["1-AA-6-RN"])["solido"]
    assert s["ok"] and any("Ordem das unidades" in a and "1-AA-6-RN" in a for a in s["avisos"])
    lims = [np.array(z) for z in s["limites"]]
    assert all((a >= b - 1e-6).all() for a, b in zip(lims, lims[1:]))


def test_sem_base_atingida_vai_ate_a_base_e_terreno_pela_mesa(tmp_path):
    b = Banco(str(tmp_path / "p.sqlite"))
    for pid, la, lo in [("1-BB-1-RN", -5.0, -37.0), ("1-BB-2-RN", -5.0, -36.97), ("1-BB-3-RN", -5.03, -36.985)]:
        poco(b, pid, la, lo, 60.0, [("F", "JANDAI", 5, 200), ("", "EMBASA", 200, None)], prof_final=300)
    s = mb.montar(b, ["1-BB-1-RN", "1-BB-2-RN", "1-BB-3-RN"])["solido"]
    assert [c["chave"] for c in s["camadas"]] == ["JANDAI", "EMBASA"]       # sem cobertura (< 5 m), sem "abaixo"
    assert any("EMBASA vai até a base" in a for a in s["avisos"])
    assert any("mesa rotativa" in a for a in s["avisos"])                   # sem cota altimétrica


def test_colineares_sem_bloco_fechado(tmp_path):
    b = Banco(str(tmp_path / "p.sqlite"))
    for k in range(4):
        poco(b, f"1-CC-{k}-RN", -5.0, -37.0 + 0.02 * k, 50.0, [("F", "JANDAI", 10, 300)], prof_final=400)
    m = mb.montar(b, [f"1-CC-{k}-RN" for k in range(4)])
    assert m["solido"]["ok"] is False and "alinhados" in m["solido"]["avisos"][0]


def test_perfil_e_prolongar(banco):
    m = mb.montar(banco, IDS)
    s, g = m["solido"], m["grade"]
    a, b = _pos(m, "1-AA-1-RN"), _pos(m, "1-AA-4-RN")
    linha = mbs.prolongar([a, b], s["contorno"])
    assert len(linha) == 4
    planos = mbs.semiplanos_do_poligono(s["contorno"])
    for q in (linha[0], linha[-1]):                       # as pontas estão na borda
        assert min(pa * q[0] + pb * q[1] + pc for pa, pb, pc in planos) == pytest.approx(0, abs=1e-6)
    pf = mbs.perfil(s, g, linha)
    assert len(pf["xy"]) > 5 and len(pf["limites"]) == len(s["limites"])
    assert all(x >= y - 1e-6 for z1, z2 in zip(pf["limites"], pf["limites"][1:]) for x, y in zip(z1, z2))
    assert mbs.perfil(s, g, [[-100, -100], [-90, -100]])["xy"] == []      # fora do bloco


def test_figura_do_bloco_fechado(banco, tmp_path):
    m = mb.montar(banco, IDS)
    for kw in ({}, {"corte": {"quadrante": "NE", "fx": 0.4, "fy": 0.6}}, {"afastar": 0.5},
               {"parede": ["1-AA-1-RN", "1-AA-5-RN", "1-AA-4-RN"]}):
        svg = mbf.desenhar(m, modo="fechado", exagero=5, titulo="Bloco fechado", **kw)
        assert "Bloco fechado (AGP)" in svg and "extrapolado" in svg and "<pattern" not in svg
        if "parede" in kw:
            assert "Seção A–A′" in svg and ">A′<" in svg
    saida = mbf.exportar(svg, str(tmp_path / "f.pdf"), "pdf")
    assert open(saida, "rb").read(4) == b"%PDF"
    # só algumas camadas
    svg = mbf.desenhar(m, modo="fechado", camadas=["ACU"])
    assert "Formação Açu" in svg or "ACU" in svg
    # registro antigo, sem bloco fechado
    velho = {k: v for k, v in m.items() if k != "solido"}
    with pytest.raises(mbf.ErroFigura):
        mbf.desenhar(velho, modo="fechado")
    assert "Topo das unidades" in mbf.desenhar(velho)


def test_topo_abaixo_do_fundo_do_poco_fica_fora(banco):
    # a operadora registrou o Embasamento a 6.000 m num poço de 1.200 m (estimativa, não perfurado)
    poco(banco, "1-AA-7-RN", -5.01, -36.99, 50.0, [("F", "JANDAI", 20, 330), ("F", "ACU", 330, 6000),
                                                    ("", "EMBASA", 6000, None)], prof_final=1200)
    m = mb.montar(banco, IDS + ["1-AA-7-RN"])
    p = next(q for q in m["pocos"] if q["id"] == "1-AA-7-RN")
    assert [u["chave"] for u in p["unidades"]] == ["JANDAI", "ACU"]
    acu = p["unidades"][1]
    assert acu["base_atingida"] is False and acu["base"] == 1200
    assert any("abaixo do fundo do poço" in a and "1-AA-7-RN" in a for a in m["avisos"])
    assert m["solido"]["base"] > -1500                    # a base do bloco não desce até a estimativa
