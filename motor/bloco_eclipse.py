"""Exportação do bloco fechado para simuladores: deck no formato ECLIPSE (.DATA + .GRDECL).

Lido pelo tNavigator, pelo OPM Flow, pelo Petrel, pelo ResInsight e pelo próprio ECLIPSE.

**O que vem do dado** (e o SIAPP garante):

- a **geometria**: grade *corner-point* em SIRGAS 2000 / UTM (metros), pilares verticais,
  profundidade = −cota (positiva para baixo, em relação ao nível do mar); cada formação
  escolhida dividida em camadas iguais entre o topo e a base do bloco fechado; células fora
  do contorno do bloco ou mais finas que 0,1 m ficam inativas (ACTNUM 0), com PINCH para a
  continuidade vertical onde a formação acunha;
- **FIPNUM**: uma região por formação (balanço de volume por formação no simulador);
- **PORO e NTG** onde há avaliação de formação (aba Perfis) na formação: a média dos poços
  avaliados, ou a grade interpolada entre eles (3 ou mais);
- os **poços** com o caminho real (trajetória, quando lida), em WELSPECS/COMPDAT, fechados
  ('SHUT') — o usuário decide onde completar e como produzir/injetar.

**O que o SIAPP não sabe e não inventa**: permeabilidade, PVT, permeabilidade relativa,
contatos e pressão inicial. Vão em arquivos .inc separados, com valores **provisórios**
marcados no próprio arquivo, só para o deck abrir e rodar — trocar antes de simular de
verdade. O LEIA-ME lista o que é dado e o que é provisório.

**Teto de células**: 275.625 por padrão (o da licença acadêmica do tNavigator), ajustável.
"""

from __future__ import annotations

import math
import os
import re
import unicodedata
from datetime import date

import numpy as np

from . import __version__
from . import bloco as mbl
from . import bloco_solido as mbs
from . import utm

MAX_CELULAS_PADRAO = 275_625
ESP_ATIVA_M = 0.1                 # célula mais fina que isso: inativa (e o PINCH a atravessa)
PORO_PROVISORIO, NTG_PROVISORIO = 0.20, 1.0
PERM_PROVISORIA_MD = 100.0
MESES = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]


class ErroEclipse(Exception):
    pass


# ============================================================== grade
def planejar(modelo: dict, camadas: list[str] | None = None, nz: int | None = None, dx_m: float | None = None,
             max_celulas: int = MAX_CELULAS_PADRAO) -> dict:
    """Escolhe as formações, o número de camadas por formação e o tamanho da célula."""
    sol = modelo.get("solido") or {}
    if not sol.get("ok"):
        raise ErroEclipse("O deck sai do bloco fechado, que este bloco não tem (veja os avisos).")
    todas = [c for c in sol["camadas"] if c["chave"] not in (mbs.CHAVE_COBERTURA, mbs.CHAVE_ABAIXO)]
    # padrão: todas menos o embasamento (raramente é parte do modelo de reservatório)
    if camadas is not None:
        escolhidas = [c for c in todas if c["chave"] in camadas]
    else:
        escolhidas = [c for c in todas if not c["chave"].upper().startswith("EMBAS")] or todas
    escolhidas = [c for c in escolhidas if c["espessura_max_m"] >= mbs.ESPESSURA_MIN_M]
    if not escolhidas:
        raise ErroEclipse("Escolha ao menos uma formação com espessura no bloco.")
    max_celulas = int(max_celulas or MAX_CELULAS_PADRAO)
    if nz is None:
        nz = min(50, max(10, 3 * len(escolhidas)))
    nz = int(nz)
    if nz < len(escolhidas):
        raise ErroEclipse(f"São {len(escolhidas)} formações: ao menos {len(escolhidas)} camadas.")
    # camadas por formação, proporcionais à espessura média (volume / área), ao menos 1
    medias = np.array([c["volume_km3"] / c["area_km2"] * 1000 if c["area_km2"] else 0.0 for c in escolhidas])
    medias = np.maximum(medias, 1e-3)
    nk = np.ones(len(escolhidas), int)
    for _ in range(nz - len(escolhidas)):
        nk[int(np.argmax(medias / nk))] += 1
    # extensão em UTM
    o = modelo["origem"]
    cont = np.asarray(sol["contorno"], float)
    lat, lon = mbl.para_geo(cont[:, 0], cont[:, 1], o["lat"], o["lon"])
    z, sul = utm.fuso(float(o["lon"])), float(o["lat"]) < 0
    e, n = utm.para_utm(lat, lon, z, sul)
    areal = max_celulas // nz
    if areal < 1:
        raise ErroEclipse("Teto de células menor que o número de camadas.")

    def caber(d):                           # grade alinhada ao passo d (múltiplos de d em UTM)
        e0_ = math.floor(e.min() / d) * d
        n1_ = math.ceil(n.max() / d) * d
        return e0_, n1_, max(1, int(math.ceil((e.max() - e0_) / d))), max(1, int(math.ceil((n1_ - n.min()) / d)))
    if dx_m is None:
        dx_m = max(10.0, math.ceil(math.sqrt(float(e.max() - e.min()) * float(n.max() - n.min()) / areal) / 10.0) * 10.0)
        while True:
            e0, n1, nx, ny = caber(dx_m)
            if nx * ny <= areal:
                break
            dx_m += 10.0
    dx_m = float(dx_m)
    e0, n1, nx, ny = caber(dx_m)
    if nx * ny * nz > max_celulas:
        raise ErroEclipse(f"{nx} × {ny} × {nz} = {nx * ny * nz:,} células passa do teto de {max_celulas:,}. "
                          "Aumente o tamanho da célula ou diminua as camadas.".replace(",", "."))
    return {"camadas": escolhidas, "nk": nk.tolist(), "nz": nz, "dx": dx_m, "nx": nx, "ny": ny,
            "e0": e0, "n1": n1, "fuso": z, "sul": sul, "epsg": utm.epsg(z, sul), "max_celulas": max_celulas,
            "celulas": nx * ny * nz}


def _local(modelo, E, N, plano):
    o = modelo["origem"]
    la, lo = utm.de_utm(E, N, plano["fuso"], plano["sul"])
    x, y, _, _ = mbl.plano(la, lo, o["lat"], o["lon"])
    return x, y


def geometria(modelo: dict, plano: dict) -> dict:
    """Profundidade de cada superfície de camada nos nós (pilares), ACTNUM e FIPNUM."""
    sol, g = modelo["solido"], modelo["grade"]
    nx, ny, dx = plano["nx"], plano["ny"], plano["dx"]
    en = plano["e0"] + dx * np.arange(nx + 1)
    nn = plano["n1"] - dx * np.arange(ny + 1)                 # J cresce para o sul
    E, N = np.meshgrid(en, nn)
    x, y = _local(modelo, E, N, plano)
    indice = {c["chave"]: k for k, c in enumerate(sol["camadas"])}
    lims = [np.asarray(z, float) for z in sol["limites"]]
    sup_topo, sup_base = [], []                               # profundidade (m, + para baixo) nos nós
    fip = []
    for f, (c, nk) in enumerate(zip(plano["camadas"], plano["nk"])):
        k = indice[c["chave"]]
        topo = -mbs.bilinear(lims[k], g, x, y)
        base = -mbs.bilinear(lims[k + 1], g, x, y)
        base = np.maximum(base, topo)
        for s in range(nk):
            sup_topo.append(topo + (base - topo) * s / nk)
            sup_base.append(topo + (base - topo) * (s + 1) / nk)
            fip.append(f + 1)
    # centros das células: dentro do contorno?
    ec = plano["e0"] + dx * (np.arange(nx) + 0.5)
    nc = plano["n1"] - dx * (np.arange(ny) + 0.5)
    EC, NC = np.meshgrid(ec, nc)
    xc, yc = _local(modelo, EC, NC, plano)
    # ativa: o centro dentro do contorno ou a até meia diagonal de célula dele — senão a
    # célula de um poço no canto do contorno (os cantos são poços) ficaria de fora
    dentro = mbs.controlado(sol["contorno"], xc, yc, tol_km=dx * math.sqrt(2) / 2 / 1000)
    esp = [0.25 * ((b[:-1, :-1] - t[:-1, :-1]) + (b[:-1, 1:] - t[:-1, 1:]) + (b[1:, :-1] - t[1:, :-1]) +
                   (b[1:, 1:] - t[1:, 1:])) for t, b in zip(sup_topo, sup_base)]
    actnum = np.array([(dentro & (e >= ESP_ATIVA_M)) for e in esp], np.int8)      # (nz, ny, nx)
    return {"E": E, "N": N, "topo": sup_topo, "base": sup_base, "fip": fip, "actnum": actnum,
            "centro_x": xc, "centro_y": yc, "dentro": dentro, "espessura": np.array(esp)}


def zcorn(geo: dict) -> np.ndarray:
    """ZCORN na ordem do ECLIPSE: para cada camada, a face de cima e a de baixo; em cada face,
    para cada J, a linha da frente e a de trás, com os dois cantos de cada I."""
    def expandir(S):
        ny1, nx1 = S.shape
        j = np.repeat(np.arange(ny1 - 1), 2) + np.tile([0, 1], ny1 - 1)
        i = np.repeat(np.arange(nx1 - 1), 2) + np.tile([0, 1], nx1 - 1)
        return S[np.ix_(j, i)]
    partes = []
    for t, b in zip(geo["topo"], geo["base"]):
        partes += [expandir(t).ravel(), expandir(b).ravel()]
    return np.concatenate(partes)


def coord(geo: dict) -> np.ndarray:
    ztopo = float(min(t.min() for t in geo["topo"]))
    zbase = float(max(b.max() for b in geo["base"]))
    E, N = geo["E"].ravel(), geo["N"].ravel()
    return np.column_stack([E, N, np.full_like(E, ztopo), E, N, np.full_like(E, zbase)]).ravel()


# ============================================================== propriedades
def propriedades(modelo: dict, plano: dict, geo: dict) -> tuple[dict, list[str]]:
    """PORO e NTG por célula: grade da avaliação (3+ poços), média dos poços avaliados, ou o
    valor provisório (marcado). Devolve ({'PORO': (nz,ny,nx), 'NTG': …}, notas por formação)."""
    props = modelo.get("propriedades") or {}
    g = modelo["grade"]
    poro, ntg, notas = [], [], []
    for c, nk in zip(plano["camadas"], plano["nk"]):
        info = props.get(c["chave"]) or {}
        campos = {}
        for chave_m, chave_av, prov in (("PORO", "phi_media_pay", PORO_PROVISORIO), ("NTG", "ntg", NTG_PROVISORIO)):
            vals = [p[chave_av] for p in info.get("pocos", []) if p.get(chave_av) is not None]
            grade = (info.get("grades") or {}).get(chave_av)
            if grade is not None:
                z = np.array([[np.nan if v is None else v for v in linha] for linha in grade], float)
                media = float(np.mean(vals)) if vals else prov
                vz = mbs.bilinear(np.nan_to_num(z, nan=media), g, geo["centro_x"], geo["centro_y"])
                fora = ~np.isfinite(mbs.bilinear(z, g, geo["centro_x"], geo["centro_y"]))
                vz = np.where(fora, media, vz)
                campos[chave_m] = vz
                notas.append(f"{chave_m} {c['nome']}: grade da avaliação de formação ({len(vals)} poços; "
                             f"média {media:.3f} fora dela)")
            elif vals:
                campos[chave_m] = np.full(geo["centro_x"].shape, float(np.mean(vals)))
                notas.append(f"{chave_m} {c['nome']}: média de {len(vals)} poço(s) avaliado(s) = {np.mean(vals):.3f}")
            else:
                campos[chave_m] = np.full(geo["centro_x"].shape, prov)
                notas.append(f"{chave_m} {c['nome']}: PROVISÓRIO {prov} (sem avaliação de formação nesta formação)")
        poro += [campos["PORO"]] * nk
        ntg += [campos["NTG"]] * nk
    return {"PORO": np.clip(np.array(poro), 0.0, 0.5), "NTG": np.clip(np.array(ntg), 0.0, 1.0)}, notas


# ============================================================== poços
def nome_curto(pid: str, usados: set) -> str:
    """Nome de até 8 caracteres (limite do ECLIPSE): 1-AURI-12-RN → AURI12."""
    partes = pid.upper().split("-")
    miolo = [p for p in partes[1:-1]] if len(partes) >= 3 else partes
    base = re.sub(r"[^A-Z0-9]", "", "".join(miolo)) or re.sub(r"[^A-Z0-9]", "", pid.upper())
    nome = base[:8]
    k = 1
    while nome in usados:
        suf = str(k)
        nome = base[:8 - len(suf)] + suf
        k += 1
    usados.add(nome)
    return nome


def completacoes(modelo: dict, plano: dict, geo: dict) -> list[dict]:
    """Células ativas que o caminho de cada poço atravessa (I, J, K a partir de 1)."""
    o = modelo["origem"]
    nx, ny, dx = plano["nx"], plano["ny"], plano["dx"]
    nz = plano["nz"]
    usados: set = set()
    saida = []
    for p in modelo["pocos"]:
        cam = p.get("caminho") or []
        if len(cam) < 2:
            continue
        md = np.array([q[0] for q in cam], float)
        mds = np.arange(md[0], md[-1], 2.0)
        if not len(mds):
            continue
        xs = np.interp(mds, md, [q[1] for q in cam])
        ys = np.interp(mds, md, [q[2] for q in cam])
        cotas = np.interp(mds, md, [q[3] for q in cam])
        la, lo = mbl.para_geo(xs, ys, o["lat"], o["lon"])
        E, N = utm.para_utm(la, lo, plano["fuso"], plano["sul"])
        I = np.floor((E - plano["e0"]) / dx).astype(int)
        J = np.floor((plano["n1"] - N) / dx).astype(int)
        celulas = []
        for i, j, prof in zip(I, J, -cotas):
            if not (0 <= i < nx and 0 <= j < ny):
                continue
            for k in range(nz):
                t = 0.25 * (geo["topo"][k][j, i] + geo["topo"][k][j, i + 1] + geo["topo"][k][j + 1, i] +
                            geo["topo"][k][j + 1, i + 1])
                b = 0.25 * (geo["base"][k][j, i] + geo["base"][k][j, i + 1] + geo["base"][k][j + 1, i] +
                            geo["base"][k][j + 1, i + 1])
                if t <= prof < b and geo["actnum"][k, j, i]:
                    if not celulas or celulas[-1] != (i + 1, j + 1, k + 1):
                        celulas.append((i + 1, j + 1, k + 1))
                    break
        if celulas:
            saida.append({"poco": p["id"], "nome": nome_curto(p["id"], usados), "celulas": celulas,
                          "trajetoria": bool(p.get("trajetoria"))})
    return saida


# ============================================================== escrita
def _numeros(vals, casas: int, por_linha: int = 8) -> str:
    """Valores com repetição compactada (n*v), como o ECLIPSE lê."""
    out, linha = [], []
    fmt = "{:." + str(casas) + "f}"
    vals = list(vals)
    i = 0
    while i < len(vals):
        v = fmt.format(vals[i]) if casas else str(int(vals[i]))
        j = i + 1
        while j < len(vals) and (fmt.format(vals[j]) if casas else str(int(vals[j]))) == v:
            j += 1
        linha.append(f"{j - i}*{v}" if j - i > 1 else v)
        if len(linha) == por_linha:
            out.append(" ".join(linha))
            linha = []
        i = j
    if linha:
        out.append(" ".join(linha))
    return "\n".join(out) + "\n/\n"


def _ascii(texto: str) -> str:
    """Simuladores leem ASCII: acentos tirados (Formação → Formacao), não trocados por '?'."""
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")


def nome_deck(titulo: str, ident: str) -> str:
    base = re.sub(r"[^A-Za-z0-9]+", "_", _ascii(titulo or "")).strip("_").upper()[:24]
    return base or "SIAPP_" + ident.replace("bloco_", "")[:15]


def exportar(modelo: dict, pasta: str, ident: str, *, camadas: list[str] | None = None, nz: int | None = None,
             dx_m: float | None = None, max_celulas: int = MAX_CELULAS_PADRAO, titulo: str = "",
             inicio: date | None = None) -> dict:
    plano = planejar(modelo, camadas, nz, dx_m, max_celulas)
    geo = geometria(modelo, plano)
    props, notas = propriedades(modelo, plano, geo)
    pocos = completacoes(modelo, plano, geo)
    nome = nome_deck(titulo, ident)
    destino = os.path.join(pasta, f"{ident}_eclipse")
    os.makedirs(destino, exist_ok=True)
    nx, ny, nz = plano["nx"], plano["ny"], plano["nz"]
    ativos = int(geo["actnum"].sum())
    if ativos == 0:
        raise ErroEclipse("Nenhuma célula ativa: confira as formações escolhidas.")
    inicio = inicio or date.today()
    arq = {}

    def gravar(sufixo, texto):
        caminho = os.path.join(destino, nome + sufixo)
        with open(caminho, "w", encoding="ascii", errors="replace", newline="\n") as f:
            f.write(_ascii(texto))
        arq[sufixo] = caminho
        return os.path.basename(caminho)
    cab = (f"-- {nome}: gerado pelo SIAPP {__version__} a partir do bloco {ident}\n"
           f"-- Topos: AGP (ANP), interpretacao da operadora. SIRGAS 2000 / UTM {plano['fuso']}"
           f"{'S' if plano['sul'] else 'N'} (EPSG:{plano['epsg']}); profundidade = -cota (m, abaixo do nivel do mar).\n")
    # GRDECL
    f_grid = gravar(".GRDECL", cab + "\nMAPUNITS\n  'METRES' /\n\nGRIDUNIT\n  'METRES' ' ' /\n\n"
                    f"SPECGRID\n  {nx} {ny} {nz} 1 F /\n\nCOORD\n" + _numeros(coord(geo), 2, 6) +
                    "\nZCORN\n" + _numeros(zcorn(geo), 2, 8) + "\nACTNUM\n" + _numeros(geo["actnum"].ravel(), 0, 20))
    f_poro = gravar("_PORO_NTG.inc", cab + "-- PORO e NTG por celula (ordem I, J, K). Origem por formacao:\n" +
                    "".join(f"--   {n_}\n" for n_ in notas) +
                    "\nPORO\n" + _numeros(props["PORO"].ravel(), 4, 10) + "\nNTG\n" + _numeros(props["NTG"].ravel(), 4, 10))
    perm = np.full((nz, ny, nx), PERM_PROVISORIA_MD)
    f_perm = gravar("_PERM.inc", cab + f"-- PROVISORIO: o SIAPP nao tem permeabilidade. {PERM_PROVISORIA_MD:g} mD em tudo,\n"
                    "-- PERMZ = 0,1 x PERMX. TROQUE antes de simular (testemunho, teste de formacao, correlacao).\n"
                    "\nPERMX\n" + _numeros(perm.ravel(), 1, 10) + "\nPERMY\n" + _numeros(perm.ravel(), 1, 10) +
                    "\nPERMZ\n" + _numeros((perm * 0.1).ravel(), 1, 10))
    fip = np.repeat(np.array(geo["fip"])[:, None, None], ny * nx, axis=1).reshape(nz, ny, nx)
    f_fip = gravar("_FIPNUM.inc", cab + "-- Uma regiao por formacao:\n" +
                   "".join(f"--   {k + 1} = {c['nome']}\n" for k, c in enumerate(plano["camadas"])) +
                   "\nFIPNUM\n" + _numeros(fip.ravel(), 0, 20))
    f_pvt = gravar("_PVT.inc", cab + "-- PROVISORIO: oleo morto e agua genericos, so para o deck rodar. TROQUE pelo PVT do campo.\n"
                   "\nPVTW\n-- Pref(bar) Bw   Cw(1/bar) visc(cP) viscosibilidade\n   200   1.02  4.5E-5   0.5   0 /\n"
                   "\nPVDO\n-- P(bar) Bo   visc(cP)\n   50   1.10  3.0\n  150   1.08  3.2\n  300   1.06  3.5 /\n"
                   "\nDENSITY\n-- oleo agua gas (kg/m3)\n   880 1030 0.9 /\n"
                   "\nROCK\n-- Pref(bar) compressibilidade(1/bar)\n   200  5.0E-5 /\n")
    f_scal = gravar("_SCAL.inc", cab + "-- PROVISORIO: Corey generico (Swc 0,2; Sor 0,2; nw = no = 2), sem pressao capilar. TROQUE.\n"
                    "\nSWOF\n-- Sw   krw    kro    Pc\n" +
                    "".join(f"  {sw:.3f} {max(0.0, (sw - 0.2) / 0.6) ** 2:.4f} {max(0.0, (0.8 - sw) / 0.6) ** 2:.4f} 0\n"
                            for sw in np.linspace(0.2, 0.8, 7)) + "  1.000 1.0000 0.0000 0 /\n")
    t0 = geo["topo"][0]
    topo_cel = 0.25 * (t0[:-1, :-1] + t0[:-1, 1:] + t0[1:, :-1] + t0[1:, 1:])
    datum = float(topo_cel[geo["dentro"]].mean()) if geo["dentro"].any() else float(topo_cel.mean())
    base_max = float(max(b.max() for b in geo["base"]))
    f_sol = gravar("_SOLUCAO.inc", cab + "-- PROVISORIO: pressao hidrostatica (0,1 bar/m) no topo da 1a formacao e contato oleo-agua\n"
                   "-- abaixo de tudo (o bloco inteiro com oleo). TROQUE pelo contato e pela pressao do campo.\n"
                   f"\nEQUIL\n-- datum(m) P(bar) OWC(m) Pcow GOC(m) Pcog\n   {datum:.1f} {max(1.0, datum * 0.1):.1f} "
                   f"{base_max + 10:.1f} 0 {max(0.0, datum - 100):.1f} 0 /\n")
    linhas_w = ["-- Pocos do bloco, com o caminho real quando a trajetoria foi lida; todos FECHADOS ('SHUT').",
                "-- Abra, complete e controle como o estudo pedir. Nomes curtos (8 caracteres):"]
    linhas_w += [f"--   {w['nome']:8s} = {w['poco']}" + (" (trajetoria)" if w["trajetoria"] else "") for w in pocos]
    texto_w = "\n".join(linhas_w) + "\n"
    if pocos:
        texto_w += "\nWELSPECS\n" + "".join(
            f"  '{w['nome']}' 'G1' {w['celulas'][0][0]} {w['celulas'][0][1]} 1* 'OIL' /\n" for w in pocos) + "/\n"
        texto_w += "\nCOMPDAT\n" + "".join(
            f"  '{w['nome']}' {i} {j} {k} {k} 'SHUT' 1* 1* 0.2159 /\n" for w in pocos for i, j, k in w["celulas"]) + "/\n"
    f_w = gravar("_POCOS.inc", cab + texto_w)
    n_fip = len(plano["camadas"])
    n_conex = sum(len(w["celulas"]) for w in pocos)
    data_txt = f"{inicio.day} '{MESES[inicio.month - 1]}' {inicio.year}"
    deck = (cab + "-- Valores PROVISORIOS em _PERM, _PVT, _SCAL e _SOLUCAO: ver LEIA-ME.txt.\n\n"
            "RUNSPEC\n\nTITLE\n" + f"{nome}\n\nDIMENS\n  {nx} {ny} {nz} /\n\nMETRIC\n\nOIL\nWATER\n\n"
            f"START\n  {data_txt} /\n\nEQLDIMS\n  1 /\n\nTABDIMS\n  1 1 20 20 {n_fip} /\n\nREGDIMS\n  {n_fip} 1 0 0 /\n\n"
            f"WELLDIMS\n  {max(1, len(pocos))} {max(1, n_conex)} 1 {max(1, len(pocos))} /\n\nUNIFOUT\n\n"
            f"GRID\n\nINCLUDE\n  '{f_grid}' /\n\nINCLUDE\n  '{f_poro}' /\n\nINCLUDE\n  '{f_perm}' /\n\n"
            f"PINCH\n  {ESP_ATIVA_M:g} GAP 1* TOPBOT TOP /\n\nINIT\n\n"
            f"PROPS\n\nINCLUDE\n  '{f_pvt}' /\n\nINCLUDE\n  '{f_scal}' /\n\n"
            f"REGIONS\n\nINCLUDE\n  '{f_fip}' /\n\n"
            f"SOLUTION\n\nINCLUDE\n  '{f_sol}' /\n\n"
            "SUMMARY\n\nFPR\nFOIP\nFWIP\nRPR\n/\nROIP\n/\n\n"
            f"SCHEDULE\n\nINCLUDE\n  '{f_w}' /\n\nTSTEP\n  1 /\n\nEND\n")
    f_deck = gravar(".DATA", deck)
    vol_poroso = _volume_poroso(geo, props, plano)
    leia = os.path.join(destino, "LEIA-ME.txt")
    with open(leia, "w", encoding="utf-8") as f:
        f.write(f"Deck {nome} — SIAPP {__version__}, bloco {ident}\n\n")
        f.write(f"Grade corner-point {nx} x {ny} x {nz} = {nx * ny * nz:,} células ({ativos:,} ativas), "
                f"células de {plano['dx']:g} m; teto {plano['max_celulas']:,}.\n".replace(",", "."))
        f.write(f"Coordenadas: SIRGAS 2000 / UTM {plano['fuso']}{'S' if plano['sul'] else 'N'} (EPSG:{plano['epsg']}); "
                "profundidade = −cota, em metros abaixo do nível do mar. I para leste, J para o sul, K para baixo.\n\n")
        f.write("Formações (FIPNUM) e camadas:\n")
        for k, (c, nk) in enumerate(zip(plano["camadas"], plano["nk"])):
            f.write(f"  {k + 1}: {c['nome']} — {nk} camada(s)\n")
        f.write("\nDO DADO (SIAPP):\n  - geometria (topos e bases do bloco fechado, AGP); ACTNUM (centro a mais de meia "
                f"diagonal de célula fora do contorno do bloco, ou mais fina que {ESP_ATIVA_M:g} m: inativa); "
                "FIPNUM;\n")
        for n_ in notas:
            f.write(f"  - {n_}\n")
        f.write("  - poços (WELSPECS/COMPDAT), todos fechados.\n\n")
        f.write("PROVISÓRIO (o SIAPP não tem esse dado — troque antes de simular):\n"
                f"  - {nome}_PERM.inc: {PERM_PROVISORIA_MD:g} mD em tudo;\n"
                f"  - {nome}_PVT.inc: óleo morto e água genéricos;\n"
                f"  - {nome}_SCAL.inc: Corey genérico;\n"
                f"  - {nome}_SOLUCAO.inc: pressão hidrostática e contato abaixo de tudo.\n")
        f.write("\nVolume poroso das células ativas (PORO × NTG × volume): "
                + "; ".join(f"{c['nome']} {v / 1e6:,.1f} milhões de m³".replace(",", "X").replace(".", ",").replace("X", ".")
                            for c, v in zip(plano["camadas"], vol_poroso)) + ".\n")
        f.write("\nPoços (nome no deck = poço):\n" + "".join(f"  {w['nome']:8s} = {w['poco']} ({len(w['celulas'])} células)\n"
                                                           for w in pocos))
    arq["LEIA-ME"] = leia
    return {"pasta": destino, "deck": f_deck, "arquivos": list(arq.values()), "nx": nx, "ny": ny, "nz": nz,
            "dx": plano["dx"], "celulas": nx * ny * nz, "ativas": ativos, "epsg": plano["epsg"],
            "camadas": [{"chave": c["chave"], "nome": c["nome"], "nk": nk} for c, nk in zip(plano["camadas"], plano["nk"])],
            "pocos": len(pocos), "notas": notas, "volume_poroso_m3": vol_poroso}


def _volume_poroso(geo, props, plano) -> list[float]:
    area = plano["dx"] ** 2
    vp = props["PORO"] * props["NTG"] * geo["espessura"] * area * geo["actnum"]
    out, k = [], 0
    for nk in plano["nk"]:
        out.append(float(vp[k:k + nk].sum()))
        k += nk
    return out
