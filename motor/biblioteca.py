"""
Biblioteca de interpretações de perfil (SIAPP 0.35).

Uma **interpretação** é uma avaliação de formação (aba Perfis) que alguém resolveu
compartilhar: em que poço e arquivo, quais curvas, métodos e parâmetros, os
intervalos e o resumo de cada um (net pay, φ, Sw, Vsh, HPV). As curvas calculadas
não vão: qualquer pessoa com o mesmo arquivo do REATE refaz o cálculo com os mesmos
parâmetros e chega no mesmo número — é isso que torna a interpretação conferível.

Ela entra no pacote de contribuição (formato v3) e na base comunitária como os
dados transcritos: com autor, origem (local, pacote, base) e licença CC-BY 4.0.

Comparar interpretações do mesmo poço mostra lado a lado o que cada pessoa escolheu
(parâmetros e métodos) e o que obteve em cada intervalo — os intervalos de autores
diferentes são casados pela profundidade (sobreposição de metade ou mais).
"""

from __future__ import annotations

import os

from . import avaliacao as mav

CAMPOS_RESUMO = ("nome", "origem", "topo", "base", "bruto_m", "com_dados_m", "reservatorio_m", "net_pay_m",
                 "ntg", "ntg_pay", "vsh_medio", "phi_media_pay", "sw_media_pay", "phi_media_res", "hpv_m",
                 "qc_arrombado_m", "qc_drho_m", "pay_com_qc_m")
PARAMETROS = tuple(mav.PADRAO)
TITULO_MAX = 120
COMENTARIO_MAX = 2000
INTERVALOS_MAX = 50
PROF_MAX_M = 12_000
SOBREPOSICAO = 0.5        # intervalos de autores diferentes "são o mesmo" com metade ou mais em comum

NOMES_PARAM = {
    "vsh_metodo": "Método do Vsh", "gr_limpo": "GR limpo (API)", "gr_argila": "GR da argila (API)",
    "gr_referencia": "Onde o GR foi estimado", "gr_estatistica": "Estatística do GR",
    "gr_ref_topo": "Janela do GR: topo (m)", "gr_ref_base": "Janela do GR: base (m)",
    "phi_metodo": "Método da φ", "rho_matriz": "ρ da matriz (g/cm³)", "rho_fluido": "ρ do fluido (g/cm³)",
    "dt_matriz": "Δt da matriz (µs/pé)", "dt_fluido": "Δt do fluido (µs/pé)", "phi_argila": "φ da argila",
    "sw_metodo": "Método da Sw", "rw": "Rw (ohm·m)", "a": "a (tortuosidade)", "m": "m (cimentação)",
    "n": "n (saturação)", "rsh": "Rsh (ohm·m)", "corte_vsh": "Corte de Vsh", "corte_phi": "Corte de φ",
    "corte_sw": "Corte de Sw", "qc_cali_pol": "QC arrombamento (pol)", "qc_drho": "QC |DRHO| (g/cm³)",
    "bs_pol": "Broca (pol)", "passo": "Passo (m)",
}
NOMES_TOTAIS = {"bruto_m": "Espessura bruta (m)", "reservatorio_m": "Reservatório (m)",
                "net_pay_m": "Net pay (m)", "phi_pay": "φ média no pay", "sw_pay": "Sw média no pay",
                "vsh": "Vsh médio", "hpv_m": "HPV (m)"}


class ErroBiblioteca(ValueError):
    pass


# ============================================================ criar
def de_execucao(reg: dict, arquivo: dict | None = None) -> dict:
    """Registro de uma execução (execucoes/avaliacao_*.json) → interpretação, sem as curvas."""
    arquivo = arquivo or {}
    if not reg.get("intervalos"):
        raise ErroBiblioteca("Esta avaliação não tem intervalos.")
    par = reg.get("parametros") or {}
    dados = {
        "siapp_versao": reg.get("siapp_versao"),
        "curvas_usadas": reg.get("curvas_usadas") or {},
        "metodos": reg.get("metodos") or {},
        "parametros": {k: par.get(k) for k in PARAMETROS if k in par},
        "parametros_automaticos": reg.get("parametros_automaticos") or {},
        "passo_m": reg.get("passo_m"),
        "intervalos": [{k: i.get(k) for k in CAMPOS_RESUMO if k in i} for i in reg["intervalos"]],
    }
    return {"poco_id": reg.get("poco") or arquivo.get("poco_id") or "",
            "arquivo_sha256": reg.get("arquivo_sha256") or arquivo.get("sha256"),
            "arquivo_caminho": arquivo.get("caminho_remoto"), "arquivo_bacia": arquivo.get("bacia"),
            "arquivo_nome": os.path.basename(reg.get("arquivo") or arquivo.get("rel") or ""),
            "execucao": reg.get("id"), "dados": dados}


def limpar_texto(titulo: str, comentario: str) -> tuple[str, str]:
    titulo = " ".join(str(titulo or "").split())
    linhas = [" ".join(x.split()) for x in str(comentario or "").splitlines()]
    comentario = "\n".join(linhas).strip()
    while "\n\n\n" in comentario:
        comentario = comentario.replace("\n\n\n", "\n\n")
    if len(titulo) > TITULO_MAX:
        raise ErroBiblioteca(f"Título longo demais ({len(titulo)} caracteres; até {TITULO_MAX}).")
    if len(comentario) > COMENTARIO_MAX:
        raise ErroBiblioteca(f"Comentário longo demais ({len(comentario)} caracteres; até {COMENTARIO_MAX}).")
    return titulo, comentario


# ============================================================ validar (pacote v3)
def _numero(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def validar(item: dict) -> list[str]:
    """Erros de uma interpretação vinda de um pacote (lista vazia = válida)."""
    rot = f"interpretação {item.get('id', '?')} ({item.get('poco', '?')})"
    if not isinstance(item, dict):
        return ["Interpretação inválida."]
    erros = []
    if not str(item.get("poco", "")).strip():
        erros.append(f"{rot}: sem poço.")
    if not isinstance(item.get("id"), str) or len(item["id"]) < 8:
        erros.append(f"{rot}: sem identificador.")
    if len(str(item.get("titulo") or "")) > TITULO_MAX:
        erros.append(f"{rot}: título longo demais.")
    if len(str(item.get("comentario") or "")) > COMENTARIO_MAX:
        erros.append(f"{rot}: comentário longo demais.")
    ints = item.get("intervalos")
    if not isinstance(ints, list) or not ints:
        erros.append(f"{rot}: sem intervalos.")
        ints = []
    if len(ints) > INTERVALOS_MAX:
        erros.append(f"{rot}: mais de {INTERVALOS_MAX} intervalos.")
    for i in ints:
        t, b = (i or {}).get("topo"), (i or {}).get("base")
        if not (_numero(t) and _numero(b) and -100 <= t < b <= PROF_MAX_M):
            erros.append(f"{rot}: intervalo {(i or {}).get('nome', '?')!r} com topo e base inválidos.")
        for k, v in (i or {}).items():
            if k in CAMPOS_RESUMO and k not in ("nome", "origem") and v is not None and not _numero(v):
                erros.append(f"{rot}: {k} não é número.")
                break
    for k, v in (item.get("metodos") or {}).items():
        if k not in ("vsh", "phi", "sw") or (v not in mav.NOMES_METODO and v != "auto"):
            erros.append(f"{rot}: método desconhecido {k}={v!r}.")
    par = item.get("parametros")
    if not isinstance(par, dict):
        erros.append(f"{rot}: sem parâmetros.")
    else:
        for k, v in par.items():
            if k not in PARAMETROS:
                erros.append(f"{rot}: parâmetro desconhecido {k!r}.")
            elif v is not None and not (_numero(v) or (isinstance(v, str) and len(v) <= 40)):
                erros.append(f"{rot}: parâmetro {k} inválido.")
    for papel, c in (item.get("curvas_usadas") or {}).items():
        if papel not in mav.PAPEIS or not isinstance(c, dict) or not str(c.get("mnemonico", "")).strip():
            erros.append(f"{rot}: curva {papel!r} inválida.")
    return erros


# ============================================================ pacote
def para_pacote(row: dict) -> dict:
    d = row["dados"]
    saida = {"id": row["id"], "poco": row["poco_id"], "criado_em": row["criado_em"],
             "titulo": row.get("titulo") or "", "comentario": row.get("comentario") or "",
             "arquivo": {k: v for k, v in (("sha256", row.get("arquivo_sha256")),
                                          ("caminho_remoto", row.get("arquivo_caminho")),
                                          ("bacia", row.get("arquivo_bacia")),
                                          ("nome", row.get("arquivo_nome"))) if v},
             **{k: d.get(k) for k in ("curvas_usadas", "metodos", "parametros", "parametros_automaticos",
                                      "passo_m", "intervalos", "siapp_versao")}}
    saida = {k: v for k, v in saida.items() if v not in (None, "", {}, [])}
    saida["intervalos"] = d.get("intervalos") or []
    saida.setdefault("parametros", {})
    return saida


def de_pacote(item: dict, autor: str, origem: str, pacote: str) -> dict:
    a = item.get("arquivo") or {}
    return {"id": item["id"], "poco_id": item["poco"], "titulo": item.get("titulo") or "",
            "comentario": item.get("comentario") or "", "arquivo_sha256": a.get("sha256"),
            "arquivo_caminho": a.get("caminho_remoto"), "arquivo_bacia": a.get("bacia"),
            "arquivo_nome": a.get("nome"), "criado_em": item.get("criado_em"),
            "dados": {k: item.get(k) for k in ("curvas_usadas", "metodos", "parametros",
                                               "parametros_automaticos", "passo_m", "intervalos",
                                               "siapp_versao")},
            "autor": autor, "origem": origem, "pacote": pacote}


# ============================================================ resumo
def totais(dados: dict) -> dict:
    """Somas e médias ponderadas de todos os intervalos (φ e Sw pelo net pay; Vsh pela espessura com dados)."""
    ints = dados.get("intervalos") or []
    soma = lambda k: round(sum((i.get(k) or 0) for i in ints), 2)   # noqa: E731

    def media(k, peso):
        pares = [(i.get(k), i.get(peso) or 0) for i in ints if i.get(k) is not None and (i.get(peso) or 0) > 0]
        p = sum(w for _, w in pares)
        return round(sum(v * w for v, w in pares) / p, 4) if p else None
    return {"bruto_m": soma("bruto_m"), "reservatorio_m": soma("reservatorio_m"), "net_pay_m": soma("net_pay_m"),
            "phi_pay": media("phi_media_pay", "net_pay_m"), "sw_pay": media("sw_media_pay", "net_pay_m"),
            "vsh": media("vsh_medio", "com_dados_m"), "hpv_m": round(sum((i.get("hpv_m") or 0) for i in ints), 3)}


def nome_metodos(m: dict) -> str:
    n = mav.NOMES_METODO
    return " / ".join(n.get(m.get(k), m.get(k) or "?") for k in ("vsh", "phi", "sw"))


def resumo(row: dict) -> dict:
    """Linha da lista da biblioteca."""
    d = row["dados"]
    ints = d.get("intervalos") or []
    return {"id": row["id"], "poco": row["poco_id"], "titulo": row.get("titulo") or "",
            "comentario": row.get("comentario") or "", "autor": row.get("autor") or "",
            "origem": row["origem"], "pacote": row.get("pacote") or "", "criado_em": row["criado_em"],
            "exportado_em": row.get("exportado_em"), "arquivo_nome": row.get("arquivo_nome") or "",
            "arquivo_sha256": row.get("arquivo_sha256"), "metodos": nome_metodos(d.get("metodos") or {}),
            "intervalos": [{"nome": i.get("nome") or "", "topo": i.get("topo"), "base": i.get("base"),
                            "net_pay_m": i.get("net_pay_m")} for i in ints],
            "totais": totais(d)}


# ============================================================ comparar
def _valor_param(dados: dict, k: str):
    if k in (dados.get("parametros_automaticos") or {}):
        v = (dados.get("parametros") or {}).get(k)
        return {"valor": v, "auto": True}
    return {"valor": (dados.get("parametros") or {}).get(k), "auto": False}


def _iguais(vs: list) -> bool:
    def norm(v):
        return round(float(v), 6) if _numero(v) else v
    return len({repr(norm(x)) for x in vs}) <= 1


def _casar_intervalos(itens: list[dict]) -> list[dict]:
    """Agrupa os intervalos de cada interpretação pela profundidade."""
    todos = sorted(((k, i) for k, it in enumerate(itens) for i in (it["dados"].get("intervalos") or [])),
                   key=lambda t: (t[1]["topo"], t[1]["base"]))
    linhas: list[dict] = []
    for k, i in todos:
        alvo = None
        for L in linhas:
            if L["por_item"][k] is not None:
                continue
            comum = min(L["base"], i["base"]) - max(L["topo"], i["topo"])
            menor = min(L["base"] - L["topo"], i["base"] - i["topo"])
            if menor > 0 and comum / menor >= SOBREPOSICAO:
                alvo = L
                break
        if alvo is None:
            alvo = {"topo": i["topo"], "base": i["base"], "nomes": [], "por_item": [None] * len(itens)}
            linhas.append(alvo)
        alvo["topo"], alvo["base"] = min(alvo["topo"], i["topo"]), max(alvo["base"], i["base"])
        if i.get("nome") and i["nome"] not in alvo["nomes"]:
            alvo["nomes"].append(i["nome"])
        alvo["por_item"][k] = i
    for L in linhas:
        nets = [x["net_pay_m"] for x in L["por_item"] if x is not None and x.get("net_pay_m") is not None]
        L["net_pay_amplitude_m"] = round(max(nets) - min(nets), 2) if len(nets) >= 2 else None
    return linhas


def comparar(itens: list[dict]) -> dict:
    """`itens`: [{id, rotulo, autor, origem, poco, arquivo_sha256, arquivo_nome, dados}] (2 a 6)."""
    if len(itens) < 2:
        raise ErroBiblioteca("Escolha ao menos duas interpretações para comparar.")
    if len(itens) > 6:
        raise ErroBiblioteca("Compare no máximo seis de cada vez.")
    avisos = []
    if len({it.get("poco") for it in itens}) > 1:
        avisos.append("São poços diferentes: compare os parâmetros, não os números dos intervalos.")
    shas = {it.get("arquivo_sha256") for it in itens if it.get("arquivo_sha256")}
    if len(shas) > 1:
        avisos.append("Os arquivos de perfil não são os mesmos (corridas diferentes ou outra versão do arquivo).")
    tot = [totais(it["dados"]) for it in itens]
    linhas_tot = [{"chave": k, "nome": n, "valores": [t[k] for t in tot]} for k, n in NOMES_TOTAIS.items()]
    metodos = [{"chave": k, "nome": n, "valores": [mav.NOMES_METODO.get((it["dados"].get("metodos") or {}).get(k),
                                                                          (it["dados"].get("metodos") or {}).get(k))
                                                    for it in itens]}
               for k, n in (("vsh", "Vsh"), ("phi", "Porosidade"), ("sw", "Saturação"))]
    for m in metodos:
        m["difere"] = not _iguais(m["valores"])
    params = []
    for k in PARAMETROS:
        if k.endswith("_metodo"):
            continue
        vs = [_valor_param(it["dados"], k) for it in itens]
        if all(v["valor"] is None for v in vs):
            continue
        params.append({"chave": k, "nome": NOMES_PARAM.get(k, k), "valores": vs,
                       "difere": not _iguais([v["valor"] for v in vs])})
    papeis = sorted({p for it in itens for p in (it["dados"].get("curvas_usadas") or {})},
                    key=lambda p: list(mav.PAPEIS).index(p) if p in mav.PAPEIS else 99)
    curvas = []
    for p in papeis:
        vs = [((it["dados"].get("curvas_usadas") or {}).get(p) or {}).get("mnemonico") for it in itens]
        curvas.append({"papel": p, "valores": vs, "difere": not _iguais(vs)})
    return {"itens": [{k: it.get(k) for k in ("id", "rotulo", "autor", "origem", "poco", "arquivo_nome", "criado_em")}
                      for it in itens],
            "totais": linhas_tot, "metodos": metodos, "parametros": params, "curvas": curvas,
            "intervalos": _casar_intervalos(itens), "avisos": avisos,
            "diferencas": [p["nome"] for p in metodos + params if p["difere"]]}
