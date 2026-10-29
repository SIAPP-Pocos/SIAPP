"""Perfis já processados pela operadora (bloco 9, item 5): achar e comparar.

Parte do acervo do REATE traz, além das curvas medidas, as **curvas interpretadas** pela operadora:
argilosidade (VSH, VCL), porosidade efetiva e total (PHIE, PHIT), saturação de água (SW, SWE) e, às vezes,
permeabilidade. Vêm na pasta "Perfil Digital Processado" (230 arquivos na Potiguar e em Alagoas, 28/10/2026)
ou em arquivos "_adic"/"_interp" junto dos perfis comuns. As famílias dessas curvas têm `"interpretacao": true`
em recursos/mnemonicos.json.

Duas coisas aqui:

- **pesquisa**: quais poços do levantamento do acervo têm essas curvas (o levantamento guarda os mnemônicos
  de cada arquivo, então a pesquisa não precisa baixar nada) — `reclassificar_acervo` refaz as famílias do
  levantamento com o arquivo de mnemônicos atual;
- **comparação**: numa avaliação de formação do SIAPP, as médias de Vsh, φ e Sw de cada intervalo ao lado
  das da operadora, no mesmo intervalo e no net pay do SIAPP.

A curva da operadora em porcentagem (mediana > 1,5) é convertida para fração. Nada aqui diz qual
interpretação está certa: a diferença aponta onde olhar (parâmetros, curvas usadas, corte).
"""

from __future__ import annotations

import glob
import json
import os

import numpy as np

from . import perfis as mpf

FAMILIAS = ("VSH", "PHIE", "PHIT", "SW", "PERM")
# o que se compara com cada resultado do SIAPP (φ: a efetiva; se não houver, a total)
COMPARAR = {"vsh": ("VSH",), "phi": ("PHIE", "PHIT"), "sw": ("SW",)}


def familias_interpretacao(familias: dict) -> list[str]:
    return [k for k, f in familias.items() if f.get("interpretacao")]


# ---------------------------------------------------------------- pesquisa no acervo
def reclassificar_acervo(banco, classificador: mpf.Classificador) -> int:
    """Famílias de cada arquivo do levantamento pelos mnemônicos guardados (sem baixar nada), e o resumo
    de cada poço. Devolve quantos arquivos mudaram."""
    from . import levantamento as mlv
    mudou, por_bacia = 0, {}
    with banco.conexao() as c:
        linhas = c.execute("SELECT bacia, caminho, poco_caminho, curvas, familias FROM acervo_arquivos "
                           "WHERE curvas IS NOT NULL AND curvas <> ''").fetchall()
        for bacia, caminho, poco_cam, curvas, fams in linhas:
            try:
                lista = json.loads(curvas)
            except (TypeError, ValueError):
                continue
            novas = json.dumps(sorted({f for f in (classificador.familia(str(m)) for m in lista) if f}))
            if novas != (fams or "[]"):
                c.execute("UPDATE acervo_arquivos SET familias = ? WHERE bacia = ? AND caminho = ?",
                          (novas, bacia, caminho))
                mudou += 1
                por_bacia.setdefault(bacia, set()).add(poco_cam)
    for bacia, caminhos in por_bacia.items():
        mlv.atualizar_pocos(banco, bacia, sorted(caminhos))
    return mudou


def pesquisar(banco, familias_interp: list[str], bacia: str | None = None) -> dict:
    """Poços do levantamento com curva interpretada: por poço, os arquivos e as famílias."""
    cond, args = ["a.familias IS NOT NULL"], []
    if bacia:
        cond.append("a.bacia = ?")
        args.append(bacia)
    with banco.conexao() as c:
        linhas = [dict(r) for r in c.execute(
            f"""SELECT a.bacia, a.poco_caminho, a.nome, a.pasta, a.tamanho, a.familias, p.poco_id, p.categoria
                FROM acervo_arquivos a LEFT JOIN acervo_pocos p ON p.bacia = a.bacia AND p.caminho = a.poco_caminho
                WHERE {' AND '.join(cond)}""", args)]
    alvo = set(familias_interp)
    por = {}
    for r in linhas:
        fams = set(json.loads(r["familias"] or "[]"))
        achou = sorted(fams & alvo)
        if not achou:
            continue
        chave = (r["bacia"], r["poco_caminho"])
        p = por.setdefault(chave, {"bacia": r["bacia"], "poco": r["poco_id"] or r["poco_caminho"].rstrip("/").split("/")[-1],
                                   "categoria": r["categoria"], "familias": set(), "arquivos": []})
        p["familias"] |= set(achou)
        p["arquivos"].append({"nome": r["nome"], "pasta": r["pasta"], "tamanho": r["tamanho"], "familias": achou})
    pocos = sorted(por.values(), key=lambda p: (p["bacia"], p["poco"]))
    for p in pocos:
        p["familias"] = sorted(p["familias"])
        p["completo"] = all(any(f in p["familias"] for f in fs) for fs in COMPARAR.values())
    return {"pocos": pocos, "n_pocos": len(pocos), "n_arquivos": sum(len(p["arquivos"]) for p in pocos),
            "completos": sum(1 for p in pocos if p["completo"])}


# ---------------------------------------------------------------- curvas do poço
def curvas_do_poco(pasta_cache: str, classificador: mpf.Classificador) -> dict[str, dict]:
    """A melhor curva de cada família de interpretação entre os perfis já abertos do poço."""
    melhor = {}
    for caminho in glob.glob(os.path.join(pasta_cache, "*.inventario.json")):
        arquivo = os.path.basename(caminho)[: -len(".inventario.json")]
        inv = mpf.ler_inventario(pasta_cache, arquivo)
        if not inv:
            continue
        for q in inv.get("quadros", []):
            for c in q.get("curvas", []):
                fam = classificador.familia(c["mnemonico"], c.get("unidade"))
                if fam not in FAMILIAS or c.get("dimensao", 1) != 1 or not c.get("n_validas"):
                    continue
                chave = (classificador.prioridade(fam, c["mnemonico"]), -c["n_validas"])
                if fam not in melhor or chave < melhor[fam][0]:
                    melhor[fam] = (chave, {"arquivo": arquivo, "quadro": q["nome"], "mnemonico": c["mnemonico"],
                                           "unidade": c.get("unidade") or "", "topo_m": c.get("topo_m"),
                                           "base_m": c.get("base_m")})
    return {k: v[1] for k, v in melhor.items()}


def _fracao(v: np.ndarray, unidade: str) -> np.ndarray:
    u = (unidade or "").strip().lower()
    ok = np.isfinite(v)
    if u in ("%", "pu", "p.u.") or (ok.any() and np.nanmedian(v[ok]) > 1.5):
        return v / 100.0
    return v


def _na_grade(pasta_cache: str, curva: dict, grade: np.ndarray) -> np.ndarray:
    q = mpf.carregar_quadro(pasta_cache, curva["arquivo"], curva["quadro"])
    prof = np.asarray(q["__prof__"], float)
    v = np.asarray(q[curva["mnemonico"]], float)
    if v.ndim != 1:
        return np.full(len(grade), np.nan)
    ok = np.isfinite(prof) & np.isfinite(v)
    if ok.sum() < 2:
        return np.full(len(grade), np.nan)
    prof, v = prof[ok], _fracao(v[ok], curva["unidade"])
    ordem = np.argsort(prof)
    prof, v = prof[ordem], v[ordem]
    saida = np.interp(grade, prof, v, left=np.nan, right=np.nan)
    # sem amostra perto (buraco na curva): fica de fora
    passo = float(np.median(np.diff(prof))) if len(prof) > 1 else 0.0
    idx = np.clip(np.searchsorted(prof, grade), 1, len(prof) - 1)
    dist = np.minimum(np.abs(grade - prof[idx - 1]), np.abs(prof[idx] - grade))
    saida[dist > max(3 * passo, 0.5)] = np.nan
    return saida


def _media(v, m):
    sel = m & np.isfinite(v)
    return round(float(np.mean(v[sel])), 4) if sel.sum() else None


def comparar(pasta_cache: str, curvas_siapp: dict, registro: dict, operador: dict[str, dict]) -> dict:
    """`curvas_siapp`: o npz da avaliação (prof, VSH, PHI, SW, PAY); `registro`: o JSON da avaliação;
    `operador`: curvas_do_poco. Por intervalo: médias do SIAPP e da operadora no intervalo e no net pay."""
    grade = np.asarray(curvas_siapp["prof"], float)
    pay = np.nan_to_num(curvas_siapp.get("PAY", np.zeros(len(grade))), nan=0) > 0.5
    usadas, serie = {}, {}
    for k, fams in COMPARAR.items():
        fam = next((f for f in fams if f in operador), None)
        if fam:
            usadas[k] = {**operador[fam], "familia": fam}
            serie[k] = _na_grade(pasta_cache, operador[fam], grade)
    siapp = {"vsh": curvas_siapp.get("VSH"), "phi": curvas_siapp.get("PHI"), "sw": curvas_siapp.get("SW")}
    linhas = []
    for i in registro.get("intervalos", []):
        m = (grade >= float(i["topo"])) & (grade <= float(i["base"]))
        ln = {"nome": i.get("nome") or "", "topo": i["topo"], "base": i["base"], "net_pay_m": i.get("net_pay_m")}
        for k in ("vsh", "phi", "sw"):
            s = np.asarray(siapp[k], float) if siapp[k] is not None else np.full(len(grade), np.nan)
            o = serie.get(k)
            d = {"siapp": _media(s, m), "operador": _media(o, m) if o is not None else None}
            if k != "vsh":
                d["siapp_pay"] = _media(s, m & pay)
                d["operador_pay"] = _media(o, m & pay) if o is not None else None
            d["diferenca"] = (round(d["siapp"] - d["operador"], 4)
                              if d["siapp"] is not None and d["operador"] is not None else None)
            ln[k] = d
        ln["cobertura_operador"] = (round(float((m & np.isfinite(serie["sw" if "sw" in serie else next(iter(serie))])).sum()
                                               / max(m.sum(), 1)), 3) if serie else 0.0)
        linhas.append(ln)
    return {"intervalos": linhas, "curvas": usadas, "faltam": [k for k in COMPARAR if k not in usadas]}
