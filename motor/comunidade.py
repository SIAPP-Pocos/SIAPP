"""
Contribuições e base comunitária (repositório SIAPP-dados).

Três operações:

  exportar   o que o usuário fez neste computador (origem "local") vira um
             pacote JSON, com autoria, para enviar ao SIAPP-dados;
  importar   o pacote de outra pessoa entra no banco com origem "pacote" e o
             id do pacote — pode ser desfeito inteiro depois;
  base       a base compilada (SQLite publicado nas Releases do SIAPP-dados)
             substitui tudo o que tem origem "base".

Formato do pacote (versão 2; a 1 é aceita na importação):

    {"formato": "siapp-contribuicao", "versao_formato": 2,
     "id": uuid, "criado_em": iso, "siapp_versao": "0.7.0", "licenca": "CC-BY-4.0",
     "autor": {"nome", "instituicao", "orcid"},
     "vocabulario": {"palavras": [...], "correcoes": [{"de", "para"}], "manter_original": [...]},
     "fatos": [{"id", "poco", "tipo", "nome", "valor", "unidade", "prof_topo", "prof_base",
                "observacao", "criado_em",
                "fonte": {"sha256", "caminho_remoto", "bacia", "pagina", "caixa": [x0,y0,x1,y1]}}],
     "apelidos": [{"apelido", "poco"}]}

Nenhum arquivo do REATE vai no pacote: documentos são citados pelo hash
SHA-256 e pelo caminho no portal.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import unicodedata

import requests

from .banco import Banco, agora, com_fuso, novo_id
from .vocabulario import normalizar

FORMATO = "siapp-contribuicao"
VERSAO_FORMATO = 2
LICENCA = "CC-BY-4.0"
URL_ULTIMA_BASE = "https://api.github.com/repos/SIAPP-Pocos/SIAPP-dados/releases/latest"
NOME_ARQUIVO_BASE = "siapp-dados.sqlite"

# Tipos de fato aceitos. A interface oferece estes; o validador do SIAPP-dados
# usa a mesma lista.
TIPOS_FATO = {
    "topo_formacao": "Topo de formação",
    "intervalo_alvo": "Intervalo-alvo",
    "profundidade_final": "Profundidade final",
    "revestimento": "Revestimento (sapata)",
    "teste_formacao": "Teste de formação",
    "canhoneio": "Canhoneio",
    "mesa_rotativa": "Elevação da mesa rotativa",
    "contato_fluido": "Contato de fluido",
    "propriedade_fluido": "Propriedade de fluido (API, densidade do gás…)",
    "observacao": "Observação",
    "trecho": "Trecho do texto (citação)",
}
PROF_MAX_M = 12_000


class ErroComunidade(ValueError):
    """Pacote ou base inválidos, com mensagem para o usuário."""


# ================================================================== exportar
def _sobrenome(nome: str) -> str:
    ultimo = (nome.split() or ["anonimo"])[-1]
    sem_acento = "".join(c for c in unicodedata.normalize("NFD", ultimo)
                         if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "", sem_acento.lower()) or "anonimo"


def nome_arquivo_pacote(autor: dict, quando: str | None = None) -> str:
    """Padrão do SIAPP-dados: AAAA-MM-DD_sobrenome_assunto.json."""
    data = (quando or agora())[:10]
    return f"{data}_{_sobrenome(autor.get('nome', ''))}_siapp.json"


def _fato_para_pacote(f: dict, arquivos: dict) -> dict:
    saida = {k: f[k] for k in ("id", "tipo", "nome", "valor", "unidade", "prof_topo",
                               "prof_base", "observacao", "criado_em") if f.get(k) not in (None, "")}
    saida["poco"] = f["poco_id"]
    if saida.get("criado_em"):
        saida["criado_em"] = com_fuso(saida["criado_em"])
    arq = arquivos.get(f.get("fonte_rel") or "", {})
    fonte = {"sha256": f.get("fonte_sha256") or arq.get("sha256"),
             "caminho_remoto": f.get("fonte_caminho") or arq.get("caminho_remoto"),
             "bacia": f.get("fonte_bacia") or arq.get("bacia"),
             "pagina": f.get("pagina"), "caixa": f.get("caixa")}
    fonte = {k: v for k, v in fonte.items() if v not in (None, "", [])}
    if fonte:
        saida["fonte"] = fonte
    return saida


def montar_pacote(banco: Banco, autor: dict, siapp_versao: str, apenas_novos: bool = True) -> dict:
    """Pacote com o que tem origem "local". `apenas_novos`: só o que mudou desde
    a última exportação (o SIAPP-dados junta os pacotes de um mesmo autor)."""
    if not (autor or {}).get("nome", "").strip():
        raise ErroComunidade("Preencha seu nome na aba Comunidade antes de exportar: "
                             "toda contribuição tem autor.")
    desde = banco.meta("ultima_exportacao", "") if apenas_novos else ""
    vocab = {"palavras": [], "correcoes": [], "manter_original": []}
    for r in banco.vocab_linhas("local"):
        if r["criado_em"] <= desde:
            continue
        if r["tipo"] == "palavra":
            vocab["palavras"].append(r["de"])
        elif r["tipo"] == "ignorar":
            vocab["manter_original"].append(r["de"])
        else:
            vocab["correcoes"].append({"de": r["de"], "para": r["para"]})
    arquivos = {a["rel"]: a for a in banco.arquivos()}
    fatos = [_fato_para_pacote(f, arquivos) for f in banco.fatos(origem="local")
             if not (apenas_novos and f.get("exportado_em"))]
    with banco.conexao() as c:
        apelidos = [{"apelido": r["chave"], "poco": r["poco_id"]}
                    for r in c.execute("SELECT * FROM apelidos WHERE origem = 'local'")]
    return {"formato": FORMATO, "versao_formato": VERSAO_FORMATO, "id": novo_id(),
            "criado_em": agora(), "siapp_versao": siapp_versao, "licenca": LICENCA,
            "autor": {k: (autor.get(k) or "").strip() for k in ("nome", "instituicao", "orcid")
                      if (autor.get(k) or "").strip()},
            "vocabulario": vocab, "fatos": fatos, "apelidos": apelidos}


def contar_itens(pacote: dict) -> dict:
    v = pacote.get("vocabulario") or {}
    return {"palavras": len(v.get("palavras", [])), "correcoes": len(v.get("correcoes", [])),
            "manter_original": len(v.get("manter_original", [])),
            "fatos": len(pacote.get("fatos", [])), "apelidos": len(pacote.get("apelidos", []))}


def pacote_vazio(pacote: dict) -> bool:
    return not any(contar_itens(pacote).values())


def gravar_pacote(banco: Banco, pacote: dict, pasta: str) -> str:
    """Grava o pacote e marca o que foi exportado."""
    os.makedirs(pasta, exist_ok=True)
    nome = nome_arquivo_pacote(pacote["autor"], pacote["criado_em"])
    caminho = os.path.join(pasta, nome)
    n = 2
    while os.path.exists(caminho):                 # mais de uma exportação no mesmo dia
        caminho = os.path.join(pasta, nome.replace("_siapp.json", f"_siapp-{n}.json"))
        n += 1
    tmp = caminho + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(pacote, f, ensure_ascii=False, indent=2)
    os.replace(tmp, caminho)
    with banco.conexao() as c:
        ids = [f["id"] for f in pacote["fatos"]]
        c.executemany("UPDATE fatos SET exportado_em = ? WHERE id = ?",
                      [(pacote["criado_em"], i) for i in ids])
        banco.definir_meta("ultima_exportacao", pacote["criado_em"], c)
        banco.registrar_pacote(pacote["id"], "exportado", autor=pacote["autor"].get("nome", ""),
                               arquivo=os.path.basename(caminho), criado_em=pacote["criado_em"],
                               resumo=contar_itens(pacote), c=c)
    return caminho


# ================================================================== validar
_RE_LETRA = re.compile(r"[A-Za-zÀ-ÿ]")


def validar_pacote(p) -> list[str]:
    """Erros que impedem a importação (lista vazia = válido)."""
    if not isinstance(p, dict) or p.get("formato") != FORMATO:
        return ["Não é um pacote de contribuição do SIAPP."]
    erros = []
    if p.get("versao_formato") not in (1, 2):
        erros.append(f"Versão de formato não suportada: {p.get('versao_formato')!r} "
                     f"(este SIAPP lê até a {VERSAO_FORMATO}). Atualize o SIAPP.")
    if not isinstance(p.get("id"), str) or len(p["id"]) < 8:
        erros.append("Pacote sem identificador (id).")
    if not ((p.get("autor") or {}).get("nome") or "").strip():
        erros.append("Pacote sem autor.")
    if p.get("licenca") != LICENCA:
        erros.append(f"Licença deve ser {LICENCA}.")
    v = p.get("vocabulario") or {}
    for c in v.get("correcoes", []):
        de = str(c.get("de", ""))
        if len(de) < 3 or not _RE_LETRA.search(de) or not str(c.get("para", "")).strip():
            erros.append(f"Correção inválida: {de!r} → {c.get('para')!r} "
                         f"(números e palavras curtas não se corrigem em todos os documentos).")
    for f in p.get("fatos", []):
        rotulo = f"fato {f.get('id', '?')} ({f.get('poco', '?')})"
        if f.get("tipo") not in TIPOS_FATO:
            erros.append(f"{rotulo}: tipo desconhecido {f.get('tipo')!r}.")
        if not str(f.get("poco", "")).strip():
            erros.append(f"{rotulo}: sem poço.")
        for campo in ("prof_topo", "prof_base"):
            x = f.get(campo)
            if x is not None and not (isinstance(x, (int, float)) and -100 <= x <= PROF_MAX_M):
                erros.append(f"{rotulo}: {campo} fora do intervalo (−100 a {PROF_MAX_M} m).")
        if (isinstance(f.get("prof_topo"), (int, float)) and isinstance(f.get("prof_base"), (int, float))
                and f["prof_base"] < f["prof_topo"]):
            erros.append(f"{rotulo}: base acima do topo.")
    return erros


def ler_pacote(caminho: str) -> dict:
    try:
        with open(caminho, encoding="utf-8") as f:
            p = json.load(f)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as e:
        raise ErroComunidade(f"Não consegui ler {os.path.basename(caminho)}: {e}") from e
    erros = validar_pacote(p)
    if erros:
        raise ErroComunidade("Pacote recusado: " + " ".join(erros[:5]))
    return p


# ================================================================== importar
def previa(banco: Banco, p: dict) -> dict:
    """O que a importação faria, sem gravar nada: novidades e conflitos."""
    efetivo = banco.vocab_efetivo()
    atuais = {normalizar(de): (para, efetivo["origens"].get(normalizar(de)))
              for de, para in efetivo["correcoes"].items()}
    novos = contar_itens(p)
    conflitos, repetidas = [], 0
    for c in (p.get("vocabulario") or {}).get("correcoes", []):
        atual = atuais.get(normalizar(c["de"]))
        if atual is None:
            continue
        if normalizar(atual[0]) == normalizar(c["para"]):
            repetidas += 1
        else:
            conflitos.append({"de": c["de"], "atual": atual[0], "origem_atual": atual[1],
                              "proposta": c["para"]})
    ids = {f["id"] for f in banco.fatos()}
    fatos_repetidos = sum(1 for f in p.get("fatos", []) if f.get("id") in ids)
    ja = any(x["id"] == p["id"] for x in banco.pacotes())
    return {"id": p["id"], "autor": p.get("autor", {}), "criado_em": p.get("criado_em"),
            "versao_formato": p.get("versao_formato"), "itens": novos,
            "correcoes_repetidas": repetidas, "fatos_repetidos": fatos_repetidos,
            "conflitos": conflitos, "ja_importado": ja}


def importar(banco: Banco, p: dict, arquivo: str = "") -> dict:
    """Aplica o pacote. Correções em conflito entram mesmo assim, mas com
    precedência menor que as suas (local > pacote > base): nada seu é trocado."""
    pid, autor = p["id"], (p.get("autor") or {}).get("nome", "")
    v = p.get("vocabulario") or {}
    with banco.conexao() as c:
        for w in v.get("palavras", []):
            banco.vocab_definir("palavra", w, origem="pacote", pacote=pid, autor=autor, c=c)
        for cr in v.get("correcoes", []):
            banco.vocab_definir("correcao", cr["de"], cr["para"], origem="pacote", pacote=pid,
                                autor=autor, c=c)
        for w in v.get("manter_original", []):
            banco.vocab_definir("ignorar", w, origem="pacote", pacote=pid, autor=autor, c=c)
        existentes = {r[0] for r in c.execute("SELECT id FROM fatos")}
        n_fatos = 0
        for f in p.get("fatos", []):
            if f.get("id") in existentes:
                continue
            fonte = f.get("fonte") or {}
            banco.salvar_fato({**{k: f.get(k) for k in ("id", "tipo", "nome", "valor", "unidade",
                                                        "prof_topo", "prof_base", "observacao",
                                                        "criado_em")},
                               "poco_id": f["poco"], "fonte_sha256": fonte.get("sha256"),
                               "fonte_caminho": fonte.get("caminho_remoto"),
                               "fonte_bacia": fonte.get("bacia"), "pagina": fonte.get("pagina"),
                               "caixa": fonte.get("caixa"), "autor": autor,
                               "origem": "pacote", "pacote": pid}, c)
            n_fatos += 1
        for a in p.get("apelidos", []):
            c.execute("INSERT OR IGNORE INTO apelidos VALUES (?, ?, 'pacote', ?)",
                      (normalizar(a["apelido"]), a["poco"], pid))
        resumo = {**contar_itens(p), "fatos_novos": n_fatos}
        banco.registrar_pacote(pid, "importado", autor=autor, arquivo=arquivo,
                               criado_em=p.get("criado_em", ""), resumo=resumo, c=c)
    return resumo


# ===================================================================== base
def aplicar_base(banco: Banco, caminho_sqlite: str) -> dict:
    """Substitui tudo o que veio da base anterior pela base compilada."""
    try:
        b = sqlite3.connect(f"file:{caminho_sqlite}?mode=ro", uri=True)
        b.row_factory = sqlite3.Row
        meta = {r["chave"]: r["valor"] for r in b.execute("SELECT chave, valor FROM meta")}
        if meta.get("formato") != "siapp-dados-base":
            raise ErroComunidade("O arquivo não é uma base compilada do SIAPP-dados.")
        if int(meta.get("versao_formato_base", "0")) > 1:
            raise ErroComunidade("Esta base é de uma versão mais nova. Atualize o SIAPP.")
        vocab = [dict(r) for r in b.execute("SELECT * FROM vocab")]
        fatos = [dict(r) for r in b.execute("SELECT * FROM fatos")]
        apelidos = [dict(r) for r in b.execute("SELECT * FROM apelidos")]
        n_contrib = b.execute("SELECT count(*) FROM contribuicoes").fetchone()[0]
        b.close()
    except sqlite3.DatabaseError as e:
        raise ErroComunidade(f"Base comunitária ilegível: {e}") from e
    versao = meta.get("versao_base") or meta.get("gerado_em", "?")
    pid = f"base:{versao}"
    tipos = {"palavra": "palavra", "correcao": "correcao", "manter_original": "ignorar"}
    with banco.conexao() as c:
        for t in ("vocab", "fatos", "apelidos"):
            c.execute(f"DELETE FROM {t} WHERE origem = 'base'")
        c.execute("DELETE FROM pacotes WHERE tipo = 'base'")
        for r in vocab:
            if r["tipo"] in tipos:
                banco.vocab_definir(tipos[r["tipo"]], r["de"], r.get("para"), origem="base",
                                    pacote=pid, autor=r.get("autor"), c=c)
        for f in fatos:
            banco.salvar_fato({"id": f["id"], "poco_id": f["poco"], "tipo": f["tipo"],
                               "nome": f.get("nome"), "valor": f.get("valor"),
                               "unidade": f.get("unidade"), "prof_topo": f.get("prof_topo"),
                               "prof_base": f.get("prof_base"), "observacao": f.get("observacao"),
                               "criado_em": f.get("criado_em"), "fonte_sha256": f.get("fonte_sha256"),
                               "fonte_caminho": f.get("fonte_caminho"),
                               "fonte_bacia": f.get("fonte_bacia"), "pagina": f.get("pagina"),
                               "caixa": json.loads(f["caixa"]) if f.get("caixa") else None,
                               "autor": f.get("autor"), "origem": "base", "pacote": pid}, c)
        for a in apelidos:
            c.execute("INSERT OR IGNORE INTO apelidos VALUES (?, ?, 'base', ?)",
                      (normalizar(a["apelido"]), a["poco"], pid))
        resumo = {"versao": versao, "contribuicoes": n_contrib, "vocabulario": len(vocab),
                  "fatos": len(fatos), "apelidos": len(apelidos)}
        banco.registrar_pacote(pid, "base", arquivo=os.path.basename(caminho_sqlite),
                               criado_em=meta.get("gerado_em", ""), resumo=resumo, c=c)
    return resumo


def baixar_base(destino: str, url: str = URL_ULTIMA_BASE, timeout: float = 30) -> dict:
    """Baixa a base mais recente das Releases do SIAPP-dados."""
    try:
        r = requests.get(url, timeout=timeout, headers={"Accept": "application/vnd.github+json"})
    except requests.exceptions.RequestException as e:
        raise ErroComunidade(f"Sem conexão com o GitHub ({type(e).__name__}).") from e
    if r.status_code == 404:
        raise ErroComunidade("A base comunitária ainda não foi publicada (ou o repositório "
                             "SIAPP-dados ainda é privado). Use \"Importar base de arquivo\".")
    if r.status_code != 200:
        raise ErroComunidade(f"O GitHub respondeu HTTP {r.status_code}.")
    rel = r.json()
    asset = next((a for a in rel.get("assets", []) if a.get("name") == NOME_ARQUIVO_BASE), None)
    if asset is None:
        raise ErroComunidade(f"A versão {rel.get('tag_name')} não traz {NOME_ARQUIVO_BASE}.")
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    try:
        with requests.get(asset["browser_download_url"], stream=True, timeout=(30, 120)) as d:
            d.raise_for_status()
            with open(destino + ".part", "wb") as f:
                for bloco in d.iter_content(256 * 1024):
                    f.write(bloco)
    except requests.exceptions.RequestException as e:
        raise ErroComunidade(f"Falha ao baixar a base ({type(e).__name__}).") from e
    os.replace(destino + ".part", destino)
    return {"versao": rel.get("tag_name"), "publicada_em": rel.get("published_at")}
