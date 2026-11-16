"""
Projetos (0.58): cada projeto é uma pasta com o seu banco (`projeto.sqlite`), os seus arquivos baixados, textos e
execuções. Dá para separar, por exemplo, Sergipe-Alagoas e o campo de Guamaré, cada um com o seu acervo.

- Pelo código (desenvolvimento): o principal é `ambiente_teste/` e os novos ficam em `projetos/<nome>/`, ao lado do app.
- Instalado (1.1): tudo em `<pasta dos projetos>\\Projetos\\`: `Projeto principal\\` e os novos ao lado.
- Qual projeto abre e a lista dos conhecidos ficam nas preferências (`projeto_atual`, `projetos`).

Este módulo só lê o banco de cada projeto (em modo somente leitura) para montar o cartão da tela inicial: nome,
bacias, quantos poços, arquivos, documentos e perfis, e uma amostra das coordenadas para o minimapa.
"""

from __future__ import annotations

import os
import re
import sqlite3
import unicodedata

from .projeto import ARQUIVO_CONFIG, Projeto, ler_json

PASTA_PROJETOS = "projetos"
NOME_PRINCIPAL = "Projeto principal"
MAX_PONTOS = 300


class ErroProjeto(Exception):
    pass


def eh_projeto(pasta: str) -> bool:
    return bool(pasta) and os.path.isfile(os.path.join(pasta, ARQUIVO_CONFIG))


def nome_do_projeto(pasta: str, pasta_principal: str = "") -> str:
    cfg = ler_json(os.path.join(pasta, ARQUIVO_CONFIG), {}) or {}
    nome = str(cfg.get("nome") or "").strip()
    if nome:
        return nome
    if pasta_principal and os.path.normcase(os.path.abspath(pasta)) == os.path.normcase(os.path.abspath(pasta_principal)):
        return NOME_PRINCIPAL
    return os.path.basename(os.path.normpath(pasta))


def apelido_de_pasta(nome: str) -> str:
    """Nome da pasta a partir do nome do projeto: sem acento, minúsculas, hífens."""
    t = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode().lower()
    t = re.sub(r"[^a-z0-9]+", "-", t).strip("-")
    return t[:40].strip("-") or "projeto"


def criar(raiz: str, nome: str, bacias: list | None = None) -> str:
    """Cria a pasta de um projeto novo em `raiz` (a pasta dos outros projetos) e grava o nome e as bacias."""
    nome = " ".join(str(nome or "").split())[:60]
    if len(nome) < 2:
        raise ErroProjeto("Dê um nome ao projeto (2 letras ou mais).")
    os.makedirs(raiz, exist_ok=True)
    base = apelido_de_pasta(nome)
    pasta, k = os.path.join(raiz, base), 2
    while os.path.exists(pasta):
        pasta, k = os.path.join(raiz, f"{base}-{k}"), k + 1
    os.makedirs(pasta)
    p = Projeto.abrir_ou_criar(pasta)
    bacias = [str(b)[:40] for b in (bacias or []) if str(b).strip()][:12]
    p.definir_config(nome=nome, bacias=bacias)
    return p.pasta


def renomear(pasta: str, nome: str) -> str:
    nome = " ".join(str(nome or "").split())[:60]
    if len(nome) < 2:
        raise ErroProjeto("Dê um nome ao projeto (2 letras ou mais).")
    if not eh_projeto(pasta):
        raise ErroProjeto("Essa pasta não é um projeto do SIAPP.")
    Projeto(pasta).definir_config(nome=nome)
    return nome


def _ler_banco(caminho: str) -> dict:
    """Números e pontos do banco de um projeto, sem travar nem criar nada (modo somente leitura)."""
    out = {"pocos": 0, "arquivos": 0, "documentos": 0, "perfis": 0, "bacias": [], "pontos": []}
    if not os.path.isfile(caminho):
        return out
    try:
        con = sqlite3.connect(f"file:{caminho}?mode=ro", uri=True, timeout=2)
    except sqlite3.Error:
        return out
    try:
        def um(sql, args=()):
            try:
                r = con.execute(sql, args).fetchone()
                return r[0] if r and r[0] is not None else 0
            except sqlite3.Error:
                return 0

        def varios(sql, args=()):
            try:
                return con.execute(sql, args).fetchall()
            except sqlite3.Error:
                return []

        out["pocos"] = um("SELECT count(DISTINCT poco_id) FROM acervo_pocos WHERE poco_id IS NOT NULL") or \
            um("SELECT count(DISTINCT poco_id) FROM reate WHERE poco_id IS NOT NULL")
        out["arquivos"] = um("SELECT count(*) FROM arquivos")
        out["documentos"] = um("SELECT count(*) FROM arquivos WHERE tipo = 'documento'")
        out["perfis"] = um("SELECT count(*) FROM arquivos WHERE tipo = 'perfil'")
        bacias = [r[0] for r in varios("SELECT bacia, count(*) n FROM acervo_pocos GROUP BY bacia ORDER BY n DESC")]
        if not bacias:
            bacias = [r[0] for r in varios("SELECT bacia, count(*) n FROM reate GROUP BY bacia ORDER BY n DESC")]
        out["bacias"] = [b for b in bacias if b][:6]
        # minimapa: poços do acervo (ou baixados) com coordenada; amostra espalhada pelo rowid
        pts = varios("""SELECT p.lon, p.lat FROM pocos p
                        WHERE p.lat IS NOT NULL AND p.lon IS NOT NULL
                          AND (p.id IN (SELECT poco_id FROM acervo_pocos) OR p.id IN (SELECT poco_id FROM reate)
                               OR p.id IN (SELECT poco_id FROM arquivos))""")
        if len(pts) > MAX_PONTOS:
            passo = len(pts) / MAX_PONTOS
            pts = [pts[int(i * passo)] for i in range(MAX_PONTOS)]
        out["pontos"] = [[round(x, 4), round(y, 4)] for x, y in pts]
    finally:
        con.close()
    return out


def resumo(pasta: str, pasta_principal: str = "") -> dict:
    """O cartão de um projeto na tela inicial."""
    cfg = ler_json(os.path.join(pasta, ARQUIVO_CONFIG), {}) or {}
    existe = eh_projeto(pasta)
    r = {"pasta": os.path.abspath(pasta), "nome": nome_do_projeto(pasta, pasta_principal) if existe
         else os.path.basename(os.path.normpath(pasta)),
         "existe": existe, "principal": bool(pasta_principal) and os.path.normcase(os.path.abspath(pasta)) ==
         os.path.normcase(os.path.abspath(pasta_principal)),
         "criado": cfg.get("criado") or "", "atualizado": cfg.get("atualizado") or ""}
    numeros = _ler_banco(os.path.join(pasta, "projeto.sqlite")) if existe else _ler_banco("")
    declaradas = [b for b in (cfg.get("bacias") or []) if isinstance(b, str)]
    r.update(numeros)
    r["bacias"] = declaradas or numeros["bacias"] or ([cfg["bacia"]] if cfg.get("bacia") else [])
    return r


def conhecidos(pasta_principal: str, lista: list, raiz: str = "") -> list[str]:
    """Pastas de projeto, sem repetir: a principal primeiro, depois as das preferências e as que estão em `raiz`
    (a pasta dos outros projetos: uma pasta copiada para lá aparece sozinha)."""
    vistos, out = set(), []

    def por(p):
        k = os.path.normcase(os.path.abspath(p))
        if k not in vistos:
            vistos.add(k)
            out.append(os.path.abspath(p))
    por(pasta_principal)
    for p in lista or []:
        if isinstance(p, str) and p:
            por(p)
    if raiz and os.path.isdir(raiz):
        for nome in sorted(os.listdir(raiz)):
            if eh_projeto(os.path.join(raiz, nome)):
                por(os.path.join(raiz, nome))
    return out
