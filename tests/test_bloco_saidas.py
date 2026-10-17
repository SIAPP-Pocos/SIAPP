"""Saídas do bloco: UTM, mapas (GeoTIFF + XYZ), deck ECLIPSE, volumetria e .glb. Poços sintéticos."""
import json
import math
import os
import re
import struct

import numpy as np
import pytest

from motor import bloco as mb
from motor import bloco_eclipse as mbe
from motor import bloco_glb as mbg
from motor import bloco_mapas as mbm
from motor import bloco_volumetria as mbvol
from motor import utm
from test_bloco_solido import IDS, banco  # noqa: F401  (banco é fixture)


# ============================================================== UTM
def test_utm_sirgas2000():
    # ponto de um arquivo de dados direcionais (cabeçalho com lat/lon e UTM do próprio arquivo)
    lat, lon = -(5 + 23 / 60 + 50.782 / 3600), -(36 + 56 / 60 + 20.388 / 3600)
    e, n = utm.para_utm(lat, lon)
    assert utm.fuso(lon) == 24 and utm.epsg(24) == 31984 and utm.epsg(20, sul=False) == 31974
    assert float(e) == pytest.approx(728376.70, abs=0.05) and float(n) == pytest.approx(9403016.60, abs=0.05)
    la, lo = utm.de_utm(e, n, 24, True)
    assert float(la) == pytest.approx(lat, abs=1e-9) and float(lo) == pytest.approx(lon, abs=1e-9)
    assert "Central_Meridian\",-39.0" in utm.wkt(24)


def test_utm_confere_com_pyproj():
    pyproj = pytest.importorskip("pyproj")
    t = pyproj.Transformer.from_crs(4674, 31985, always_xy=True)
    la, lo = np.linspace(-9, -4, 50), np.linspace(-37, -33, 50)
    e, n = utm.para_utm(la, lo, 25, True)
    e2, n2 = t.transform(lo, la)
    assert np.abs(e - e2).max() < 1e-3 and np.abs(n - n2).max() < 1e-3


# ============================================================== mapas
def _ler_tiff(caminho):
    """Leitor mínimo do nosso GeoTIFF (sem dependência): tags e a matriz float32."""
    b = open(caminho, "rb").read()
    assert b[:4] == b"II*\0"
    ifd = struct.unpack("<I", b[4:8])[0]
    n = struct.unpack("<H", b[ifd:ifd + 2])[0]
    tags = {}
    tam = {2: 1, 3: 2, 4: 4, 12: 8}
    fmt = {2: "c", 3: "H", 4: "I", 12: "d"}
    for k in range(n):
        tag, tipo, cont, val = struct.unpack("<HHII", b[ifd + 2 + 12 * k: ifd + 14 + 12 * k])
        nbytes = tam[tipo] * cont
        bruto = b[ifd + 10 + 12 * k: ifd + 14 + 12 * k][:nbytes] if nbytes <= 4 else b[val:val + nbytes]
        tags[tag] = struct.unpack("<" + fmt[tipo] * cont, bruto)
    nx, ny = tags[256][0], tags[257][0]
    dados = b"".join(b[o:o + c] for o, c in zip(tags[273], tags[279]))
    return tags, np.frombuffer(dados, "<f4").reshape(ny, nx)


def test_mapas_geotiff_e_xyz(banco, tmp_path):
    m = mb.montar(banco, IDS)
    r = mbm.exportar(m, str(tmp_path), "bloco_x", passo_m=100)
    assert r["epsg"] == 31984 and "terreno" in r["mapas"] and "topo_acu" in r["mapas"] and "isopaca_jandai" in r["mapas"]
    tags, z = _ler_tiff(os.path.join(r["pasta"], "topo_acu.tif"))
    assert tags[339] == (3,) and tags[258] == (32,) and tags[33550][:2] == (100.0, 100.0)
    assert 3072 in tags[34735] and 31984 in tags[34735]
    e0, n1 = tags[33922][3], tags[33922][4]
    # no poço do meio, o topo do Açu do mapa = o do AGP
    p = next(q for q in m["pocos"] if q["id"] == "1-AA-5-RN")
    e, n = utm.para_utm(p["lat"], p["lon"], 24, True)
    i, j = int((float(e) - e0) // 100), int((n1 - float(n)) // 100)
    leste = (p["lon"] + 37.0) * 111.0
    assert float(z[j, i]) == pytest.approx(50 - (300 + 10 * leste), abs=3.0)
    assert (z == mbm.SEM_DADO).any() and (z != mbm.SEM_DADO).any()          # fora do contorno: sem dado
    xyz = open(os.path.join(r["pasta"], "bloco_x_mapas_xyz.csv"), encoding="utf-8-sig").read().splitlines()
    assert xyz[0].startswith("leste_m;norte_m;lat;lon;terreno") and len(xyz) > 100
    assert os.path.exists(os.path.join(r["pasta"], "LEIA-ME.txt"))


def test_geotiff_lido_pelo_rasterio(banco, tmp_path):
    rasterio = pytest.importorskip("rasterio")
    m = mb.montar(banco, IDS)
    r = mbm.exportar(m, str(tmp_path), "bloco_x")
    with rasterio.open(os.path.join(r["pasta"], "terreno.tif")) as ds:
        assert ds.crs.to_epsg() == 31984 and ds.nodata == mbm.SEM_DADO
        a = ds.read(1, masked=True)
        assert float(a.max()) == pytest.approx(45.0, abs=0.5)


# ============================================================== ECLIPSE
def _valores(texto, palavra):
    bloco = re.search(rf"^{palavra}\n(.*?)^/", texto, re.S | re.M).group(1)
    out = []
    for tok in bloco.split():
        if "*" in tok:
            k, v = tok.split("*")
            out += [float(v)] * int(k)
        else:
            out.append(float(tok))
    return np.array(out)


def test_deck_eclipse(banco, tmp_path):
    m = mb.montar(banco, IDS)
    r = mbe.exportar(m, str(tmp_path), "bloco_x", titulo="Campo teste", max_celulas=20000)
    nx, ny, nz = r["nx"], r["ny"], r["nz"]
    assert nx * ny * nz <= 20000 and r["ativas"] > 0 and r["deck"] == "CAMPO_TESTE.DATA"
    assert [c["chave"] for c in r["camadas"]] == ["_cobertura"][:0] + ["JANDAI", "ACU", "ALAGAM", "PENDEN"]
    grd = open(os.path.join(r["pasta"], "CAMPO_TESTE.GRDECL")).read()
    coord, zc, act = _valores(grd, "COORD"), _valores(grd, "ZCORN"), _valores(grd, "ACTNUM")
    assert len(coord) == 6 * (nx + 1) * (ny + 1) and len(zc) == 8 * nx * ny * nz and len(act) == nx * ny * nz
    assert act.sum() == r["ativas"]
    Z = zc.reshape(nz, 2, 2 * ny, 2 * nx)
    assert (Z[:, 1] >= Z[:, 0] - 1e-6).all()               # base de cada célula abaixo do topo
    assert (Z[1:, 0] >= Z[:-1, 1] - 1e-6).all()            # camadas não se cruzam
    # topo da Jandaíra (1ª camada) = −cota 30 m em todo o bloco
    assert np.median(Z[0, 0]) == pytest.approx(-30.0, abs=1.0)
    deck = open(os.path.join(r["pasta"], "CAMPO_TESTE.DATA")).read()
    for chave in ("DIMENS", "EQLDIMS", "REGDIMS", "PINCH", "INCLUDE", "SCHEDULE", f"  {nx} {ny} {nz} /"):
        assert chave in deck
    poro = open(os.path.join(r["pasta"], "CAMPO_TESTE_PORO_NTG.inc")).read()
    assert "PROVISORIO" in poro and "?" not in poro                      # sem avaliação: marcado, sem acento
    pocos = open(os.path.join(r["pasta"], "CAMPO_TESTE_POCOS.inc")).read()
    nomes = re.findall(r"^  '(\w+)' 'G1'", pocos, re.M)
    assert len(nomes) == 5 and all(len(n) <= 8 for n in nomes) and len(set(nomes)) == 5 and "'SHUT'" in pocos
    leia = open(os.path.join(r["pasta"], "LEIA-ME.txt"), encoding="utf-8").read()
    assert "PROVISÓRIO" in leia and "EPSG:31984" in leia
    with pytest.raises(mbe.ErroEclipse):
        mbe.exportar(m, str(tmp_path), "bloco_x", max_celulas=3)
    with pytest.raises(mbe.ErroEclipse):
        mbe.exportar(m, str(tmp_path), "bloco_x", camadas=["NADA"])
    assert mbe.nome_curto("1-AURI-12-RN", set()) == "AURI12"


def test_deck_lido_pelo_opm(banco, tmp_path):
    opm = pytest.importorskip("opm.io.parser")
    from opm.io.ecl_state import EclipseState
    from opm.io.schedule import Schedule
    m = mb.montar(banco, IDS)
    r = mbe.exportar(m, str(tmp_path), "bloco_x", titulo="T", max_celulas=20000)
    deck = opm.Parser().parse(os.path.join(r["pasta"], "T.DATA"), opm.ParseContext())
    st = EclipseState(deck)
    assert st.grid().nactive == r["ativas"]
    assert len(Schedule(deck, st).get_wells(0)) == r["pocos"]


# ============================================================== volumetria
def test_volumetria(banco):
    m = mb.montar(banco, IDS)
    v = mbvol.calcular(m, {"ACU": {"ntg": "0,5", "phi": "0,2", "sw": "0,3", "bo": "1,2"}},
                       {"eficiencia": "0,02", "densidade": "700"})
    acu = next(l for l in v["linhas"] if l["chave"] == "ACU")
    assert acu["fonte"] == {"ntg": "informado", "phi": "informado", "sw": "informado"}
    assert acu["vp_m3"] == pytest.approx(acu["grv_m3"] * 0.1)
    assert acu["hc_m3"] == pytest.approx(acu["vp_m3"] * 0.7) and acu["voip_m3"] == pytest.approx(acu["hc_m3"] / 1.2)
    assert acu["co2_t"] == pytest.approx(acu["vp_m3"] * 0.02 * 700 / 1000)
    ja = next(l for l in v["linhas"] if l["chave"] == "JANDAI")
    assert ja["vp_m3"] is None and any("Jandaíra" in n or "JANDAI" in n for n in v["notas"])
    assert v["total"]["vp_m3"] == pytest.approx(acu["vp_m3"])
    with pytest.raises(mbvol.ErroVolumetria):
        mbvol.calcular(m, {"ACU": {"phi": "25"}})
    with pytest.raises(mbvol.ErroVolumetria):
        mbvol.calcular(m, {}, {"eficiencia": "2"})


# ============================================================== glb
def test_glb(banco, tmp_path):
    m = mb.montar(banco, IDS)
    r = mbg.exportar(m, str(tmp_path / "b.glb"), exagero=5, titulo="Teste")
    b = open(r["arquivo"], "rb").read()
    magia, versao, total = struct.unpack("<III", b[:12])
    assert magia == 0x46546C67 and versao == 2 and total == len(b)
    njs = struct.unpack("<I", b[12:16])[0]
    doc = json.loads(b[20:20 + njs])
    nomes = [n["name"] for n in doc["nodes"]]
    assert "poços" in nomes and any("JANDAI" in n or "Jandaíra" in n for n in nomes)
    for a in doc["accessors"]:
        assert a["count"] % 3 == 0
    assert r["triangulos"] > 100
    so = mbg.exportar(m, str(tmp_path / "c.glb"), camadas=["ACU"], pocos=False)
    assert so["triangulos"] < r["triangulos"]


def test_glb_lido_pelo_trimesh(banco, tmp_path):
    trimesh = pytest.importorskip("trimesh")
    m = mb.montar(banco, IDS)
    r = mbg.exportar(m, str(tmp_path / "b.glb"))
    cena = trimesh.load(r["arquivo"])
    assert len(cena.geometry) >= 4
