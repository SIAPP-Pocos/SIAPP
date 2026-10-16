"""
Poços: identificador canônico e cadastro oficial da ANP.

O MESMO poço aparece com grafias diferentes:
    7-GMR-13-RN        pasta no REATE e nome ANP (Resolução ANP nº 699/2017)
    7GMR_0013__RN      nome de arquivo da geração antiga
    7GMR13RN           nome no cadastro do operador
Sem um identificador único, nenhum dado se cruza. `canonico()` reduz todas
essas formas ao nome ANP: <tipo>-<sigla>-<número><sufixo>-<UF>.

Cadastro: a "Tabela de Poços" dos dados abertos da ANP (CSV com ";", ~30 mil
poços, atualização mensal) traz coordenadas, bacia, campo, operador,
profundidade, situação e o número de CADASTRO — o mesmo número que os
arquivos DLIS gravam como "well id".
"""

from __future__ import annotations

import csv
import io
import json
import os
import re
import unicodedata

import requests

from .banco import Banco, agora

URLS_CADASTRO = (
    "https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/arquivos/"
    "arquivos-acervo-de-dados-tecnicos/tabela-pocos.csv",
    "https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/arquivos/"
    "arquivos-acervo-de-dados-tecnicos/tabela-pocos.csv/@@download/file",
)
PAGINA_CADASTRO = ("https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/"
                   "acervo-de-dados-tecnicos")

# Siglas de estado usadas no nome ANP; com "S" no fim, poço no mar (RJS, SES…).
_UF = {"AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA",
       "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"}
_UF_MAR = {uf + "S" for uf in _UF}
_RE_NOME = re.compile(r"^(\d{1,2})([A-Z]{1,7})0*(\d{1,5})([A-Z]{2,6})$")


class ErroCadastro(ValueError):
    """Falha ao obter ou ler o cadastro da ANP, com mensagem para o usuário."""


def _sem_acento(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")


def canonico(nome: str) -> str | None:
    """Nome ANP do poço, ou None se o texto não tem cara de nome de poço.

    >>> canonico("7GMR_0013__RN")
    '7-GMR-13-RN'
    >>> canonico("7GVR26DMA")
    '7-GVR-26D-MA'
    """
    if not nome:
        return None
    s = re.sub(r"[^A-Z0-9]", "", _sem_acento(str(nome)).upper())
    m = _RE_NOME.match(s)
    if not m:
        return None
    tipo, sigla, numero, resto = m.groups()
    # o final é <sufixo opcional><UF>: tenta UF de mar (3 letras) e depois a comum (2)
    for n in (3, 2):
        uf, sufixo = resto[-n:], resto[:-n]
        if (uf in _UF_MAR if n == 3 else uf in _UF) and len(sufixo) <= 3:
            return f"{int(tipo)}-{sigla}-{int(numero)}{sufixo}-{uf}"
    return None


def chave(nome: str) -> str:
    """Chave de busca: o nome canônico, ou o texto em maiúsculas só com letras e
    números (para nomes fora do padrão, como os de poços muito antigos)."""
    return canonico(nome) or re.sub(r"[^A-Z0-9]", "", _sem_acento(str(nome or "")).upper())


# ================================================================ cadastro
def _texto(v) -> str:
    return " ".join(str(v or "").split())


def _numero(v) -> float | None:
    t = _texto(v)
    if not t:
        return None
    if "," in t and "." in t:          # 1.234,5
        t = t.replace(".", "").replace(",", ".")
    else:
        t = t.replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return None


def _data(v) -> str | None:
    """'24/04/2017 00:00' → '2017-04-24'."""
    m = re.match(r"(\d{2})/(\d{2})/(\d{4})", _texto(v))
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else None


def _decodificar(dados: bytes) -> str:
    for cod in ("utf-8-sig", "cp1252"):
        try:
            return dados.decode(cod)
        except UnicodeDecodeError:
            continue
    return dados.decode("latin-1")


# Colunas da Tabela de Poços (metadados ANP) → colunas da tabela pocos.
_CAMPOS = {
    "nome_anp": ("POCO", _texto), "cadastro": ("CADASTRO", _texto),
    "operador": ("OPERADOR", _texto), "estado": ("ESTADO", _texto),
    "bacia": ("BACIA", _texto), "bloco": ("BLOCO", _texto), "campo": ("CAMPO", _texto),
    "terra_mar": ("TERRA_MAR", _texto), "tipo": ("TIPO", lambda v: int(_numero(v) or 0) or None),
    "categoria": ("CATEGORIA", _texto), "reclassificacao": ("RECLASSIFICACAO", _texto),
    "situacao": ("SITUACAO", _texto), "inicio": ("INICIO", _data),
    "termino": ("TERMINO", _data), "conclusao": ("CONCLUSAO", _data),
    "titularidade": ("TITULARIDADE", _texto),
    "lat": ("LATITUDE_BASE_DD", _numero), "lon": ("LONGITUDE_BASE_DD", _numero),
    "datum": ("DATUM_HORIZONTAL", _texto), "direcao": ("DIRECAO", _texto),
    "prof_vertical": ("PROFUNDIDADE_VERTICAL_M", _numero),
    "prof_sondador": ("PROFUNDIDADE_SONDADOR_M", _numero),
    "prof_medida": ("PROFUNDIDADE_MEDIDA_M", _numero),
    "mesa_rotativa": ("MESA_ROTATIVA", _numero),
    "cota_altimetrica": ("COTA_ALTIMETRICA_M", _numero),
    "lamina_agua": ("LAMINA_D_AGUA_M", _numero),
    "formacao_final": ("GEOLOGIA_FORMACAO_FINAL", _texto),
}
_USADAS = {c for c, _ in _CAMPOS.values()}
COLUNAS_POCOS = ("id", *_CAMPOS, "dados_anp", "fonte", "atualizado_em")


def ler_cadastro(conteudo: bytes) -> list[dict]:
    """Linhas da Tabela de Poços, já convertidas (datas ISO, números com ponto)."""
    texto = _decodificar(conteudo)
    primeira = texto.split("\n", 1)[0]
    leitor = csv.DictReader(io.StringIO(texto), delimiter=";" if ";" in primeira else ",")
    cab = [c.strip().upper() for c in (leitor.fieldnames or [])]
    if "POCO" not in cab or "LATITUDE_BASE_DD" not in cab:
        raise ErroCadastro("O arquivo não parece a Tabela de Poços da ANP "
                           "(faltam as colunas POCO e LATITUDE_BASE_DD).")
    leitor.fieldnames = cab
    saida = []
    for linha in leitor:
        nome = _texto(linha.get("POCO"))
        if not nome:
            continue
        p = {campo: conv(linha.get(col)) for campo, (col, conv) in _CAMPOS.items()}
        p = {k: (v if v != "" else None) for k, v in p.items()}
        if p["lat"] is not None and not (-35 <= p["lat"] <= 6):
            p["lat"] = None                     # fora do Brasil: coordenada inválida
        if p["lon"] is not None and not (-75 <= p["lon"] <= -28):
            p["lon"] = None
        p["id"] = chave(nome)
        extras = {k: _texto(v) for k, v in linha.items() if k and k not in _USADAS and _texto(v)}
        p["dados_anp"] = json.dumps(extras, ensure_ascii=False)
        p["poco_operador"] = _texto(linha.get("POCO_OPERADOR"))
        saida.append(p)
    return saida


def importar_cadastro(banco: Banco, linhas: list[dict], fonte: str) -> dict:
    """Substitui o cadastro (tabela pocos) e os apelidos vindos da ANP."""
    quando = agora()
    with banco.conexao() as c:
        c.execute("DELETE FROM pocos WHERE fonte LIKE 'anp%'")
        c.execute("DELETE FROM apelidos WHERE origem = 'anp'")
        c.executemany(
            f"INSERT OR REPLACE INTO pocos ({', '.join(COLUNAS_POCOS)}) "
            f"VALUES ({', '.join('?' for _ in COLUNAS_POCOS)})",
            [[*(p.get(k) for k in COLUNAS_POCOS[:-2]), fonte, quando] for p in linhas])
        apelidos = []
        for p in linhas:
            for outro in (p.get("poco_operador"), p.get("nome_anp")):
                k = chave(outro or "")
                if k and k != p["id"]:
                    apelidos.append((k, p["id"]))
        c.executemany("INSERT OR IGNORE INTO apelidos VALUES (?, ?, 'anp', '')", apelidos)
        banco.definir_meta("cadastro_anp", json.dumps({"fonte": fonte, "importado_em": quando,
                                                       "pocos": len(linhas)}), c)
    com_coord = sum(1 for p in linhas if p["lat"] is not None and p["lon"] is not None)
    return {"pocos": len(linhas), "com_coordenadas": com_coord, "apelidos": len(apelidos)}


def baixar_cadastro(timeout: float = 120) -> bytes:
    ultimo = ""
    for url in URLS_CADASTRO:
        try:
            r = requests.get(url, timeout=(30, timeout),
                             headers={"User-Agent": "SIAPP (pesquisa academica, UFAL)"})
        except requests.exceptions.RequestException as e:
            ultimo = type(e).__name__
            continue
        if r.status_code == 200 and r.content[:400].upper().find(b"POCO") >= 0:
            return r.content
        ultimo = f"HTTP {r.status_code}"
    raise ErroCadastro(f"Não consegui baixar a Tabela de Poços da ANP ({ultimo}). Baixe o CSV em "
                       f"{PAGINA_CADASTRO} e use \"Importar cadastro de arquivo\".")


# ================================================================ consultas
def resolver(banco: Banco, nome: str) -> str:
    """Id do poço para qualquer grafia: canônico se houver; senão, um apelido
    conhecido; senão, a própria chave."""
    k = chave(nome)
    with banco.conexao() as c:
        if c.execute("SELECT 1 FROM pocos WHERE id = ?", (k,)).fetchone():
            return k
        r = c.execute("SELECT poco_id FROM apelidos WHERE chave = ?", (k,)).fetchone()
    return r[0] if r else k


def registrar_reate(banco: Banco, bacia: str, categoria: str, pocos: list[dict]) -> int:
    """Pastas de poço vistas no portal (resultado de ClienteREATE.listar_pocos)."""
    quando = agora()
    with banco.conexao() as c:
        c.executemany("INSERT OR REPLACE INTO reate VALUES (?, ?, ?, ?, ?, ?, ?)",
                      [(bacia, p["caminho"], p["nome"], chave(p["nome"]), categoria,
                        p.get("parte"), quando) for p in pocos])
    return len(pocos)


def importar_catalogo_json(banco: Banco, pasta_catalogo: str) -> int:
    """Traz para o banco as listas de poços já salvas em catalogo/<bacia>/*.json."""
    n = 0
    if not os.path.isdir(pasta_catalogo):
        return 0
    for bacia in os.listdir(pasta_catalogo):
        pasta = os.path.join(pasta_catalogo, bacia)
        if not os.path.isdir(pasta):
            continue
        for nome in os.listdir(pasta):
            if not nome.endswith(".json") or nome == "categorias.json":
                continue
            try:
                with open(os.path.join(pasta, nome), encoding="utf-8") as f:
                    d = json.load(f)
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(d, dict) and d.get("pocos"):
                n += registrar_reate(banco, d.get("bacia", bacia), d.get("categoria", nome[:-5]),
                                     d["pocos"])
    return n


_CAMPOS_MAPA = ("id", "lat", "lon", "bacia", "campo", "tipo", "categoria", "situacao",
                "terra_mar", "operador", "prof_sondador")


def bacias(banco: Banco) -> list[dict]:
    with banco.conexao() as c:
        q = c.execute("""SELECT p.bacia AS bacia, count(*) AS pocos,
                                count(r.poco_id) AS no_reate
                         FROM pocos p LEFT JOIN (SELECT DISTINCT poco_id FROM reate) r
                              ON r.poco_id = p.id
                         WHERE p.bacia IS NOT NULL GROUP BY p.bacia ORDER BY p.bacia""")
        return [dict(r) for r in q]


def pocos_mapa(banco: Banco, *, bacia: str = "", texto: str = "", terra_mar: str = "",
               tipo: int | None = None, so_reate: bool = False, so_baixados: bool = False,
               acervo: str = "", familia: str = "", limite: int = 40000) -> dict:
    """Poços para o mapa, em colunas (menos texto trafegando para a janela)."""
    cond, args = ["p.lat IS NOT NULL", "p.lon IS NOT NULL"], []
    if bacia:
        cond.append("p.bacia = ?")
        args.append(bacia)
    if terra_mar:
        cond.append("p.terra_mar = ?")
        args.append(terra_mar)
    if tipo:
        cond.append("p.tipo = ?")
        args.append(int(tipo))
    if texto:
        t = f"%{_texto(texto).upper()}%"
        cond.append("(upper(p.id) LIKE ? OR upper(p.campo) LIKE ? OR upper(p.operador) LIKE ?)")
        args += [t, t, t]
    if so_reate:
        cond.append("EXISTS (SELECT 1 FROM reate r WHERE r.poco_id = p.id)")
    if so_baixados:
        cond.append("EXISTS (SELECT 1 FROM arquivos a WHERE a.poco_id = p.id)")
    if acervo == "nao_levantado":
        cond.append("ac.situacao IS NULL")
    elif acervo:
        cond.append("ac.situacao = ?")
        args.append(acervo)
    if familia:
        cond.append("(',' || ac.familias || ',') LIKE ?")
        args.append(f"%,{familia},%")
    # um poço pode aparecer em mais de uma bacia/categoria do portal: vale a
    # melhor situação (digital > imagem > pendente > sem perfil)
    sql = f"""WITH ac AS (
                SELECT poco_id,
                       CASE max(CASE situacao WHEN 'digital' THEN 4 WHEN 'imagem' THEN 3
                                              WHEN 'pendente' THEN 2 WHEN 'sem_perfil' THEN 1 ELSE 0 END)
                            WHEN 4 THEN 'digital' WHEN 3 THEN 'imagem' WHEN 2 THEN 'pendente'
                            WHEN 1 THEN 'sem_perfil' END AS situacao,
                       group_concat(familias) AS familias
                FROM acervo_pocos GROUP BY poco_id)
              SELECT {', '.join('p.' + c for c in _CAMPOS_MAPA)},
                     EXISTS (SELECT 1 FROM reate r WHERE r.poco_id = p.id) AS reate,
                     (SELECT count(*) FROM arquivos a WHERE a.poco_id = p.id) AS baixados,
                     (SELECT count(*) FROM fatos f WHERE f.poco_id = p.id) AS fatos,
                     ac.situacao AS acervo, ac.familias AS familias
              FROM pocos p LEFT JOIN ac ON ac.poco_id = p.id
              WHERE {' AND '.join(cond)} LIMIT ?"""
    with banco.conexao() as c:
        linhas = c.execute(sql, [*args, limite + 1]).fetchall()
    colunas = (*_CAMPOS_MAPA, "reate", "baixados", "fatos", "acervo", "familias")
    return {"colunas": colunas, "linhas": [list(r) for r in linhas[:limite]],
            "truncado": len(linhas) > limite}


def ficha(banco: Banco, poco_id: str) -> dict | None:
    with banco.conexao() as c:
        p = c.execute("SELECT * FROM pocos WHERE id = ?", (poco_id,)).fetchone()
        reate = [dict(r) for r in c.execute(
            "SELECT * FROM reate WHERE poco_id = ? ORDER BY bacia, categoria", (poco_id,))]
        arquivos = [dict(r) for r in c.execute(
            "SELECT rel, bytes, tipo, caminho_remoto, baixado_em FROM arquivos WHERE poco_id = ? ORDER BY rel",
            (poco_id,))]
        apelidos = [r[0] for r in c.execute("SELECT chave FROM apelidos WHERE poco_id = ?", (poco_id,))]
        curvas = [dict(r) for r in c.execute(
            """SELECT c.familia, count(*) AS n, min(c.topo_m) AS topo, max(c.base_m) AS base
               FROM curvas c JOIN perfis pf ON pf.rel = c.rel
               WHERE pf.poco_id = ? AND c.familia IS NOT NULL GROUP BY c.familia""", (poco_id,))]
    if p is None and not reate and not arquivos:
        return None
    d = dict(p) if p else {"id": poco_id}
    d["dados_anp"] = json.loads(d.get("dados_anp") or "{}")
    return {"poco": d, "no_cadastro": p is not None, "reate": reate, "arquivos": arquivos,
            "apelidos": apelidos, "fatos": banco.fatos(poco_id), "curvas": curvas}
