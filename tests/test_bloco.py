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


# ============================================== trajetórias, trilhas, propriedades (0.19)
def _avaliacao(pasta, poco_id, ident, prof, res, pay, intervalos):
    os.makedirs(pasta, exist_ok=True)
    np.savez_compressed(os.path.join(pasta, ident + ".npz"), prof=np.asarray(prof, float),
                        RES=np.asarray(res, np.float32), PAY=np.asarray(pay, np.float32))
    import json
    with open(os.path.join(pasta, ident + ".json"), "w", encoding="utf-8") as f:
        json.dump({"id": ident, "tipo": "avaliacao_formacao", "criado_em": "2026-10-17T09:00:00-03:00",
                   "poco": poco_id, "intervalos": intervalos}, f)


def test_trajetoria_move_os_topos(banco):
    from motor import direcionais as mdi
    from test_direcionais import NOVO
    # 1-AA-5-RN: 100 m vertical e depois ~77 m para leste até 400 m
    mdi.gravar(banco, bacia="Potiguar", caminho="/d/1.txt", poco_id="1-AA-5-RN", nome="1.txt", tamanho=1,
               texto=NOVO.replace("7-xx-2d-rn", "1-AA-5-RN"))
    ids = ["1-AA-1-RN", "1-AA-2-RN", "1-AA-3-RN", "1-AA-4-RN", "1-AA-5-RN"]
    m = mb.montar(banco, ids)
    p = next(q for q in m["pocos"] if q["id"] == "1-AA-5-RN")
    assert p["trajetoria"]["afastamento_m"] > 70
    acu = next(u for u in p["unidades"] if u["chave"] == "ACU")          # topo a ~343 m: já desviado
    assert (acu["x"] - p["x"]) * 1000 == pytest.approx(mdi.posicao(mdi.do_poco(banco, "1-AA-5-RN"), acu["topo"])[1][0],
                                                       abs=1)
    assert p["caminho"][0][0] == 0 and p["caminho"][-1][0] >= 900
    assert any("Trajetória pelos dados direcionais" in a for a in m["avisos"])
    sem = mb.montar(banco, ids, usar_trajetorias=False)
    p2 = next(q for q in sem["pocos"] if q["id"] == "1-AA-5-RN")
    assert p2["trajetoria"] is None and all(u["x"] == p2["x"] for u in p2["unidades"])


def test_trilhas_de_pay_com_prioridade_e_gas(banco, tmp_path):
    ex = str(tmp_path / "execucoes")
    prof = np.arange(400, 500, 0.2)
    res = np.where(prof < 430, 0, 1.0)
    pay = np.where((prof >= 460) & (prof < 460.4), 1.0, 0)          # pay de 0,4 m: não pode sumir
    _avaliacao(ex, "1-AA-1-RN", "avaliacao_1-AA-1-RN_1", prof, res, pay,
               [{"nome": "Açu", "topo": 400, "base": 500, "hpv_m": 5.0, "net_pay_m": 0.4, "ntg": 0.7,
                 "phi_media_pay": 0.2, "sw_media_pay": 0.4}])
    m = mb.montar(banco, ["1-AA-1-RN", "1-AA-2-RN", "1-AA-3-RN", "1-AA-4-RN"], pasta_execucoes=ex)
    p = next(q for q in m["pocos"] if q["id"] == "1-AA-1-RN")
    assert p["avaliacao"] == "avaliacao_1-AA-1-RN_1"
    classes = [c for _, _, c in p["classes"]]
    assert classes == [1, 2, 3, 2]
    a, b, _ = next(t for t in p["classes"] if t[2] == 3)
    assert a <= 460 and b >= 460.4 and b - a <= mb.BLOCO_TRILHA_M + 0.01
    # indício de gás do AGP sobre o pay → "pay com indício de gás"
    import json
    with banco.conexao() as c:
        r = c.execute("SELECT caminho, dados FROM agp WHERE poco_id = '1-AA-1-RN'").fetchone()
        d = json.loads(r["dados"])
        d["indicios"] = [{"fluido": "gás", "topo": 455, "base": 465}, {"fluido": "óleo", "topo": 470, "base": 480}]
        c.execute("UPDATE agp SET dados = ? WHERE caminho = ?", (json.dumps(d), r["caminho"]))
    m = mb.montar(banco, ["1-AA-1-RN", "1-AA-2-RN", "1-AA-3-RN", "1-AA-4-RN"], pasta_execucoes=ex)
    p = next(q for q in m["pocos"] if q["id"] == "1-AA-1-RN")
    assert 4 in [c for _, _, c in p["classes"]] and 3 not in [c for _, _, c in p["classes"]]
    assert [i["fluido"] for i in p["indicios"]] == ["gás", "óleo"]


def test_propriedade_no_topo(banco, tmp_path):
    ex = str(tmp_path / "execucoes")
    ids = ["1-AA-1-RN", "1-AA-2-RN", "1-AA-3-RN", "1-AA-4-RN", "1-AA-5-RN"]
    for k, pid in enumerate(ids[:4]):
        _avaliacao(ex, pid, f"avaliacao_{pid}_1", [400, 401], [1, 1], [1, 1],
                   [{"nome": "Formação Açu (teste)", "topo": 350, "base": 650, "hpv_m": 2.0 + 4 * k,
                     "net_pay_m": 10.0, "ntg": 0.5, "phi_media_pay": 0.2, "sw_media_pay": 0.3}])
    m = mb.montar(banco, ids, pasta_execucoes=ex)
    pr = m["propriedades"]["ACU"]
    assert len(pr["pocos"]) == 4 and pr["faixas"]["hpv_m"] == [2.0, 14.0]
    vals = [v for linha in pr["grades"]["hpv_m"] for v in linha if v is not None]
    assert min(vals) >= 2.0 - 1e-6 and max(vals) <= 14.0 + 1e-6
    assert "JANDAI" not in m["propriedades"]           # a avaliação é do Açu (pelo nome)


def test_figura_estilo_artigo(banco, tmp_path):
    import math
    from motor import bloco_figura as bf
    ex = str(tmp_path / "execucoes")
    ids = ["1-AA-1-RN", "1-AA-2-RN", "1-AA-3-RN", "1-AA-4-RN", "1-AA-5-RN"]
    for k, pid in enumerate(ids[:3]):
        _avaliacao(ex, pid, f"avaliacao_{pid}_1", np.arange(300, 700, 0.5), np.ones(800), np.ones(800),
                   [{"nome": "Açu", "topo": 300, "base": 700, "hpv_m": 3.0 * (k + 1), "net_pay_m": 9.0,
                     "ntg": 0.5, "phi_media_pay": 0.2, "sw_media_pay": 0.3}])
    m = mb.montar(banco, ids, pasta_execucoes=ex)
    svg = bf.desenhar(m, azimute=math.radians(-35), elevacao=math.radians(30), exagero=20, trilha="avaliacao",
                      drape={"chave": "ACU", "prop": "hpv_m"}, titulo="Campo teste", autor="Fulano", data="17/10/2026")
    assert svg.startswith("<svg") and "Campo teste" in svg and "HPV (m)" in svg and "pay" in svg
    assert "<pattern" not in svg and "clipPath" not in svg and svg.count("<polygon") > 50
    for fmt in ("svg", "pdf", "png"):
        f = bf.exportar(svg, str(tmp_path / "fig" / f"f.{fmt}"), fmt)
        assert os.path.getsize(f) > 2000
    # de cima (elevação 90°): continua desenhando
    assert "<polygon" in bf.desenhar(m, azimute=0, elevacao=math.radians(89.9), exagero=1)
