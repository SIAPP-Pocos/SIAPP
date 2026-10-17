"""Modelo 3D do bloco fechado em glTF binário (.glb).

Abre no PowerPoint (Inserir → Modelos 3D, e gira no slide), no Visualizador 3D do Windows,
no Blender e em qualquer visualizador de glTF. Cada camada é uma malha com a cor da unidade
(a parte extrapolada, mais clara, num material à parte); os poços são tubos finos. O exagero
vertical é o da tela. Unidades em km (o PowerPoint ajusta o tamanho).

glTF 2.0 escrito aqui mesmo (JSON + um buffer binário), sem bibliotecas de fora.
"""

from __future__ import annotations

import json
import math
import os
import struct

import numpy as np

from . import __version__
from . import bloco_solido as mbs

MAX_CELULAS_GLB = 90


def _clarear(cor: str, sim: bool):
    c = np.array([int(cor.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4)])
    return c + 0.55 * (1 - c) if sim else c


def _srgb_para_linear(c):
    c = np.asarray(c, float)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def _recortar(pol):
    f = [p[2] - p[3] - mbs.ESPESSURA_MIN_M for p in pol]
    out = []
    for i in range(len(pol)):
        P, Q, fp, fq = pol[i], pol[(i + 1) % len(pol)], f[i], f[(i + 1) % len(pol)]
        if fp >= 0:
            out.append(P)
        if (fp >= 0) != (fq >= 0):
            t = fp / (fp - fq)
            out.append([a + t * (b - a) for a, b in zip(P, Q)])
    return out


def geometria(modelo: dict, exagero: float = 10.0, camadas: list[str] | None = None,
              pocos: bool = True) -> list[dict]:
    """[{nome, cor (rgb 0–1), tris: (n, 3, 3) em km}] — uma entrada por camada e por
    controle (interpolado / extrapolado), mais os poços."""
    sol, g = modelo["solido"], modelo["grade"]
    lims = [np.asarray(z, float) for z in sol["limites"]]
    lado = max((g["nx"] - 1) * g["passo"], (g["ny"] - 1) * g["passo"])
    gc = dict(g)
    gc["passo"] = max(g["passo"], lado / MAX_CELULAS_GLB)
    gc["nx"] = int(math.ceil((g["nx"] - 1) * g["passo"] / gc["passo"])) + 1
    gc["ny"] = int(math.ceil((g["ny"] - 1) * g["passo"] / gc["passo"])) + 1
    malha = mbs.malha_contorno(gc, sol["contorno"])
    borda = mbs.borda(gc, sol["contorno"])
    cx = g["x0"] + (g["nx"] - 1) * g["passo"] / 2
    cy = g["y0"] + (g["ny"] - 1) * g["passo"] / 2
    cz = (sol["cota_topo_max"] + sol["base"]) / 2
    ez = exagero / 1000.0

    def P(x, y, cota):                      # glTF: Y para cima, −Z = norte
        return (x - cx, (cota - cz) * ez, -(y - cy))
    xs, ys = malha["pts"][:, 0], malha["pts"][:, 1]
    vals = [mbs.bilinear(z, g, xs, ys) for z in lims]
    bx, by = borda[:, 0], borda[:, 1]
    valb = [mbs.bilinear(z, g, bx, by) for z in lims]
    saida = []
    for k, c in enumerate(sol["camadas"]):
        if camadas is not None and c["chave"] not in camadas:
            continue
        T, B, Tb, Bb = vals[k], vals[k + 1], valb[k], valb[k + 1]
        grupos = {True: [], False: []}
        for a, b, d in malha["tris"]:
            e = [T[i] - B[i] for i in (a, b, d)]
            if max(e) < mbs.ESPESSURA_MIN_M:
                continue
            pol = [[xs[i], ys[i], T[i], B[i]] for i in (a, b, d)]
            if min(e) < mbs.ESPESSURA_MIN_M:
                pol = _recortar(pol)
            if len(pol) < 3:
                continue
            ctl = bool(mbs.controlado(c["controle"], np.mean([p[0] for p in pol]), np.mean([p[1] for p in pol])))
            for j in range(1, len(pol) - 1):
                q = [pol[0], pol[j], pol[j + 1]]
                grupos[ctl].append([P(p[0], p[1], p[2]) for p in q])                 # topo
                grupos[ctl].append([P(p[0], p[1], p[3]) for p in (q[0], q[2], q[1])])  # fundo
        for i in range(len(borda) - 1):
            Pp = [bx[i], by[i], Tb[i], Bb[i]]
            Qp = [bx[i + 1], by[i + 1], Tb[i + 1], Bb[i + 1]]
            fp, fq = Pp[2] - Pp[3] - mbs.ESPESSURA_MIN_M, Qp[2] - Qp[3] - mbs.ESPESSURA_MIN_M
            if fp < 0 and fq < 0:
                continue
            if fp < 0 or fq < 0:
                t = fp / (fp - fq)
                M = [a + t * (b - a) for a, b in zip(Pp, Qp)]
                Pp, Qp = (M, Qp) if fp < 0 else (Pp, M)
            ctl = bool(mbs.controlado(c["controle"], (Pp[0] + Qp[0]) / 2, (Pp[1] + Qp[1]) / 2))
            a1, b1 = P(Pp[0], Pp[1], Pp[2]), P(Qp[0], Qp[1], Qp[2])
            d1, e1 = P(Qp[0], Qp[1], Qp[3]), P(Pp[0], Pp[1], Pp[3])
            grupos[ctl] += [[a1, e1, d1], [a1, d1, b1]]
        for ctl, tris in grupos.items():
            if tris:
                saida.append({"nome": c["nome"] + ("" if ctl else " (extrapolado)"), "cor": _clarear(c["cor"], not ctl),
                              "tris": np.array(tris, float)})
    if pocos:
        r = lado * 0.002
        tubos = []
        for p in modelo["pocos"]:
            cam = p.get("caminho") or []
            pts = [P(q[1], q[2], q[3]) for q in cam]
            if len(pts) >= 2:
                tubos += _tubo(np.array(pts, float), r)
        if tubos:
            saida.append({"nome": "poços", "cor": np.array([0.11, 0.13, 0.15]), "tris": np.array(tubos, float)})
    return saida


def _tubo(pts, r, lados=6):
    """Tubo hexagonal ao longo da polilinha (triângulos)."""
    tris = []
    ang = np.linspace(0, 2 * math.pi, lados, endpoint=False)
    for a, b in zip(pts[:-1], pts[1:]):
        d = b - a
        L = np.linalg.norm(d)
        if L < 1e-9:
            continue
        d /= L
        ref = np.array([0.0, 1.0, 0.0]) if abs(d[1]) < 0.9 else np.array([1.0, 0.0, 0.0])
        u = np.cross(d, ref)
        u /= np.linalg.norm(u)
        v = np.cross(d, u)
        anel = [r * (math.cos(t) * u + math.sin(t) * v) for t in ang]
        for k in range(lados):
            p0, p1 = anel[k], anel[(k + 1) % lados]
            tris += [[a + p0, b + p0, b + p1], [a + p0, b + p1, a + p1]]
    return tris


def escrever(partes: list[dict], caminho: str, titulo: str = "") -> str:
    """glTF binário: um nó por parte, triângulos soltos com normal por face."""
    binario = bytearray()
    vistas, acess, malhas, materiais, nos = [], [], [], [], []
    for parte in partes:
        tris = parte["tris"].astype(np.float32)
        n = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
        nn = np.linalg.norm(n, axis=1, keepdims=True)
        n = np.where(nn > 0, n / np.where(nn > 0, nn, 1), 0).astype(np.float32)
        pos = tris.reshape(-1, 3)
        nor = np.repeat(n, 3, axis=0)
        for arr, tipo in ((pos, "POSITION"), (nor, "NORMAL")):
            while len(binario) % 4:
                binario += b"\0"
            ini = len(binario)
            binario += arr.tobytes()
            vistas.append({"buffer": 0, "byteOffset": ini, "byteLength": arr.nbytes, "target": 34962})
            a = {"bufferView": len(vistas) - 1, "componentType": 5126, "count": len(arr), "type": "VEC3"}
            if tipo == "POSITION":
                a["min"] = [float(v) for v in arr.min(0)]
                a["max"] = [float(v) for v in arr.max(0)]
            acess.append(a)
        cor = [float(v) for v in _srgb_para_linear(parte["cor"])] + [1.0]
        materiais.append({"name": parte["nome"], "doubleSided": True,
                          "pbrMetallicRoughness": {"baseColorFactor": cor, "metallicFactor": 0.0, "roughnessFactor": 0.9}})
        malhas.append({"name": parte["nome"], "primitives": [{"attributes": {"POSITION": len(acess) - 2,
                                                                             "NORMAL": len(acess) - 1},
                                                               "material": len(materiais) - 1, "mode": 4}]})
        nos.append({"name": parte["nome"], "mesh": len(malhas) - 1})
    while len(binario) % 4:
        binario += b"\0"
    doc = {"asset": {"version": "2.0", "generator": f"SIAPP {__version__}"},
           "scene": 0, "scenes": [{"name": titulo or "Bloco SIAPP", "nodes": list(range(len(nos)))}],
           "nodes": nos, "meshes": malhas, "materials": materiais, "accessors": acess, "bufferViews": vistas,
           "buffers": [{"byteLength": len(binario)}]}
    js = json.dumps(doc, ensure_ascii=False).encode("utf-8")
    js += b" " * ((4 - len(js) % 4) % 4)
    total = 12 + 8 + len(js) + 8 + len(binario)
    os.makedirs(os.path.dirname(caminho) or ".", exist_ok=True)
    with open(caminho, "wb") as f:
        f.write(struct.pack("<III", 0x46546C67, 2, total))
        f.write(struct.pack("<II", len(js), 0x4E4F534A) + js)
        f.write(struct.pack("<II", len(binario), 0x004E4942) + bytes(binario))
    return caminho


def exportar(modelo: dict, caminho: str, *, exagero: float = 10.0, camadas: list[str] | None = None,
             pocos: bool = True, titulo: str = "") -> dict:
    sol = modelo.get("solido") or {}
    if not sol.get("ok"):
        raise ValueError("O modelo 3D sai do bloco fechado, que este bloco não tem.")
    partes = geometria(modelo, exagero, camadas, pocos)
    escrever(partes, caminho, titulo)
    return {"arquivo": caminho, "triangulos": int(sum(len(p["tris"]) for p in partes)),
            "bytes": os.path.getsize(caminho)}
