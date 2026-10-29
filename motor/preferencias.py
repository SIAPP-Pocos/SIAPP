"""
Preferências de quem usa o SIAPP neste computador: cores, tamanho do texto, abrir o
projeto ao iniciar e o arranjo das janelas (posição, tamanho, divisão, abas destacadas).

Ficam em `ambiente_teste/preferencias.json`, ao lado dos dados — a pasta do projeto é
fixa, então viajam junto quando a pasta é copiada. Nada aqui afeta resultado de cálculo.

Só chaves conhecidas entram, cada uma conferida (`normalizar`): um arquivo editado à mão
ou de outra versão nunca quebra a abertura; o que não vale volta ao padrão.
"""

from __future__ import annotations

import copy
import json
import os
import threading

NOME_ARQUIVO = "preferencias.json"

PALETAS = ("marinho", "petroleo", "oceano", "arenito", "grafite", "floresta", "contraste")
TEMAS = ("claro", "escuro")
FONTES = ("P", "M", "G")
ABAS = ("projeto", "dados", "mapa", "docs", "perfis", "interp", "viab", "comunidade")
SUB_DADOS = ("catalogo", "cadastro", "levantamento", "producao", "camadas", "consolidado")
SUB_INTERP = ("secao", "bloco")
SUB_COM = ("contribuir", "painel", "biblioteca")

PADRAO = {
    "paleta": "marinho",
    "tema": "claro",
    "fonte": "M",
    "abrir_ao_iniciar": True,
    "lembrar_arranjo": True,
    "recolhidas": {},          # {aba: True} barras laterais recolhidas
    "layout": {"ativa": "projeto", "dividida": False, "direita": "mapa", "razao": 0.5,
               "sub_dados": "catalogo", "sub_interp": "secao", "sub_com": "contribuir"},
    "principal": {},           # geometria da janela principal {x, y, largura, altura, maximizada}
    "janelas": {},             # {aba: geometria} das janelas destacadas
    "abertas": [],             # abas que estavam em janela própria ao fechar o SIAPP
    "bloco": {},               # bloco 3D: {ambiente, aparencia} (guia de interpolação, aparência dos poços)
}

FORMAS_MARCADOR = ("esfera", "cubo", "losango", "cone", "cilindro", "nenhum")
POR_CIMA = ("fechado", "sempre", "nunca")


def _cor(c) -> str | None:
    return c.lower() if isinstance(c, str) and len(c) == 7 and c[0] == "#" and all(
        ch in "0123456789abcdefABCDEF" for ch in c[1:]) else None


def _faixa(v, lo, hi):
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return round(min(hi, max(lo, float(v))), 2)
    return None


def _aparencia(a) -> dict:
    """Aparência dos poços no bloco 3D (só o que vale; o resto fica no padrão do visor)."""
    if not isinstance(a, dict):
        return {}
    out: dict = {}
    m = a.get("marcador")
    if isinstance(m, dict):
        mm = {}
        if m.get("forma") in FORMAS_MARCADOR:
            mm["forma"] = m["forma"]
        if _cor(m.get("cor")):
            mm["cor"] = _cor(m["cor"])
        if _faixa(m.get("tamanho"), 0.3, 4) is not None:
            mm["tamanho"] = _faixa(m["tamanho"], 0.3, 4)
        if mm:
            out["marcador"] = mm
    if isinstance(a.get("linha"), dict) and _cor(a["linha"].get("cor")):
        out["linha"] = {"cor": _cor(a["linha"]["cor"])}
    t = a.get("trilha")
    if isinstance(t, dict):
        tt = {}
        if _faixa(t.get("espessura"), 0.3, 5) is not None:
            tt["espessura"] = _faixa(t["espessura"], 0.3, 5)
        if isinstance(t.get("cores"), dict):
            tt["cores"] = {str(k)[:40]: _cor(c) for k, c in list(t["cores"].items())[:40] if _cor(c)}
        if tt:
            out["trilha"] = tt
    for k in ("topos", "legenda"):
        if isinstance(a.get(k), bool):
            out[k] = a[k]
    if a.get("por_cima") in POR_CIMA:
        out["por_cima"] = a["por_cima"]
    return out


def _geometria(g) -> dict:
    if not isinstance(g, dict):
        return {}
    out = {}
    for k in ("x", "y", "largura", "altura"):
        v = g.get(k)
        if isinstance(v, (int, float)) and not isinstance(v, bool) and -20000 < v < 20000:
            out[k] = int(v)
    if out.get("largura", 1) < 200 or out.get("altura", 1) < 150:
        out.pop("largura", None)
        out.pop("altura", None)
    if isinstance(g.get("maximizada"), bool):
        out["maximizada"] = g["maximizada"]
    return out


def normalizar(d) -> dict:
    """Preferências válidas a partir de qualquer coisa (dicionário parcial, lixo…)."""
    p = copy.deepcopy(PADRAO)
    if not isinstance(d, dict):
        return p
    for chave, opcoes in (("paleta", PALETAS), ("tema", TEMAS), ("fonte", FONTES)):
        if d.get(chave) in opcoes:
            p[chave] = d[chave]
    for chave in ("abrir_ao_iniciar", "lembrar_arranjo"):
        if isinstance(d.get(chave), bool):
            p[chave] = d[chave]
    if isinstance(d.get("recolhidas"), dict):
        p["recolhidas"] = {a: True for a, v in d["recolhidas"].items() if a in ABAS and v is True}
    lay = d.get("layout")
    if isinstance(lay, dict):
        L = p["layout"]
        for chave, opcoes in (("ativa", ABAS), ("direita", ABAS), ("sub_dados", SUB_DADOS),
                              ("sub_interp", SUB_INTERP), ("sub_com", SUB_COM)):
            if lay.get(chave) in opcoes:
                L[chave] = lay[chave]
        if isinstance(lay.get("dividida"), bool):
            L["dividida"] = lay["dividida"]
        r = lay.get("razao")
        if isinstance(r, (int, float)) and not isinstance(r, bool):
            L["razao"] = round(min(0.8, max(0.2, float(r))), 3)
        if L["direita"] == L["ativa"]:
            L["dividida"] = False
    p["principal"] = _geometria(d.get("principal"))
    if isinstance(d.get("janelas"), dict):
        p["janelas"] = {a: g for a, g in ((a, _geometria(g)) for a, g in d["janelas"].items() if a in ABAS) if g}
    if isinstance(d.get("abertas"), list):
        p["abertas"] = [a for a in dict.fromkeys(d["abertas"]) if a in ABAS and a != "projeto"]
    b = d.get("bloco")
    if isinstance(b, dict):
        amb = b.get("ambiente")
        if isinstance(amb, str) and 0 < len(amb) <= 40 and amb.replace("_", "").isalnum():
            p["bloco"]["ambiente"] = amb
        ap = _aparencia(b.get("aparencia"))
        if ap:
            p["bloco"]["aparencia"] = ap
    return p


def mesclar(atual: dict, mudancas) -> dict:
    """`atual` com as mudanças aplicadas (layout e janelas mesclam por chave)."""
    novo = copy.deepcopy(atual)
    if not isinstance(mudancas, dict):
        return normalizar(novo)
    for k, v in mudancas.items():
        if k in ("layout", "janelas", "recolhidas", "bloco") and isinstance(v, dict) and isinstance(novo.get(k), dict):
            novo[k] = {**novo[k], **v}
        else:
            novo[k] = v
    return normalizar(novo)


class Preferencias:
    """Leitura e gravação do arquivo, com trava (várias janelas gravam ao mesmo tempo)."""

    def __init__(self, pasta: str):
        self.caminho = os.path.join(pasta, NOME_ARQUIVO)
        self._trava = threading.Lock()
        self.dados = self._ler()

    def _ler(self) -> dict:
        try:
            with open(self.caminho, encoding="utf-8") as f:
                return normalizar(json.load(f))
        except (OSError, ValueError):
            return normalizar({})

    def atualizar(self, mudancas) -> dict:
        with self._trava:
            self.dados = mesclar(self.dados, mudancas)
            os.makedirs(os.path.dirname(self.caminho), exist_ok=True)
            tmp = self.caminho + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.dados, f, ensure_ascii=False, indent=1)
            os.replace(tmp, self.caminho)
            return copy.deepcopy(self.dados)

    def ler(self) -> dict:
        with self._trava:
            return copy.deepcopy(self.dados)


def visivel(g: dict, telas: list) -> bool:
    """A janela com geometria `g` aparece em alguma das telas? (barra de título à vista)
    `telas`: [(x, y, largura, altura)]. Sem telas conhecidas, confia na geometria."""
    if not g or "x" not in g or "y" not in g:
        return False
    if not telas:
        return True
    larg = g.get("largura", 800)
    for x, y, w, h in telas:
        # pelo menos 120 px da barra de título dentro da tela
        if y <= g["y"] <= y + h - 40 and g["x"] + larg - 120 >= x and g["x"] + 120 <= x + w:
            return True
    return False
