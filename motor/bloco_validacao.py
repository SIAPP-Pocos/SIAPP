"""Validação cruzada do bloco (deixar um poço de fora) e prognóstico num ponto.

**Validação cruzada.** Cada poço sai do bloco, um de cada vez; o bloco é refeito sem ele e
prevê, na posição de cada topo daquele poço, a cota do topo — que se compara com a do AGP.
O erro (previsto − AGP) mede quanto o bloco erra *a uma certa distância do poço mais
próximo*: é o que transforma o "contexto espacial" num número.

Os dois modos são avaliados com as mesmas regras da montagem:

- **bloco fechado**: o empilhamento de motor/bloco_solido.py — por espessuras (referência +
  espessuras) ou topo a topo — cortado no terreno e na base; fora do contorno dos poços com o
  dado, o valor da borda — conta como **extrapolado**;
- **superfícies**: o topo da unidade interpolado direto entre os poços que a têm; só dentro
  do contorno (fora, o modo superfícies não desenha nada — conta como "fora").

Refazer a triangulação inteira para cada poço seria lento num bloco regional (429 poços ×
15 campos). Tirar um ponto de uma triangulação de Delaunay só muda a "estrela" dele: os
triângulos que o tocam viram a triangulação de Delaunay dos vizinhos. É o que o
`Interpolador` faz — e os testes conferem com a triangulação refeita do zero.

**Prognóstico.** Num ponto qualquer, a coluna prevista (topo, base e espessura de cada
camada, profundidade abaixo do terreno) e, com a validação feita, a **incerteza** de cada
topo: o erro que 68% das previsões daquela unidade não passaram, na mesma faixa de
distância ao poço mais próximo.
"""

from __future__ import annotations

import math

import numpy as np

from . import bloco as mbl
from . import bloco_solido as mbs
from . import interpolacao as mint
from .banco import agora

FAIXAS_KM = [(0.0, 1.0), (1.0, 2.0), (2.0, 5.0), (5.0, 10.0), (10.0, math.inf)]
N_MIN_FAIXA = 5          # comparações mínimas para usar o erro de uma faixa como incerteza
TOL_KM = 1e-6


class ErroValidacao(Exception):
    pass


# O interpolador linear por ponto (com "sem um poço") mora em motor/interpolacao.py, junto
# com os outros métodos; o nome antigo fica para quem já o usa.
Interpolador = mint.Linear
_no_triangulo = mint.no_triangulo


# ============================================================== empilhamento por ponto
class Empilhamento:
    """O bloco fechado avaliado num ponto (sem grade), com as regras de bloco_solido."""

    def __init__(self, modelo: dict, interpolacao: dict | None = None):
        self.modelo = modelo
        self.cfg = mint.configuracao(interpolacao if interpolacao is not None else
                                     (modelo.get("parametros") or {}).get("interpolacao"))
        sol = modelo.get("solido") or {}
        self.ok = bool(sol.get("ok"))
        self.ob = mbs.observacoes(modelo)
        self.n = self.ob["n"]
        self.ref = self.ob["referencia"]
        self.base = sol.get("base")
        est, esp = self.cfg["estrutura"], self.cfg["espessura"]
        self.f_ter = mint.Linear(self.ob["terreno"])
        self.f_ref = mint.ajustar(est, self.ob["lim"][self.ref]) if self.ref is not None else None
        self.f_esp = [mint.ajustar(esp, e, campo="espessura") if e else None for e in self.ob["esp"]]
        # superfícies: só os topos da própria unidade
        self.f_sup = [mint.ajustar(est, [o for o in L if o[4]]) for L in self.ob["lim"][:self.n]]
        self.topos = self.cfg["empilhamento"] == "topos"
        self.f_lim = [(mint.ajustar(est, L) if L else None) if k != self.ref else self.f_ref
                      for k, L in enumerate(self.ob["lim"])] if self.topos else None
        chaves = [c["chave"] for c in sol.get("camadas", [])]
        self.com_cobertura = bool(chaves) and chaves[0] == mbs.CHAVE_COBERTURA
        self.com_abaixo = bool(chaves) and chaves[-1] == mbs.CHAVE_ABAIXO

    def limites(self, x: float, y: float, sem_poco=None) -> dict:
        """Terreno e limites 0..n (topo de cada unidade e a base da última), já cortados no
        terreno e na base, e se cada espessura usada foi interpolada (dentro do contorno)."""
        n, ref = self.n, self.ref
        lim = [None] * (n + 1)
        interp = [True] * (n + 1)
        v, d, _ = self.f_ref.valor(x, y, sem_poco)
        lim[ref], interp[ref] = v, d
        esp = [None] * n
        dentro_esp = [True] * n
        for k in range(n):
            f = self.f_esp[k]
            if f is not None and len(f):
                e, d, _ = f.valor(x, y, sem_poco)
                if e is not None:
                    esp[k], dentro_esp[k] = max(0.0, e), d
        if self.topos:
            for k in range(n + 1):
                f = self.f_lim[k]
                if k != ref and f is not None and len(f):
                    lim[k], interp[k], _ = f.valor(x, y, sem_poco)
                if lim[k] is None and k > 0 and lim[k - 1] is not None:
                    if esp[k - 1] is not None:
                        lim[k], interp[k] = lim[k - 1] - esp[k - 1], interp[k - 1] and dentro_esp[k - 1]
                    else:
                        lim[k], interp[k] = self.base, False
            for k in range(1, n + 1):
                if lim[k] is not None and lim[k - 1] is not None:
                    lim[k] = min(lim[k], lim[k - 1])
            lim = [self.base if v is None else v for v in lim]
        else:
            for k in range(ref - 1, -1, -1):
                lim[k] = lim[k + 1] + (esp[k] or 0.0)
                interp[k] = interp[k + 1] and dentro_esp[k]
            for k in range(ref, n):
                if esp[k] is None:
                    for j in range(k + 1, n + 1):
                        lim[j], interp[j] = self.base, False
                    break
                lim[k + 1] = lim[k] - esp[k]
                interp[k + 1] = interp[k] and dentro_esp[k]
        ter, _, _ = self.f_ter.valor(x, y, sem_poco)
        base = self.base if self.base is not None else -math.inf
        lim = [max(min(v, ter), base) for v in lim]
        return {"terreno": max(ter, base), "lim": lim, "interpolado": interp}


# ============================================================== validação cruzada
def validar(modelo: dict, interpolacao: dict | None = None) -> dict:
    """Deixar um poço de fora, para cada poço: erro de cada topo previsto (bloco fechado e
    superfícies) e da espessura de cada unidade. `interpolacao`: outra configuração de
    métodos (a comparação); sem ela, a do bloco."""
    if len(modelo.get("pocos", [])) < 4:
        raise ErroValidacao("A validação cruzada precisa de ao menos 4 poços.")
    emp = Empilhamento(modelo, interpolacao)
    if emp.ref is None:
        raise ErroValidacao("Sem topos utilizáveis para validar.")
    legenda = modelo["legenda"]
    nomes = {u["chave"]: u for u in legenda}
    linhas = []
    for k in range(emp.n):
        u = legenda[k]
        for o in emp.ob["lim"][k]:
            if not o[4]:
                continue
            x, y, obs, poco = o[0], o[1], o[2], o[3]
            linha = {"poco": poco, "chave": u["chave"], "unidade": u["nome"], "x": round(x, 4), "y": round(y, 4),
                     "observado": round(obs, 2), "fechado": None, "erro_fechado": None, "interpolado": None,
                     "superficie": None, "erro_superficie": None, "esp_obs": None, "esp_prev": None}
            sup, dentro, dist = emp.f_sup[k].valor(x, y, poco)
            linha["dist_km"] = None if math.isinf(dist) else round(dist, 3)
            if sup is not None and dentro:
                linha["superficie"] = round(sup, 2)
                linha["erro_superficie"] = round(sup - obs, 2)
            if emp.ok:
                L = emp.limites(x, y, poco)
                linha["fechado"] = round(L["lim"][k], 2)
                linha["erro_fechado"] = round(L["lim"][k] - obs, 2)
                linha["interpolado"] = bool(L["interpolado"][k])
                eo = next((e[2] for e in emp.ob["esp"][k] if e[3] == poco), None)
                if eo is not None:
                    linha["esp_obs"] = round(eo, 2)
                    linha["esp_prev"] = round(max(0.0, L["lim"][k] - L["lim"][k + 1]), 2)
            linhas.append(linha)
    if not linhas:
        raise ErroValidacao("Nenhum topo para comparar.")

    def resumo(sel, campo):
        errs = [(l[campo], l) for l in sel if l[campo] is not None]
        if not errs:
            return {"n": 0}
        e = np.array([v for v, _ in errs])
        pior = max(errs, key=lambda t: abs(t[0]))
        a = np.abs(e)
        return {"n": len(e), "vies": round(float(e.mean()), 2), "ema": round(float(a.mean()), 2),
                "mediana": round(float(np.median(a)), 2), "reqm": round(float(np.sqrt((e ** 2).mean())), 2),
                "p68": round(float(np.percentile(a, 68)), 2), "p90": round(float(np.percentile(a, 90)), 2),
                "max": round(float(abs(pior[0])), 2), "max_poco": pior[1]["poco"]}
    unidades = []
    for u in legenda:
        sel = [l for l in linhas if l["chave"] == u["chave"]]
        if not sel:
            continue
        f = resumo(sel, "erro_fechado")
        f["n_extrapolado"] = sum(1 for l in sel if l["interpolado"] is False)
        s = resumo(sel, "erro_superficie")
        s["n_fora"] = sum(1 for l in sel if l["erro_superficie"] is None)
        esp = [l["esp_prev"] - l["esp_obs"] for l in sel if l["esp_obs"] is not None]
        unidades.append({"chave": u["chave"], "nome": u["nome"], "cor": u["cor"], "n": len(sel), "fechado": f,
                         "superficie": s,
                         "espessura": ({"n": len(esp), "ema": round(float(np.abs(esp).mean()), 2),
                                        "reqm": round(float(np.sqrt(np.mean(np.square(esp)))), 2)} if esp else {"n": 0})})
    comuns = [l for l in linhas if l["erro_fechado"] is not None and l["erro_superficie"] is not None]
    glob = {"fechado": resumo(linhas, "erro_fechado"), "superficie": resumo(linhas, "erro_superficie"),
            "comum": {"n": len(comuns),
                      "ema_fechado": round(float(np.mean([abs(l["erro_fechado"]) for l in comuns])), 2) if comuns else None,
                      "ema_superficie": round(float(np.mean([abs(l["erro_superficie"]) for l in comuns])), 2)
                      if comuns else None}}
    glob["fechado"]["n_extrapolado"] = sum(1 for l in linhas if l["interpolado"] is False)
    faixas = []
    por_unidade = {u["chave"]: [] for u in unidades}
    for de, ate in FAIXAS_KM:
        sel = [l for l in linhas if l["dist_km"] is not None and de <= l["dist_km"] < ate]
        f, s = resumo(sel, "erro_fechado"), resumo(sel, "erro_superficie")
        faixas.append({"de": de, "ate": None if math.isinf(ate) else ate, "n": len(sel),
                       "n_fechado": f["n"], "p68_fechado": f.get("p68"), "mediana_fechado": f.get("mediana"),
                       "ema_fechado": f.get("ema"), "reqm_fechado": f.get("reqm"),
                       "n_superficie": s["n"], "p68_superficie": s.get("p68"), "mediana_superficie": s.get("mediana"),
                       "ema_superficie": s.get("ema"), "reqm_superficie": s.get("reqm")})
        for u in unidades:
            r = resumo([l for l in sel if l["chave"] == u["chave"]], "erro_fechado")
            por_unidade[u["chave"]].append({"n": r["n"], "p68": r.get("p68")})
    avisos = []
    if not emp.ok:
        avisos.append("Sem bloco fechado neste bloco: só o modo superfícies foi avaliado.")
    poucos = [u["nome"] for u in unidades if u["n"] < 5]
    if poucos:
        avisos.append(f"Menos de 5 poços com a unidade (erro pouco representativo): {', '.join(poucos)}.")
    return {"versao": 1, "criado_em": agora(), "n_pocos": len({l["poco"] for l in linhas}),
            "interpolacao": emp.cfg, "metodos": {"estrutura": emp.f_ref.descricao() if emp.f_ref else "",
                                                "espessura": mint.nome(emp.cfg["espessura"])},
            "n_comparacoes": len(linhas), "linhas": linhas, "unidades": unidades, "global": glob,
            "faixas": faixas, "por_unidade_faixa": por_unidade, "avisos": avisos,
            "cores": {k: v["cor"] for k, v in nomes.items()}}


# ============================================================== comparar métodos
# Spline e krigagem só topo a topo: empilhadas por espessuras, o erro de uma referência lisa
# se soma ao das espessuras (no regional: 22 m contra 16 m de mediana).
CANDIDATOS = [
    ("linear", "Linear, por espessuras", {"estrutura": "linear", "espessura": "linear", "empilhamento": "espessuras"}),
    ("linear_topos", "Linear, topo a topo", {"estrutura": "linear", "espessura": "linear", "empilhamento": "topos"}),
    ("idw", "Inverso da distância, topo a topo", {"estrutura": "idw", "espessura": "idw", "empilhamento": "topos"}),
    ("spline", "Spline (automática), topo a topo", {"estrutura": "spline", "espessura": "spline", "empilhamento": "topos"}),
    ("rbf", "RBF multiquádrica (automática), topo a topo", {"estrutura": {"metodo": "rbf", "funcao": "multiquadrica"},
                                                            "espessura": {"metodo": "rbf", "funcao": "multiquadrica"},
                                                            "empilhamento": "topos"}),
    ("rbf_inversa", "RBF multiquádrica inversa (automática), topo a topo",
     {"estrutura": {"metodo": "rbf", "funcao": "inversa"}, "espessura": {"metodo": "rbf", "funcao": "inversa"},
      "empilhamento": "topos"}),
    ("krigagem", "Krigagem, topo a topo", {"estrutura": "krigagem", "espessura": "krigagem", "empilhamento": "topos"}),
    ("tendencia", "Tendência + krigagem, topo a topo", {"estrutura": "tendencia", "espessura": "krigagem",
                                                        "empilhamento": "topos"}),
]


def comparar(modelo: dict, parametros: dict | None = None, candidatos: list | None = None,
             progresso=None) -> dict:
    """Validação cruzada com cada método: por unidade e no geral, a mediana e o erro de 68%
    (bloco fechado e superfícies); sugere o melhor no geral (menor mediana no bloco fechado,
    desempate pelo 68%) e mostra o melhor de cada unidade."""
    candidatos = candidatos or CANDIDATOS
    saida = []
    for k, (ident, nome_c, cfg) in enumerate(candidatos):
        if progresso:
            progresso(k, len(candidatos), nome_c)
        c = dict(cfg, parametros=parametros or {})
        try:
            v = validar(modelo, c)
        except mint.ErroInterpolacao as e:
            raise ErroValidacao(str(e)) from e
        saida.append({"id": ident, "nome": nome_c, "interpolacao": v["interpolacao"], "metodos": v["metodos"],
                      "global": {"fechado": v["global"]["fechado"], "superficie": v["global"]["superficie"]},
                      "unidades": {u["chave"]: {"nome": u["nome"], "cor": u["cor"], "n": u["n"],
                                                "fechado": {q: u["fechado"].get(q) for q in ("n", "mediana", "p68")},
                                                "superficie": {q: u["superficie"].get(q) for q in ("n", "mediana", "p68")}}
                                   for u in v["unidades"]},
                      "faixas": [{q: f.get(q) for q in ("de", "ate", "n_fechado", "p68_fechado")} for f in v["faixas"]]})

    def chave(c, campo="fechado", u=None):
        g = c["unidades"][u][campo] if u else c["global"][campo]
        return (g.get("mediana") if g.get("mediana") is not None else math.inf,
                g.get("p68") if g.get("p68") is not None else math.inf)
    # sem bloco fechado (camadas sem espessura), decide pelas superfícies
    campo = "fechado" if any(c["global"]["fechado"].get("n") for c in saida) else "superficie"
    melhor = min(saida, key=lambda c: chave(c, campo))["id"]
    unidades = list(saida[0]["unidades"])
    por_unidade = {u: min(saida, key=lambda c: chave(c, campo, u))["id"] for u in unidades
                   if any(c["unidades"][u][campo].get("n") for c in saida)}
    return {"versao": 1, "criado_em": agora(), "candidatos": saida, "melhor": melhor, "por_unidade": por_unidade,
            "criterio": campo,
            "melhor_superficie": min(saida, key=lambda c: chave(c, "superficie"))["id"],
            "n_comparacoes": saida[0]["global"]["fechado"].get("n") or saida[0]["global"]["superficie"].get("n"),
            "parametros": parametros or {}}


def incerteza(validacao: dict | None, chave: str, dist_km: float) -> tuple[float | None, str]:
    """Erro que 68% das previsões da validação não passaram (o "1 sigma" robusto: não se
    deixa levar por um poço com o AGP errado, como a raiz do erro quadrático se deixaria), da
    unidade na faixa de distância — ou de todas as unidades na faixa, ou da unidade inteira —,
    com a explicação de onde veio."""
    if not validacao or dist_km is None or math.isinf(dist_km):
        return None, ""
    k = next((i for i, (de, ate) in enumerate(FAIXAS_KM) if de <= dist_km < ate), len(FAIXAS_KM) - 1)
    rot = _rotulo_faixa(k)
    pu = (validacao.get("por_unidade_faixa") or {}).get(chave) or []
    if k < len(pu) and pu[k]["n"] >= N_MIN_FAIXA and pu[k]["p68"] is not None:
        return pu[k]["p68"], f"68% dos erros da unidade a {rot} ({pu[k]['n']} comparações)"
    fx = validacao["faixas"][k]
    if fx["n_fechado"] >= N_MIN_FAIXA and fx["p68_fechado"] is not None:
        return fx["p68_fechado"], f"68% dos erros de todas as unidades a {rot} ({fx['n_fechado']} comparações)"
    un = next((u for u in validacao["unidades"] if u["chave"] == chave), None)
    if un and un["fechado"].get("n", 0) >= N_MIN_FAIXA:
        return un["fechado"]["p68"], f"68% dos erros da unidade, todas as distâncias ({un['fechado']['n']} comparações)"
    g = validacao["global"]["fechado"]
    if g.get("n", 0):
        return g["p68"], f"68% de todos os erros ({g['n']} comparações)"
    return None, ""


def _rotulo_faixa(k: int) -> str:
    de, ate = FAIXAS_KM[k]
    if math.isinf(ate):
        return f"mais de {de:g} km"
    return f"{de:g}–{ate:g} km".replace(".", ",")


# ============================================================== prognóstico
def prognostico(modelo: dict, x: float, y: float, validacao: dict | None = None,
                emp: Empilhamento | None = None) -> dict:
    """A coluna prevista no ponto (x, y em km do plano do bloco)."""
    emp = emp or Empilhamento(modelo)
    if not emp.ok:
        raise ErroValidacao("Este bloco não tem bloco fechado: sem prognóstico.")
    sol, g = modelo["solido"], modelo["grade"]
    x1, y1 = g["x0"] + (g["nx"] - 1) * g["passo"], g["y0"] + (g["ny"] - 1) * g["passo"]
    if not (g["x0"] - TOL_KM <= x <= x1 + TOL_KM and g["y0"] - TOL_KM <= y <= y1 + TOL_KM):
        raise ErroValidacao("Ponto fora da área do bloco.")
    L = emp.limites(x, y)
    bordas = ([L["terreno"]] if emp.com_cobertura else []) + L["lim"] + ([emp.base] if emp.com_abaixo else [])
    lat, lon = mbl.para_geo(np.array([x]), np.array([y]), modelo["origem"]["lat"], modelo["origem"]["lon"])
    dentro_bloco = bool(mbs.controlado(sol["contorno"], x, y))
    camadas = []
    ordem = {u["chave"]: k for k, u in enumerate(modelo["legenda"])}
    for i, c in enumerate(sol["camadas"]):
        topo, base = bordas[i], bordas[i + 1]
        esp = max(0.0, topo - base)
        k = ordem.get(c["chave"])
        dist = emp.f_sup[k].valor(x, y)[2] if k is not None and len(emp.f_sup[k]) else None
        inc, fonte = incerteza(validacao, c["chave"], dist) if k is not None else (None, "")
        camadas.append({"chave": c["chave"], "nome": c["nome"], "cor": c["cor"],
                        "topo": round(topo, 1), "base": round(base, 1), "espessura": round(esp, 1),
                        "prof_topo": round(L["terreno"] - topo, 1), "presente": esp >= mbs.ESPESSURA_MIN_M,
                        "interpolado": bool(mbs.controlado(c["controle"], x, y)),
                        "dist_km": None if dist is None or math.isinf(dist) else round(dist, 3),
                        "incerteza_m": inc, "incerteza_fonte": fonte})
    proximos = sorted(((p["id"], float(math.hypot(p["x"] - x, p["y"] - y))) for p in modelo["pocos"]),
                      key=lambda t: t[1])[:3]
    avisos = []
    if not dentro_bloco:
        avisos.append("Ponto fora do contorno do bloco: tudo extrapolado.")
    if not validacao:
        avisos.append("Sem validação cruzada neste bloco: rode \"Validar\" para ter a incerteza de cada topo.")
    return {"x": round(x, 4), "y": round(y, 4), "lat": round(float(lat[0]), 6), "lon": round(float(lon[0]), 6),
            "terreno": round(L["terreno"], 1), "base": sol["base"], "dentro_bloco": dentro_bloco,
            "camadas": camadas, "proximos": [{"poco": p, "dist_km": round(d, 3)} for p, d in proximos],
            "avisos": avisos}


# ============================================================== saídas
COLUNAS_CSV = ["poco", "unidade", "x_km", "y_km", "dist_km", "cota_agp", "previsto_fechado", "erro_fechado",
               "interpolado", "previsto_superficie", "erro_superficie", "espessura_agp", "espessura_prevista"]


def linhas_csv(validacao: dict) -> list[list]:
    out = []
    for l in validacao["linhas"]:
        out.append([l["poco"], l["unidade"], l["x"], l["y"], l["dist_km"], l["observado"], l["fechado"],
                    l["erro_fechado"], {True: "sim", False: "não"}.get(l["interpolado"], ""), l["superficie"],
                    l["erro_superficie"], l["esp_obs"], l["esp_prev"]])
    return out


def figura(validacao: dict, *, titulo: str = "", autor: str = "", data: str = "", versao: str = "") -> str:
    """Figura estilo artigo da validação: (a) previsto × AGP, (b) |erro| × distância ao poço
    mais próximo com a unidade, (c) tabela por unidade."""
    from .bloco_figura import FONTE, TINTA, TINTA2, GRADE, _t, _fmt, _passo
    v = validacao
    L = [l for l in v["linhas"] if l["erro_fechado"] is not None]
    usa_sup = not L
    if usa_sup:                                    # bloco sem modo fechado: só superfícies
        L = [l for l in v["linhas"] if l["erro_superficie"] is not None]
    chave_prev, chave_err = ("superficie", "erro_superficie") if usa_sup else ("fechado", "erro_fechado")
    if not L:
        raise ErroValidacao("Nada para desenhar.")
    unidades = v["unidades"]
    W = 1100
    n_lin = len(unidades)
    H = 600 + 16 * n_lin + 70
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
           f'<rect width="100%" height="100%" fill="#ffffff"/>']
    if titulo:
        out.append(_t(70, 34, titulo, 17, TINTA, peso="bold"))

    def eixos(x0, y0, x1, y1, lo_x, hi_x, lo_y, hi_y, rot_x, rot_y, letra, fmt_x=0):
        g = []
        px, py = _passo(hi_x - lo_x), _passo(hi_y - lo_y)
        X = lambda v: x0 + (v - lo_x) / (hi_x - lo_x) * (x1 - x0)
        Y = lambda v: y1 - (v - lo_y) / (hi_y - lo_y) * (y1 - y0)
        t = math.ceil(lo_x / px) * px
        while t <= hi_x + 1e-9:
            g.append(f'<line x1="{X(t):.1f}" y1="{y0}" x2="{X(t):.1f}" y2="{y1}" stroke="{GRADE}" stroke-width="0.3"/>')
            g.append(f'<line x1="{X(t):.1f}" y1="{y1}" x2="{X(t):.1f}" y2="{y1 - 5}" stroke="{TINTA}" stroke-width="0.8"/>')
            g.append(_t(X(t), y1 + 15, _fmt(t, fmt_x if px < 1 else 0), 10, TINTA, "middle"))
            t += px
        t = math.ceil(lo_y / py) * py
        while t <= hi_y + 1e-9:
            g.append(f'<line x1="{x0}" y1="{Y(t):.1f}" x2="{x1}" y2="{Y(t):.1f}" stroke="{GRADE}" stroke-width="0.3"/>')
            g.append(f'<line x1="{x0}" y1="{Y(t):.1f}" x2="{x0 + 5}" y2="{Y(t):.1f}" stroke="{TINTA}" stroke-width="0.8"/>')
            g.append(_t(x0 - 6, Y(t) + 3.5, _fmt(t), 10, TINTA, "end"))
            t += py
        g.append(f'<rect x="{x0}" y="{y0}" width="{x1 - x0}" height="{y1 - y0}" fill="none" stroke="{TINTA}" '
                 f'stroke-width="0.9"/>')
        g.append(_t((x0 + x1) / 2, y1 + 34, rot_x, 11, TINTA, "middle"))
        g.append(_t(x0 - 48, (y0 + y1) / 2, rot_y, 11, TINTA, "middle", rot=-90))
        g.append(_t(x0 + 8, y0 + 17, letra, 12, TINTA, peso="bold"))
        return g, X, Y

    # ---- (a) previsto × AGP
    obs = np.array([l["observado"] for l in L])
    prev = np.array([l[chave_prev] for l in L])
    lo, hi = float(min(obs.min(), prev.min())), float(max(obs.max(), prev.max()))
    pad = 0.05 * (hi - lo or 100)
    lo, hi = lo - pad, hi + pad
    ax0, ay0, ax1, ay1 = 110, 70, 500, 460
    g, X, Y = eixos(ax0, ay0, ax1, ay1, lo, hi, lo, hi, "cota do topo no AGP (m)", "cota prevista sem o poço (m)", "(a)")
    out += g
    out.append(f'<line x1="{X(lo):.1f}" y1="{Y(lo):.1f}" x2="{X(hi):.1f}" y2="{Y(hi):.1f}" stroke="{TINTA2}" '
               f'stroke-width="0.8"/>')
    m1 = lo + 0.12 * (hi - lo)
    out.append(_t(X(m1) + 8, Y(m1) + 4, "1:1", 10, TINTA2, "start", estilo="italic"))
    cor = v.get("cores", {})
    for l in L:
        c = cor.get(l["chave"], TINTA)
        cheio = l.get("interpolado") is not False
        out.append(f'<circle cx="{X(l["observado"]):.1f}" cy="{Y(l[chave_prev]):.1f}" r="3.2" '
                   f'fill="{c if cheio else "#ffffff"}" stroke="{c if not cheio else "#ffffff"}" '
                   f'stroke-width="{1.2 if not cheio else 0.6}"/>')
    gl = v["global"]["superficie" if usa_sup else "fechado"]
    out.append(_t(ax0 + 30, ay0 + 17, f"{'superfícies' if usa_sup else 'bloco fechado'} · n = {gl['n']} · "
                                       f"mediana |erro| = {_fmt(gl['mediana'], 1)} m · 68% ≤ {_fmt(gl['p68'], 1)} m",
                  10, TINTA))
    if not usa_sup:
        out.append(_t(ax0 + 30, ay0 + 31, "vazado: extrapolado (fora do contorno dos poços com o dado)", 9.5,
                      TINTA2, estilo="italic"))

    # ---- (b) |erro| × distância
    dist = np.array([l["dist_km"] if l["dist_km"] is not None else np.nan for l in L])
    err = np.abs(np.array([l[chave_err] for l in L]))
    ok = ~np.isnan(dist)
    # eixo pelo grosso dos erros (o percentil 90 × 2): um AGP errado não achata o resto
    teto = float(np.percentile(err[ok], 90)) * 2 if ok.any() else float(err.max())
    teto = min(max(teto, 1.0), float(err.max()) * 1.05 or 1.0)
    dmax = float(np.nanpercentile(dist, 99)) * 1.05 if ok.any() else 1.0
    bx0, by0, bx1, by1 = 620, 70, 1010, 460
    g, X, Y = eixos(bx0, by0, bx1, by1, 0, dmax, 0, teto, "distância ao poço mais próximo com a unidade (km)",
                    "|erro| (m)", "(b)", fmt_x=1)
    out += g
    acima = alem = 0
    for d, e in zip(dist[ok], err[ok]):
        if e > teto or d > dmax:
            acima += e > teto
            alem += d > dmax and e <= teto
            continue
        out.append(f'<circle cx="{X(d):.1f}" cy="{Y(e):.1f}" r="2.2" fill="{GRADE}" fill-opacity="0.8"/>')
    estilos = {"bloco fechado": (TINTA, 2.0), "superfícies": ("#8a949b", 1.6)}
    for campo, tra, nome in (("p68_fechado", "", "bloco fechado"), ("p68_superficie", "5 3", "superfícies")):
        if usa_sup and campo == "p68_fechado":
            continue
        pts = []
        for f in v["faixas"]:
            val = f.get(campo)
            n = f["n_superficie" if "superficie" in campo else "n_fechado"]
            if val is None or n < N_MIN_FAIXA:
                continue
            de, ate = f["de"], f["ate"] if f["ate"] is not None else dmax
            if de >= dmax:
                continue
            ate = min(ate, dmax)
            pts += [(X(de), Y(min(val, teto))), (X(ate), Y(min(val, teto)))]
        if pts:
            caminho = " ".join(f"{a:.1f},{b:.1f}" for a, b in pts)
            cor_l, larg = estilos[nome]
            out.append(f'<polyline points="{caminho}" fill="none" stroke="{cor_l}" stroke-width="{larg}"/>')
    lx, ly = bx1 - 190, by0 + 12
    out.append(f'<rect x="{lx}" y="{ly}" width="180" height="{50 if not usa_sup else 36}" fill="#ffffff" '
               f'stroke="{TINTA}" stroke-width="0.6"/>')
    out.append(_t(lx + 8, ly + 14, "68% dos erros, por faixa:", 9.5, TINTA))
    yy = ly + 28
    for _, nome in (("", "bloco fechado"), ("", "superfícies")):
        if usa_sup and nome == "bloco fechado":
            continue
        cor_l, larg = estilos[nome]
        out.append(f'<line x1="{lx + 8}" y1="{yy - 4}" x2="{lx + 34}" y2="{yy - 4}" stroke="{cor_l}" '
                   f'stroke-width="{larg}"/>')
        out.append(_t(lx + 40, yy, nome, 9.5, TINTA))
        yy += 14
    fora_txt = []
    if acima:
        fora_txt.append(f"{acima} ponto(s) acima de {_fmt(teto)} m (maior: {_fmt(float(err.max()))} m)")
    if alem:
        fora_txt.append(f"{alem} além de {_fmt(dmax, 1)} km")
    if fora_txt:
        out.append(_t(bx1, by1 + 48, "Fora do gráfico: " + "; ".join(fora_txt) + ".", 9, TINTA2, "end",
                      estilo="italic"))

    # ---- (c) tabela
    ty = 545
    out.append(_t(70, ty - 12, "(c)", 12, TINTA, peso="bold"))
    cols = [(70, "unidade", "start"), (300, "n", "end"), (360, "viés", "end"), (440, "mediana", "end"),
            (510, "68% ≤", "end"), (575, "máx.", "end"), (590, "poço do máx.", "start"),
            (790, "n", "end"), (860, "mediana", "end"), (930, "68% ≤", "end"), (1030, "espessura, EMA", "end")]
    out.append(_t(430, ty - 12, "bloco fechado (m)" if not usa_sup else "—", 10, TINTA2, "middle", estilo="italic"))
    out.append(_t(860, ty - 12, "superfícies (m)", 10, TINTA2, "middle", estilo="italic"))
    for x, nome, anc in cols:
        out.append(_t(x, ty + 4, nome, 10, TINTA, anc, peso="bold"))
    out.append(f'<line x1="70" y1="{ty + 9}" x2="1030" y2="{ty + 9}" stroke="{TINTA}" stroke-width="0.8"/>')
    y = ty + 24
    for u in unidades:
        f, s, e = u["fechado"], u["superficie"], u["espessura"]
        out.append(f'<rect x="70" y="{y - 9}" width="11" height="10" fill="{u["cor"]}" stroke="{TINTA}" '
                   f'stroke-width="0.4"/>')
        vals = [(86, u["nome"], "start"), (300, str(u["n"]), "end"),
                (360, _fmt(f["vies"], 1) if f.get("n") else "—", "end"),
                (440, _fmt(f["mediana"], 1) if f.get("n") else "—", "end"),
                (510, _fmt(f["p68"], 1) if f.get("n") else "—", "end"),
                (575, _fmt(f["max"], 0) if f.get("n") else "—", "end"), (590, f.get("max_poco", "") or "", "start"),
                (790, str(s.get("n", 0)), "end"), (860, _fmt(s["mediana"], 1) if s.get("n") else "—", "end"),
                (930, _fmt(s["p68"], 1) if s.get("n") else "—", "end"),
                (1030, _fmt(e["ema"], 1) if e.get("n") else "—", "end")]
        for x, txt, anc in vals:
            out.append(_t(x, y, txt, 10, TINTA, anc))
        y += 16
    out.append(f'<line x1="70" y1="{y - 9}" x2="1030" y2="{y - 9}" stroke="{TINTA}" stroke-width="0.8"/>')
    notas = [f"Validação cruzada (deixar um poço de fora): {v['n_pocos']} poços, {v['n_comparacoes']} topos. Erro = "
             "cota prevista sem o poço − cota do AGP. Superfícies: só dentro do contorno dos outros poços com a unidade.",
             "Topos: AGP (ANP), interpretação da operadora. " + (f"SIAPP {versao}" if versao else "SIAPP")
             + (f" · {autor}" if autor else "") + (f" · {data}" if data else "")]
    for k, t in enumerate(notas):
        out.append(_t(70, y + 14 + 15 * k, t, 9.5, TINTA2))
    out.append("</svg>")
    return "".join(out)


# ============================================================== comparação: CSV e figura
COLUNAS_CSV_COMPARACAO = ["metodo", "nome", "unidade", "n", "mediana_fechado", "p68_fechado", "mediana_superficie",
                          "p68_superficie", "melhor_da_unidade"]


def linhas_csv_comparacao(cmp: dict) -> list[list]:
    out = []
    for c in cmp["candidatos"]:
        g = c["global"]
        out.append([c["id"], c["nome"], "(todas)", g["fechado"].get("n") or g["superficie"].get("n"),
                    g["fechado"].get("mediana"), g["fechado"].get("p68"), g["superficie"].get("mediana"),
                    g["superficie"].get("p68"), "sim" if c["id"] == cmp["melhor"] else ""])
        for k, u in c["unidades"].items():
            out.append([c["id"], c["nome"], u["nome"], u["n"], u["fechado"].get("mediana"), u["fechado"].get("p68"),
                        u["superficie"].get("mediana"), u["superficie"].get("p68"),
                        "sim" if cmp["por_unidade"].get(k) == c["id"] else ""])
    return out


# um símbolo por método (sem depender de cor): círculo, quadrado, triângulo, losango, triângulo
# invertido, estrela; cheio = o melhor da linha
_SIMBOLOS = ("circulo", "quadrado", "triangulo", "losango", "invertido", "cruz", "pentagono", "mais")


def _simbolo(tipo: str, x: float, y: float, r: float, cheio: bool, cor: str) -> str:
    preench = cor if cheio else "#ffffff"
    a = f'fill="{preench}" stroke="{cor}" stroke-width="1"'
    if tipo == "circulo":
        return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" {a}/>'
    if tipo == "quadrado":
        return f'<rect x="{x - r * 0.9:.1f}" y="{y - r * 0.9:.1f}" width="{r * 1.8:.1f}" height="{r * 1.8:.1f}" {a}/>'
    if tipo == "mais":
        d = r * 1.05
        return (f'<path d="M{x - d:.1f},{y:.1f} L{x + d:.1f},{y:.1f} M{x:.1f},{y - d:.1f} L{x:.1f},{y + d:.1f}" '
                f'stroke="{cor}" stroke-width="{2.4 if cheio else 1.2}"/>')
    if tipo == "cruz":
        d = r * 0.95
        return (f'<path d="M{x - d:.1f},{y - d:.1f} L{x + d:.1f},{y + d:.1f} M{x - d:.1f},{y + d:.1f} '
                f'L{x + d:.1f},{y - d:.1f}" stroke="{cor}" stroke-width="{2.2 if cheio else 1.1}"/>')
    pts = {"pentagono": [(math.sin(2 * math.pi * k / 5) * 1.1, -math.cos(2 * math.pi * k / 5) * 1.1) for k in range(5)],
           "triangulo": [(0, -1.15), (1.05, 0.75), (-1.05, 0.75)],
           "invertido": [(0, 1.15), (1.05, -0.75), (-1.05, -0.75)],
           "losango": [(0, -1.25), (1.0, 0), (0, 1.25), (-1.0, 0)]}[tipo]
    caminho = " ".join(f"{x + px * r:.1f},{y + py * r:.1f}" for px, py in pts)
    return f'<polygon points="{caminho}" {a}/>'


def figura_comparacao(cmp: dict, *, titulo: str = "", autor: str = "", data: str = "", versao: str = "",
                      n_min: int = 3) -> str:
    """Figura estilo artigo da comparação de métodos: mediana do |erro| por unidade (escala
    log), um símbolo por método, o melhor de cada linha cheio; (a) bloco fechado, (b) superfícies."""
    from .bloco_figura import FONTE, TINTA, TINTA2, GRADE, _t, _fmt
    cand = cmp["candidatos"]
    if not cand:
        raise ErroValidacao("Nada para desenhar.")
    chaves = [k for k, u in cand[0]["unidades"].items() if u["n"] >= n_min]
    campos = [c for c in ("fechado", "superficie") if any(x["global"][c].get("n") for x in cand)]
    linhas = [None] + chaves                              # None = todas as unidades
    W = 1100
    alt_l = 24
    y0 = 90 if titulo else 64
    painel_h = alt_l * len(linhas) + 20
    H = y0 + painel_h + 60 + 22 * math.ceil(len(cand) / 2) + 60
    vals = [v for x in cand for c in campos
            for v in [x["global"][c].get("mediana")] + [x["unidades"][k][c].get("mediana") for k in chaves]
            if v is not None and v > 0]
    lo = 10 ** math.floor(math.log10(max(min(vals), 0.1))) if vals else 1
    hi = 10 ** math.ceil(math.log10(max(vals))) if vals else 100
    if hi <= lo:
        hi = lo * 10
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
           f'<rect width="100%" height="100%" fill="#ffffff"/>']
    if titulo:
        out.append(_t(70, 34, titulo, 17, TINTA, peso="bold"))
    rot_x0 = 70
    paineis = [(250, 650), (690, 1060)] if len(campos) == 2 else [(250, 1060)]
    nomes_campo = {"fechado": "bloco fechado", "superficie": "superfícies"}

    def melhor_da_linha(campo, k):
        def m(x):
            g = x["unidades"][k][campo] if k else x["global"][campo]
            return g.get("mediana") if g.get("mediana") is not None else math.inf
        b = min(cand, key=m)
        return b["id"] if m(b) < math.inf else None

    for p, campo in enumerate(campos):
        x0, x1 = paineis[p]
        X = lambda v, x0=x0, x1=x1: x0 + (math.log10(v) - math.log10(lo)) / (math.log10(hi) - math.log10(lo)) * (x1 - x0)
        ytop, ybot = y0, y0 + painel_h
        d = lo
        while d <= hi * 1.0001:
            for m in (1, 2, 5):
                t = d * m
                if lo <= t <= hi * 1.0001:
                    out.append(f'<line x1="{X(t):.1f}" y1="{ytop}" x2="{X(t):.1f}" y2="{ybot}" stroke="{GRADE}" '
                               f'stroke-width="{0.5 if m == 1 else 0.25}"/>')
                    out.append(_t(X(t), ybot + 15, _fmt(t, 1 if t < 1 else 0), 10, TINTA, "middle"))
            d *= 10
        out.append(f'<rect x="{x0}" y="{ytop}" width="{x1 - x0}" height="{ybot - ytop}" fill="none" stroke="{TINTA}" '
                   f'stroke-width="0.9"/>')
        out.append(_t((x0 + x1) / 2, ybot + 34, f"mediana do |erro| (m, escala log) — {nomes_campo[campo]}", 11,
                      TINTA, "middle"))
        out.append(_t(x0 + 6, ytop - 8, f"({'ab'[p]})", 12, TINTA, peso="bold"))
        for i, k in enumerate(linhas):
            y = ytop + 10 + alt_l * (i + 0.5)
            if i == 1:
                out.append(f'<line x1="{x0}" y1="{y - alt_l / 2:.1f}" x2="{x1}" y2="{y - alt_l / 2:.1f}" '
                           f'stroke="{TINTA}" stroke-width="0.5"/>')
            b = melhor_da_linha(campo, k)
            for j, x in sorted(enumerate(cand), key=lambda jx: jx[1]["id"] == b):    # o melhor por cima
                g = x["unidades"][k][campo] if k else x["global"][campo]
                v = g.get("mediana")
                if v is None or v <= 0:
                    continue
                dy = (j - (len(cand) - 1) / 2) * min(2.4, 12 / max(len(cand), 1))   # métodos empatados não se tapam
                out.append(_simbolo(_SIMBOLOS[j % len(_SIMBOLOS)], X(min(max(v, lo), hi)), y + dy, 4.2,
                                    x["id"] == b, TINTA))
    for i, k in enumerate(linhas):
        y = y0 + 10 + alt_l * (i + 0.5)
        if k is None:
            out.append(_t(rot_x0, y + 3.5, "todas as unidades", 10.5, TINTA, peso="bold"))
        else:
            u = cand[0]["unidades"][k]
            out.append(f'<rect x="{rot_x0}" y="{y - 5:.1f}" width="10" height="10" fill="{u["cor"]}" stroke="{TINTA}" '
                       f'stroke-width="0.4"/>')
            out.append(_t(rot_x0 + 15, y + 3.5, f"{u['nome'][:24]} (n = {u['n']})", 10, TINTA))
    # legenda: duas colunas
    ly = y0 + painel_h + 62
    for j, x in enumerate(cand):
        cx, cy = 90 + (j % 2) * 500, ly + 22 * (j // 2)
        out.append(_simbolo(_SIMBOLOS[j % len(_SIMBOLOS)], cx, cy - 4, 4.6, False, TINTA))
        txt = x["nome"] + (" — sugerido" if x["id"] == cmp["melhor"] else "")
        out.append(_t(cx + 12, cy, txt, 10, TINTA, peso="bold" if x["id"] == cmp["melhor"] else "normal"))
        out.append(_t(cx + 12, cy + 11, x["metodos"].get("estrutura", "")[:90] if isinstance(x["metodos"].get("estrutura"), str)
                      else "", 8.5, TINTA2))
    yn = ly + 22 * math.ceil(len(cand) / 2) + 8
    notas = [f"Validação cruzada (deixar um poço de fora) com cada método: {cmp.get('n_comparacoes') or '—'} topos. "
             f"Símbolo cheio: o menor erro da linha. Unidades com menos de {n_min} topos ficam de fora.",
             "Topos: AGP (ANP), interpretação da operadora. " + (f"SIAPP {versao}" if versao else "SIAPP")
             + (f" · {autor}" if autor else "") + (f" · {data}" if data else "")]
    for k, t in enumerate(notas):
        out.append(_t(70, yn + 15 * k, t, 9.5, TINTA2))
    out.append("</svg>")
    return "".join(out)
