"""Bloco fechado: o volume inteiro, do terreno a uma base plana, fatiado nas unidades.

O modo *Superfícies* (motor/bloco.py) interpola o topo de cada unidade só onde há poços com
ela. O **bloco fechado** preenche o contorno convexo dos poços (mais a margem) de uma ponta à
outra, com paredes retas, como um bloco-diagrama. Para isso precisa de uma regra para onde a
unidade não foi vista — e a regra é a das **espessuras (isópacas)**, que nunca deixa duas
superfícies se cruzarem:

- **limites**: o limite *k* é o topo da unidade *k* na ordem estratigráfica (a da legenda); o
  último é a base da última unidade. Num poço, o limite *k* é observado se o poço chegou a
  alguma unidade de índice ≥ *k*: é o topo da primeira delas (unidade ausente = espessura 0,
  o poço passou pela posição dela);
- **espessura** da unidade *k* num poço = limite *k* − limite *k*+1, quando os dois foram
  observados; poço que parou antes, ou base não atingida na última unidade: desconhecida
  (não entra, em vez de entrar como zero);
- um **limite de referência** (o mais fundo observado em quase todos os poços) é interpolado
  direto; os de cima somam espessuras, os de baixo subtraem. Espessura interpolada é ≥ 0,
  então os limites nunca se cruzam;
- **topo** = terreno (cota altimétrica do cadastro da ANP; sem ela, a mesa rotativa menos a
  diferença mediana mesa − terreno dos outros poços); o que estiver acima é cortado. Entre o
  terreno e o primeiro topo do AGP fica uma camada cinza, *sem descrição no AGP* (cota
  altimétrica 0,0 no cadastro = não informada; sem nenhuma, a mesa menos 5 m);
- **base plana**: abaixo do poço mais fundo (ou a cota pedida); a última unidade sem base
  atingida vai até ela (com base atingida, entre a base dela e a base do bloco fica outra
  camada cinza, *abaixo da última unidade*);
- **interpolação**: linear nos triângulos de Delaunay dos poços com o dado; fora do contorno
  deles, o valor do ponto mais próximo da borda do contorno (linear entre os dois poços da
  aresta: contínuo, sem degrau na borda). Essa parte é **extrapolada** e a janela a mostra mais
  clara (`controle` de cada camada: o contorno convexo dos poços com a espessura).

Tudo é guardado em grades (a mesma grade do modelo): é a forma que a janela, a figura e a
exportação para simuladores (corner-point) usam. A malha do contorno (`malha_contorno`)
recorta as células da grade pelo polígono, para que as paredes fiquem retas.
"""

from __future__ import annotations

import math

import numpy as np

from . import bloco as mbl
from . import interpolacao as mint

COR_COBERTURA = "#d9d6cf"
CHAVE_COBERTURA = "_cobertura"
CHAVE_ABAIXO = "_abaixo"
ESPESSURA_MIN_M = 0.5            # abaixo disso a camada não aparece (acunhamento)
DIF_MESA_PADRAO_M = 5.0          # mesa − terreno sem nenhum poço com cota altimétrica (Potiguar: ~5,5)
COBERTURA_MIN_M = 5.0            # cobertura mais fina que isso é só a diferença mesa/terreno
FRACAO_REFERENCIA = 0.9          # referência: o limite mais fundo com ≥ 90% das observações


# ============================================================== grade
def interpolar_grade(pts, valores, grade: dict) -> tuple[np.ndarray, np.ndarray]:
    """Valor em todos os nós da grade: linear nos triângulos dos pontos; fora deles, o do
    ponto mais próximo na borda do contorno (com menos de 3 pontos ou alinhados: o do ponto
    mais próximo). Devolve (z, controle), controle = nó dentro do contorno dos pontos."""
    pts, valores = unicos(pts, valores)
    nx, ny = grade["nx"], grade["ny"]
    gx, gy = _nos(grade)
    if len(pts) == 0:
        return np.full((ny, nx), np.nan), np.zeros((ny, nx), bool)
    z = np.full((ny, nx), np.nan)
    controle = np.zeros((ny, nx), bool)
    h = mbl.contorno_convexo(pts)
    if len(pts) >= 3 and len(h) >= 3 and mbl.largura_relativa(h) >= mbl.FRACAO_COLINEAR:
        tris = mbl.delaunay(pts)
        z = _linear(pts, valores, tris, grade)
        controle = mbl.dentro(h, gx, gy) & ~np.isnan(z)
        falta = np.isnan(z)
        if falta.any():
            z[falta] = _pela_borda(pts, valores, h, gx[falta], gy[falta])
    falta = np.isnan(z)
    if falta.any():
        _, k = mbl.distancia_mais_proximo(pts, gx[falta], gy[falta])
        z[falta] = valores[k]
    return z, controle


def unicos(pts, valores) -> tuple[np.ndarray, np.ndarray]:
    """Pontos repetidos (mesma posição, ao milímetro) viram um só, com a média dos valores —
    poços do mesmo pad, ou o topo de duas unidades no mesmo ponto."""
    pts, valores = np.asarray(pts, float).reshape(-1, 2), np.asarray(valores, float)
    if len(pts) == 0:
        return pts, valores
    chaves = [(round(float(a), 6), round(float(b), 6)) for a, b in pts]
    grupos: dict = {}
    for i, c in enumerate(chaves):
        grupos.setdefault(c, []).append(i)
    if len(grupos) == len(pts):
        return pts, valores
    ids = list(grupos.values())
    return (np.array([pts[g[0]] for g in ids]), np.array([float(np.mean(valores[g])) for g in ids]))


def _pela_borda(pts, valores, h, x, y) -> np.ndarray:
    """Valor no ponto mais próximo da borda do contorno convexo `h`: as arestas do contorno
    são arestas da triangulação, e nelas a interpolação linear vai de um poço ao outro.
    (`pts` sem repetidos.)"""
    val = {(round(float(a), 9), round(float(b), 9)): v for (a, b), v in zip(pts, valores)}
    vh = np.array([val[(round(float(a), 9), round(float(b), 9))] for a, b in h])
    melhor = np.full(x.shape, np.inf)
    out = np.zeros(x.shape)
    for k in range(len(h)):
        a, b = h[k], h[(k + 1) % len(h)]
        d = b - a
        L2 = float(d @ d)
        t = np.clip(((x - a[0]) * d[0] + (y - a[1]) * d[1]) / L2, 0, 1) if L2 > 0 else np.zeros(x.shape)
        dist = np.hypot(a[0] + t * d[0] - x, a[1] + t * d[1] - y)
        m = dist < melhor
        melhor[m] = dist[m]
        out[m] = ((1 - t) * vh[k] + t * vh[(k + 1) % len(h)])[m]
    return out


def _nos(grade: dict):
    return np.meshgrid(grade["x0"] + grade["passo"] * np.arange(grade["nx"]),
                       grade["y0"] + grade["passo"] * np.arange(grade["ny"]))


def _linear(pts, valores, tris, grade: dict) -> np.ndarray:
    """Interpolação linear nos triângulos, olhando só os nós da caixa de cada triângulo (a
    grade é regular), NaN fora deles."""
    x0, y0, p, nx, ny = grade["x0"], grade["y0"], grade["passo"], grade["nx"], grade["ny"]
    z = np.full((ny, nx), np.nan)
    for t in tris:
        (ax, ay), (bx, by), (cx, cy) = pts[t]
        det = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(det) < 1e-15:
            continue
        i0 = max(0, int(math.floor((min(ax, bx, cx) - x0) / p)))
        i1 = min(nx - 1, int(math.ceil((max(ax, bx, cx) - x0) / p)))
        j0 = max(0, int(math.floor((min(ay, by, cy) - y0) / p)))
        j1 = min(ny - 1, int(math.ceil((max(ay, by, cy) - y0) / p)))
        if i1 < i0 or j1 < j0:
            continue
        X, Y = np.meshgrid(x0 + p * np.arange(i0, i1 + 1), y0 + p * np.arange(j0, j1 + 1))
        l1 = ((by - cy) * (X - cx) + (cx - bx) * (Y - cy)) / det
        l2 = ((cy - ay) * (X - cx) + (ax - cx) * (Y - cy)) / det
        l3 = 1 - l1 - l2
        ok = (l1 >= -1e-9) & (l2 >= -1e-9) & (l3 >= -1e-9)
        sub = z[j0:j1 + 1, i0:i1 + 1]
        ok &= np.isnan(sub)
        sub[ok] = (l1 * valores[t[0]] + l2 * valores[t[1]] + l3 * valores[t[2]])[ok]
    return z


def bilinear(z, grade: dict, x, y) -> np.ndarray:
    """Valor da grade `z` (ny × nx) nos pontos (x, y), por interpolação bilinear."""
    z = np.asarray(z, float)
    x, y = np.asarray(x, float), np.asarray(y, float)
    fx = np.clip((x - grade["x0"]) / grade["passo"], 0, grade["nx"] - 1)
    fy = np.clip((y - grade["y0"]) / grade["passo"], 0, grade["ny"] - 1)
    i = np.minimum(np.floor(fx).astype(int), grade["nx"] - 2)
    j = np.minimum(np.floor(fy).astype(int), grade["ny"] - 2)
    u, v = fx - i, fy - j
    return ((1 - u) * (1 - v) * z[j, i] + u * (1 - v) * z[j, i + 1] +
            (1 - u) * v * z[j + 1, i] + u * v * z[j + 1, i + 1])


# ============================================================== malha
def recortar(poligono: list, semiplanos: list) -> list:
    """Recorta um polígono convexo por semiplanos (a, b, c): fica a·x + b·y + c ≥ 0
    (Sutherland–Hodgman)."""
    pol = [tuple(p) for p in poligono]
    for a, b, c in semiplanos:
        if not pol:
            break
        novo = []
        for k in range(len(pol)):
            p, q = pol[k], pol[(k + 1) % len(pol)]
            fp, fq = a * p[0] + b * p[1] + c, a * q[0] + b * q[1] + c
            if fp >= 0:
                novo.append(p)
            if (fp >= 0) != (fq >= 0):
                s = fp / (fp - fq)
                novo.append((p[0] + s * (q[0] - p[0]), p[1] + s * (q[1] - p[1])))
        pol = novo
    return pol


def semiplanos_do_poligono(poligono) -> list:
    """Semiplanos de um polígono convexo anti-horário (o lado de dentro de cada aresta)."""
    p = np.asarray(poligono, float)
    out = []
    for k in range(len(p)):
        (x1, y1), (x2, y2) = p[k], p[(k + 1) % len(p)]
        a, b = -(y2 - y1), (x2 - x1)
        n = math.hypot(a, b)
        if n > 0:
            out.append((a / n, b / n, -(a * x1 + b * y1) / n))
    return out


def malha_contorno(grade: dict, poligono, extra: list | None = None) -> dict:
    """Triângulos que cobrem o polígono convexo, feitos das células da grade recortadas por
    ele (borda reta). `extra`: semiplanos a mais (o corte da figura). Devolve
    {pts: N×2, tris: M×3}."""
    x0, y0, p, nx, ny = grade["x0"], grade["y0"], grade["passo"], grade["nx"], grade["ny"]
    planos = semiplanos_do_poligono(poligono) + list(extra or [])
    gx, gy = _nos(grade)
    tol = 1e-9 * max(1.0, abs(x0) + abs(y0) + p * max(nx, ny))
    dentro_no = np.ones(gx.shape, bool)
    for a, b, c in planos:
        dentro_no &= a * gx + b * gy + c >= -tol
    cel = dentro_no[:-1, :-1] & dentro_no[:-1, 1:] & dentro_no[1:, :-1] & dentro_no[1:, 1:]
    pts: list = []
    indice: dict = {}

    def ponto(x, y):
        k = (round(x, 7), round(y, 7))
        if k not in indice:
            indice[k] = len(pts)
            pts.append((x, y))
        return indice[k]
    tris = []
    # células inteiras dentro: dois triângulos
    js, is_ = np.nonzero(cel)
    for j, i in zip(js.tolist(), is_.tolist()):
        a = ponto(x0 + p * i, y0 + p * j)
        b = ponto(x0 + p * (i + 1), y0 + p * j)
        c = ponto(x0 + p * (i + 1), y0 + p * (j + 1))
        d = ponto(x0 + p * i, y0 + p * (j + 1))
        tris += [(a, b, c), (a, c, d)]
    # células da borda: recortadas
    algum = dentro_no[:-1, :-1] | dentro_no[:-1, 1:] | dentro_no[1:, :-1] | dentro_no[1:, 1:]
    pol = np.asarray(poligono, float)
    bx0, by0 = pol.min(0)
    bx1, by1 = pol.max(0)
    i0, i1 = max(0, int((bx0 - x0) // p) - 1), min(nx - 2, int((bx1 - x0) // p) + 1)
    j0, j1 = max(0, int((by0 - y0) // p) - 1), min(ny - 2, int((by1 - y0) // p) + 1)
    for j in range(j0, j1 + 1):
        for i in range(i0, i1 + 1):
            if cel[j, i]:
                continue
            xa, ya = x0 + p * i, y0 + p * j
            sq = [(xa, ya), (xa + p, ya), (xa + p, ya + p), (xa, ya + p)]
            r = recortar(sq, planos)
            if len(r) < 3 or (not algum[j, i] and _area(r) < 1e-12 * p * p):
                continue
            if _area(r) < 1e-9 * p * p:
                continue
            ids = [ponto(x, y) for x, y in r]
            ids = [v for k, v in enumerate(ids) if v != ids[k - 1]]
            for k in range(1, len(ids) - 1):
                tris.append((ids[0], ids[k], ids[k + 1]))
    return {"pts": np.array(pts, float).reshape(-1, 2), "tris": np.array(tris, int).reshape(-1, 3)}


def _area(pol) -> float:
    return mbl.area_shoelace(pol) if len(pol) >= 3 else 0.0


def borda(grade: dict, poligono) -> np.ndarray:
    """Pontos ao longo do polígono (fechado): os vértices e onde as arestas cruzam as linhas
    da grade — os mesmos vértices da malha recortada, para as paredes casarem com o topo."""
    x0, y0, p = grade["x0"], grade["y0"], grade["passo"]
    pol = np.asarray(poligono, float)
    out = []
    for k in range(len(pol)):
        a, b = pol[k], pol[(k + 1) % len(pol)]
        ts = {0.0}
        for eixo, orig in ((0, x0), (1, y0)):
            lo, hi = sorted((a[eixo], b[eixo]))
            if hi - lo < 1e-12:
                continue
            for n in range(int(math.ceil((lo - orig) / p)), int(math.floor((hi - orig) / p)) + 1):
                t = (orig + n * p - a[eixo]) / (b[eixo] - a[eixo])
                if 1e-9 < t < 1 - 1e-9:
                    ts.add(t)
        out += [a + t * (b - a) for t in sorted(ts)]
    out.append(pol[0])
    return np.array(out, float)


# ============================================================== bloco fechado
def observacoes(modelo: dict) -> dict:
    """O que os poços dizem, nas regras do bloco fechado (usado pela montagem, pela validação
    cruzada e pelo prognóstico, para os três seguirem exatamente as mesmas regras).

    - terreno: [(x, y, cota, poço)];
    - lim[k]: [(x, y, cota, poço, presente)] — limite *k* observado no poço; `presente` = é o
      topo da própria unidade *k* (e não o de uma mais funda, com a *k* ausente);
    - esp[k]: [(x, y, espessura, poço)] — espessura da unidade *k* (≥ 0);
    - referencia: índice do limite interpolado direto (o mais fundo com ≥ 90% das observações).
    """
    pocos, legenda = modelo["pocos"], modelo["legenda"]
    ordem = {u["chave"]: k for k, u in enumerate(legenda)}
    n = len(legenda)
    terreno, fonte = [], {"cadastro": 0, "mesa": 0}
    difs = [p["mesa"] - p["terreno"] for p in pocos if p.get("terreno") is not None and p["mesa"] is not None]
    dif = float(np.median(difs)) if difs else DIF_MESA_PADRAO_M
    for p in pocos:
        if p.get("terreno") is not None:
            terreno.append((p["x"], p["y"], float(p["terreno"]), p["id"]))
            fonte["cadastro"] += 1
        elif p["mesa"] is not None:
            terreno.append((p["x"], p["y"], float(p["mesa"]) - dif, p["id"]))
            fonte["mesa"] += 1
    lim = [[] for _ in range(n + 1)]
    esp = [[] for _ in range(n)]
    negativas = set()
    for p in pocos:
        us = sorted((u for u in p["unidades"] if u["chave"] in ordem), key=lambda u: ordem[u["chave"]])
        if not us:
            continue
        por = {}
        for u in us:                                  # unidade repetida: a de cima
            por.setdefault(ordem[u["chave"]], u)
        ultimo = max(por)
        B = [None] * (n + 1)
        for k in range(n + 1):
            j = next((j for j in sorted(por) if j >= k), None)
            if j is not None:
                B[k] = (por[j]["x"], por[j]["y"], por[j]["cota_topo"], p["id"], j == k)
        u = por[ultimo]
        if u.get("base_atingida") and ultimo + 1 <= n:
            B[ultimo + 1] = (u["x"], u["y"], u["cota_base"], p["id"], False)
        for k in range(n + 1):
            if B[k] is not None:
                lim[k].append(B[k])
        for k in range(n):
            if B[k] is not None and B[k + 1] is not None:
                e = B[k][2] - B[k + 1][2]
                if e < -0.5:
                    negativas.add(p["id"])
                esp[k].append((B[k][0], B[k][1], max(0.0, e), p["id"]))
    cont = [len(v) for v in lim[:n]]
    ref = max(k for k in range(n) if cont[k] >= FRACAO_REFERENCIA * max(cont)) if n and max(cont) else None
    return {"n": n, "ordem": ordem, "terreno": terreno, "fonte": fonte, "dif": dif, "dif_medida": bool(difs),
            "lim": lim, "esp": esp, "negativas": negativas, "referencia": ref}


def montar(modelo: dict, *, base_cota: float | None = None) -> dict:
    """Bloco fechado a partir do modelo do bloco (motor/bloco.montar). Não lê o banco."""
    pocos, legenda, g = modelo["pocos"], modelo["legenda"], modelo["grade"]
    avisos: list[str] = []
    contorno = np.asarray(modelo["contorno"], float)
    if len(contorno) < 3 or mbl.largura_relativa(contorno) < mbl.FRACAO_COLINEAR:
        return {"ok": False, "avisos": ["Poços quase alinhados: sem bloco fechado (a direção transversal não "
                                         "tem dado)."]}
    if not legenda:
        return {"ok": False, "avisos": ["Sem unidades com topo no AGP: sem bloco fechado."]}
    poligono = mbl.com_margem(contorno, modelo.get("margem_km") or 0.0)
    ordem = {u["chave"]: k for k, u in enumerate(legenda)}
    n = len(legenda)

    ob = observacoes(modelo)
    tp, tv = [o[:2] for o in ob["terreno"]], [o[2] for o in ob["terreno"]]
    lim_pts, lim_val = [[o[:2] for o in L] for L in ob["lim"]], [[o[2] for o in L] for L in ob["lim"]]
    esp_pts, esp_val = [[o[:2] for o in L] for L in ob["esp"]], [[o[2] for o in L] for L in ob["esp"]]
    fonte, dif, negativas = ob["fonte"], ob["dif"], ob["negativas"]
    if not tp:
        return {"ok": False, "avisos": ["Nenhum poço com cota do terreno ou da mesa: sem bloco fechado."]}
    if fonte["mesa"]:
        avisos.append(f"Terreno: {fonte['mesa']} poço(s) sem cota altimétrica no cadastro, usada a mesa rotativa "
                      f"menos {dif:.1f} m " + ("(diferença mediana dos outros)." if ob["dif_medida"]
                                               else "(diferença típica)."))
    terreno, _ = interpolar_grade(tp, tv, g)
    if negativas:
        avisos.append(f"Ordem das unidades diferente da ordem média em {len(negativas)} poço(s) (espessura negativa "
                      f"tratada como zero): {', '.join(sorted(negativas)[:12])}{'…' if len(negativas) > 12 else ''}.")

    ref = ob["referencia"]
    if ref is None:
        return {"ok": False, "avisos": ["Sem topos utilizáveis: sem bloco fechado."]}
    cont = [len(v) for v in lim_val[:n]]
    if cont[ref] < 3:
        avisos.append(f"Referência ({legenda[ref]['nome']}) com só {cont[ref]} poço(s): o bloco é plano por partes.")

    # ---- empilhamento por espessuras
    lim = [None] * (n + 1)
    cfg = mint.configuracao((modelo.get("parametros") or {}).get("interpolacao"))
    lim[ref], _, aj_ref = mint.grade(cfg["estrutura"], ob["lim"][ref], g)
    metodos = {"estrutura": aj_ref.descricao(), "espessura": {}}
    esp = [None] * n
    for k in range(n):
        if esp_val[k]:
            z, _, aj = mint.grade(cfg["espessura"], ob["esp"][k], g, campo="espessura")
            esp[k] = np.maximum(z, 0.0)
            metodos["espessura"][legenda[k]["chave"]] = aj.descricao()
            for a_ in aj.avisos:
                avisos.append(f"Espessura de {legenda[k]['nome']}: {a_}.")
    for a_ in aj_ref.avisos:
        avisos.append(f"Referência ({legenda[ref]['nome']}): {a_}.")
    if cfg["empilhamento"] == "topos":
        # cada limite direto dos poços; o que não tem observação sai da espessura de cima
        metodos["estrutura"] = {}
        for k in range(n + 1):
            if k == ref:
                metodos["estrutura"][legenda[k]["chave"]] = aj_ref.descricao()
                continue
            if ob["lim"][k]:
                lim[k], _, ajk = mint.grade(cfg["estrutura"], ob["lim"][k], g)
                if k < n:
                    metodos["estrutura"][legenda[k]["chave"]] = ajk.descricao()
            elif k > 0 and lim[k - 1] is not None and esp[k - 1] is not None:
                lim[k] = lim[k - 1] - esp[k - 1]
        for k in range(1, n + 1):                       # não cruzar: corta no de cima
            if lim[k] is not None and lim[k - 1] is not None:
                lim[k] = np.minimum(lim[k], lim[k - 1])
    else:
        for k in range(ref - 1, -1, -1):
            lim[k] = lim[k + 1] + (esp[k] if esp[k] is not None else 0.0)
        for k in range(ref, n):
            if esp[k] is None:
                break
            lim[k + 1] = lim[k] - esp[k]

    # ---- base plana
    fundos = [p["cota_fundo"] for p in pocos if p.get("cota_fundo") is not None]
    obs = [v for vs in lim_val for v in vs]
    # pelo dado (fundos dos poços e limites observados), não pela interpolação: espessuras
    # extrapoladas na borda podem descer muito além de qualquer poço — ali o bloco é cortado
    baixo = min(fundos + obs)
    alto = float(np.max(terreno))
    if base_cota is None:
        folga = max(10.0, 0.05 * (alto - baixo))
        base = math.floor((baixo - folga) / 10.0) * 10.0
    else:
        base = float(base_cota)
        if base > baixo:
            avisos.append(f"Base pedida ({base:.0f} m) acima do ponto mais fundo dos dados ({baixo:.0f} m): o que "
                          "estiver abaixo dela fica de fora.")
    for k in range(n + 1):
        if lim[k] is None:
            lim[k] = np.full_like(terreno, base)
    sem_base = [legenda[k]["nome"] for k in range(n) if esp[k] is None]
    if sem_base:
        avisos.append(f"Sem base atingida nos poços: {', '.join(sem_base)} {'vai' if len(sem_base) == 1 else 'vão'} "
                      f"até a base plana do bloco ({base:.0f} m).")

    # corta no terreno e na base (min/max com o mesmo campo preservam a ordem)
    lim = [np.clip(np.minimum(z, terreno), base, None) for z in lim]
    terreno_c = np.maximum(terreno, base)

    # ---- camadas: cobertura (terreno → 1º topo) + unidades
    limites = [terreno_c] + lim
    camadas = [{"chave": CHAVE_COBERTURA, "nome": "sem descrição no AGP", "cor": COR_COBERTURA, "slot": None,
                "n_espessuras": len(tp), "controle": contorno_dados(tp)}]
    for k, u in enumerate(legenda):
        # a última unidade sem espessura medida: controle pelos poços que chegaram ao topo dela
        c = contorno_dados(esp_pts[k] if esp_val[k] else lim_pts[k])
        camadas.append({"chave": u["chave"], "nome": u["nome"], "cor": u["cor"], "slot": u.get("slot"),
                        "n_espessuras": len(esp_val[k]), "controle": c})
    if esp[n - 1] is not None:                 # base da última unidade atingida: o resto até a base
        limites.append(np.full_like(terreno, base))
        camadas.append({"chave": CHAVE_ABAIXO, "nome": "abaixo da última unidade (sem descrição no AGP)",
                        "cor": COR_COBERTURA, "slot": None, "n_espessuras": len(lim_val[n]),
                        "controle": contorno_dados(lim_pts[n])})

    malha = malha_contorno(g, poligono)
    area_tri = _areas(malha)
    xs, ys = malha["pts"][:, 0], malha["pts"][:, 1]
    saida_camadas = []
    for k, cam in enumerate(camadas):
        topo_v = bilinear(limites[k], g, xs, ys)
        base_v = bilinear(limites[k + 1], g, xs, ys)
        e_v = np.maximum(topo_v - base_v, 0.0)
        e_tri = e_v[malha["tris"]].mean(1)
        vol = float((e_tri / 1000.0 * area_tri).sum())                     # km³
        presente = e_tri >= ESPESSURA_MIN_M
        area_pres = float(area_tri[presente].sum())
        cx, cy = xs[malha["tris"]].mean(1), ys[malha["tris"]].mean(1)
        extrap = float(area_tri[presente & ~controlado(cam["controle"], cx, cy)].sum())
        saida_camadas.append({
            "chave": cam["chave"], "nome": cam["nome"], "cor": cam["cor"], "slot": cam["slot"],
            "n_espessuras": cam["n_espessuras"], "volume_km3": round(vol, 4),
            "espessura_max_m": round(float(e_v.max()) if len(e_v) else 0.0, 1),
            "area_km2": round(area_pres, 3),
            "fracao_extrapolada": round(extrap / area_pres, 3) if area_pres > 0 else 0.0,
            "controle": cam["controle"],
        })
    # as camadas cinza só entram se tiverem espessura de verdade em algum lugar
    if saida_camadas[-1]["chave"] == CHAVE_ABAIXO and saida_camadas[-1]["espessura_max_m"] < COBERTURA_MIN_M:
        saida_camadas.pop()
        limites.pop()
    if saida_camadas[0]["espessura_max_m"] < COBERTURA_MIN_M:
        saida_camadas.pop(0)
        limites.pop(0)
    area_total = float(area_tri.sum())
    return {
        "ok": True, "avisos": avisos, "camadas": saida_camadas,
        "limites": [[[round(float(v), 1) for v in linha] for linha in z] for z in limites],
        "base": base, "referencia": legenda[ref]["chave"], "contorno": [[round(float(a), 4), round(float(b), 4)]
                                                                       for a, b in poligono],
        "area_km2": round(area_total, 3), "terreno": fonte, "metodos": metodos,
        "empilhamento": cfg["empilhamento"],
        "cota_topo_max": round(alto, 1),
    }


def contorno_dados(pts) -> list | None:
    """Contorno convexo dos poços com o dado (onde a camada é interpolada, não extrapolada);
    None com menos de 3 poços ou poços quase alinhados."""
    pts = np.asarray(pts, float).reshape(-1, 2)
    if len(pts) < 3:
        return None
    h = mbl.contorno_convexo(pts)
    if len(h) < 3 or mbl.largura_relativa(h) < mbl.FRACAO_COLINEAR:
        return None
    return [[round(float(a), 4), round(float(b), 4)] for a, b in h]


def controlado(contorno, x, y, tol_km: float = 1e-3) -> np.ndarray:
    """Pontos dentro do contorno dos dados (borda conta, com folga de 1 m)."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    if not contorno:
        return np.zeros(np.broadcast(x, y).shape, bool)
    ok = np.ones(np.broadcast(x, y).shape, bool)
    for a, b, c in semiplanos_do_poligono(contorno):
        ok &= a * x + b * y + c >= -tol_km
    return ok


def _areas(malha: dict) -> np.ndarray:
    p, t = malha["pts"], malha["tris"]
    if len(t) == 0:
        return np.zeros(0)
    a, b, c = p[t[:, 0]], p[t[:, 1]], p[t[:, 2]]
    return np.abs((b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (b[:, 1] - a[:, 1]) * (c[:, 0] - a[:, 0])) / 2


def trecho_dentro(a, b, planos) -> tuple[float, float] | None:
    """Trecho [t0, t1] do segmento a→b dentro do polígono convexo (Cyrus–Beck)."""
    t0, t1 = 0.0, 1.0
    dx, dy = b[0] - a[0], b[1] - a[1]
    for pa, pb, pc in planos:
        f, d = pa * a[0] + pb * a[1] + pc, pa * dx + pb * dy
        if abs(d) < 1e-15:
            if f < 0:
                return None
            continue
        t = -f / d
        if d > 0:
            t0 = max(t0, t)
        else:
            t1 = min(t1, t)
        if t0 > t1:
            return None
    return t0, t1


def prolongar(linha, poligono) -> list:
    """A linha prolongada nas duas pontas até a borda do polígono (a seção atravessa o bloco)."""
    linha = [np.asarray(p, float) for p in linha]
    if len(linha) < 2:
        return [p.tolist() for p in linha]
    planos = semiplanos_do_poligono(poligono)
    pol = np.asarray(poligono, float)
    L = 4 * float(np.hypot(*(pol.max(0) - pol.min(0)))) + 1

    def ponta(a, b):
        d = float(np.hypot(*(b - a))) or 1.0
        fim = b + (b - a) / d * L
        tr = trecho_dentro(b, fim, planos)
        return b + tr[1] * (fim - b) if tr else b
    return [p.tolist() for p in [ponta(linha[1], linha[0])] + linha + [ponta(linha[-2], linha[-1])]]


def perfil(solido: dict, grade: dict, linha, passo_km: float | None = None) -> dict:
    """Perfil vertical do bloco fechado ao longo de uma linha (lista de [x, y]): distância ao
    longo da linha e a cota de cada limite, só dentro do contorno (com os pontos exatos onde
    a linha entra e sai). Base da parede da seção A–A′ e das tampas do corte."""
    planos = semiplanos_do_poligono(solido["contorno"])
    passo_km = passo_km or grade["passo"] / 2
    pts, dist, acum = [], [], 0.0
    for a, b in zip(linha[:-1], linha[1:]):
        a, b = np.asarray(a, float), np.asarray(b, float)
        comp = float(np.hypot(*(b - a)))
        tr = trecho_dentro(a, b, planos) if comp > 0 else None
        if tr:
            n = max(1, int(math.ceil((tr[1] - tr[0]) * comp / passo_km)))
            for k in range(n + 1):
                t = tr[0] + (tr[1] - tr[0]) * k / n
                if k == 0 and dist and abs(dist[-1] - (acum + t * comp)) < 1e-9:
                    continue
                pts.append(a + t * (b - a))
                dist.append(acum + t * comp)
        acum += comp
    if not pts:
        return {"dist": [], "xy": [], "limites": []}
    pts = np.array(pts)
    lims = [bilinear(z, grade, pts[:, 0], pts[:, 1]) for z in solido["limites"]]
    return {"dist": [round(float(d), 4) for d in dist], "xy": pts.round(4).tolist(),
            "limites": [[round(float(v), 1) for v in z] for z in lims]}
