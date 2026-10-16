"""Monta uma base compilada como a do SIAPP-dados (ferramentas/compilar.py),
para testar a aplicação da base sem depender do outro repositório."""
import json
import sqlite3

ESQUEMA_BASE = """
CREATE TABLE meta (chave TEXT PRIMARY KEY, valor TEXT);
CREATE TABLE contribuicoes (id TEXT PRIMARY KEY, autor TEXT, instituicao TEXT, orcid TEXT,
                            criado_em TEXT, arquivo TEXT);
CREATE TABLE vocab (tipo TEXT, de TEXT, para TEXT, autor TEXT, contribuicao TEXT);
CREATE TABLE fatos (id TEXT PRIMARY KEY, poco TEXT, tipo TEXT, nome TEXT, valor TEXT, unidade TEXT,
                    prof_topo REAL, prof_base REAL, observacao TEXT, criado_em TEXT,
                    fonte_sha256 TEXT, fonte_caminho TEXT, fonte_bacia TEXT, pagina INTEGER,
                    caixa TEXT, autor TEXT, contribuicao TEXT);
CREATE TABLE apelidos (apelido TEXT, poco TEXT, contribuicao TEXT);
"""


def montar_base(caminho, pacotes, versao="v2026.10.0"):
    c = sqlite3.connect(caminho)
    c.executescript(ESQUEMA_BASE)
    c.executemany("INSERT INTO meta VALUES (?, ?)", [
        ("formato", "siapp-dados-base"), ("versao_formato_base", "1"),
        ("versao_base", versao), ("gerado_em", "2026-10-16T10:00:00")])
    for p in pacotes:
        a = p["autor"]
        c.execute("INSERT INTO contribuicoes VALUES (?,?,?,?,?,?)",
                  (p["id"], a["nome"], a.get("instituicao"), a.get("orcid"), p["criado_em"], "x.json"))
        v = p.get("vocabulario", {})
        for w in v.get("palavras", []):
            c.execute("INSERT INTO vocab VALUES ('palavra', ?, NULL, ?, ?)", (w, a["nome"], p["id"]))
        for cr in v.get("correcoes", []):
            c.execute("INSERT INTO vocab VALUES ('correcao', ?, ?, ?, ?)",
                      (cr["de"], cr["para"], a["nome"], p["id"]))
        for w in v.get("manter_original", []):
            c.execute("INSERT INTO vocab VALUES ('manter_original', ?, NULL, ?, ?)", (w, a["nome"], p["id"]))
        for f in p.get("fatos", []):
            fo = f.get("fonte", {})
            c.execute("INSERT INTO fatos VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                      (f["id"], f["poco"], f["tipo"], f.get("nome"), f.get("valor"), f.get("unidade"),
                       f.get("prof_topo"), f.get("prof_base"), f.get("observacao"), f.get("criado_em"),
                       fo.get("sha256"), fo.get("caminho_remoto"), fo.get("bacia"), fo.get("pagina"),
                       json.dumps(fo["caixa"]) if fo.get("caixa") else None, a["nome"], p["id"]))
        for ap in p.get("apelidos", []):
            c.execute("INSERT INTO apelidos VALUES (?,?,?)", (ap["apelido"], ap["poco"], p["id"]))
    c.commit()
    c.close()
