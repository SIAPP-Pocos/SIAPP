"""
Perfis de poço: DLIS, LIS e LAS → curvas padronizadas.

O que este módulo resolve (todas as armadilhas vistas em arquivos reais):

  - Profundidade em unidades variadas. No DLIS do 1-AURI-12-RN o índice vem em
    DÉCIMOS DE POLEGADA ("0.1 in"): 848520 = 2.155,2 m. Tudo é convertido
    para metros, e a unidade original fica registrada.
  - Vários "quadros" (frames) por arquivo, cada um com seu passo de amostragem
    (no AIT_P: 60B a cada 6 pol., 10B a cada 1 pol., 20B a cada 2 pol.…).
    As curvas ficam no quadro de origem; só a exportação reamostra.
  - Valores nulos (-999.25, -9999) viram "sem dado" (NaN).
  - Mnemônicos diferentes para a mesma grandeza (GR, ECGR, HGR…): cada curva
    recebe uma FAMÍLIA, pelo dicionário recursos/mnemonicos.json.

Cache: depois de lido, cada quadro é guardado em
<projeto>/pocos/<poço>/<arquivo>__<quadro>.npz (NumPy, só curvas de 1 valor por
profundidade). Abrir de novo é instantâneo e não depende do arquivo original.
"""

from __future__ import annotations

import json
import math
import os
import re
from datetime import datetime

import numpy as np

FORMATOS = (".dlis", ".lis", ".las")
NULOS = (-999.25, -9999.0, -999.0, -99999.0)
VERSAO_CACHE = 1

# unidade de profundidade → metros
_UNIDADES_M = {"m": 1.0, "meter": 1.0, "meters": 1.0, "metro": 1.0, "ft": 0.3048, "f": 0.3048,
               "feet": 0.3048, "foot": 0.3048, "in": 0.0254, "inch": 0.0254, "cm": 0.01, "mm": 0.001}


class ErroPerfil(ValueError):
    """Arquivo de perfil ilegível ou sem índice de profundidade."""


def fator_metros(unidade: str | None) -> float | None:
    """'0.1 in' → 0.00254; '.1IN' → 0.00254; 'ft' → 0.3048; desconhecida → None."""
    u = (unidade or "").strip().lower().replace(" ", "")
    if not u:
        return None
    m = re.fullmatch(r"(\d*\.?\d+)?([a-z]+)", u)
    if not m:
        return None
    mult, base = m.groups()
    if base not in _UNIDADES_M:
        return None
    return float(mult or 1) * _UNIDADES_M[base]


# =============================================================== famílias
def ler_familias(caminho: str) -> dict:
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)["familias"]


class Classificador:
    def __init__(self, familias: dict):
        self.familias = familias
        self._exato = {}
        for nome, f in familias.items():
            for m in f.get("preferencia", []):
                self._exato.setdefault(m.upper(), nome)
        self._padroes = [(re.compile(p), nome) for nome, f in familias.items()
                         for p in f.get("padroes", [])]

    def familia(self, mnemonico: str) -> str | None:
        m = mnemonico.upper().split(":")[-1]
        if m in self._exato:
            return self._exato[m]
        for rx, nome in self._padroes:
            if rx.match(m):
                return nome
        return None

    def prioridade(self, familia: str, mnemonico: str) -> int:
        pref = [x.upper() for x in self.familias.get(familia, {}).get("preferencia", [])]
        m = mnemonico.upper()
        return pref.index(m) if m in pref else len(pref)


# ================================================================ leitura
def _limpar(a: np.ndarray) -> np.ndarray:
    a = np.asarray(a, dtype=np.float64)
    for n in NULOS:
        a[np.isclose(a, n)] = np.nan
    a[~np.isfinite(a)] = np.nan
    return a


def _quadro(nome, indice_mnem, indice_unid, prof_bruta, curvas_brutas, descricoes):
    """Monta um quadro padronizado (profundidade em m, crescente)."""
    fator = fator_metros(indice_unid)
    if fator is None:
        raise ErroPerfil(f"Quadro {nome}: índice {indice_mnem!r} em unidade desconhecida "
                         f"{indice_unid!r} (só profundidade é suportada).")
    prof = _limpar(prof_bruta) * fator
    ordem = np.argsort(prof, kind="stable")
    prof = prof[ordem]
    curvas = {}
    for mn, (valores, unidade, dim) in curvas_brutas.items():
        if dim != 1:
            curvas[mn] = {"unidade": unidade, "dimensao": dim, "valores": None}
            continue
        curvas[mn] = {"unidade": unidade, "dimensao": 1, "valores": _limpar(valores)[ordem]}
    validas = np.isfinite(prof)
    passo = float(np.nanmedian(np.diff(prof[validas]))) if validas.sum() > 1 else None
    return {"nome": nome, "indice": {"mnemonico": indice_mnem, "unidade": indice_unid, "fator_m": fator},
            "prof": prof, "curvas": curvas, "descricoes": descricoes,
            "topo_m": float(np.nanmin(prof)) if validas.any() else None,
            "base_m": float(np.nanmax(prof)) if validas.any() else None,
            "passo_m": round(passo, 5) if passo else None}


def _texto(v) -> str:
    if v is None:
        return ""
    if isinstance(v, (list, tuple, np.ndarray)):
        v = v[0] if len(v) else ""
    return str(v).strip()


def ler_dlis(caminho: str):
    from dlisio import dlis
    quadros, cab = [], {}
    with dlis.load(caminho) as arquivos:
        varios = len(arquivos) > 1
        for i, lf in enumerate(arquivos):
            if lf.origins and not cab:
                o = lf.origins[0]
                cab = {"poco": _texto(o.well_name), "campo": _texto(o.field_name),
                       "empresa": _texto(o.company), "cadastro": _texto(o.well_id),
                       "produtor": _texto(getattr(o, "producer_name", "")),
                       "conjunto": _texto(o.file_set_name),
                       "criado": str(o.creation_time or "")}
            params = {p.name: p.values for p in lf.parameters}
            if "TD" in params:
                cab.setdefault("parametros", {})["TD"] = _texto(params["TD"])
            if lf.tools:
                cab["ferramentas"] = sorted({t.name for t in lf.tools})
            for fr in lf.frames:
                if not fr.channels:
                    continue
                try:
                    dados = fr.curves()
                except Exception as e:  # noqa: BLE001 — arquivo real com quadro corrompido
                    cab.setdefault("avisos", []).append(f"quadro {fr.name}: {e}")
                    continue
                canais = fr.channels
                idx = canais[0]
                curvas, desc = {}, {}
                nomes = dados.dtype.names
                for j, ch in enumerate(canais[1:], start=2):
                    campo = nomes[j] if j < len(nomes) else ch.name
                    dim = int(np.prod(ch.dimension or [1]))
                    curvas[ch.name] = (dados[campo] if dim == 1 else None, ch.units or "", dim)
                    desc[ch.name] = ch.long_name if isinstance(ch.long_name, str) else _texto(ch.long_name)
                nome = f"{i}:{fr.name}" if varios else fr.name
                quadros.append(_quadro(nome, idx.name, idx.units, dados[nomes[1]], curvas, desc))
    return quadros, cab


def ler_lis(caminho: str):
    from dlisio import lis
    quadros, cab = [], {}
    with lis.load(caminho) as arquivos:
        for i, lf in enumerate(arquivos):
            for k, dfsr in enumerate(lf.data_format_specs()):
                taxas = dfsr.sample_rates()
                try:
                    dados = (lis.curves(lf, dfsr) if len(taxas) <= 1
                             else lis.curves(lf, dfsr, sample_rate=min(taxas)))
                except Exception as e:  # noqa: BLE001
                    cab.setdefault("avisos", []).append(f"bloco {i}.{k}: {e}")
                    continue
                nomes = dados.dtype.names
                indice = dfsr.index_mnem or nomes[0]
                curvas = {}
                for sb in dfsr.specs:
                    mn = sb.mnemonic.strip()
                    if mn == indice or mn not in nomes:
                        continue
                    col = dados[mn]
                    dim = 1 if col.ndim == 1 else int(np.prod(col.shape[1:]))
                    curvas[mn] = (col if dim == 1 else None, (sb.units or "").strip(), dim)
                quadros.append(_quadro(f"{i}.{k}", indice, (dfsr.index_units or "").strip(),
                                       dados[indice], curvas, {}))
    return quadros, cab


def ler_las(caminho: str):
    import lasio
    las = lasio.read(caminho, ignore_header_errors=True)
    if not las.curves:
        raise ErroPerfil("LAS sem curvas.")
    idx = las.curves[0]
    curvas = {c.mnemonic: (np.asarray(c.data), c.unit or "", 1) for c in las.curves[1:]}
    desc = {c.mnemonic: c.descr for c in las.curves[1:]}
    w = las.well

    def campo(m):
        try:
            return _texto(w[m].value)
        except KeyError:
            return ""
    cab = {"poco": campo("WELL"), "campo": campo("FLD"), "empresa": campo("COMP"),
           "cadastro": campo("UWI") or campo("API"), "servico": campo("SRVC"), "data": campo("DATE")}
    unidade = idx.unit or campo("STRT") and w["STRT"].unit
    return [_quadro("LAS", idx.mnemonic, unidade, np.asarray(idx.data), curvas, desc)], cab


def ler(caminho: str):
    ext = os.path.splitext(caminho)[1].lower()
    leitores = {".dlis": ler_dlis, ".lis": ler_lis, ".las": ler_las}
    if ext not in leitores:
        raise ErroPerfil(f"Formato não suportado: {ext}")
    try:
        return leitores[ext](caminho)
    except ErroPerfil:
        raise
    except Exception as e:  # noqa: BLE001 — qualquer falha do leitor vira mensagem legível
        raise ErroPerfil(f"Não consegui ler {os.path.basename(caminho)} ({type(e).__name__}: {e})") from e


# ============================================================ inventário
def inventariar(caminho: str, classificador: Classificador, pasta_cache: str) -> dict:
    """Lê o arquivo, grava o cache e devolve o inventário (quadros e curvas)."""
    quadros, cab = ler(caminho)
    if not quadros:
        raise ErroPerfil("Nenhum quadro de curvas legível no arquivo.")
    os.makedirs(pasta_cache, exist_ok=True)
    base = os.path.basename(caminho)
    inventario = []
    for q in quadros:
        prof = q["prof"]
        arrays = {"__prof__": prof.astype(np.float64)}
        curvas = []
        for mn, c in q["curvas"].items():
            fam = classificador.familia(mn)
            item = {"mnemonico": mn, "unidade": c["unidade"], "dimensao": c["dimensao"],
                    "descricao": q["descricoes"].get(mn, ""), "familia": fam,
                    "n_validas": 0, "topo_m": None, "base_m": None}
            v = c["valores"]
            if v is not None:
                ok = np.isfinite(v) & np.isfinite(prof)
                item["n_validas"] = int(ok.sum())
                if ok.any():
                    item["topo_m"] = float(prof[ok].min())
                    item["base_m"] = float(prof[ok].max())
                arrays[mn] = v.astype(np.float32)
            curvas.append(item)
        np.savez_compressed(os.path.join(pasta_cache, _nome_cache(base, q["nome"])), **arrays)
        inventario.append({"nome": q["nome"], "indice": q["indice"], "topo_m": q["topo_m"],
                           "base_m": q["base_m"], "passo_m": q["passo_m"], "n_amostras": int(len(prof)),
                           "curvas": curvas})
    topos = [q["topo_m"] for q in inventario if q["topo_m"] is not None]
    bases = [q["base_m"] for q in inventario if q["base_m"] is not None]
    resumo = {"arquivo": base, "formato": os.path.splitext(base)[1].lower().lstrip("."),
              "cabecalho": cab, "quadros": inventario,
              "topo_m": min(topos) if topos else None, "base_m": max(bases) if bases else None,
              "versao_cache": VERSAO_CACHE,
              "inventariado_em": datetime.now().isoformat(timespec="seconds")}
    with open(os.path.join(pasta_cache, base + ".inventario.json"), "w", encoding="utf-8") as f:
        json.dump(resumo, f, ensure_ascii=False, indent=1)
    return resumo


def _nome_cache(arquivo: str, quadro: str) -> str:
    return f"{arquivo}__{re.sub(r'[^A-Za-z0-9._-]', '_', quadro)}.npz"


def ler_inventario(pasta_cache: str, arquivo: str) -> dict | None:
    try:
        with open(os.path.join(pasta_cache, arquivo + ".inventario.json"), encoding="utf-8") as f:
            inv = json.load(f)
        return inv if inv.get("versao_cache") == VERSAO_CACHE else None
    except (OSError, json.JSONDecodeError):
        return None


def carregar_quadro(pasta_cache: str, arquivo: str, quadro: str) -> dict:
    caminho = os.path.join(pasta_cache, _nome_cache(arquivo, quadro))
    if not os.path.isfile(caminho):
        raise ErroPerfil("Cache do perfil ausente: inventarie o arquivo de novo.")
    with np.load(caminho) as z:
        return {k: z[k] for k in z.files}


def curvas_padrao(inventario: dict, classificador: Classificador) -> list[dict]:
    """Uma curva por família (a de maior preferência; empate: a com mais dados)."""
    melhor: dict[str, tuple] = {}
    for q in inventario["quadros"]:
        for c in q["curvas"]:
            fam = c["familia"]
            if not fam or c["dimensao"] != 1 or not c["n_validas"]:
                continue
            chave_ = (classificador.prioridade(fam, c["mnemonico"]), -c["n_validas"])
            if fam not in melhor or chave_ < melhor[fam][0]:
                melhor[fam] = (chave_, {"quadro": q["nome"], "mnemonico": c["mnemonico"],
                                        "familia": fam, "unidade": c["unidade"]})
    return [v[1] for v in melhor.values()]


# ========================================================= visualização
def _decimar(prof, valores, max_pontos):
    """Reduz para o gráfico preservando picos (mínimo e máximo de cada bloco)."""
    n = len(prof)
    if n <= max_pontos:
        return prof, valores
    bloco = math.ceil(n / (max_pontos / 2))
    p_out, v_out = [], []
    for i in range(0, n, bloco):
        v = valores[i:i + bloco]
        p = prof[i:i + bloco]
        ok = np.isfinite(v)
        if not ok.any():
            p_out.append(p[0])
            v_out.append(np.nan)
            continue
        i_min, i_max = np.nanargmin(v), np.nanargmax(v)
        for j in sorted({i_min, i_max}):
            p_out.append(p[j])
            v_out.append(v[j])
    return np.asarray(p_out), np.asarray(v_out)


def dados_grafico(pasta_cache: str, arquivo: str, selecao: list[dict], topo: float | None = None,
                  base: float | None = None, max_pontos: int = 2500) -> list[dict]:
    """Curvas recortadas no intervalo [topo, base] (m), prontas para desenhar."""
    cache: dict[str, dict] = {}
    saida = []
    for s in selecao:
        q = cache.setdefault(s["quadro"], carregar_quadro(pasta_cache, arquivo, s["quadro"]))
        prof = q["__prof__"]
        if s["mnemonico"] not in q:
            continue
        v = q[s["mnemonico"]].astype(np.float64)
        sel = np.isfinite(prof)
        if topo is not None:
            sel &= prof >= topo
        if base is not None:
            sel &= prof <= base
        p, vv = _decimar(prof[sel], v[sel], max_pontos)
        saida.append({**s, "prof": [round(float(x), 3) for x in p],
                      "valores": [None if not np.isfinite(x) else round(float(x), 5) for x in vv]})
    return saida


# =============================================================== exportar
def reamostrar(pasta_cache: str, arquivo: str, selecao: list[dict], passo: float | None = None):
    """`passo` em metros; sem passo, usa o menor passo entre as curvas escolhidas."""
    """Todas as curvas escolhidas numa profundidade comum (o menor passo entre elas)."""
    series, passos, topos, bases = [], [], [], []
    for s in selecao:
        q = carregar_quadro(pasta_cache, arquivo, s["quadro"])
        prof = q["__prof__"]
        if s["mnemonico"] not in q:
            continue
        v = q[s["mnemonico"]].astype(np.float64)
        ok = np.isfinite(prof) & np.isfinite(v)
        if ok.sum() < 2:
            continue
        p, vv = prof[ok], v[ok]
        series.append((s, p, vv))
        passos.append(float(np.median(np.diff(p))))
        topos.append(p.min())
        bases.append(p.max())
    if not series:
        raise ErroPerfil("Nenhuma das curvas escolhidas tem dados.")
    passo = passo or max(min(passos), 0.01)
    grade = np.round(np.arange(min(topos), max(bases) + passo / 2, passo), 4)
    colunas = []
    for s, p, vv in series:
        r = np.interp(grade, p, vv, left=np.nan, right=np.nan)
        # não inventar dado em falhas maiores que 2 passos da curva original
        lacuna = np.searchsorted(p, grade)
        lacuna = np.clip(lacuna, 1, len(p) - 1)
        distante = (p[lacuna] - p[lacuna - 1]) > 2.5 * max(np.median(np.diff(p)), passo)
        r[distante] = np.nan
        colunas.append((s, r))
    return grade, colunas, passo


def exportar_las(caminho_saida: str, pasta_cache: str, arquivo: str, selecao: list[dict],
                 cabecalho: dict, poco: str, passo: float | None = None) -> dict:
    import lasio
    grade, colunas, passo = reamostrar(pasta_cache, arquivo, selecao, passo)
    las = lasio.LASFile()
    las.well["STRT"].value, las.well["STRT"].unit = float(grade[0]), "M"
    las.well["STOP"].value, las.well["STOP"].unit = float(grade[-1]), "M"
    las.well["STEP"].value, las.well["STEP"].unit = float(passo), "M"
    las.well["NULL"].value = -999.25
    las.well["WELL"].value = poco or cabecalho.get("poco", "")
    las.well["FLD"].value = cabecalho.get("campo", "")
    las.well["COMP"].value = cabecalho.get("empresa", "")
    las.well["UWI"].value = cabecalho.get("cadastro", "")
    las.well["SRVC"].value = "SIAPP (a partir de " + arquivo + ")"
    las.well["DATE"].value = datetime.now().strftime("%Y-%m-%d")
    las.append_curve("DEPT", grade, unit="M", descr="Profundidade medida")
    nomes = set()
    for s, r in colunas:
        nome = s["mnemonico"] if s["mnemonico"] not in nomes else f"{s['mnemonico']}_{s['quadro']}"
        nomes.add(nome)
        las.append_curve(nome, np.where(np.isfinite(r), r, -999.25), unit=s.get("unidade", ""),
                         descr=f"{s.get('familia') or ''} quadro {s['quadro']}".strip())
    las.other = ("Gerado pelo SIAPP. Curvas reamostradas por interpolação linear na grade comum; "
                 "falhas maiores que 2,5 passos ficam como nulo. Original: " + arquivo)
    os.makedirs(os.path.dirname(caminho_saida), exist_ok=True)
    with open(caminho_saida, "w", encoding="utf-8") as f:
        las.write(f, version=2.0)
    return {"amostras": int(len(grade)), "passo_m": passo, "curvas": len(colunas)}


def exportar_csv(caminho_saida: str, pasta_cache: str, arquivo: str, selecao: list[dict],
                 passo: float | None = None) -> dict:
    grade, colunas, passo = reamostrar(pasta_cache, arquivo, selecao, passo)
    os.makedirs(os.path.dirname(caminho_saida), exist_ok=True)
    with open(caminho_saida, "w", encoding="utf-8", newline="") as f:
        f.write("PROF_M;" + ";".join(f"{s['mnemonico']} ({s.get('unidade') or '-'})" for s, _ in colunas) + "\n")
        for i, prof in enumerate(grade):
            vals = ["" if not np.isfinite(r[i]) else f"{r[i]:.5g}".replace(".", ",") for _, r in colunas]
            f.write(f"{prof:.4f}".replace(".", ",") + ";" + ";".join(vals) + "\n")
    return {"amostras": int(len(grade)), "passo_m": passo, "curvas": len(colunas)}
