"""Zonas produtoras (net pay) no bloco 3D (0.55): topo e base de cada reservatório, poço a poço, em vez dos topos de formação.

Por que existe: o trabalho à mão do Guamaré não interpolou formações; interpolou **a zona produtora** (onde a pasta de poço diz que
há óleo ou gás em quantidade para produzir), com mais de um reservatório. O bloco 3D passa a aceitar essas zonas como "unidades":

- cada poço entra com **intervalos candidatos**, de várias fontes (canhoneados, testes de formação, análise de perfis, amostra de
  fluido, zonas-reservatório do AGP, intervalos que você marcou, e uma tabela sua em CSV/Excel);
- os intervalos de todos os poços são **agrupados em reservatórios** pela profundidade (cota): intervalos que se sobrepõem, ou
  que ficam a menos de `tolerancia_m` um do outro, são o mesmo reservatório. Os grupos são numerados do mais raso ao mais fundo;
- em cada poço e reservatório fica **um** intervalo: o da fonte de maior prioridade (`regra = "prioridade"`) ou o envelope de todos
  (`"envelope"`: do menor topo ao maior fim);
- cada reservatório vira **duas superfícies**: o topo (`ZP1`) e a base (`ZP1_B`). A espessura é a diferença entre elas.

Tudo é editável: você pode mover um intervalo para outro reservatório, ignorá-lo, corrigir os números e escolher quais
reservatórios aparecem. Cada intervalo mostra o documento de origem e se a página foi lida por OCR (números de OCR pedem conferência).

Limites: o agrupamento é por profundidade, não por geologia (falhas podem deslocar um mesmo reservatório mais que a tolerância:
aumente-a ou reatribua à mão); intervalo é "zona com indício de produção", não "net pay" no sentido estrito (corte de Vsh, φ e Sw);
o net pay da avaliação de formação, quando existe, aparece à parte.
"""

from __future__ import annotations

import csv
import io
import json
import os
import re
import unicodedata

import numpy as np

from . import agp as magp
from . import dados_poco as mdp
from . import pocos as mpo
from . import utm as mutm
from .banco import Banco

FONTES = {
    "tabela": "Tabela sua (CSV ou Excel importado)",
    "marcado": "Intervalos que você marcou (intervalo-alvo)",
    "canhoneado": "Canhoneados (RFCP)",
    "teste": "Testes de formação (RFP, TFR)",
    "analise_perfil": "Análise de perfis do operador (RFP)",
    "fluido": "Análise de fluido (amostra do PVT)",
    "agp_zonas": "Zonas-reservatório do AGP",
}
PRIORIDADE_PADRAO = list(FONTES)
REGRAS = ("prioridade", "envelope")
TOLERANCIA_PADRAO_M = 20.0
MAX_ZONAS = 8
SLOTS_ZONA = {f"ZP{k}": k for k in range(1, MAX_ZONAS + 1)}      # cores do bloco (as mesmas das formações)


class ErroZonas(ValueError):
    pass


def chave_zona(n: int) -> str:
    return f"ZP{n}"


def chave_base(chave: str) -> str:
    return f"{chave}_B"


# ------------------------------------------------------------------------------------------------------------- candidatos
def _valido(topo, base) -> bool:
    return topo is not None and base is not None and base > topo


def _valido_em(topo, base, ref: str) -> bool:
    """Em profundidade medida a base é maior que o topo; em cota (positiva para cima) é menor."""
    return topo is not None and base is not None and (base < topo if ref == "cota" else base > topo)


def coletar(banco: Banco, poco: str, fontes: list[str], tabela: list[dict] | None = None, leitura=None) -> list[dict]:
    """Intervalos candidatos do poço (profundidade medida), das fontes pedidas. `leitura(rel, pagina)` → "digital" | "ocr" | ""."""
    out: list[dict] = []
    vistos: set = set()

    def somar(fonte: str, nome: str, topo, base, item: dict | None = None, **extra):
        if not _valido_em(topo, base, extra.get("ref", "md")):
            return
        topo, base = float(topo), float(base)
        ident = f"{poco}|{fonte}|{topo:g}-{base:g}"
        if ident in vistos:
            return
        vistos.add(ident)
        rel, pag = (item or {}).get("rel"), (item or {}).get("pagina")
        out.append({"id": ident, "poco": poco, "fonte": fonte, "fonte_rotulo": FONTES[fonte], "nome": nome or "",
                    "topo": topo, "base": base, "ref": "md", "documento": (item or {}).get("documento") or "",
                    "rel": rel or "", "pagina": pag, "leitura": (leitura(rel, pag) if leitura and rel else ""), **extra})

    for fonte in fontes:
        if fonte == "tabela":
            for r in tabela or []:
                if r.get("poco_id") == poco:
                    somar("tabela", r.get("zona") or "tabela", r["topo"], r["base"], ref=r.get("ref", "md"))
        elif fonte == "marcado":
            for f in banco.fatos(poco, tipo="intervalo_alvo"):
                somar("marcado", f.get("nome"), f.get("prof_topo"), f.get("prof_base"))
        elif fonte == "canhoneado":
            for i in mdp.itens_do_poco(banco, poco, "canhoneado"):
                somar("canhoneado", i.get("nome"), i["prof_topo"], i["prof_base"], i)
        elif fonte == "teste":
            for tipo in ("teste_formacao", "teste_tfr"):
                for i in mdp.itens_do_poco(banco, poco, tipo):
                    somar("teste", " ".join(x for x in (i.get("nome"), i.get("texto")) if x), i["prof_topo"], i["prof_base"], i)
        elif fonte == "analise_perfil":
            for i in mdp.itens_do_poco(banco, poco, "analise_perfil"):
                somar("analise_perfil", " ".join(x for x in (i.get("texto"), i.get("nome")) if x), i["prof_topo"], i["prof_base"], i)
        elif fonte == "fluido":
            for i in mdp.itens_do_poco(banco, poco, "pvt"):
                somar("fluido", " ".join(x for x in (i.get("nome"), i.get("texto")) if x), i["prof_topo"], i["prof_base"], i)
        elif fonte == "agp_zonas":
            for g in magp.do_poco(banco, poco)[:1]:
                for z in g["dados"].get("zonas", []):
                    somar("agp_zonas", f"Zona {z['codigo']}", z.get("topo"), z.get("base"))
    return out


# ------------------------------------------------------------------------------------------------------------- agrupamento
def agrupar(cands: list[dict], tolerancia_m: float) -> list[list[dict]]:
    """Grupos de intervalos (reservatórios) pela profundidade: cada um com `cota_topo`/`cota_base` já calculadas.
    Do mais raso ao mais fundo. Sobrepostos ou a menos de `tolerancia_m` de distância ficam juntos."""
    if not cands:
        return []
    ordem = sorted(cands, key=lambda c: (-c["cota_topo"], -c["cota_base"]))          # raso primeiro (cota maior)
    grupos: list[list[dict]] = [[ordem[0]]]
    fundo = -ordem[0]["cota_base"]                                                    # prof. abaixo do datum, positiva
    for c in ordem[1:]:
        if -c["cota_topo"] > fundo + tolerancia_m:
            grupos.append([c])
            fundo = -c["cota_base"]
        else:
            grupos[-1].append(c)
            fundo = max(fundo, -c["cota_base"])
    return grupos


class Conversor:
    """Profundidade medida ↔ cota (m, positiva para cima) de um poço, vertical ou pela trajetória/pontos de controle."""

    def __init__(self, f_md_cota, md_max: float):
        self._f = f_md_cota
        self._md = np.linspace(0.0, max(md_max, 1.0), 2000)
        self._cota = np.asarray(f_md_cota(self._md), float)

    def cota(self, md) -> np.ndarray:
        return np.asarray(self._f(np.atleast_1d(np.asarray(md, float))), float)

    def md(self, cota) -> np.ndarray:
        c = np.atleast_1d(np.asarray(cota, float))
        ordem = np.argsort(self._cota)
        return np.interp(c, self._cota[ordem], self._md[ordem])


def planejar(candidatos: dict[str, list[dict]], conversores: dict[str, Conversor], config: dict | None = None) -> dict:
    """Escolhe, em cada poço, o intervalo de cada reservatório. Devolve:
    `zonas` (lista com chave, nome, n_pocos, cota_media, ativa), `por_poco` ({poço: [intervalos escolhidos, do raso ao fundo]}),
    `candidatos` (todas as linhas, com a zona, se foi usado e os números editados) e `avisos`."""
    cfg = config or {}
    regra = cfg.get("regra", "prioridade")
    if regra not in REGRAS:
        raise ErroZonas(f"Regra desconhecida: {regra} (use {', '.join(REGRAS)}).")
    tol = float(cfg.get("tolerancia_m", TOLERANCIA_PADRAO_M))
    if tol < 0:
        raise ErroZonas("A tolerância não pode ser negativa.")
    ordem_fontes = [f for f in cfg.get("fontes", PRIORIDADE_PADRAO) if f in FONTES]
    ajustes = cfg.get("ajustes") or {}
    avisos: list[str] = []
    todos: list[dict] = []
    for poco, lista in candidatos.items():
        conv = conversores.get(poco)
        for c in lista:
            c = dict(c)
            aj = ajustes.get(c["id"]) or {}
            c["topo_orig"], c["base_orig"] = c["topo"], c["base"]
            if aj.get("topo") is not None:
                c["topo"] = float(aj["topo"])
            if aj.get("base") is not None:
                c["base"] = float(aj["base"])
            c["editado"] = (c["topo"], c["base"]) != (c["topo_orig"], c["base_orig"])
            c["ignorado"] = aj.get("zona") == "ignorar" or c["fonte"] not in ordem_fontes
            c["zona_manual"] = aj.get("zona") if aj.get("zona") not in (None, "", "auto", "ignorar") else None
            c["zona"], c["usado"], c["aviso"] = "", False, ""
            if not _valido_em(c["topo"], c["base"], c.get("ref", "md")):
                c["aviso"], c["ignorado"] = "topo e base inválidos (a base precisa ficar mais fundo que o topo)", True
            elif conv is None:
                c["aviso"], c["ignorado"] = "sem mesa rotativa para converter em cota", True
            else:
                if c.get("ref") == "cota":                                   # a tabela veio em cota: acha a profundidade medida
                    c["cota_topo"], c["cota_base"] = float(c["topo"]), float(c["base"])
                    c["topo"], c["base"] = float(conv.md(c["cota_topo"])[0]), float(conv.md(c["cota_base"])[0])
                else:
                    c["cota_topo"], c["cota_base"] = float(conv.cota(c["topo"])[0]), float(conv.cota(c["base"])[0])
            todos.append(c)
    ativos = [c for c in todos if not c["ignorado"]]
    automaticos = [c for c in ativos if not c["zona_manual"]]
    grupos = agrupar(automaticos, tol)
    if len(grupos) > MAX_ZONAS:
        avisos.append(f"{len(grupos)} reservatórios pelo agrupamento (máximo {MAX_ZONAS}): aumente a tolerância; os mais fundos foram descartados.")
        grupos = grupos[:MAX_ZONAS]
    chaves = [chave_zona(k + 1) for k in range(len(grupos))]
    for ch, g in zip(chaves, grupos):
        for c in g:
            c["zona"] = ch
    for c in ativos:
        if c["zona_manual"]:
            c["zona"] = c["zona_manual"]
            if c["zona"] not in chaves:
                chaves.append(c["zona"])
    chaves = sorted(set(chaves), key=lambda ch: int(ch[2:]) if ch[2:].isdigit() else 99)
    # um intervalo por poço e reservatório
    por_poco: dict[str, list[dict]] = {}
    for poco in candidatos:
        escolhidos = []
        for ch in chaves:
            g = [c for c in ativos if c["poco"] == poco and c["zona"] == ch]
            if not g:
                continue
            if regra == "envelope":
                usados = g
            else:
                melhor = next((f for f in ordem_fontes if any(c["fonte"] == f for c in g)), g[0]["fonte"])
                usados = [c for c in g if c["fonte"] == melhor]
            for c in usados:
                c["usado"] = True
            topo, base = min(c["topo"] for c in usados), max(c["base"] for c in usados)
            conv = conversores[poco]
            escolhidos.append({"zona": ch, "topo": topo, "base": base, "cota_topo": float(conv.cota(topo)[0]),
                               "cota_base": float(conv.cota(base)[0]),
                               "fonte": ", ".join(dict.fromkeys(FONTES[c["fonte"]] for c in usados)),
                               "n_candidatos": len(g)})
        escolhidos.sort(key=lambda e: -e["cota_topo"])
        for a, b in zip(escolhidos, escolhidos[1:]):
            if b["cota_topo"] > a["cota_base"] + 0.5:                        # reservatório mais fundo começa acima do fim do raso
                avisos.append(f"{poco}: {a['zona']} e {b['zona']} se sobrepõem em cota (confira os números e a tolerância).")
        if escolhidos:
            por_poco[poco] = escolhidos
    ativas = cfg.get("ativas")
    nomes = cfg.get("nomes") or {}
    zonas = []
    for ch in chaves:
        itens = [(p, e) for p, es in por_poco.items() for e in es if e["zona"] == ch]
        zonas.append({"chave": ch, "nome": nomes.get(ch) or f"Reservatório {ch[2:]}", "n_pocos": len(itens),
                      "cota_media": float(np.mean([(e["cota_topo"] + e["cota_base"]) / 2 for _, e in itens])) if itens else None,
                      "espessura_media": float(np.mean([e["cota_topo"] - e["cota_base"] for _, e in itens])) if itens else None,
                      "ativa": ativas is None or ch in ativas})
        if len(itens) < 3:
            avisos.append(f"{nomes.get(ch) or 'Reservatório ' + ch[2:]}: só {len(itens)} poço(s): sem superfície (precisa de 3).")
    sem = [p for p, lista in candidatos.items() if lista and p not in por_poco]
    if sem:
        avisos.append("Poços com intervalos, mas nenhum utilizável nas fontes escolhidas: " + ", ".join(sem[:12]) + ".")
    vazios = [p for p, lista in candidatos.items() if not lista]
    if vazios:
        avisos.append("Sem nenhum intervalo nas fontes escolhidas (fora do bloco): " + ", ".join(vazios[:12]) +
                      (" …" if len(vazios) > 12 else "") + ".")
    return {"zonas": zonas, "por_poco": por_poco, "candidatos": todos, "avisos": avisos,
            "config": {"fontes": ordem_fontes, "regra": regra, "tolerancia_m": tol, "ativas": ativas}}


def unidades_do_poco(escolhidos: list[dict], ativas: list[str] | None, nomes_zonas: dict, prof_final, cota_fundo) -> list[dict]:
    """As unidades do bloco para um poço: para cada reservatório ativo, ele mesmo (topo→base) e a "base" (da base até o
    próximo reservatório ou o fundo do poço). A superfície da "base" é a base do reservatório."""
    ativos = [e for e in escolhidos if ativas is None or e["zona"] in ativas]
    uns = []
    for k, e in enumerate(ativos):
        nome = nomes_zonas.get(e["zona"], e["zona"])
        uns.append({"chave": e["zona"], "nome": nome, "topo": e["topo"], "base": e["base"], "cota_topo": e["cota_topo"],
                    "cota_base": e["cota_base"], "base_atingida": True})
        prox = ativos[k + 1] if k + 1 < len(ativos) else None
        if prox is not None:
            fim_md, fim_cota, atingida = prox["topo"], prox["cota_topo"], True
        elif prof_final and cota_fundo is not None and float(prof_final) > e["base"]:
            fim_md, fim_cota, atingida = float(prof_final), float(cota_fundo), False
        else:
            fim_md, fim_cota, atingida = e["base"], e["cota_base"], False
        uns.append({"chave": chave_base(e["zona"]), "nome": f"Base do {nome}", "topo": e["base"], "base": fim_md,
                    "cota_topo": e["cota_base"], "cota_base": fim_cota, "base_atingida": atingida})
    return uns


# ------------------------------------------------------------------------------------------------------ tabela do usuário
SINONIMOS = {
    "poco": ("poco", "pocos", "poço", "poços", "well", "nome", "nome do poco", "id", "id well", "id poco", "id do poco"),
    "topo": ("topo", "top", "prof topo", "prof_topo", "topo md", "topo m", "profundidade topo", "top depth"),
    "base": ("base", "bottom", "prof base", "prof_base", "base md", "base m", "profundidade base", "fundo", "bottom depth"),
    "zona": ("zona", "reservatorio", "reservatório", "camada", "horizonte", "formacao", "formação", "reservoir"),
    "x": ("x", "leste", "este", "easting", "utm e", "utm_e", "utm x", "utm_x", "coord x", "e"),
    "y": ("y", "norte", "northing", "utm n", "utm_n", "utm y", "utm_y", "coord y", "n"),
    "lat": ("lat", "latitude"),
    "lon": ("lon", "long", "longitude", "lng"),
}


def _norm(s) -> str:
    s = "".join(c for c in unicodedata.normalize("NFD", str(s or "")) if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", s.lower().replace("_", " ").replace(".", " ").strip())


def _numero(v):
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    t = str(v).strip().replace(" ", "")
    if not t:
        return None
    if "," in t:
        t = t.replace(".", "").replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return None


def resolver_nome(banco: Banco, nome: str) -> str:
    """Id do poço para o nome escrito na tabela do usuário. Além das grafias que o cadastro já conhece, aceita o nome
    sem a sigla do estado (7-GMR-28A → 7-GMR-28A-RN, se só houver um) e com o número do intervalo no fim
    (7-GMR-8-1 → 7-GMR-8-RN), como nas tabelas feitas à mão com uma linha por intervalo (0.56)."""
    partes = [p for p in re.split(r"\s*-\s*", str(nome).strip()) if p]
    candidatos = [str(nome)]
    if len(partes) >= 4 and partes[-1].isdigit():
        candidatos.append("-".join(partes[:-1]))
    with banco.conexao() as c:
        for cand in candidatos:
            pid = mpo.resolver(banco, cand)
            if c.execute("SELECT 1 FROM pocos WHERE id = ?", (pid,)).fetchone():
                return pid
            base = re.sub(r"\s+", "", cand).upper()
            achados = [r[0] for r in c.execute("SELECT id FROM pocos WHERE id LIKE ?", (f"{base}-__",))]
            if len(achados) == 1:
                return achados[0]
    return mpo.resolver(banco, str(nome))


def _linhas_arquivo(caminho: str) -> list[list]:
    nome = caminho.lower()
    if nome.endswith(".xlsx"):
        import openpyxl
        wb = openpyxl.load_workbook(caminho, read_only=True, data_only=True)
        try:
            return [list(r) for r in wb.worksheets[0].iter_rows(values_only=True)]
        finally:
            wb.close()
    if nome.endswith(".xls"):
        import xlrd
        sh = xlrd.open_workbook(caminho).sheets()[0]
        return [sh.row_values(r) for r in range(sh.nrows)]
    with open(caminho, "rb") as f:
        bruto = f.read()
    try:
        texto = bruto.decode("utf-8-sig")
    except UnicodeDecodeError:
        texto = bruto.decode("latin-1")
    amostra = texto[:4000]
    sep = max((";", ",", "\t"), key=amostra.count)
    return [r for r in csv.reader(io.StringIO(texto), delimiter=sep)]


def ler_tabela(caminho: str, banco: Banco, ref: str = "md", utm_zona: int | None = None, utm_sul: bool = True) -> dict:
    """Lê a tabela do usuário (poço, topo, base e, se tiver, zona/reservatório e coordenadas). `ref`: "md" (profundidade
    medida) ou "cota" (m, negativa abaixo do nível do mar). Coordenadas: lat/lon em graus, ou x/y UTM (precisa de `utm_zona`)."""
    if ref not in ("md", "cota"):
        raise ErroZonas("Referência de profundidade: use md ou cota.")
    linhas = [l for l in _linhas_arquivo(caminho) if any(str(c).strip() for c in l if c is not None)]
    if len(linhas) < 2:
        raise ErroZonas("A tabela precisa de um cabeçalho e ao menos uma linha.")
    cab = [_norm(c) for c in linhas[0]]
    mapa: dict[str, int] = {}
    for campo, nomes in SINONIMOS.items():
        for j, h in enumerate(cab):
            if h in [_norm(n) for n in nomes] and campo not in mapa and j not in mapa.values():
                mapa[campo] = j
    faltam = [c for c in ("poco", "topo", "base") if c not in mapa]
    if faltam:
        raise ErroZonas("Não achei no cabeçalho a coluna de: " + ", ".join(faltam) + f". Cabeçalho lido: {', '.join(str(c) for c in linhas[0])}.")
    tem_utm = "x" in mapa and "y" in mapa and not ("lat" in mapa and "lon" in mapa)
    if tem_utm and not utm_zona:
        raise ErroZonas("A tabela tem coordenadas x/y (UTM): informe a zona UTM (ex.: 24 para Guamaré) e o hemisfério.")
    rows, avisos, nao_resolvidos = [], [], []
    for n, l in enumerate(linhas[1:], start=2):
        def cel(c):
            j = mapa.get(c)
            return l[j] if j is not None and j < len(l) else None
        nome = str(cel("poco") or "").strip()
        topo, base = _numero(cel("topo")), _numero(cel("base"))
        if not nome or topo is None or base is None:
            avisos.append(f"Linha {n}: sem poço, topo ou base legíveis; ignorada.")
            continue
        if ref == "md" and base <= topo:
            avisos.append(f"Linha {n} ({nome}): a base ({base:g}) não é maior que o topo ({topo:g}); ignorada.")
            continue
        if ref == "cota" and base >= topo:
            avisos.append(f"Linha {n} ({nome}): em cota a base ({base:g}) deveria ser menor que o topo ({topo:g}); ignorada.")
            continue
        pid = resolver_nome(banco, nome)
        r = {"poco": nome, "poco_id": pid, "topo": topo, "base": base, "ref": ref, "zona": str(cel("zona") or "").strip(),
             "lat": None, "lon": None}
        if "lat" in mapa and "lon" in mapa:
            r["lat"], r["lon"] = _numero(cel("lat")), _numero(cel("lon"))
        elif tem_utm:
            x, y = _numero(cel("x")), _numero(cel("y"))
            if x is not None and y is not None:
                la, lo = mutm.de_utm(x, y, int(utm_zona), bool(utm_sul))
                r["lat"], r["lon"] = float(np.ravel(la)[0]), float(np.ravel(lo)[0])
        rows.append(r)
        with banco.conexao() as c:
            if not c.execute("SELECT 1 FROM pocos WHERE id = ?", (pid,)).fetchone():
                nao_resolvidos.append(nome)
    if not rows:
        raise ErroZonas("Nenhuma linha utilizável na tabela.")
    nr = sorted(set(nao_resolvidos))
    if nr:
        avisos.append("Poços que o SIAPP não reconheceu no cadastro (confira a grafia): " + ", ".join(nr[:15]) + ".")
    return {"linhas": rows, "colunas": {c: str(linhas[0][j]) for c, j in mapa.items()}, "avisos": avisos, "ref": ref,
            "com_coordenadas": any(r["lat"] is not None for r in rows), "n_pocos": len({r["poco_id"] for r in rows})}


def guardar_tabela(pasta_projeto: str, tabela: dict, origem: str) -> str:
    pasta = os.path.join(pasta_projeto, "zonas")
    os.makedirs(pasta, exist_ok=True)
    caminho = os.path.join(pasta, "tabela_usuario.json")
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump({**tabela, "origem": origem}, f, ensure_ascii=False, indent=1)
    return caminho


def tabela_guardada(pasta_projeto: str) -> dict | None:
    try:
        with open(os.path.join(pasta_projeto, "zonas", "tabela_usuario.json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def apagar_tabela(pasta_projeto: str) -> bool:
    try:
        os.remove(os.path.join(pasta_projeto, "zonas", "tabela_usuario.json"))
        return True
    except OSError:
        return False


def coordenadas_da_tabela(tabela: dict | None) -> dict[str, tuple[float, float]]:
    """{poço: (lat, lon)} da tabela do usuário (a primeira coordenada de cada poço)."""
    out: dict[str, tuple[float, float]] = {}
    for r in (tabela or {}).get("linhas", []):
        if r.get("lat") is not None and r.get("lon") is not None and r["poco_id"] not in out:
            out[r["poco_id"]] = (float(r["lat"]), float(r["lon"]))
    return out


def comparar(plano: dict, tabela: dict | None) -> list[dict]:
    """A tabela do usuário (cada linha) ao lado do que o SIAPP escolheu nos mesmos poços, por sobreposição de profundidade.
    `plano` deve ter sido montado SEM a fonte "tabela". Diferenças em metros (SIAPP − tabela), na profundidade medida."""
    saida = []
    for r in (tabela or {}).get("linhas", []):
        achado = None
        melhor = 0.0
        for e in plano["por_poco"].get(r["poco_id"], []):
            if r["ref"] == "md":                                   # sobreposição na profundidade medida
                sobre = min(e["base"], r["base"]) - max(e["topo"], r["topo"])
            else:                                                  # ou na cota (profundidade abaixo do nível do mar)
                sobre = min(-e["cota_base"], -r["base"]) - max(-e["cota_topo"], -r["topo"])
            if sobre > melhor:
                melhor, achado = sobre, e
        linha = {"poco": r["poco"], "poco_id": r["poco_id"], "zona_tabela": r["zona"], "topo_tabela": r["topo"],
                 "base_tabela": r["base"], "ref": r["ref"], "zona_siapp": None, "topo_siapp": None, "base_siapp": None,
                 "dif_topo": None, "dif_base": None, "fonte_siapp": None, "situacao": "o SIAPP não achou intervalo neste poço"}
        if r["poco_id"] in plano["por_poco"] and achado is None:
            linha["situacao"] = "o SIAPP tem intervalo neste poço, mas em outra profundidade"
        if achado is not None:
            linha.update(zona_siapp=achado["zona"], topo_siapp=achado["topo"], base_siapp=achado["base"],
                         fonte_siapp=achado["fonte"], situacao="comparado")
            if r["ref"] == "md":
                linha["dif_topo"], linha["dif_base"] = round(achado["topo"] - r["topo"], 2), round(achado["base"] - r["base"], 2)
            else:
                linha["dif_topo"] = round(achado["cota_topo"] - r["topo"], 2)
                linha["dif_base"] = round(achado["cota_base"] - r["base"], 2)
        saida.append(linha)
    return saida
