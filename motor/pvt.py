"""Análise PVT do laboratório (bloco 9, item 3): liberação diferencial e liberação flash.

Pasta "Dados De Rochas e Fluidos/PVT" do REATE: planilhas `.xls` (às vezes `.xlsx`) com uma linha por
estágio, no formato da Petrobras/ANP. As primeiras colunas repetem, em toda linha, a amostra:
poço (sigla da operadora e da ANP), tipo de amostragem, intervalo, temperatura, densidade do gás e
grau API do tanque, RGO do tanque, fluido. Depois vêm:

- **liberação diferencial**: pressão (kgf/cm²), Bo, Rs, viscosidade e massa específica do óleo, Bg,
  densidade do gás, Z e viscosidade do gás em cada estágio. A **pressão de saturação** é a do maior
  Bo (acima dela o óleo só se expande; abaixo, libera gás);
- **liberação flash**: a composição (% molar) do óleo estabilizado, do gás e do fluido do
  reservatório, C1 a C20+, CO₂, N₂, com a densidade e a massa molar do último componente.

Conferido em 29/10/2026 no 1-BRSA-1304-BA (amostra de fundo 1.680–1.684 m, 83,7 °C):
Psat = 155,4 kgf/cm², Bo = 1,4013, Rs = 125,37 m³/m³, 38,6 °API, RGO 117,8 m³/m³.

As colunas são reconhecidas pelo título (sem acento, sem diferença de maiúsculas), não pela posição.
"-" e célula vazia = sem dado. Números com vírgula decimal ("1,3678") ou ponto.
"""

from __future__ import annotations

import re
import unicodedata

VERSAO = 1
NOME = "Análise PVT (liberação diferencial e flash)"
DOCUMENTOS = {"pvt_diferencial": "PVT — liberação diferencial", "pvt_flash": "PVT — liberação flash (composição)"}
PRIORIDADE = {"pvt_diferencial": 0, "pvt_flash": 1}
KGF_BAR = 0.980665


class ErroPVT(ValueError):
    pass


def _norm(s) -> str:
    s = "".join(c for c in unicodedata.normalize("NFD", str(s or "")) if unicodedata.category(c) != "Mn")
    return " ".join(s.upper().replace("\n", " ").split())


def reconhece(rel: str) -> bool:
    r = _norm(str(rel or "").replace("\\", "/"))
    nome = r.rsplit("/", 1)[-1]
    if not nome.endswith((".XLS", ".XLSX")):
        return False
    return "PVT" in nome or "/PVT/" in r or ("ROCHAS E FLUIDOS" in r and "LIBERA" in nome)


def numero(v) -> float | None:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    t = str(v).strip().replace(" ", "")
    if t in ("", "-", "—", "--"):
        return None
    if "," in t and "." in t:
        t = t.replace(".", "").replace(",", ".")
    else:
        t = t.replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return None


# título normalizado (começo) → chave
COL_AMOSTRA = [
    ("NOME DO POCO PETROBRAS", "poco_operadora"), ("NOME DO POCO ANP", "poco"), ("TIPO AMOSTRAGEM", "amostragem"),
    ("TOPO", "topo"), ("BASE", "base"), ("TEMPERATURA LIB DIF", "temp_lib_dif_c"), ("TEMPERATURA", "temp_c"),
    ("DG LIBERADO TANQUE", "dg_tanque"), ("GRAU API TANQUE", "api_tanque"), ("RGO TANQUE", "rgo_tanque"),
    ("DG MEDIA LIB DIF", "dg_lib_dif"), ("GRAU API OLEO LIB DIF", "api_lib_dif"), ("FLUIDO DA AMOSTRA", "fluido"),
    ("DENSIDADE ULT COMP", "densidade_ultimo"), ("MASSA MOL ULT COMP", "massa_molar_ultimo"),
]
COL_DIF = [
    ("PRESSAO", "p_kgf_cm2"), ("BO", "bo"), ("RS", "rs"), ("VISCOSIDADE DO OLEO", "mu_o_cp"),
    ("MASSA ESPECIFICA DO OLEO", "rho_o_g_cm3"), ("BG", "bg"), ("DENS. GAS", "dg"), ("Z DO GAS", "z"),
    ("VISCOSIDADE DO GAS", "mu_g_cp"),
]
COL_FLASH = [
    ("ULTIMO COMPONENTE", "ultimo"), ("COMPONENTE GAS", "gas_pct"), ("COMPONENTE", "componente"),
    ("OLEO ESTABILIZADO", "oleo_pct"), ("FLUIDO RESERVATORIO", "fluido_pct"),
]
_TEXTO = {"poco_operadora", "poco", "amostragem", "fluido", "componente", "ultimo"}


def _mapa(cabecalho: list) -> dict[int, str]:
    mapa = {}
    for i, titulo in enumerate(cabecalho):
        n = _norm(titulo)
        for lista in (COL_AMOSTRA, COL_DIF, COL_FLASH):
            k = next((k for pref, k in lista if n.startswith(pref)), None)
            if k:
                if k not in mapa.values():
                    mapa[i] = k
                break
    return mapa


def _linhas_planilha(caminho: str) -> list[list]:
    if caminho.lower().endswith(".xlsx"):
        import openpyxl
        wb = openpyxl.load_workbook(caminho, read_only=True, data_only=True)
        try:
            return [list(r) for r in wb.worksheets[0].iter_rows(values_only=True)]
        finally:
            wb.close()
    import xlrd
    try:
        sh = xlrd.open_workbook(caminho).sheet_by_index(0)
    except xlrd.biffh.XLRDError as e:
        raise ErroPVT(f"Planilha ilegível: {e}") from e
    return [sh.row_values(r) for r in range(sh.nrows)]


def ler_linhas(linhas: list[list]) -> dict:
    if not linhas:
        raise ErroPVT("Planilha vazia.")
    mapa = _mapa(linhas[0])
    chaves = set(mapa.values())
    if "p_kgf_cm2" in chaves and "bo" in chaves:
        documento = "pvt_diferencial"
    elif "componente" in chaves:
        documento = "pvt_flash"
    else:
        raise ErroPVT("Planilha sem as colunas de uma análise PVT (pressão e Bo, ou componentes).")
    registros = []
    for ln in linhas[1:]:
        r = {}
        for i, k in mapa.items():
            v = ln[i] if i < len(ln) else None
            if k in _TEXTO:
                t = str(v if v is not None else "").strip()
                r[k] = None if t in ("", "-", "—") else t
            else:
                r[k] = numero(v)
        if any(v is not None for v in r.values()):
            registros.append(r)
    if not registros:
        raise ErroPVT("Planilha sem linhas de dados.")
    amostra = {}
    for _, k in COL_AMOSTRA:          # a amostra se repete em toda linha; algum campo só vem numa (C20+)
        v = next((r.get(k) for r in registros if r.get(k) is not None), None)
        if v is not None:
            amostra[k] = v
    dados = {"documento": documento, "titulo": DOCUMENTOS[documento], "amostra": amostra,
             "gerais": {"poco": amostra.get("poco")},
             "apelidos": [amostra["poco_operadora"]] if amostra.get("poco_operadora") else []}
    if documento == "pvt_diferencial":
        tab = sorted(({k: r.get(k) for _, k in COL_DIF} for r in registros if r.get("p_kgf_cm2") is not None),
                     key=lambda r: -r["p_kgf_cm2"])
        dados["tabela"] = tab
        dados["saturacao"] = saturacao(tab)
    else:
        dados["componentes"] = [{k: r.get(k) for _, k in COL_FLASH} for r in registros if r.get("componente")]
        dados["componentes"].sort(key=lambda c: _ordem_componente(c["componente"]))
    return dados


def _ordem_componente(nome: str) -> tuple:
    n = (nome or "").upper()
    fixos = {"N2": 0, "CO2": 1, "H2S": 2, "C1": 3, "C2": 4, "C3": 5, "IC4": 6, "NC4": 7, "IC5": 8, "NC5": 9}
    if n in fixos:
        return (0, fixos[n])
    m = re.match(r"C(\d+)", n)
    return (1, int(m[1])) if m else (2, n)


def saturacao(tab: list[dict]) -> dict | None:
    """Pressão de saturação: o estágio de maior Bo (o óleo deixa de só expandir e passa a liberar gás)."""
    com_bo = [r for r in tab if r.get("bo") is not None]
    if not com_bo:
        return None
    s = max(com_bo, key=lambda r: r["bo"])
    acima = sorted((r for r in com_bo if r["p_kgf_cm2"] > s["p_kgf_cm2"]), key=lambda r: r["p_kgf_cm2"])
    co = None
    if len(acima) >= 1:       # compressibilidade do óleo acima da saturação: −(1/Bo)·ΔBo/Δp
        r1 = acima[-1]
        dp = r1["p_kgf_cm2"] - s["p_kgf_cm2"]
        if dp > 0:
            co = -(r1["bo"] - s["bo"]) / dp / ((r1["bo"] + s["bo"]) / 2)
    return {"p_kgf_cm2": s["p_kgf_cm2"], "p_bar": round(s["p_kgf_cm2"] * KGF_BAR, 2), "bo": s["bo"], "rs": s.get("rs"),
            "mu_o_cp": s.get("mu_o_cp"), "rho_o_g_cm3": s.get("rho_o_g_cm3"),
            "co_por_kgf_cm2": round(co, 8) if co is not None else None}


def interpolar(tab: list[dict], chave: str, p_kgf_cm2: float) -> float | None:
    """Valor de `chave` na pressão dada, interpolando entre os estágios (fora da faixa: o extremo)."""
    pts = sorted((r["p_kgf_cm2"], r[chave]) for r in tab if r.get(chave) is not None and r.get("p_kgf_cm2") is not None)
    if not pts:
        return None
    if p_kgf_cm2 <= pts[0][0]:
        return pts[0][1]
    if p_kgf_cm2 >= pts[-1][0]:
        return pts[-1][1]
    for (p0, v0), (p1, v1) in zip(pts, pts[1:]):
        if p0 <= p_kgf_cm2 <= p1:
            return v0 + (v1 - v0) * (p_kgf_cm2 - p0) / (p1 - p0) if p1 > p0 else v0
    return None


def ler(caminho: str) -> dict:
    try:
        linhas = _linhas_planilha(caminho)
    except ErroPVT:
        raise
    except Exception as e:  # noqa: BLE001 — arquivo que não é planilha
        raise ErroPVT(f"Não consegui abrir a planilha: {type(e).__name__}: {e}") from e
    return ler_linhas(linhas)


def apelidos(dados: dict) -> list[str]:
    return list(dados.get("apelidos") or [])


def itens(dados: dict) -> list[dict]:
    a = dados.get("amostra") or {}
    base = {"prof_topo": a.get("topo"), "prof_base": a.get("base"), "nome": a.get("amostragem")}
    if dados["documento"] == "pvt_diferencial":
        s = dados.get("saturacao") or {}
        return [{"tipo": "pvt", **base, "valor": s.get("p_kgf_cm2"), "unidade": "kgf/cm²",
                 "texto": a.get("fluido"), "extra": {**{k: a.get(k) for k in ("temp_c", "api_tanque", "rgo_tanque",
                                                                               "dg_tanque", "dg_lib_dif", "api_lib_dif")},
                                                     "saturacao": s, "n_estagios": len(dados.get("tabela") or [])}}]
    comp = dados.get("componentes") or []
    c1 = next((c for c in comp if (c["componente"] or "").upper() == "C1"), {})
    return [{"tipo": "composicao", **base, "valor": c1.get("fluido_pct"), "unidade": "% C1 no reservatório",
             "texto": a.get("fluido"), "extra": {"n_componentes": len(comp),
                                                 "co2_pct": next((c["fluido_pct"] for c in comp if c["componente"] == "CO2"), None),
                                                 "n2_pct": next((c["fluido_pct"] for c in comp if c["componente"] == "N2"), None),
                                                 "densidade_ultimo": a.get("densidade_ultimo"),
                                                 "massa_molar_ultimo": a.get("massa_molar_ultimo")}}]
