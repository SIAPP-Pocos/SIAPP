"""Topos de formação de várias fontes: comparar, escolher e usar (SIAPP 0.45).

O mesmo topo chega por até quatro caminhos — o AGP da ANP, a transcrição do usuário (ou da comunidade), o RFP
(topos constatados) e a descrição de calha do PAG. Este módulo:

1. reúne os **candidatos** de cada fonte por unidade (a chave da unidade sai do nome: "FM AÇU", "Açu", "ACU" e a
   sigla do AGP viram a mesma; os topos sem nome do RFP ganham o nome da formação da calha a até 10 m);
2. escolhe o topo **efetivo** de cada unidade: a fonte que o usuário escolheu para aquela unidade naquele poço
   (tabela `escolhas`) ou, sem escolha, a primeira da **precedência** do projeto (padrão: AGP, transcrito, RFP,
   calha — onde há AGP, nada muda em relação às versões anteriores);
3. entrega os efetivos no formato das unidades do AGP, para a seção estratigráfica e o bloco 3D.

Diferença entre fontes acima de `TOLERANCIA_M` fica marcada para o usuário olhar.
"""

from __future__ import annotations

import json
import re
import unicodedata

from . import agp as magp
from .banco import Banco, agora

FONTES = {"agp": "AGP", "transcrito": "Transcrito", "rfp": "RFP", "calha": "Calha (PAG)"}
PRECEDENCIA_PADRAO = ["agp", "transcrito", "rfp", "calha"]
NENHUMA = "nenhuma"
TOLERANCIA_M = 5.0
TEMA = "topo"

_PREFIXOS = (("FORMACAO", "F"), ("FM", "F"), ("MEMBRO", "M"), ("MB", "M"), ("GRUPO", "G"), ("GR", "G"),
             ("CAMADA", "C"), ("SUPERGRUPO", "S"))


def _sem_acento(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", str(s or "")) if unicodedata.category(c) != "Mn")


def nome_e_nivel(nome: str) -> tuple[str, str]:
    """'FM. AÇU' → ('ACU', 'F'); 'Membro Mossoró' → ('MOSSORO', 'M'); 'Agua Grande' → ('AGUA GRANDE', '')."""
    n = " ".join(_sem_acento(nome).upper().replace(".", " ").split())
    nivel = ""
    for pref, nv in _PREFIXOS:
        if n.startswith(pref + " "):
            n, nivel = n[len(pref) + 1:], nv
            break
    n = re.sub(r"^(DE|DO|DA)\s+", "", n)
    return n.strip(), nivel


def mapa_siglas(nomes: dict) -> dict[str, str]:
    """Nome por extenso normalizado → sigla do AGP (de recursos/estratigrafia.json)."""
    saida = {}
    for k, v in nomes.items():
        if k.startswith("#") or k.isdigit():
            continue
        saida.setdefault(nome_e_nivel(v)[0], k)
        saida.setdefault(nome_e_nivel(k)[0], k)
    return saida


def chave_de(nome: str, siglas: dict) -> tuple[str, str]:
    """Chave da unidade (a sigla do AGP quando se conhece; senão o nome normalizado) e o nível."""
    base, nivel = nome_e_nivel(nome)
    return siglas.get(base, base), nivel


# ---------------------------------------------------------------- precedência e escolhas
def precedencia(banco: Banco) -> list[str]:
    try:
        p = json.loads(banco.meta("precedencia_topos", "") or "[]")
    except ValueError:
        p = []
    p = [x for x in p if x in FONTES]
    return p + [x for x in PRECEDENCIA_PADRAO if x not in p]


def definir_precedencia(banco: Banco, ordem: list[str]) -> list[str]:
    ordem = [x for x in dict.fromkeys(ordem) if x in FONTES]
    ordem += [x for x in PRECEDENCIA_PADRAO if x not in ordem]
    banco.definir_meta("precedencia_topos", json.dumps(ordem))
    return ordem


def escolhas(banco: Banco, pid: str) -> dict[str, str]:
    with banco.conexao() as c:
        return {r["chave"]: r["fonte"] for r in c.execute(
            "SELECT chave, fonte FROM escolhas WHERE poco_id = ? AND tema = ?", (pid, TEMA))}


def escolher(banco: Banco, pid: str, chave: str, fonte: str | None, autor: str = "") -> None:
    """Fonte do topo da unidade `chave` no poço; None (ou "padrao") volta à precedência do projeto."""
    with banco.conexao() as c:
        if not fonte or fonte == "padrao":
            c.execute("DELETE FROM escolhas WHERE poco_id = ? AND tema = ? AND chave = ?", (pid, TEMA, chave))
            return
        if fonte not in FONTES and fonte != NENHUMA:
            raise ValueError(f"Fonte desconhecida: {fonte}")
        c.execute("INSERT OR REPLACE INTO escolhas VALUES (?, ?, ?, ?, ?, ?)", (pid, TEMA, chave, fonte, autor, agora()))


# ---------------------------------------------------------------- candidatos
def _agp(banco, pid, nomes, siglas):
    from . import secao as msc
    agps = magp.do_poco(banco, pid)
    g = agps[0] if agps else None
    saida, outras = [], []
    for u in magp.unidades_do_poco(banco, pid):
        if g and u["caminho"] != g["caminho"]:
            continue
        n = msc._normalizar(u, nomes)
        if n["tip"] != "L":
            outras.append(n)
            continue
        if n["topo"] is None:
            continue
        # sigla conhecida (recursos/estratigrafia.json): ela; senão, o nome normalizado, para casar com as outras fontes
        chave = n["sigla"].upper() if n["sigla"].upper() in nomes else siglas.get(nome_e_nivel(n["nome"])[0],
                                                                                    nome_e_nivel(n["nome"])[0])
        saida.append({"fonte": "agp", "chave": chave,
                      "unidade": n, "nome": n["nome"], "nivel": n["nivel"], "topo": n["topo"], "base": n["base"],
                      "cota_topo": n["cota_topo"], "ref": u["caminho"],
                      "detalhe": " · ".join(x for x in (n.get("fonte"), magp.QUALIDADES.get(n.get("ql") or "", "")) if x)})
    return saida, outras, g


def _dp(banco, pid, tipo):
    from . import dados_poco as mdp
    return mdp.itens_do_poco(banco, pid, tipo)


def candidatos(banco: Banco, pid: str, nomes: dict) -> dict:
    """Candidatos por unidade: {chave: {nome, nivel, fontes: {fonte: cand}}} e as unidades não litológicas do AGP."""
    siglas = mapa_siglas(nomes)
    agp, outras, g = _agp(banco, pid, nomes, siglas)
    cands = list(agp)
    for f in banco.fatos(pid, tipo="topo_formacao"):
        if f["prof_topo"] is None or not f["nome"]:
            continue
        chave, nivel = chave_de(f["nome"], siglas)
        cands.append({"fonte": "transcrito", "chave": chave, "nome": f["nome"], "nivel": nivel or "F",
                      "topo": f["prof_topo"], "base": f["prof_base"], "cota_topo": None,
                      "ref": f.get("fonte_rel") or "", "detalhe": f"{f['origem']}" + (f" · {f['autor']}" if f.get("autor") else "")})
    calha = [t for t in _dp(banco, pid, "topo_calha") if t["prof_topo"] is not None and t["nome"]]
    for t in calha:
        chave, nivel = chave_de(t["nome"], siglas)
        cands.append({"fonte": "calha", "chave": chave, "nome": t["nome"], "nivel": nivel or "F", "topo": t["prof_topo"],
                      "base": None, "cota_topo": None, "ref": t["rel"],
                      "detalhe": f"entre {t['extra'].get('acima'):g} e {t['prof_topo']:g} m" if t["extra"].get("acima") else ""})
    rfp = [t for t in _dp(banco, pid, "topo") if t["prof_topo"] is not None]
    # o RFP sem nome: cada topo da calha nomeia o topo sem nome do RFP mais perto dele, até 10 m (um para um)
    nome_rfp = {}
    for c in calha:
        livres = [t for t in rfp if not t["nome"] and id(t) not in nome_rfp and abs(t["prof_topo"] - c["prof_topo"]) <= 10]
        if livres:
            nome_rfp[id(min(livres, key=lambda t: abs(t["prof_topo"] - c["prof_topo"])))] = c["nome"]
    for t in rfp:
        nome, derivado = t["nome"], False
        if not nome:
            if id(t) not in nome_rfp:
                continue
            nome, derivado = nome_rfp[id(t)], True
        chave, nivel = chave_de(nome, siglas)
        cands.append({"fonte": "rfp", "chave": chave, "nome": nome, "nivel": nivel or "F", "topo": t["prof_topo"],
                      "base": None, "cota_topo": t.get("cota"), "ref": t["rel"],
                      "detalhe": ("nome pela calha · " if derivado else "") + (
                          f"previsto {t['extra'].get('prev_medida'):g} m" if t["extra"].get("prev_medida") is not None else "")})
    por = {}
    for c in sorted(cands, key=lambda c: c["topo"]):
        u = por.setdefault(c["chave"], {"chave": c["chave"], "nome": nomes.get(c["chave"]) or c["nome"],
                                        "nivel": c["nivel"], "fontes": {}})
        if c["fonte"] not in u["fontes"]:            # a primeira (a mais rasa) de cada fonte
            u["fontes"][c["fonte"]] = c
        if c["fonte"] == "agp":
            u["nome"], u["nivel"] = c["nome"], c["nivel"]
    return {"unidades": por, "outras": outras, "agp": g}


def comparar(banco: Banco, pid: str, nomes: dict) -> dict:
    """Para a tela: por unidade, o topo de cada fonte, a diferença e o que vale (e por quê)."""
    cs = candidatos(banco, pid, nomes)
    prec, esc = precedencia(banco), escolhas(banco, pid)
    linhas = []
    for chave, u in cs["unidades"].items():
        ef = _efetivo(u, prec, esc.get(chave))
        tops = [c["topo"] for c in u["fontes"].values()]
        linhas.append({"chave": chave, "nome": u["nome"], "nivel": u["nivel"],
                       "fontes": {f: {k: c[k] for k in ("topo", "base", "cota_topo", "detalhe", "ref", "nome")}
                                  for f, c in u["fontes"].items()},
                       "diferenca_m": round(max(tops) - min(tops), 2) if len(tops) > 1 else 0.0,
                       "escolha": esc.get(chave), "usada": ef["fonte"] if ef else None,
                       "por": "você" if esc.get(chave) else "precedência"})
    linhas.sort(key=lambda x: min(c["topo"] for c in x["fontes"].values()))
    return {"poco": pid, "unidades": linhas, "precedencia": prec, "fontes": FONTES, "tolerancia_m": TOLERANCIA_M,
            "divergentes": sum(1 for x in linhas if x["diferenca_m"] > TOLERANCIA_M)}


def _efetivo(u: dict, prec: list[str], escolha: str | None) -> dict | None:
    if escolha == NENHUMA:
        return None
    if escolha and escolha in u["fontes"]:
        return u["fontes"][escolha]
    return next((u["fontes"][f] for f in prec if f in u["fontes"]), None)


def efetivas(banco: Banco, pid: str, nomes: dict) -> tuple[list[dict], list[dict], dict | None]:
    """Unidades litológicas efetivas no formato do AGP (tip L) + as não litológicas do AGP + o AGP do poço."""
    cs = candidatos(banco, pid, nomes)
    prec, esc = precedencia(banco), escolhas(banco, pid)
    saida = []
    for ordem, (chave, u) in enumerate(cs["unidades"].items()):
        c = _efetivo(u, prec, esc.get(chave))
        if c is None:
            continue
        if c["fonte"] == "agp":
            saida.append({**c["unidade"], "fonte": c["unidade"].get("fonte") or "AGP"})
            continue
        saida.append({"tip": "L", "sigla": chave, "codigo": nomes.get("#" + chave), "nome": u["nome"],
                      "nivel": u["nivel"] if u["nivel"] in ("F", "M", "G", "C", "S") else "F",
                      "topo": c["topo"], "base": c["base"], "cota_topo": c["cota_topo"], "cota_base": None,
                      "desc_topo": None, "desc_base": None, "ql": None, "metodo": None, "data": None,
                      "ordem": 1000 + ordem, "caminho": c["ref"], "fonte": FONTES[c["fonte"]]})
    return saida, cs["outras"], cs["agp"]


def pocos_com_topos(banco: Banco) -> set[str]:
    """Poços com algum topo, de qualquer fonte (para a seção e o bloco achar poços sem AGP)."""
    with banco.conexao() as c:
        ids = {r[0] for r in c.execute("SELECT DISTINCT poco_id FROM agp_unidades WHERE tip = 'L' AND topo IS NOT NULL")}
        ids |= {r[0] for r in c.execute("SELECT DISTINCT poco_id FROM fatos WHERE tipo = 'topo_formacao' "
                                        "AND prof_topo IS NOT NULL")}
        ids |= {r[0] for r in c.execute("""SELECT DISTINCT d.poco_id FROM dados_poco d JOIN leituras l ON l.rel = d.rel
                                           WHERE d.tipo IN ('topo', 'topo_calha') AND coalesce(l.confere, 1) = 1""")}
    return {i for i in ids if i}
