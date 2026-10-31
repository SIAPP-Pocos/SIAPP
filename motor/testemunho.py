"""Testemunho × perfil (0.50): porosidade dos plugs contra a do perfil, e o deslocamento de profundidade pelo gama.

Dois resultados independentes um do outro (o plug é medida de laboratório; o perfil é medida de poço aberto), por isso a
comparação diz algo. O que NÃO fazemos: dizer que um dos dois "está certo". Os números mostram o quanto diferem; as
causas possíveis (escala de amostragem, danos ao plug, calibração, deslocamento do testemunho) ficam para o intérprete.

Convenção do deslocamento: profundidade no perfil = profundidade do testemunho + deslocamento.
"""

from __future__ import annotations

import numpy as np


def _limpar(prof, v):
    prof, v = np.asarray(prof, float), np.asarray(v, float)
    ok = np.isfinite(prof) & np.isfinite(v)
    prof, v = prof[ok], v[ok]
    ordem = np.argsort(prof)
    return prof[ordem], v[ordem]


def valor_em(prof, v, alvo: float, janela: float = 0.3) -> float | None:
    """Valor da curva na profundidade `alvo` (interpolação linear). None se não há amostra a até `janela` m."""
    prof, v = _limpar(prof, v)
    if len(prof) < 2 or alvo < prof[0] - janela or alvo > prof[-1] + janela:
        return None
    i = int(np.searchsorted(prof, alvo))
    vizinhas = [prof[j] for j in (i - 1, i) if 0 <= j < len(prof)]
    if min(abs(alvo - p) for p in vizinhas) > janela:
        return None
    return float(np.interp(alvo, prof, v))


def deslocamento_gama(prof_core, gr_core, prof_log, gr_log, max_m: float = 5.0, passo: float = 0.05,
                      minimo: int = 15) -> dict:
    """Deslocamento que mais aproxima o gama do testemunho do gama do perfil (máxima correlação de Pearson).

    Devolve `deslocamento_m`, `correlacao` (no melhor deslocamento), `correlacao_sem_deslocamento`, `n` (pontos usados
    no melhor deslocamento) e `confiavel`: só é True se a correlação for ao menos 0,6 e o pico se destacar do resto da
    varredura. `curva`: [(deslocamento, correlação)] para quem quiser ver."""
    pc, gc = _limpar(prof_core, gr_core)
    pl, gl = _limpar(prof_log, gr_log)
    if len(pc) < minimo or len(pl) < 2:
        return {"deslocamento_m": None, "correlacao": None, "correlacao_sem_deslocamento": None, "n": int(len(pc)),
                "confiavel": False, "motivo": f"poucos pontos de gama do testemunho ({len(pc)}; mínimo {minimo})",
                "curva": []}
    curva = []
    for d in np.arange(-max_m, max_m + passo / 2, passo):
        alvo = pc + d
        dentro = (alvo >= pl[0]) & (alvo <= pl[-1])
        if dentro.sum() < minimo:
            continue
        a, b = gc[dentro], np.interp(alvo[dentro], pl, gl)
        if np.std(a) < 1e-9 or np.std(b) < 1e-9:
            continue
        curva.append((round(float(d), 4), float(np.corrcoef(a, b)[0, 1]), int(dentro.sum())))
    if not curva:
        return {"deslocamento_m": None, "correlacao": None, "correlacao_sem_deslocamento": None, "n": int(len(pc)),
                "confiavel": False, "motivo": "o testemunho não se sobrepõe ao perfil de gama ou uma das curvas é constante",
                "curva": []}
    melhor = max(curva, key=lambda c: c[1])
    zero = min(curva, key=lambda c: abs(c[0]))
    rs = np.array([c[1] for c in curva])
    destaca = melhor[1] - float(np.median(rs)) >= 0.2
    borda = melhor[0] in (curva[0][0], curva[-1][0])
    confiavel = bool(melhor[1] >= 0.6 and destaca and not borda)
    motivo = None
    if not confiavel:
        motivo = ("correlação baixa (< 0,6)" if melhor[1] < 0.6 else
                  "o melhor deslocamento está na borda da busca" if borda else
                  "o pico de correlação não se destaca do resto da varredura")
    return {"deslocamento_m": melhor[0], "correlacao": round(melhor[1], 3), "n": melhor[2],
            "correlacao_sem_deslocamento": round(zero[1], 3), "confiavel": confiavel, "motivo": motivo,
            "curva": [(c[0], round(c[1], 3)) for c in curva]}


def _estatisticas(pares: list[tuple[float, float]]) -> dict:
    """`pares`: (plug %, perfil %). Diferença = perfil − plug, em pontos percentuais."""
    if not pares:
        return {"n": 0}
    plug = np.array([p[0] for p in pares])
    perfil = np.array([p[1] for p in pares])
    d = perfil - plug
    r = {"n": len(pares), "diferenca_media_pp": round(float(d.mean()), 2),
         "erro_absoluto_medio_pp": round(float(np.abs(d).mean()), 2), "rmse_pp": round(float(np.sqrt((d ** 2).mean())), 2)}
    if len(pares) >= 3 and plug.std() > 1e-9 and perfil.std() > 1e-9:
        r["correlacao"] = round(float(np.corrcoef(plug, perfil)[0, 1]), 3)
    return r


def comparar_plugs(prof_log, phi_log, plugs: list[dict], deslocamento: float = 0.0, janela: float = 0.3) -> dict:
    """Porosidade do perfil (fração) nas profundidades dos plugs (`prof` em m, `phi_pct` em %).
    Cada plug ganha `perfil_pct` (None se o perfil não cobre) e `diferenca_pp` (perfil − plug)."""
    linhas, pares = [], []
    for p in plugs:
        v = valor_em(prof_log, phi_log, p["prof"] + deslocamento, janela)
        ln = {**p, "prof_perfil": round(p["prof"] + deslocamento, 3),
              "perfil_pct": None if v is None else round(v * 100.0, 2), "diferenca_pp": None}
        if v is not None and p.get("phi_pct") is not None:
            ln["diferenca_pp"] = round(v * 100.0 - p["phi_pct"], 2)
            pares.append((p["phi_pct"], v * 100.0))
        linhas.append(ln)
    return {"deslocamento_m": deslocamento, "plugs": linhas, "estatisticas": _estatisticas(pares)}


def comparar(prof_log, phi_log, plugs: list[dict], gama_core: list[dict] | None = None, prof_gr=None, gr=None,
             janela: float = 0.3) -> dict:
    """Plugs × perfil, sem deslocamento e, se o gama do testemunho e do perfil permitem, com o deslocamento achado.
    `plugs`: [{"prof", "phi_pct", "perm_md", ...}]; `gama_core`: [{"prof", "gr"}]."""
    r = {"sem_deslocamento": comparar_plugs(prof_log, phi_log, plugs, 0.0, janela), "deslocamento": None,
         "com_deslocamento": None}
    if gama_core and prof_gr is not None and gr is not None:
        d = deslocamento_gama([g["prof"] for g in gama_core], [g["gr"] for g in gama_core], prof_gr, gr)
        r["deslocamento"] = {k: v for k, v in d.items() if k != "curva"}
        r["curva_deslocamento"] = d["curva"]
        if d["deslocamento_m"] is not None and abs(d["deslocamento_m"]) >= 0.05:
            r["com_deslocamento"] = comparar_plugs(prof_log, phi_log, plugs, d["deslocamento_m"], janela)
    return r
