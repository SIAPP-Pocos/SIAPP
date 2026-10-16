"""Leitor do AGP — "Dados Gerais de Poços" da ANP (ANP/SDT/BDEP).

O AGP é um texto de largura fixa (~20–160 KB) que acompanha boa parte dos poços
no REATE, na pasta `AGP` ou `Arquivo_geral_de_poco` (`<poço>_agp.txt`). Traz, já
interpretados pela operadora:

- cabeçalho do poço (bacia, campo, coordenadas, mesa rotativa, profundidade final…);
- **unidades verticalizadas**: topos e bases de formações, membros, grupos, marcos;
- **zonas-reservatório** (poços de desenvolvimento);
- revestimentos, intervalos tamponados, indícios de hidrocarbonetos;
- **cabeçalho de cada corrida de perfilagem**: resistividade da lama, do filtrado e
  do reboco com as temperaturas, temperatura de fundo, salinidade;
- temperatura extrapolada e gradiente geotérmico (°F/m);
- testes de formação (intervalo, resultado, observações).

Formato conferido em 16/10/2026 em AGPs da Potiguar (cat. 1 e 3), Alagoas (cat. 7) e
Recôncavo. Linha que não tem a forma esperada é ignorada — nunca inventada. As
temperaturas do AGP estão em **°F** (o próprio arquivo rotula o gradiente em GRAU F/M).

Os nomes das unidades vêm abreviados (JANDAI, ACU, BARITI…) com um código numérico
de 6 dígitos; o nome por extenso, quando conhecido, vem de recursos/estratigrafia.json.
"""

from __future__ import annotations

import json
import os
import re

from .banco import Banco, agora
from .pocos import chave

CODIFICACOES = ("utf-8", "cp1252", "latin-1")

# Títulos de seção, como aparecem no arquivo (com ou sem traço no fim)
SECOES = {
    "revestimentos": r"REVESTIMENTOS\s+-",
    "tampoes": r"INTERVALOS TAMPONEADOS\s+-",
    "unidades": r"UNID\.VERTICALIZADAS\s+-",
    "indicios": r"INDICIOS DE HIDROCARBONETOS\s+-",
    "falhas": r"FALHAS\s+-",
    "zonas": r"ZONAS RESERVATORIO",
    "perfis_cabecalho": r"PERFIS:\s*REGISTRO DE CABECALHO DE PERFIS",
    "perfis_aquisicao": r"PERFIS:\s*AQUISICAO/PROCESSAMENTO",
    "temperatura": r"PERFIS:\s*REGISTRO DE DADOS DE TEMPERATURA EXTRAPOLADA",
    "testes": r"TESTES DE FORMACAO\s+-",
    "litologia": r"LITOLOGIA\s+-",
    "rochas": r"RESUMO DAS ROCHAS ENCONTRADAS NO POCO",
}
_RE_SECAO = re.compile("|".join(f"(?P<{k}>{v})" for k, v in SECOES.items()))
NUM = r"(?:-?\d+(?:\.\d*)?|-?\.\d+)"
_PROF_COTA = rf"(?P<{{n}}>{NUM})\s*\(\s*(?P<{{n}}_cota>{NUM})\s*\)"

# Dicionários que o próprio AGP traz no fim ("DICIONARIO DE CODIGOS"), conferidos em 16/10/2026
TIPOS_UNIDADE = {
    "L": "unidade litoestratigráfica", "D": "discordância", "C": "unidade cronoestratigráfica",
    "E": "unidade cronoestratigráfica especial", "S": "unidade crono-sísmica", "M": "marco (camada-chave)",
    "N": "nanofóssil", "P": "palinologia/chitinozoa/acritarca", "O": "ostracodes", "F": "foraminífero",
    "X": "zona estéril/não avaliada", "T": "ambiente deposicional", "G": "dinoflagelados",
}
QUALIDADES = {"B": "bom", "R": "regular", "Q": "questionável", "I": "inferido", "X": "dado não revisto"}
METODOS = {
    "A": "perfil", "B": "litologia", "C": "sísmica", "D": "paleontologia", "E": "perfil e litologia",
    "F": "perfil e sísmica", "G": "perfil e paleontologia", "H": "paleontologia e litologia",
    "I": "paleontologia e sísmica", "J": "perfil, litologia e paleontologia", "K": "perfil, litologia e sísmica",
    "L": "perfil, litologia, paleontologia e sísmica", "X": "dado não revisto", "Z": "informação não existente",
}
NIVEIS = {"F": "Formação", "M": "Membro", "G": "Grupo", "S": "Supergrupo"}


class ErroAGP(ValueError):
    pass


def decodificar(dados: bytes) -> str:
    for cod in CODIFICACOES:
        try:
            return dados.decode(cod)
        except UnicodeDecodeError:
            continue
    return dados.decode("latin-1", "replace")


def eh_agp(nome: str, pasta: str = "") -> bool:
    n = nome.lower()
    if not n.endswith(".txt"):
        return False
    return "_agp" in n or pasta.replace(" ", "_").lower().split("/")[-1] in ("agp", "arquivo_geral_de_poco")


def _num(s):
    if s is None:
        return None
    s = str(s).strip().replace(",", ".")
    if s in ("", "-", "."):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _prof_cota(texto: str, nome: str):
    m = re.search(_PROF_COTA.format(n=nome), texto)
    return m


# ================================================================ seções
def secoes(texto: str) -> dict[str, list[str]]:
    """Fatia o texto pelas seções conhecidas. A mesma seção pode aparecer mais
    de uma vez (cabeçalho de perfis tem continuação): as linhas se somam."""
    marcas = [(m.start(), m.lastgroup) for m in _RE_SECAO.finditer(texto)]
    saida: dict[str, list[str]] = {"cabecalho": texto[:marcas[0][0] if marcas else len(texto)].splitlines()}
    for k, (ini, nome) in enumerate(marcas):
        fim = marcas[k + 1][0] if k + 1 < len(marcas) else len(texto)
        saida.setdefault(nome, []).extend(texto[ini:fim].splitlines())
    return saida


_RE_CHAVE_VALOR = re.compile(r"^\s?(?P<k1>[A-ZÇ][A-ZÇ0-9 .\/?()&]{1,18}?)\s*:\s?(?P<v1>.*?)"
                             r"(?:\s{2,}(?P<k2>[A-ZÇ][A-ZÇ0-9 .\/?()&]{1,18}?)\s*:\s*(?P<v2>.*?))?\s*$")


def cabecalho(linhas: list[str]) -> dict:
    cab = {}
    for ln in linhas:
        m = _RE_CHAVE_VALOR.match(ln)
        if not m:
            continue
        for k, v in ((m["k1"], m["v1"]), (m["k2"], m["v2"])):
            if k:
                k = " ".join(k.split())
                v = " ".join((v or "").split())
                if k not in cab or not cab[k]:
                    cab[k] = v
    poco = cab.get("POÇO") or cab.get("POCO") or ""
    lat = _num((cab.get("LATITUDE") or "").split("(")[0])
    lon = _num((cab.get("LONGITUDE") or "").split("(")[0])
    return {
        "poco_agp": poco, "poco_id": chave(poco) if poco else "",
        "bacia": cab.get("BACIA", ""), "campo": cab.get("CAMPO", ""), "datum": cab.get("DATUM", ""),
        "lat": lat, "lon": lon, "estado": cab.get("ESTADO", ""), "municipio": cab.get("MUNICIPIO", ""),
        "mesa_rotativa": _num(cab.get("MESA ROTATIVA")), "bap": _num(cab.get("B.A.P")),
        "prof_final": _num(cab.get("P.F.SONDADOR")), "maior_prof": _num(cab.get("MAIOR PROF.")),
        "formacao_pf": cab.get("FORMACAO P.F.", ""), "classificacao": cab.get("CLASSIFICACAO", ""),
        "reclassificacao": cab.get("RECLASSIFICACAO", ""), "direcional": cab.get("DIRECIONAL?", ""),
        "terra_mar": cab.get("TERRA / MAR", ""), "inicio": cab.get("INICIO", ""), "termino": cab.get("TERMINO", ""),
        "operadora": cab.get("EMPR. OPER.1/2", ""), "nome": cab.get("NOME", ""),
        "campos": cab,
    }


_RE_UNIDADE = re.compile(
    rf"^ (?P<tip>[A-Z])\s+(?P<ql>[A-Z])\s+(?P<nome>\S.{{0,9}}?)\s+(?P<codigo>\d{{6}})\s+"
    rf"(?P<topo>{NUM})\s*\(\s*(?P<cota_topo>{NUM})\s*\)(?P<resto>.*)$")
_RE_DATA_FIM = re.compile(r"(\d\d/\d\d/\d{4})\s*$")


def unidades(linhas: list[str], estratigrafia: dict | None = None) -> list[dict]:
    est = estratigrafia or {}
    saida = []
    for ln in linhas:
        m = _RE_UNIDADE.match(ln)
        if not m:
            continue
        resto = m["resto"]
        base = re.search(rf"(?P<base>{NUM})\s*\(\s*(?P<cota>{NUM})\s*\)", resto)
        desc_topo = (resto[:base.start()] if base else resto[:30]).strip()
        data = _RE_DATA_FIM.search(resto)
        cauda = resto[base.end():] if base else resto[30:]
        if data:
            cauda = cauda[:cauda.rfind(data.group(1))]
        # depois da base: descrição da base, método (1 letra), tempo, fonte
        mt = re.match(r"\s*(?P<desc>[A-Z][A-Z. ]*?[A-Z.])?\s+(?P<met>[A-Z])\s+(?P<tempo>\d{4})?\s*(?P<fonte>.*?)\s*$",
                      cauda)
        nome = m["nome"].strip()
        nv = re.match(r"^([FMGS])\s+(\S.*)$", nome) if m["tip"] == "L" else None
        sigla = nv.group(2).strip() if nv else nome
        conhecido = est.get(m["codigo"]) or est.get(sigla.upper())
        saida.append({
            "tip": m["tip"], "ql": m["ql"], "nivel": nv.group(1) if nv else "",
            "tipo_desc": TIPOS_UNIDADE.get(m["tip"], ""), "qualidade": QUALIDADES.get(m["ql"], ""),
            "sigla": sigla, "codigo": m["codigo"], "nome": conhecido or sigla,
            "topo": _num(m["topo"]), "cota_topo": _num(m["cota_topo"]),
            "desc_topo": " ".join(desc_topo.split()) if desc_topo and not re.fullmatch(NUM, desc_topo) else "",
            "base": _num(base["base"]) if base else None, "cota_base": _num(base["cota"]) if base else None,
            "desc_base": (mt["desc"] or "") if mt else "",
            "metodo": mt["met"] if mt else "", "metodo_desc": METODOS.get(mt["met"], "") if mt else "",
            "fonte": " ".join((mt["fonte"] if mt else "").split()),
            "data": data.group(1) if data else "",
        })
    return saida


_RE_ZONA = re.compile(rf"^ (?P<codigo>\d+/\S+|\S+)\s{{2,}}(?P<fonte>\S.*?)\s{{2,}}"
                      rf"(?P<topo>{NUM})\s*\(\s*(?P<cota_topo>{NUM})\s*\)\s*(?P<ql>[A-Z]?)\s*"
                      rf"(?P<base>{NUM})\s*\(\s*(?P<cota_base>{NUM})\s*\)")


def zonas(linhas: list[str]) -> list[dict]:
    saida = []
    for ln in linhas:
        m = _RE_ZONA.match(ln)
        if m and not m["codigo"].startswith("COD"):
            saida.append({"codigo": m["codigo"], "fonte": " ".join(m["fonte"].split()),
                          "topo": _num(m["topo"]), "cota_topo": _num(m["cota_topo"]),
                          "base": _num(m["base"]), "cota_base": _num(m["cota_base"])})
    return saida


_RE_REVEST = re.compile(rf"^\s+(?P<tipo>REV\.\s?\S.*?)\s{{2,}}(?P<prof>{NUM})\s*\(\s*(?P<cota>{NUM})\s*\)\s+"
                        rf"(?P<diam>\d[\d /]*?)\s{{2,}}(?P<rec>.*?)\s*$")


def revestimentos(linhas: list[str]) -> list[dict]:
    saida = []
    for ln in linhas:
        m = _RE_REVEST.match(ln)
        if m:
            saida.append({"tipo": " ".join(m["tipo"].split()), "prof": _num(m["prof"]),
                          "cota": _num(m["cota"]), "diametro": " ".join(m["diam"].split()),
                          "recuperacao": " ".join(m["rec"].split())})
    return saida


_RE_INDICIO = re.compile(rf"^\s+(?P<tipo>[A-Z])\s+(?P<origem>[A-Z])\s+(?P<amostra>[A-Z])\s+"
                         rf"(?P<topo>{NUM})\s*\(\s*(?P<cota_topo>{NUM})\s*\)"
                         rf"(?:\s+(?P<base>{NUM})\s*\(\s*(?P<cota_base>{NUM})\s*\))?(?P<resto>.*)$")
TIPOS_INDICIO = {"O": "óleo", "G": "gás"}


def indicios(linhas: list[str]) -> list[dict]:
    saida = []
    for ln in linhas:
        m = _RE_INDICIO.match(ln)
        if m:
            saida.append({"tipo": m["tipo"], "fluido": TIPOS_INDICIO.get(m["tipo"], m["tipo"]),
                          "origem": m["origem"], "amostra": m["amostra"],
                          "topo": _num(m["topo"]), "base": _num(m["base"]),
                          "descricao": " ".join(m["resto"].replace("/", " ").split())})
    return saida


_CAMPOS_CORRIDA = {
    "NUMERO CORRIDA": "corrida", "GRUPO PERFIS COMBINADOS": "grupo", "PROF. ALCANCADA": "prof_alcancada",
    "PROF. DA SAPATA": "prof_sapata", "DENSIDADE LAMA": "densidade_lama", "COMPANHIA PERF.": "companhia",
    "RESISTIVIDADE LAMA": "rm", "TEMPERATURA LAMA": "t_rm", "RESISTIVIDADE FILTRADO": "rmf",
    "TEMPERATURA FILTRADO": "t_rmf", "RESISTIVIDADE REBOCO": "rmc", "TEMPERATURA REBOCO": "t_rmc",
    "TEMPERATURA FUNDO POCO": "bht", "TEMP. FUNDO MAR/BAP": "t_superficie", "SALINIDADE LAMA": "salinidade_lama",
    "PH LAMA": "ph_lama",
}
_NUMERICOS = {"prof_alcancada", "prof_sapata", "densidade_lama", "rm", "t_rm", "rmf", "t_rmf", "rmc", "t_rmc",
              "bht", "t_superficie", "salinidade_lama", "ph_lama"}
_RE_KV = re.compile(r"(?P<k>[A-Z][A-Z. /]*?[A-Z.]):\s*(?P<v>.*?)(?=\s{2,}[A-Z][A-Z. /]*?[A-Z.]:|\s*$)")


def corridas(linhas: list[str]) -> list[dict]:
    """Cabeçalho de cada corrida de perfilagem. Temperaturas em °F."""
    blocos, atual = [], None
    for ln in linhas:
        if "NUMERO CORRIDA:" in ln:
            atual = {}
            blocos.append(atual)
        if atual is None:
            continue
        for m in _RE_KV.finditer(ln):
            k = " ".join(m["k"].split())
            if k in _CAMPOS_CORRIDA:
                v = " ".join(m["v"].split())
                campo = _CAMPOS_CORRIDA[k]
                if campo in ("prof_alcancada", "prof_sapata"):
                    v = v.split("(")[0]
                atual[campo] = _num(v) if campo in _NUMERICOS else v
        t = re.search(r"TIPO LAMA\s+(\S.*?)\s{2,}PH LAMA", ln)
        if t:
            atual["tipo_lama"] = " ".join(t.group(1).split())
        d = re.search(r"DATA DE INICIO\s+(\d\d/\d\d/\d{4})", ln)
        if d:
            atual["data"] = d.group(1)
    uteis = [b for b in blocos if any(b.get(k) is not None for k in ("rm", "rmf", "bht", "prof_alcancada"))]
    # o AGP repete a corrida para cada grupo de perfis combinados: uma por (corrida, dados)
    vistos, saida = set(), []
    for b in uteis:
        chave_ = (b.get("corrida"), b.get("rm"), b.get("rmf"), b.get("bht"), b.get("prof_alcancada"))
        if chave_ not in vistos:
            vistos.add(chave_)
            saida.append(b)
    return saida


_RE_TEMP = re.compile(rf"^\s+(?P<corrida>\d+)\s+(?P<metodo>\S.*?)\s{{2,}}(?P<temp>{NUM})\s+"
                      rf"(?P<prof>{NUM})\s*\(\s*(?P<cota>{NUM})\s*\)\s+(?P<grad>{NUM})")


def temperaturas(linhas: list[str]) -> list[dict]:
    """Temperatura extrapolada (°F) por corrida e gradiente geotérmico (°F/m)."""
    saida = []
    for ln in linhas:
        m = _RE_TEMP.match(ln)
        if m:
            saida.append({"corrida": m["corrida"], "metodo": " ".join(m["metodo"].split()),
                          "temperatura_f": _num(m["temp"]), "prof": _num(m["prof"]), "gradiente_f_m": _num(m["grad"])})
    return saida


_RE_AQUIS = re.compile(rf"^\s+(?P<cod>\d{{3}})\s+(?P<gr>\d+)\s+(?P<tipo>\S+?)\s.*?"
                       rf"(?P<topo>{NUM})\s*\(\s*{NUM}\s*\)\s*(?P<base>{NUM})\s*\(\s*{NUM}\s*\)\s*$")


def perfis_corridos(linhas: list[str]) -> list[dict]:
    saida = []
    for ln in linhas:
        m = _RE_AQUIS.match(ln)
        if m:
            saida.append({"codigo": m["cod"], "tipo": m["tipo"].rstrip("/"),
                          "topo": _num(m["topo"]), "base": _num(m["base"])})
    return saida


_RE_LITO = re.compile(rf"^\s+(?:(?P<topo>{NUM})\s*\(\s*{NUM}\s*\)\s+)?(?P<base>{NUM})\s*\(\s*{NUM}\s*\)\s+"
                      rf"(?P<cod>\d+)\s+(?P<rocha>[A-ZÇÃÕÁÉÍÓÚ][A-ZÇÃÕÁÉÍÓÚ/ -]*?)(?:\s{{2,}}(?P<resto>\S.*?))?\s*$")


def litologia(linhas: list[str]) -> list[dict]:
    """Litologia descrita (amostras de calha), em camadas contínuas: cada linha traz
    a base; o topo é a base da anterior. É o gabarito para conferir o Vsh do GR."""
    saida, topo = [], None
    for ln in linhas:
        m = _RE_LITO.match(ln)
        if not m:
            continue
        t = _num(m["topo"]) if m["topo"] else topo
        b = _num(m["base"])
        partes = (m["resto"] or "").split()
        saida.append({"topo": t, "base": b, "codigo": m["cod"], "rocha": " ".join(m["rocha"].split()),
                      "descricao": " ".join(partes)})
        topo = b
    return saida


def testes(linhas: list[str]) -> list[dict]:
    """Testes de formação: intervalo, data, tipo, resultado, temperatura e o texto
    das observações (que às vezes traz a salinidade da água recuperada)."""
    texto = "\n".join(linhas)
    saida = []
    for bloco in re.split(r"\n\s*NUMERO\s*-\s*", texto)[1:]:
        def campo(rotulo, b=bloco):
            m = re.search(rotulo + r"\s*:\s*(.*?)(?:\s{2,}[A-Z][A-Z .]+:|\n|$)", b)
            return " ".join(m.group(1).split()) if m else ""
        topo = re.search(rf"TOPO\s*:\s*({NUM})\s*M", bloco)
        base = re.search(rf"BASE\s*:\s*({NUM})\s*M", bloco)
        obs = re.search(r"\*+ OBSERVACOES \*+\n(.*?)(?:\n\s*\*{4}|\Z)", bloco, re.S)
        obs_txt = " ".join(re.sub(r"^\s*[A-Z]\s", "", l) for l in obs.group(1).splitlines()) if obs else ""
        sal = re.search(r"SAL(?:INIDADE)?\s*=?\s*([\d.,]+)\s*PPM", obs_txt, re.I)
        saida.append({
            "numero": bloco.split("\n", 1)[0].strip(), "data": campo("DATA"), "tipo": campo("TIPO"),
            "topo": _num(topo.group(1)) if topo else None, "base": _num(base.group(1)) if base else None,
            "temp_max": campo(r"TEMP\. MAX\. TESTE"), "resultado": campo("RESULTADO"),
            "objetivo": campo("OBJETIVO"), "observacoes": " ".join(obs_txt.split()),
            "salinidade_ppm": _num(sal.group(1).replace(".", "").replace(",", "")) if sal else None,
        })
    return saida


# ================================================================ geral
def ler(texto: str, estratigrafia: dict | None = None) -> dict:
    if "UNID.VERTICALIZADAS" not in texto and "AGP" not in texto[:600] and "POCO" not in texto[:300].upper():
        raise ErroAGP("Não parece um AGP (Dados Gerais de Poços).")
    s = secoes(texto)
    cab = cabecalho(s.get("cabecalho", []))
    return {
        "cabecalho": cab,
        "unidades": unidades(s.get("unidades", []), estratigrafia),
        "zonas": zonas(s.get("zonas", [])),
        "revestimentos": revestimentos(s.get("revestimentos", [])),
        "indicios": indicios(s.get("indicios", [])),
        "corridas": corridas(s.get("perfis_cabecalho", [])),
        "temperaturas": temperaturas(s.get("temperatura", [])),
        "perfis": perfis_corridos(s.get("perfis_aquisicao", [])),
        "testes": testes(s.get("testes", [])),
        "litologia": litologia(s.get("litologia", [])),
        "secoes": sorted(k for k in s if k != "cabecalho"),
    }


def ler_estratigrafia(caminho: str) -> dict:
    """{código ou sigla: nome por extenso} de recursos/estratigrafia.json."""
    try:
        with open(caminho, encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}
    saida = {}
    for item in d.get("unidades", []):
        for k in [item.get("sigla", "")] + list(item.get("codigos", [])):
            if k:
                saida[str(k).upper()] = item["nome"]
    return saida


def caminho_local(pasta_projeto: str, bacia: str, nome_arquivo: str) -> str:
    return os.path.join(pasta_projeto, "agp", re.sub(r"[^\w .-]+", "_", bacia), os.path.basename(nome_arquivo))


# ================================================================== banco
_COLS_UNIDADE = ("tip", "ql", "nivel", "sigla", "codigo", "nome", "topo", "cota_topo", "desc_topo",
                 "base", "cota_base", "desc_base", "metodo", "fonte", "data")


def gravar(banco: Banco, *, bacia: str, caminho: str, poco_caminho: str, poco_pasta: str,
           tamanho: int, texto: str | None, estratigrafia: dict | None = None,
           arquivo_local: str = "", erro: str = "") -> dict | None:
    """Lê e grava um AGP. `poco_pasta`: id do poço da pasta do REATE onde o arquivo
    está. Se o AGP for de outro poço (acontece no portal), os topos vão para o poço
    que o próprio AGP declara, e `confere` fica 0."""
    dados, poco_id, poco_agp, confere = None, poco_pasta, "", None
    if texto is not None and not erro:
        try:
            dados = ler(texto, estratigrafia)
            poco_agp = dados["cabecalho"]["poco_agp"]
            if dados["cabecalho"]["poco_id"]:
                confere = int(dados["cabecalho"]["poco_id"] == poco_pasta)
                poco_id = dados["cabecalho"]["poco_id"]
        except ErroAGP as e:
            erro = str(e)
    with banco.conexao() as c:
        c.execute("INSERT OR REPLACE INTO agp VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                  (bacia, caminho, poco_caminho, poco_pasta, poco_id, poco_agp, confere, tamanho,
                   arquivo_local, agora(), json.dumps(dados, ensure_ascii=False) if dados else None, erro or None))
        c.execute("DELETE FROM agp_unidades WHERE bacia = ? AND caminho = ?", (bacia, caminho))
        if dados:
            c.executemany(
                f"INSERT INTO agp_unidades (bacia, caminho, poco_id, ordem, {', '.join(_COLS_UNIDADE)}) "
                f"VALUES (?, ?, ?, ?, {', '.join('?' * len(_COLS_UNIDADE))})",
                [(bacia, caminho, poco_id, k, *[u.get(col) for col in _COLS_UNIDADE])
                 for k, u in enumerate(dados["unidades"])])
    return dados


def do_poco(banco: Banco, poco_id: str) -> list[dict]:
    """AGPs que descrevem o poço (normalmente um), com os dados lidos."""
    with banco.conexao() as c:
        linhas = [dict(r) for r in c.execute(
            "SELECT * FROM agp WHERE poco_id = ? AND dados IS NOT NULL ORDER BY confere DESC, lido_em DESC",
            (poco_id,))]
    for r in linhas:
        r["dados"] = json.loads(r["dados"])
    return linhas


def unidades_do_poco(banco: Banco, poco_id: str) -> list[dict]:
    with banco.conexao() as c:
        return [dict(r) for r in c.execute(
            "SELECT * FROM agp_unidades WHERE poco_id = ? ORDER BY topo, ordem", (poco_id,))]


def unidades_frequentes(banco: Banco, bacia: str | None = None, limite: int = 200) -> list[dict]:
    """Unidades (por código) e em quantos poços aparecem — para escolher uma
    formação e aplicar em vários poços."""
    cond, args = "", []
    if bacia:
        cond, args = "WHERE bacia = ?", [bacia]
    with banco.conexao() as c:
        return [dict(r) for r in c.execute(
            f"""SELECT codigo, tip, nivel, sigla, max(nome) AS nome, count(DISTINCT poco_id) AS pocos,
                       sum(base IS NOT NULL) AS com_base
                FROM agp_unidades {cond} GROUP BY codigo, tip, nivel, sigla
                ORDER BY pocos DESC LIMIT ?""", [*args, limite])]
