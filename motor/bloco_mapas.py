"""Mapas do bloco para SIG: terreno, topo e espessura (isópaca) de cada camada.

Saem em **SIRGAS 2000 / UTM** (o fuso do centro do bloco), numa grade regular em metros:

- **GeoTIFF** (um por mapa, ponto flutuante de 32 bits, sem dado = −9999), que o QGIS, o
  ArcGIS, o Surfer e o Petrel abrem com a coordenada certa — escrito aqui mesmo (TIFF sem
  compressão + as chaves GeoTIFF do EPSG), sem GDAL;
- **XYZ** (um CSV com todos os mapas em colunas, `;` e vírgula decimal), mais lat/lon.

O modelo do bloco está num plano local em km (motor/bloco.py). Cada pixel da grade UTM volta
para lat/lon (motor/utm.py), dali para o plano local, e pega o valor da grade do bloco por
interpolação bilinear; fora do contorno do bloco, sem dado. Do bloco fechado quando há; senão,
das superfícies de topo.
"""

from __future__ import annotations

import csv
import math
import os
import struct

import numpy as np

from . import bloco as mbl
from . import bloco_solido as mbs
from . import utm

SEM_DADO = -9999.0
PASSOS_M = (5, 10, 20, 25, 50, 100, 200, 250, 500, 1000, 2000)


class ErroMapa(Exception):
    pass


# ============================================================== grade UTM
def grade_utm(modelo: dict, passo_m: float | None = None) -> dict:
    """Grade UTM regular que cobre o contorno do bloco (pixels pelo centro)."""
    o, g = modelo["origem"], modelo["grade"]
    sol = modelo.get("solido") or {}
    contorno = np.asarray(sol["contorno"] if sol.get("ok") else mbl.com_margem(
        np.asarray(modelo["contorno"], float), modelo.get("margem_km") or 0.0), float)
    lat, lon = mbl.para_geo(contorno[:, 0], contorno[:, 1], o["lat"], o["lon"])
    z, sul = utm.fuso(float(o["lon"])), float(o["lat"]) < 0
    e, n = utm.para_utm(lat, lon, z, sul)
    if passo_m is None:                     # o passo da grade do bloco, arredondado para cima
        alvo = g["passo"] * 1000.0
        passo_m = next((p for p in PASSOS_M if p >= alvo * 0.95), PASSOS_M[-1])
    passo_m = float(passo_m)
    e0 = math.floor(e.min() / passo_m) * passo_m
    n1 = math.ceil(n.max() / passo_m) * passo_m
    nx = int(math.ceil((e.max() - e0) / passo_m))
    ny = int(math.ceil((n1 - n.min()) / passo_m))
    if nx * ny > 25_000_000:
        raise ErroMapa(f"Grade grande demais ({nx} × {ny}); use um passo maior.")
    ec = e0 + passo_m * (np.arange(nx) + 0.5)
    nc = n1 - passo_m * (np.arange(ny) + 0.5)          # linha 0 = norte (como no TIFF)
    E, N = np.meshgrid(ec, nc)
    la, lo = utm.de_utm(E, N, z, sul)
    x, y, _, _ = mbl.plano(la, lo, o["lat"], o["lon"])
    return {"fuso": z, "sul": sul, "epsg": utm.epsg(z, sul), "e0": e0, "n1": n1, "passo": passo_m, "nx": nx,
            "ny": ny, "x": x, "y": y, "lat": la, "lon": lo, "E": E, "N": N,
            "dentro": mbs.controlado(contorno.tolist(), x, y, tol_km=0.0)}


def mapas(modelo: dict, gu: dict) -> list[dict]:
    """[{nome, titulo, unidade, z (ny × nx, NaN fora)}]: terreno, topo e isópaca de cada camada."""
    g = modelo["grade"]
    x, y, fora = gu["x"], gu["y"], ~gu["dentro"]
    out = []
    sol = modelo.get("solido") or {}
    if sol.get("ok"):
        lims = [mbs.bilinear(np.asarray(z, float), g, x, y) for z in sol["limites"]]
        camadas = sol["camadas"]
        com_cob = camadas[0]["chave"] == mbs.CHAVE_COBERTURA
        ter = lims[0]
        if not com_cob:                     # sem a camada de cobertura, o 1º limite é o 1º topo
            ter = None
        terreno = _terreno(modelo, gu) if ter is None else ter
        out.append({"nome": "terreno", "titulo": "terreno (cota, m)", "z": terreno})
        for k, c in enumerate(camadas):
            if c["chave"] in (mbs.CHAVE_COBERTURA, mbs.CHAVE_ABAIXO):
                continue
            esp = np.maximum(lims[k] - lims[k + 1], 0.0)
            topo = np.where(esp >= mbs.ESPESSURA_MIN_M, lims[k], np.nan)
            out.append({"nome": f"topo_{_seguro(c['chave'])}", "titulo": f"topo de {c['nome']} (cota, m)",
                        "z": topo})
            out.append({"nome": f"isopaca_{_seguro(c['chave'])}", "titulo": f"espessura de {c['nome']} (m)",
                        "z": esp})
    else:
        for s in modelo["superficies"]:
            if not s.get("z"):
                continue
            z = np.array([[np.nan if v is None else v for v in linha] for linha in s["z"]], float)
            out.append({"nome": f"topo_{_seguro(s['chave'])}", "titulo": f"topo de {s['nome']} (cota, m)",
                        "z": mbs.bilinear(z, g, x, y)})
    for m in out:
        m["z"] = np.where(fora, np.nan, m["z"]).astype(float)
    return [m for m in out if np.isfinite(m["z"]).any()]


def _terreno(modelo, gu):
    ob = mbs.observacoes(modelo)
    z, _ = mbs.interpolar_grade([o[:2] for o in ob["terreno"]], [o[2] for o in ob["terreno"]], modelo["grade"])
    return mbs.bilinear(z, modelo["grade"], gu["x"], gu["y"])


def _seguro(txt: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in txt).strip("_").lower() or "camada"


# ============================================================== GeoTIFF
def geotiff(caminho: str, z, e0: float, n1: float, passo: float, codigo_epsg: int) -> str:
    """GeoTIFF float32 de uma banda (linha 0 = norte), sem compressão, sem dado = −9999."""
    z = np.where(np.isfinite(z), z, SEM_DADO).astype("<f4")
    ny, nx = z.shape
    linhas_faixa = max(1, 65536 // (nx * 4))
    faixas = [(r, min(ny, r + linhas_faixa)) for r in range(0, ny, linhas_faixa)]
    dados = [z[a:b].tobytes() for a, b in faixas]
    geokeys = [1, 1, 0, 4,
               1024, 0, 1, 1,                 # GTModelType = projetado
               1025, 0, 1, 1,                 # GTRasterType = PixelIsArea
               3072, 0, 1, codigo_epsg,       # ProjectedCSType = EPSG
               3076, 0, 1, 9001]              # ProjLinearUnits = metro
    nodata = (f"{SEM_DADO:g}".encode() + b"\0")
    # (tag, tipo, valores); tipos: 3 SHORT, 4 LONG, 12 DOUBLE, 2 ASCII
    entradas = [(256, 4, [nx]), (257, 4, [ny]), (258, 3, [32]), (259, 3, [1]), (262, 3, [1]),
                (273, 4, [0] * len(faixas)), (277, 3, [1]), (278, 4, [linhas_faixa]),
                (279, 4, [len(d) for d in dados]), (284, 3, [1]), (339, 3, [3]),
                (33550, 12, [passo, passo, 0.0]), (33922, 12, [0.0, 0.0, 0.0, e0, n1, 0.0]),
                (34735, 3, geokeys), (42113, 2, nodata)]
    tam = {2: 1, 3: 2, 4: 4, 12: 8}
    fmt = {3: "H", 4: "I", 12: "d"}
    n_ent = len(entradas)
    ifd_ini = 8
    extra_ini = ifd_ini + 2 + 12 * n_ent + 4
    # valores que não cabem em 4 bytes vão depois do IFD; depois, os dados da imagem
    extras = []
    pos = extra_ini
    offs_extra = {}
    for tag, tipo, vals in entradas:
        nbytes = tam[tipo] * len(vals)
        if nbytes > 4:
            offs_extra[tag] = pos
            pos += nbytes + (nbytes % 2)
    dados_ini = pos
    offsets, p = [], dados_ini
    for d in dados:
        offsets.append(p)
        p += len(d)
    entradas = [(t, ty, offsets if t == 273 else v) for t, ty, v in entradas]
    cab = b"II*\0" + struct.pack("<I", ifd_ini)
    ifd = struct.pack("<H", n_ent)
    for tag, tipo, vals in entradas:
        cont = len(vals)
        if tipo == 2:
            bruto = bytes(vals)
        else:
            bruto = struct.pack("<" + fmt[tipo] * cont, *vals)
        if len(bruto) > 4:
            ifd += struct.pack("<HHII", tag, tipo, cont, offs_extra[tag])
            extras.append(bruto + (b"\0" if len(bruto) % 2 else b""))
        else:
            ifd += struct.pack("<HHI", tag, tipo, cont) + bruto.ljust(4, b"\0")
    ifd += struct.pack("<I", 0)
    os.makedirs(os.path.dirname(caminho) or ".", exist_ok=True)
    with open(caminho, "wb") as f:
        f.write(cab + ifd + b"".join(extras))
        for d in dados:
            f.write(d)
    return caminho


# ============================================================== exportação
def exportar(modelo: dict, pasta: str, ident: str, passo_m: float | None = None) -> dict:
    """Pasta `<ident>_mapas/` com um GeoTIFF por mapa, o XYZ e um LEIA-ME."""
    gu = grade_utm(modelo, passo_m)
    ms = mapas(modelo, gu)
    if not ms:
        raise ErroMapa("Nada para exportar: o bloco não tem superfícies.")
    destino = os.path.join(pasta, f"{ident}_mapas")
    os.makedirs(destino, exist_ok=True)
    arquivos = []
    for m in ms:
        arquivos.append(geotiff(os.path.join(destino, m["nome"] + ".tif"), m["z"], gu["e0"], gu["n1"], gu["passo"],
                                gu["epsg"]))
    xyz = os.path.join(destino, f"{ident}_mapas_xyz.csv")

    def n(v, c):
        return "" if not np.isfinite(v) else f"{v:.{c}f}".replace(".", ",")
    with open(xyz, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["leste_m", "norte_m", "lat", "lon"] + [m["nome"] for m in ms])
        dentro = np.argwhere(gu["dentro"])
        for j, i in dentro:
            w.writerow([n(gu["E"][j, i], 1), n(gu["N"][j, i], 1), n(gu["lat"][j, i], 6), n(gu["lon"][j, i], 6)]
                       + [n(m["z"][j, i], 1) for m in ms])
    arquivos.append(xyz)
    prj = os.path.join(destino, f"{ident}_mapas_xyz.prj")
    with open(prj, "w", encoding="ascii") as f:
        f.write(utm.wkt(gu["fuso"], gu["sul"]))
    arquivos.append(prj)
    sol = modelo.get("solido") or {}
    leia = os.path.join(destino, "LEIA-ME.txt")
    with open(leia, "w", encoding="utf-8") as f:
        f.write(f"Mapas do bloco {ident} (SIAPP)\n\n")
        f.write(f"Sistema: SIRGAS 2000 / UTM fuso {gu['fuso']}{'S' if gu['sul'] else 'N'} (EPSG:{gu['epsg']}).\n")
        f.write(f"Grade: {gu['nx']} x {gu['ny']} pixels de {gu['passo']:g} m; sem dado = {SEM_DADO:g}.\n")
        f.write("Cotas em metros (positivas para cima, em relação ao nível do mar); espessuras em metros.\n")
        f.write("Fonte: " + ("bloco fechado (camadas empilhadas por espessura a partir dos topos do AGP)."
                             if sol.get("ok") else "superfícies de topo interpoladas entre os poços (AGP).") + "\n")
        f.write("Fora do contorno dos poços com o dado, o valor é extrapolado (ver o bloco no SIAPP).\n\n")
        for m in ms:
            f.write(f"{m['nome']}.tif  {m['titulo']}\n")
    arquivos.append(leia)
    return {"pasta": destino, "arquivos": arquivos, "epsg": gu["epsg"], "passo_m": gu["passo"],
            "nx": gu["nx"], "ny": gu["ny"], "mapas": [m["nome"] for m in ms]}
