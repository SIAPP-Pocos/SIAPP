"""Bloco 3D: geometria (contorno, área, Delaunay, interpolação), modelo e saídas."""
import csv
import math
import os

import numpy as np
import pytest

from motor import bloco as mb
from motor.banco import Banco
from test_secao import poco


# ============================================================== geometria
def test_contorno_e_area_shoelace():
    pts = [(0, 0), (4, 0), (4, 3), (0, 3), (2, 1), (1, 2)]
    h = mb.contorno_convexo(pts)
    assert len(h) == 4 and mb.area_shoelace(h) == pytest.approx(12.0)
    assert mb.area_shoelace(mb.contorno_convexo([(0, 0), (1, 0), (0, 1)])) == pytest.approx(0.5)


def test_plano_local_111_km_por_grau():
    x, y, lat0, lon0 = mb.plano([0.0, 1.0], [0.0, 0.0], 0.0, 0.0)
    assert y[1] == pytest.approx(111.19, abs=0.1) and x[1] == 0
    lat, lon = mb.para_geo(x, y, lat0, lon0)
    assert lat[1] == pytest.approx(1.0) and lon[1] == pytest.approx(0.0)


def test_delaunay_e_interpolacao_linear_exata_num_plano():
    rng = np.random.default_rng(1)
    pts = rng.uniform(0, 10, (25, 2))
    val = 100 - 3 * pts[:, 0] + 2 * pts[:, 1]          # um plano: linear tem de acertar em cheio
    tris = mb.delaunay(pts)
    assert len(tris) >= 25                               # ~2n − 2 − k triângulos
    gx, gy = np.meshgrid(np.linspace(0, 10, 41), np.linspace(0, 10, 41))
    z = mb.interpolar_linear(pts, val, tris, gx, gy)
    h = mb.contorno_convexo(pts)
    dentro = mb.dentro(h, gx, gy)
    ok = ~np.isnan(z)
    assert np.array_equal(ok, dentro)                    # definido só dentro do contorno
    assert np.allclose(z[ok], 100 - 3 * gx[ok] + 2 * gy[ok])
    # soma das áreas dos triângulos = área do contorno (nada sobrando, nada sobreposto)
    def area(t):
        (ax, ay), (bx, by), (cx, cy) = pts[t]
        return abs((bx - ax) * (cy - ay) - (by - ay) * (cx - ax)) / 2
    a = sum(area(t) for t in tris)
    assert a == pytest.approx(mb.area_shoelace(h))


def test_margem_e_colinearidade():
    q = mb.contorno_convexo([(0, 0), (2, 0), (2, 2), (0, 2)])
    ext = mb.com_margem(q, 1.0)
    assert mb.area_shoelace(ext) == pytest.approx(4 + 8 + math.pi, rel=0.03)
    assert mb.largura_relativa(mb.contorno_convexo([(0, 0), (10, 0.1), (5, 0.04)])) < mb.FRACAO_COLINEAR
    assert mb.largura_relativa(q) > 0.5


# ================================================================== modelo
@pytest.fixture
def banco(tmp_path):
    b = Banco(str(tmp_path / "projeto.sqlite"))
    # 5 poços num quadrado de ~4 km: Açu mergulha para leste (10 m/km); Jandaíra em todos;
    # Alagamar só em 3; Pendência só em 2 (sem superfície)
    for pid, la, lo in [("1-AA-1-RN", -5.00, -37.00), ("1-AA-2-RN", -5.00, -36.96), ("1-AA-3-RN", -5.04, -37.00),
                        ("1-AA-4-RN", -5.04, -36.96), ("1-AA-5-RN", -5.02, -36.98)]:
        leste = (lo + 37.00) * 111.0                    # km para leste
        un = [("F", "JANDAI", 20, 300 + 10 * leste), ("F", "ACU", 300 + 10 * leste, 700)]
        if pid in ("1-AA-1-RN", "1-AA-2-RN", "1-AA-3-RN"):
            un.append(("F", "ALAGAM", 700, 900))
        if pid in ("1-AA-1-RN", "1-AA-4-RN"):
            un.append(("F", "PENDEN", 900, 1100))
        poco(b, pid, la, lo, 50.0, un, prof_final=1200)
    return b


def test_montar_bloco(banco):
    m = mb.montar(banco, ["1-AA-1-RN", "1-AA-2-RN", "1-AA-3-RN", "1-AA-4-RN", "1-AA-5-RN"],
                  slots={"JANDAI": 1, "ACU": 2})
    assert len(m["pocos"]) == 5 and m["area_km2"] == pytest.approx(4.44 * 4.42, rel=0.03)
    assert [u["chave"] for u in m["legenda"]] == ["JANDAI", "ACU", "ALAGAM", "PENDEN"]
    s = {x["chave"]: x for x in m["superficies"]}
    assert s["ACU"]["z"] and s["ACU"]["malha"] and s["ACU"]["n_pocos"] == 5
    assert s["ALAGAM"]["area_km2"] == pytest.approx(s["ACU"]["area_km2"] / 2, rel=0.05)   # só 3 poços: metade
    assert s["PENDEN"]["z"] is None and "só 2 poço(s)" in s["PENDEN"]["aviso"]
    # topo do Açu: cota = 50 − (300 + 10·leste); a 4,4 km para leste, ~44 m mais fundo
    assert s["ACU"]["cota_max"] == pytest.approx(-250, abs=1)
    assert s["ACU"]["cota_min"] == pytest.approx(-250 - 44.4, abs=1.5)
    g = m["grade"]
    assert g["nx"] >= 100 and len(s["ACU"]["z"]) == g["ny"] and len(s["ACU"]["z"][0]) == g["nx"]
    assert m["pocos"][0]["unidades"][0]["cor"] == "#2a78d6"
    assert any("Pendência" in a or "PENDEN" in a for a in m["avisos"])


def test_margem_preenche_com_o_vizinho_e_corte_por_distancia(banco):
    ids = ["1-AA-1-RN", "1-AA-2-RN", "1-AA-3-RN", "1-AA-4-RN"]
    sem = mb.montar(banco, ids)
    com = mb.montar(banco, ids, margem_km=1.0)
    n = lambda m: sum(v is not None for linha in m["superficies"][0]["z"] for v in linha)  # noqa: E731
    assert com["area_km2"] == sem["area_km2"]               # a área é a do contorno dos poços
    assert "malha" not in com["superficies"][0]             # com margem, a janela desenha a grade
    nz_sem = n(sem) * sem["grade"]["passo"] ** 2
    nz_com = n(com) * com["grade"]["passo"] ** 2
    assert nz_com > nz_sem * 1.5
    corte = mb.montar(banco, ids, dist_max_km=1.0)
    assert n(corte) * corte["grade"]["passo"] ** 2 < nz_sem * 0.5


def test_colineares_e_poco_longe(tmp_path):
    b = Banco(str(tmp_path / "p.sqlite"))
    for k in range(4):
        poco(b, f"7-LL-{k}-RN", -5.0, -37.0 + 0.01 * k, 10.0, [("F", "ACU", 100 + k, 200)], prof_final=300)
    poco(b, "1-BRSA-264-ES", -19.0, -40.0, 10.0, [("F", "ACU", 100, 200)], prof_final=300)
    m = mb.montar(b, [f"7-LL-{k}-RN" for k in range(4)] + ["1-BRSA-264-ES"])
    assert [p["id"] for p in m["pocos"]] == [f"7-LL-{k}-RN" for k in range(4)]
    assert any("1-BRSA-264-ES" in a and "Longe" in a for a in m["avisos"])
    assert m["superficies"][0]["z"] is None and "alinhados" in m["superficies"][0]["aviso"]


def test_selecionar(banco):
    assert len(mb.selecionar(banco, modo="todos", bacia="Potiguar")) == 5
    assert len(mb.selecionar(banco, modo="campo", campo="campo teste")) == 5
    assert mb.selecionar(banco, modo="raio", poco="1-AA-5-RN", raio_km=1.0) == ["1-AA-5-RN"]
    assert len(mb.selecionar(banco, modo="raio", poco="1-AA-5-RN", raio_km=3.5)) == 5
    with pytest.raises(mb.ErroBloco):
        mb.selecionar(banco, modo="todos")
    with pytest.raises(mb.ErroBloco):
        mb.montar(banco, ["1-AA-1-RN", "1-AA-2-RN"])


def test_registro_historico_e_csv(banco, tmp_path):
    m = mb.montar(banco, ["1-AA-1-RN", "1-AA-2-RN", "1-AA-3-RN", "1-AA-4-RN"])
    pasta = str(tmp_path / "execucoes")
    i1, _ = mb.registrar(pasta, m, autor="Fulano")
    i2, _ = mb.registrar(pasta, m)
    assert i1 != i2 and [e["id"] for e in mb.execucoes(pasta)][0] == i2
    reg = mb.abrir(pasta, i1)
    assert reg["autor"] == "Fulano" and reg["area_km2"] == m["area_km2"]
    with pytest.raises(mb.ErroBloco):
        mb.abrir(pasta, "../x")
    topos, grade = mb.exportar_csv(reg, str(tmp_path / "exp"), i1)
    with open(topos, encoding="utf-8-sig") as f:
        linhas = list(csv.reader(f, delimiter=";"))
    assert linhas[0][:3] == ["poco", "lat", "lon"] and len(linhas) == 1 + 4 + 3 + 3 + 3
    with open(grade, encoding="utf-8-sig") as f:
        g = list(csv.reader(f, delimiter=";"))
    assert g[0][4:] == ["cota_topo_JANDAI_m", "cota_topo_ACU_m", "cota_topo_ALAGAM_m"] and len(g) > 100
    assert os.path.basename(grade) == f"{i1}_superficies.csv"
