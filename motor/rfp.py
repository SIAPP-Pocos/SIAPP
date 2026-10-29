"""Leitor dos formulários CDPE da ANP: Relatório Final de Poço (RFP), Relatório Final de
Completação (RFCP) e Notificação/Relatório de Perfuração.

Esses PDFs vêm na "Pasta de Poço" do REATE (`<poço>_CDPE_<n>_RFP.pdf`,
`..._RFCP_1.pdf`, `..._Perfuracao.pdf`). São gerados pelo sistema da ANP (SDT) com
**texto embutido e leiaute fixo** — A4 retrato, 595 × 841 pt, cada campo sempre na mesma
coluna. Por isso a leitura é pela **posição do texto**, sem OCR: cada seção começa num
título conhecido ("Topos Estratigráficos", "Teste de Formação"…) e cada coluna de tabela
ocupa uma faixa fixa de x. Conferido em 29/10/2026 em RFP/RFCP/Perfuração de poços da
Potiguar (1-AURI-12-RN, 3-BRSA-1151-RN) e do Recôncavo (1-BRSA-1304-BA).

O que cada formulário traz (e o SIAPP lê):

- **RFP**: dados do poço (datas, profundidade final do sondador e do perfil, mesa
  rotativa, unidade na profundidade final), coordenadas da base/alvo/fundo, resultado
  (descobridor, fluido, abandono), **topos estratigráficos** previstos × constatados,
  **indícios** de petróleo/gás, testemunhos, amostras laterais, **análise de perfis**
  (intervalos com litologia), **testes de formação** (tipo, intervalo, fluido, °API,
  pressão estática em kgf/cm²), **temperaturas** (°F, lidas ou extrapoladas),
  amostragem de calha e observações;
- **RFCP**: revestimentos de produção, **intervalos canhoneados**, coluna de produção,
  dados do teste (vazão, °API, pressão de fluxo) e a **sigla antiga do poço na base da
  operadora** (ex.: 1-BRSA-1304-BA = 1-FPA-1-BA), que vira apelido;
- **Perfuração**: sonda, categoria, coordenadas previstas, e por **fase**: diâmetro,
  revestimento, topo do cimento e **fluido de perfuração com o peso (lb/gal)**.

Convenções do formulário respeitadas aqui: números em pt-BR ("1.948,50", "-1.854,40");
"0,0" é o campo vazio (profundidade com cota também 0,0, °API 0, pressão 0…), e não é
transformado em zero; tudo o que não está na posição esperada é ignorado — nunca inventado.
"""

from __future__ import annotations

import re
import unicodedata

VERSAO = 2          # 2 (0.38): NPR, Relatório de Descoberta, Reentrada e CDPE de título desconhecido
NOME = "Formulários CDPE da ANP (RFP, RFCP, Perfuração, Descoberta, Perfilagens, Reentrada)"

# ---------------------------------------------------------------- reconhecimento
_RE_NOME = re.compile(r"(?:^|[_\-\s])(CDPE|RFP|RFCP|PERFURACAO)(?:[_\-\s.]|\d|$)", re.I)

DOCUMENTOS = {
    "rfp": "Relatório Final de Poço",
    "rfcp": "Relatório Final de Completação",
    "perfuracao": "Notificação e Relatório de Perfuração",
    "nd": "Relatório de Descoberta",
    "npr": "Relatório de Perfilagens Realizadas",
    "reentrada": "Relatório de Reentrada",
    "cdpe": "Formulário CDPE",
}
# Ordem de preferência quando dois formulários trazem o mesmo dado (ficha, intervalos)
PRIORIDADE = {"rfp": 0, "rfcp": 1, "perfuracao": 2, "nd": 3, "npr": 4, "reentrada": 5, "cdpe": 9}
_TITULOS_DOC = (
    ("RELATORIO FINAL DE POCO", "rfp"),
    ("RELATORIO FINAL COMPLETACAO", "rfcp"),
    ("RELATORIO FINAL DE COMPLETACAO", "rfcp"),
    ("NOTIFICACAO DE PERFURACAO DE POCO", "perfuracao"),
    ("RELATORIO DE PERFURACAO DE POCO", "perfuracao"),
    ("RELATORIO DE DESCOBERTA DE POCO", "nd"),
    ("RELATORIO DE PERFILAGENS REALIZADAS", "npr"),
    ("RELATORIO DE REENTRADA", "reentrada"),
)


class ErroRFP(ValueError):
    pass


def reconhece_nome(nome: str) -> bool:
    """Pelo nome do arquivo: só PDFs com CDPE/RFP/RFCP/Perfuracao (o conteúdo confirma)."""
    base = _sem_acento(str(nome or "")).upper()
    return base.endswith(".PDF") and bool(_RE_NOME.search(base))


def reconhece(rel: str) -> bool:
    return reconhece_nome(str(rel or "").replace("\\", "/").rsplit("/", 1)[-1])


# ---------------------------------------------------------------- texto
def _sem_acento(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def _norm(s: str) -> str:
    return " ".join(_sem_acento(s).upper().split())


def numero(s) -> float | None:
    """'1.948,50' → 1948.5; '-1.854,40' → -1854.4; '88,5' → 88.5. Texto que não é número → None."""
    t = str(s or "").strip().replace(" ", "")
    if not re.fullmatch(r"-?\d{1,3}(?:\.\d{3})*(?:,\d+)?|-?\d+(?:,\d+)?", t):
        return None
    return float(t.replace(".", "").replace(",", "."))


def _nz(v):
    """0,0 do formulário = vazio."""
    return None if v in (None, 0.0) else v


def grau_decimal(s: str) -> float | None:
    """'-12:04:45,845' → -12.07940…"""
    m = re.fullmatch(r"(-?)(\d{1,3}):(\d{1,2}):(\d{1,2}(?:[,.]\d+)?)", str(s or "").strip())
    if not m:
        return None
    v = int(m[2]) + int(m[3]) / 60 + float(m[4].replace(",", ".")) / 3600
    return round(-v if m[1] else v, 7)


def _texto_celula(s: str) -> str:
    # aspas de polegada vêm como "¿¿" ou "``" em alguns RFCP
    return " ".join(s.replace("¿¿", '"').replace("``", '"').split())


# ---------------------------------------------------------------- página → fragmentos
# Cabeçalho da ANP (logo, data, hora, "CDPE") e rodapé (SDT…, nº da página) ficam fora.
TOPO_UTIL, BASE_UTIL = 95.0, 780.0
_PASSO_PAGINA = 1000.0      # y "contínuo": seção que continua na página seguinte segue a mesma faixa


def fragmentos(doc) -> list[tuple[float, float, str, int]]:
    """(x, y contínuo, texto, página) de cada trecho de texto, na área útil."""
    saida = []
    for n, pagina in enumerate(doc):
        for b in pagina.get_text("dict")["blocks"]:
            for linha in b.get("lines", []):
                for s in linha["spans"]:
                    t = s["text"].strip()
                    x, y = s["bbox"][0], s["bbox"][1]
                    if t and TOPO_UTIL <= y <= BASE_UTIL:
                        saida.append((round(x, 1), round(n * _PASSO_PAGINA + y, 1), t, n + 1))
    saida.sort(key=lambda f: (f[1], f[0]))
    return saida


SECOES = {
    # RFP
    "DADOS DO POCO": "dados", "COORDENADAS": "coordenadas", "RESULTADO DO POCO": "resultado",
    "TOPOS ESTRATIGRAFICOS": "topos", "INDICIOS DE PETROLEO E/OU GAS": "indicios",
    "TESTEMUNHOS": "testemunhos", "AMOSTRAS LATERAIS": "laterais", "ANALISE DE PERFIS": "analise_perfis",
    "TESTE DE FORMACAO": "testes", "TEMPERATURAS": "temperaturas", "AMOSTRAGEM DE CALHA": "calha",
    "OBSERVACOES": "observacoes",
    # RFCP
    "DADOS GERAIS": "dados", "REVESTIMENTOS DE PRODUCAO": "revestimentos",
    "INTERVALOS DE PRODUCAO": "canhoneados", "OPERACOES ESPECIAIS": "operacoes",
    "COLUNA DE PRODUCAO": "coluna", "DADOS DE TESTE DE FORMACAO": "testes_completacao",
    # Perfuração
    "POCO": "dados", "NOTIFICACAO DE PERFURACAO DE POCO": "notificacao", "DADOS DA SONDA": "sonda",
    "PROFUNDIDADES FINAIS PREVISTAS": "previstas", "COMUNICACAO DE INICIO DE PERFURACAO DE POCO": "inicio",
    "COORDENADA DA BASE": "coordenada_base", "RELATORIO DE PERFURACAO DE POCO": "relatorio_perfuracao",
    "FASES E DEMAIS INFORMACOES": "fases", "TEMPO DE PERFURACAO (DIAS)": "tempos",
    "NAO CONFORMIDADES": "nao_conformidades",
    # Relatório de Descoberta (nd)
    "INDICIOS": "indicios_nd", "PERFIS": "perfis_nd", "TESTES DE FORMACAO": "testes_nd",
    "ESTADO ATUAL DO POCO": "estado_atual",
    # Relatório de Perfilagens Realizadas (npr)
    "OPERACOES DURANTE A PERFURACAO": "perf_operacoes",
    "OPERACOES DE PERFILAGENS CONVENCIONAIS": "perf_convencionais",
    "OPERACOES DE PERFILAGENS ESPECIAIS - INTERVALOS ABRANGIDOS": "perf_especiais",
    "OPERACOES DE PERFILAGENS ESPECIAIS - AMOSTRAGEM E RESULTADO": "perf_resultado",
    # Reentrada
    "MOTIVO DA REENTRADA": "motivo", "OPERACOES PREVISTAS": "operacoes_previstas",
    "RESULTADO REENTRADA": "resultado_reentrada", "DADOS ADQUIRIDOS": "dados_adquiridos",
}


_TITULO_EM_LINHA_DE_COLUNAS = {"TEMPO DE PERFURACAO (DIAS)"}


def _eh_titulo(f, k, frags) -> bool:
    """Título de seção fica sozinho na linha (ou repetido, como "COORDENADAS" × 3). Assim o
    título de coluna "Perfis" do NPR não é tomado pela seção "Perfis" do Relatório de Descoberta."""
    if k in _TITULO_EM_LINHA_DE_COLUNAS:
        return True
    return all(_norm(g[2]) == k for g in frags if abs(g[1] - f[1]) <= 3)


def faixas(frags) -> tuple[list[str], dict[str, list[tuple[float, float, str, int]]]]:
    """Separa os fragmentos por seção (do título de uma até o da próxima). Uma seção que
    se repete (ex.: "DADOS DO POÇO" e "DADOS GERAIS" num mesmo formulário) acumula."""
    titulos, inicio = [], []
    for f in frags:
        k = _norm(f[2])
        for t, doc in _TITULOS_DOC:
            if k.startswith(t):
                titulos.append(doc)
        if k in SECOES and (not inicio or abs(inicio[-1][0] - f[1]) > 3) and _eh_titulo(f, k, frags):
            inicio.append((f[1], SECOES[k]))
    por = {}
    for i, (y0, nome) in enumerate(inicio):
        y1 = inicio[i + 1][0] if i + 1 < len(inicio) else float("inf")
        # o título está na própria linha y0; a linha de títulos de coluna também pode estar (tempos)
        por.setdefault(nome, []).extend(f for f in frags if y0 <= f[1] < y1 and _norm(f[2]) not in SECOES)
    return titulos, por


# ---------------------------------------------------------------- tabelas
def _coluna(x: float, colunas: list[tuple[str, float]]) -> str | None:
    escolhida = None
    for nome, x0 in colunas:
        if x >= x0:
            escolhida = nome
    return escolhida


def tabela(frags, colunas: list[tuple[str, float]], ancora: str, *, tol: float = 14.0) -> list[dict]:
    """Linhas de uma tabela de leiaute fixo.

    `colunas`: (nome, x onde a coluna começa), em ordem de x. Uma linha existe onde a coluna
    `ancora` tem um número; os títulos das colunas (acima da primeira linha) ficam de fora.
    Célula de duas linhas (ex.: "FILTRADO/ ÁGUA" + "FORMAÇÃO", "FM" + "ALAGAMAR/PENDÊNCIA"):
    o pedaço de baixo vai para a linha imediatamente acima dele (até `tol` pt)."""
    ancoras = sorted({f[1] for f in frags if _coluna(f[0], colunas) == ancora and numero(f[2]) is not None})
    linhas = {y: {"_pagina": None} for y in ancoras}
    for x, y, t, pg in frags:
        acima = [a for a in ancoras if a <= y + 3]
        if not acima or y - acima[-1] > tol:
            continue
        a, col = acima[-1], _coluna(x, colunas)
        if col is None:
            continue
        ln = linhas[a]
        ln["_pagina"] = ln["_pagina"] or pg
        ln[col] = f"{ln[col]} {t}" if col in ln else t
    return [linhas[y] for y in ancoras]


# ---------------------------------------------------------------- campos de formulário
_RE_COORD = re.compile(r"^-?\d{1,3}:\d{1,2}:\d{1,2}(?:[,.]\d+)?$")


def _eh_rotulo(t: str) -> bool:
    n = _norm(t)
    return n.endswith(":") or n.endswith("-") or n.endswith("?") or n in _ROTULOS_SEM_DOIS_PONTOS


_ROTULOS_SEM_DOIS_PONTOS = {"UNIDADE ESTRATIGRAFICA", "PROFUNDIDADE FINAL POR PERFIL -"}


def campos(frags, rotulos: dict[str, str], *, alcance: float = 40.0) -> dict[str, str]:
    """Valor de cada rótulo: o texto logo abaixo dele (até `alcance` pt), na faixa de x que vai
    do rótulo até o próximo rótulo da mesma linha. `rotulos`: início do rótulo normalizado → chave.
    O mesmo rótulo em colunas diferentes (Profundidade Final por Perfil – medida / em cota) usa
    a chave com sufixo @<ordem na linha>."""
    labels = [f for f in frags if _eh_rotulo(f[2])]
    saida = {}
    for x, y, t, _ in labels:
        n = _norm(t)
        chave = next((k for r, k in rotulos.items() if n.startswith(r)), None)
        if chave is None:
            continue
        mesma = sorted(f[0] for f in labels if abs(f[1] - y) <= 3)
        if "@" in chave:
            base, _, ordem = chave.partition("@")
            pos = [i for i, xx in enumerate(mesma) if abs(xx - x) < 1]
            chaves = dict(p.split("=") for p in ordem.split(","))
            chave = f"{base}_{chaves.get(str(pos[0] if pos else 0), str(pos[0] if pos else 0))}"
        prox = [xx for xx in mesma if xx > x + 1]
        x1 = (prox[0] - 6) if prox else 1e9
        cand = [f for f in frags if x - 6 <= f[0] < x1 and y + 2 < f[1] <= y + alcance and not _eh_rotulo(f[2])]
        if cand and chave not in saida:
            linha = min(c[1] for c in cand)
            saida[chave] = _texto_celula(" ".join(c[2] for c in sorted(cand) if abs(c[1] - linha) <= 3))
    return saida


def coordenadas(frags, grupos: list[tuple[str, float]]) -> dict[str, dict]:
    """Coordenadas (g:mm:ss,sss) agrupadas pela coluna (`grupos`: nome, x inicial). Em cada
    grupo, latitude e longitude se distinguem pelo valor: no Brasil |lon| > |lat| sempre."""
    por = {}
    for x, y, t, _ in frags:
        if _RE_COORD.match(t):
            g = _coluna(x, grupos)
            if g:
                por.setdefault(g, []).append(grau_decimal(t))
    saida = {}
    for g, vals in por.items():
        if len(vals) >= 2:
            a, b = vals[0], vals[1]
            lat, lon = (a, b) if abs(a) < abs(b) else (b, a)
            saida[g] = {"lat": lat, "lon": lon}
    return saida


def _texto_corrido(frags) -> str:
    linhas, ult = [], None
    for x, y, t, _ in sorted(frags, key=lambda f: (f[1], f[0])):
        if ult is not None and abs(y - ult) <= 3:
            linhas[-1] += " " + t
        else:
            linhas.append(t)
        ult = y
    return "\n".join(linhas).strip()


# ---------------------------------------------------------------- colunas de cada tabela
COL_TOPOS = [("unidade", 0), ("prev_medida", 180), ("prev_cota", 290), ("medida", 390), ("cota", 490)]
COL_INDICIOS = [("topo", 0), ("base", 58), ("unidade", 100), ("ocorrencia", 240), ("tipo", 275),
                ("fluorescencia", 300), ("corte", 350), ("gas_total", 400), ("gas_parcial", 470),
                ("cromatografia", 530)]
COL_TESTEMUNHOS = [("ordem", 0), ("topo", 60), ("base", 125), ("recuperacao", 200), ("unidade", 250),
                   ("litologia", 350)]
COL_LATERAIS = [("ordem", 0), ("prof", 70), ("unidade", 150), ("litologia", 290)]
COL_ANALISE = [("topo", 0), ("base", 75), ("unidade", 125), ("litologia", 420)]
COL_TESTES = [("tipo", 0), ("topo", 80), ("base", 145), ("vazao", 205), ("fluido", 280), ("api", 400),
              ("deplecao", 445), ("pressao", 490), ("prof_registrador", 535)]
COL_TEMPERATURAS = [("valor", 0), ("unidade", 95), ("medida", 170), ("cota", 240), ("tipo", 330),
                    ("origem", 400)]
COL_CALHA = [("topo", 0), ("base", 130), ("padrao", 230)]
COL_REVEST = [("diametro", 0), ("topo", 95), ("base", 150), ("peso", 200), ("topo_peso", 290),
              ("base_peso", 340), ("grau", 400), ("topo_grau", 470), ("base_grau", 520)]
COL_CANHONEADOS = [("unidade", 0), ("topo", 240), ("base", 310), ("canhao", 370), ("densidade", 450)]
COL_COLUNA = [("equipamento", 0), ("od", 340), ("id", 440), ("topo", 510)]
COL_TESTE_COMPL = [("tipo", 0), ("abertura", 70), ("vazao", 115), ("pressao_montante", 170), ("rgo", 235),
                   ("bsw", 285), ("areia", 330), ("hc", 370), ("api", 400), ("dg", 440),
                   ("prof_vertical", 470), ("pressao_fluxo", 515)]
COL_FASES = [("fase", 0), ("diametro", 40), ("prof", 90), ("prof_vertical", 135), ("rev_diametro", 185),
             ("rev_prof", 235), ("rev_prof_vertical", 280), ("cimento_topo", 330), ("cimento_topo_vertical", 370),
             ("fluido", 415), ("peso_lb_gal", 530)]
COL_TEMPOS = [("fase", 0), ("diametro", 40), ("prof", 90), ("prof_vertical", 135), ("util_produtivo", 190),
              ("util_improdutivo", 250), ("perdido", 310), ("total", 360), ("absorcao_bbl", 420),
              ("peso_equivalente", 490)]
COL_INDICIOS_ND = [("topo", 0), ("base", 75), ("unidade", 125), ("tipo", 300), ("fluorescencia", 350),
                   ("corte", 400), ("gas_total", 450), ("gas_parcial", 520)]
COL_PERFIS_ND = [("topo", 0), ("base", 100), ("unidade", 165), ("litologia", 400)]
COL_TESTES_ND = [("tipo", 0), ("topo", 75), ("base", 130), ("vazao", 170), ("fluido", 320), ("api", 460),
                 ("deplecao", 515)]
COL_PERF_OPER = [("n", 0), ("data", 55), ("companhia", 110), ("operacao", 250), ("perfis", 315), ("topo", 470),
                 ("base", 525)]
COL_PERF_CONV = [("n", 0), ("data", 55), ("ambiente", 135), ("companhia", 180), ("perfis", 315), ("topo", 470),
                 ("base", 525)]
COL_PERF_ESP = [("n", 0), ("data", 55), ("ambiente", 130), ("companhia", 175), ("perfis", 295), ("topo", 455),
                ("base", 497), ("prof", 533)]
COL_PERF_RES = [("n", 0), ("perfis", 45), ("niveis_sismicos", 200), ("laterais_programadas", 255),
                ("laterais_recuperadas", 300), ("laterais_perdidas", 340), ("pretestes_conclusivos", 385),
                ("pretestes_falhos", 445), ("testes_conclusivos", 485), ("testes_falhos", 530)]
COL_NC = [("unidade", 0), ("de", 140), ("a", 185), ("de_vertical", 230), ("a_vertical", 275),
          ("peso_antes", 315), ("peso_depois", 355)]


def _n(ln, k):
    return numero(ln.get(k))


def _t(ln, k):
    v = _texto_celula(ln.get(k, ""))
    return v or None


def _par(medida, cota):
    """Profundidade e cota 0,0 juntas = linha vazia daquele lado."""
    return (None, None) if not medida and not cota else (medida, cota)


# ---------------------------------------------------------------- leitura de cada seção
def _topos(fs):
    saida = []
    for i, ln in enumerate(tabela(fs, COL_TOPOS, "prev_medida"), 1):
        pm, pc = _par(_n(ln, "prev_medida"), _n(ln, "prev_cota"))
        m, c = _par(_n(ln, "medida"), _n(ln, "cota"))
        if pm is None and m is None:
            continue
        saida.append({"ordem": i, "unidade": _t(ln, "unidade"), "prev_medida": pm, "prev_cota": pc,
                      "prof": m, "cota": c, "pagina": ln["_pagina"]})
    return saida


def _indicios(fs):
    return [{"topo": _n(ln, "topo"), "base": _n(ln, "base"), "unidade": _t(ln, "unidade"),
             "ocorrencia": _t(ln, "ocorrencia"), "tipo": _t(ln, "tipo"),
             "fluorescencia": _t(ln, "fluorescencia"), "corte": _t(ln, "corte"),
             "gas_total": _t(ln, "gas_total"), "gas_parcial": _t(ln, "gas_parcial"),
             "cromatografia": _t(ln, "cromatografia"), "pagina": ln["_pagina"]}
            for ln in tabela(fs, COL_INDICIOS, "topo")]


def _testemunhos(fs):
    return [{"ordem": _t(ln, "ordem"), "topo": _n(ln, "topo"), "base": _n(ln, "base"),
             "recuperacao_pct": _n(ln, "recuperacao"), "unidade": _t(ln, "unidade"),
             "litologia": _t(ln, "litologia"), "pagina": ln["_pagina"]}
            for ln in tabela(fs, COL_TESTEMUNHOS, "topo")]


def _laterais(fs):
    return [{"ordem": _t(ln, "ordem"), "prof": _n(ln, "prof"), "unidade": _t(ln, "unidade"),
             "litologia": _t(ln, "litologia"), "pagina": ln["_pagina"]}
            for ln in tabela(fs, COL_LATERAIS, "prof")]


def _analise(fs):
    return [{"topo": _n(ln, "topo"), "base": _nz(_n(ln, "base")), "unidade": _t(ln, "unidade"),
             "litologia": _t(ln, "litologia"), "pagina": ln["_pagina"]}
            for ln in tabela(fs, COL_ANALISE, "topo")]


def _testes(fs):
    saida = []
    for ln in tabela(fs, COL_TESTES, "topo"):
        topo, base = _n(ln, "topo"), _nz(_n(ln, "base"))
        saida.append({"tipo": _t(ln, "tipo"), "topo": topo, "base": base if base and base > (topo or 0) else None,
                      "vazao_m3_dia": _nz(_n(ln, "vazao")), "fluido": _t(ln, "fluido"),
                      "api": _nz(_n(ln, "api")), "deplecao_kgf_cm2": _nz(_n(ln, "deplecao")),
                      "pressao_estatica_kgf_cm2": _nz(_n(ln, "pressao")),
                      "prof_registrador": _nz(_n(ln, "prof_registrador")), "pagina": ln["_pagina"]})
    return saida


def _temperaturas(fs):
    saida = []
    for ln in tabela(fs, COL_TEMPERATURAS, "valor"):
        m, c = _par(_n(ln, "medida"), _n(ln, "cota"))
        tipo = (_t(ln, "tipo") or "").upper()
        saida.append({"valor": _n(ln, "valor"), "unidade": (_t(ln, "unidade") or "").upper() or None,
                      "prof": m, "cota": c,
                      "tipo": {"L": "lida", "E": "extrapolada"}.get(tipo, tipo or None),
                      "origem": _t(ln, "origem"), "pagina": ln["_pagina"]})
    return saida


def _calha(fs):
    return [{"topo": _n(ln, "topo"), "base": _n(ln, "base"), "padrao": _t(ln, "padrao"),
             "pagina": ln["_pagina"]} for ln in tabela(fs, COL_CALHA, "topo")]


def _revestimentos(fs):
    return [{"diametro": _t(ln, "diametro"), "topo": _n(ln, "topo"), "base": _n(ln, "base"),
             "peso_lb_pe": _n(ln, "peso"), "grau": _t(ln, "grau"), "pagina": ln["_pagina"]}
            for ln in tabela(fs, COL_REVEST, "topo")]


def _canhoneados(fs):
    return [{"unidade": _t(ln, "unidade"), "topo": _n(ln, "topo"), "base": _n(ln, "base"),
             "canhao": _t(ln, "canhao"), "densidade_tiros_pe": _n(ln, "densidade"), "pagina": ln["_pagina"]}
            for ln in tabela(fs, COL_CANHONEADOS, "topo")]


def _coluna_producao(fs):
    return [{"equipamento": _t(ln, "equipamento"), "od": _t(ln, "od"), "id": _n(ln, "id"),
             "topo": _n(ln, "topo"), "pagina": ln["_pagina"]} for ln in tabela(fs, COL_COLUNA, "topo")]


def _testes_completacao(fs):
    return [{"tipo": _t(ln, "tipo"), "abertura": _t(ln, "abertura"), "vazao_m3_dia": _n(ln, "vazao"),
             "pressao_montante_kgf_cm2": _nz(_n(ln, "pressao_montante")), "rgo_m3_m3": _nz(_n(ln, "rgo")),
             "bsw_pct": _n(ln, "bsw"), "areia_pct": _n(ln, "areia"), "hc": _t(ln, "hc"),
             "api": _nz(_n(ln, "api")), "densidade_gas": _nz(_n(ln, "dg")),
             "prof_vertical": _nz(_n(ln, "prof_vertical")), "pressao_fluxo_kgf_cm2": _nz(_n(ln, "pressao_fluxo")),
             "pagina": ln["_pagina"]} for ln in tabela(fs, COL_TESTE_COMPL, "vazao")]


def _fases(fs):
    saida = []
    for ln in tabela(fs, COL_FASES, "fase"):
        saida.append({"fase": int(_n(ln, "fase")), "diametro": _t(ln, "diametro"), "prof": _nz(_n(ln, "prof")),
                      "prof_vertical": _nz(_n(ln, "prof_vertical")), "rev_diametro": _t(ln, "rev_diametro"),
                      "rev_prof": _nz(_n(ln, "rev_prof")), "rev_prof_vertical": _nz(_n(ln, "rev_prof_vertical")),
                      "cimento_topo": _nz(_n(ln, "cimento_topo")), "fluido": _t(ln, "fluido"),
                      "peso_lb_gal": _nz(_n(ln, "peso_lb_gal")), "pagina": ln["_pagina"]})
    return saida


def _tempos(fs):
    return [{"fase": int(_n(ln, "fase")), "diametro": _t(ln, "diametro"), "prof": _nz(_n(ln, "prof")),
             "util_produtivo_d": _n(ln, "util_produtivo"), "util_improdutivo_d": _n(ln, "util_improdutivo"),
             "perdido_d": _n(ln, "perdido"), "total_d": _n(ln, "total"), "absorcao_bbl": _n(ln, "absorcao_bbl"),
             "peso_equivalente_lb_gal": _nz(_n(ln, "peso_equivalente")), "pagina": ln["_pagina"]}
            for ln in tabela(fs, COL_TEMPOS, "fase")]


def _nao_conformidades(fs):
    return [{"unidade": _t(ln, "unidade"), "de": _n(ln, "de"), "a": _n(ln, "a"),
             "peso_antes_lb_gal": _nz(_n(ln, "peso_antes")), "peso_depois_lb_gal": _nz(_n(ln, "peso_depois")),
             "pagina": ln["_pagina"]} for ln in tabela(fs, COL_NC, "de")]


def _sem_traco(v):
    return None if v in (None, "-", "—") else v


def _indicios_nd(fs):
    return [{"topo": _n(ln, "topo"), "base": _n(ln, "base"), "unidade": _t(ln, "unidade"),
             "ocorrencia": _sem_traco(_t(ln, "tipo")), "tipo": None,
             "fluorescencia": _sem_traco(_t(ln, "fluorescencia")), "corte": _sem_traco(_t(ln, "corte")),
             "gas_total": _sem_traco(_t(ln, "gas_total")), "gas_parcial": _sem_traco(_t(ln, "gas_parcial")),
             "cromatografia": None, "pagina": ln["_pagina"]}
            for ln in tabela(fs, COL_INDICIOS_ND, "topo")]


def _perfis_nd(fs):
    return [{"topo": _n(ln, "topo"), "base": _nz(_n(ln, "base")), "unidade": _t(ln, "unidade"),
             "litologia": _t(ln, "litologia"), "pagina": ln["_pagina"]}
            for ln in tabela(fs, COL_PERFIS_ND, "topo")]


def _testes_nd(fs):
    saida = []
    for ln in tabela(fs, COL_TESTES_ND, "topo"):
        topo, base = _n(ln, "topo"), _nz(_n(ln, "base"))
        saida.append({"tipo": _t(ln, "tipo"), "topo": topo, "base": base if base and base > (topo or 0) else None,
                      "vazao_m3_dia": _nz(_n(ln, "vazao")), "fluido": _t(ln, "fluido"), "api": _nz(_n(ln, "api")),
                      "deplecao_kgf_cm2": _nz(_n(ln, "deplecao")), "pressao_estatica_kgf_cm2": None,
                      "prof_registrador": None, "pagina": ln["_pagina"]})
    return saida


def _perfilagens(fs, colunas, tipo):
    saida = []
    for ln in tabela(fs, colunas, "n"):
        topo, base, prof = _nz(_n(ln, "topo")), _nz(_n(ln, "base")), _nz(_n(ln, "prof"))
        saida.append({"n": int(_n(ln, "n")), "tipo": tipo, "data": _t(ln, "data"), "ambiente": _t(ln, "ambiente"),
                      "companhia": _t(ln, "companhia"), "operacao": _t(ln, "operacao"), "perfis": _t(ln, "perfis"),
                      "topo": topo if topo is not None else prof, "base": base, "pagina": ln["_pagina"]})
    return saida


ROTULOS_DOC = {
    "nd": {"DATA DA DESCOBERTA": "data_descoberta", "DATA DA NOTIFICACAO": "data_notificacao",
           "FLUIDO(S)": "fluidos"},
    "npr": {"DATA DA CONCLUSAO DA PERFILAGEM FINAL": "conclusao_perfilagem",
            "OPERACAO FEITA DURANTE A REENTRADA": "durante_reentrada", "POCO PERFILADO": "perfilado"},
    "reentrada": {"N DA REENTRADA": "reentrada", "Nº DA REENTRADA": "reentrada", "DATA DA COMUNICACAO": "comunicacao",
                  "INICIO DA REENTRADA": "inicio", "FIM DA REENTRADA": "fim", "PROFUNDIDADE FINAL": "prof_final",
                  "SONDA:": "sonda", "LICENCA AMBIENTAL": "licenca_ambiental", "ESTADO ATUAL": "estado_atual"},
}


ROTULOS_GERAIS = {
    "POCO:": "poco", "BLOCO:": "bloco", "BACIA:": "bacia", "ESTADO:": "estado", "OPERADOR:": "operador",
    "N CONTRATO": "contrato", "Nº CONTRATO": "contrato", "CADASTRO DO POCO": "cadastro",
    "NOME POCO PARA O OPERADOR": "nome_operador",
    "DATA TERMINO DA PERFURACAO": "termino_perfuracao", "DATA CONCLUSAO": "conclusao",
    "PROFUNDIDADE FINAL DO SONDADOR": "prof_sondador",
    "UNIDADE ESTRATIGRAFICA": "unidade_prof_final",
    "PROFUNDIDADE FINAL POR PERFIL": "prof_perfil@1=medida,2=cota",
    "ELEVACAO BAP": "elevacao", "LAMINA D'AGUA": "lamina_agua", "MESA ROTATIVA": "mesa_rotativa",
    "COTA ALTIMETRICA": "elevacao",
    "INICIO DA COMPLETACAO": "inicio_completacao", "TERMINO DA COMPLETACAO": "termino_completacao",
    "UNIDADE COMPLETACAO": "sonda_completacao",
    "INICIO DA PERFURACAO": "inicio_perfuracao", "TERMINO DA PERFURACAO": "termino_perfuracao",
    "DATA DE REMESSA DA NOTIFICACAO": "data_notificacao",
    "DATA PREVISTA PARA INICIO DA PERFURACAO": "inicio_previsto",
    "SIGLA:": "sonda", "UNIDADE:": "sonda_unidade", "OPERADORA:": "sonda_operadora",
    "CATEGORIA DO POCO": "categoria", "TIPO DO POCO": "tipo_poco", "IDENTIFICACAO PAT/LOC": "pat_loc",
    "POCO DESCOBRIDOR DE CAMPO": "descobridor", "TIPO DE FLUIDO DESCOBERTO": "fluido_descoberto",
    "TIPO DE ABANDONO": "tipo_abandono", "RAZAO DO ABANDONO": "razao_abandono",
    "JUSTIFICATIVAS DO ABANDONO": "justificativa_abandono",
}
ROTULOS_PREVISTAS = {"MEDIDA (M)": "prof_prevista", "COTA (M)": "cota_prevista"}
_NUMERICOS = {"prof_sondador", "prof_perfil_medida", "prof_perfil_cota", "elevacao", "lamina_agua",
              "mesa_rotativa", "prof_prevista", "cota_prevista"}

_RE_SIGLA_EP = re.compile(r"SIGLA DO PO[CÇ]O NA BASE D[OA] E&P:\s*([0-9A-Z][0-9A-Z\-]+[A-Z])", re.I)


def apelidos(dados: dict) -> list[str]:
    """Outros nomes do poço que o formulário declara (sigla na base da operadora)."""
    vistos = []
    for m in _RE_SIGLA_EP.finditer(dados.get("observacoes") or ""):
        if m[1] not in vistos:
            vistos.append(m[1])
    nome_op = (dados.get("gerais") or {}).get("nome_operador")
    if nome_op and nome_op not in vistos:
        vistos.append(nome_op)
    return vistos


def ler_documento(doc) -> dict:
    """Lê um PDF já aberto (pymupdf.Document)."""
    frags = fragmentos(doc)
    if not frags:
        raise ErroRFP("O PDF não tem texto embutido (é imagem); este leitor não usa OCR.")
    titulos, s = faixas(frags)
    if not titulos:
        # formulário CDPE de outro tipo: o cabeçalho da ANP tem "CDPE" e o rodapé, a SDT
        topo = doc[0].get_text().upper()
        if "CDPE" not in topo or "SUPERINTEND" not in topo:
            raise ErroRFP("Não é um formulário CDPE da ANP.")
        titulos = ["cdpe"]
    documento = titulos[0]
    gerais = {}
    for nome in ("dados", "resultado", "sonda", "notificacao", "previstas", "inicio", "relatorio_perfuracao"):
        if nome in s:
            rot = ROTULOS_PREVISTAS if nome == "previstas" else ROTULOS_GERAIS
            for k, v in campos(s[nome], rot).items():
                gerais.setdefault(k, v)
    for k in list(gerais):
        if k in _NUMERICOS:
            gerais[k] = numero(gerais[k])
    if "coordenadas" in s:
        if documento == "perfuracao":
            grupos = [("base", 150), ("alvo", 340)]
        else:
            grupos = [("base", 0), ("alvo", 200), ("fundo", 390)]
        gerais["coordenadas"] = coordenadas(s["coordenadas"], grupos)
    if "coordenada_base" in s:
        cb = coordenadas(s["coordenada_base"], [("base", 0)])
        if cb:
            gerais.setdefault("coordenadas", {})["base_definitiva"] = cb["base"]
    leitores = {"topos": _topos, "indicios": _indicios, "testemunhos": _testemunhos, "laterais": _laterais,
                "analise_perfis": _analise, "testes": _testes, "temperaturas": _temperaturas, "calha": _calha,
                "revestimentos": _revestimentos, "canhoneados": _canhoneados, "coluna": _coluna_producao,
                "testes_completacao": _testes_completacao, "fases": _fases, "tempos": _tempos,
                "nao_conformidades": _nao_conformidades}
    dados = {"documento": documento, "titulo": DOCUMENTOS[documento], "paginas": doc.page_count,
             "gerais": gerais}
    if documento == "cdpe":     # título que o SIAPP não conhece: guarda o título e o texto
        dados["titulo_formulario"] = frags[0][2]
        dados["texto"] = _texto_corrido(frags)
    if documento in ROTULOS_DOC and "dados" in s:
        c = campos(s["dados"], ROTULOS_DOC[documento])
        if "prof_final" in c:
            c["prof_final"] = numero(c["prof_final"])
        dados["campos"] = c
    if documento in ("reentrada", "nd"):
        # campos que no RFP têm outro sentido não entram nos gerais desses formulários
        for k in ("termino_perfuracao", "inicio_perfuracao", "prof_sondador", "sonda"):
            gerais.pop(k, None)
    textos = {"estado_atual": "Estado atual do poço", "motivo": "Motivo da reentrada",
              "operacoes_previstas": "Operações previstas", "resultado_reentrada": "Resultado",
              "dados_adquiridos": "Dados adquiridos"}
    partes = [(rot, _texto_corrido(s[k])) for k, rot in textos.items() if k in s]
    if any(t for _, t in partes):
        dados["secoes_texto"] = [{"titulo": rot, "texto": t} for rot, t in partes if t]
    if "indicios_nd" in s:
        dados["indicios"] = _indicios_nd(s["indicios_nd"])
    if "perfis_nd" in s:
        dados["analise_perfis"] = _perfis_nd(s["perfis_nd"])
    if "testes_nd" in s:
        dados["testes"] = _testes_nd(s["testes_nd"])
    perf = []
    for k, col, tipo in (("perf_operacoes", COL_PERF_OPER, "durante a perfuração"),
                         ("perf_convencionais", COL_PERF_CONV, "convencional"),
                         ("perf_especiais", COL_PERF_ESP, "especial")):
        if k in s:
            perf += _perfilagens(s[k], col, tipo)
    if perf:
        dados["perfilagens"] = perf
    if "perf_resultado" in s:
        dados["perfilagens_resultado"] = [
            {"n": int(_n(ln, "n")), "perfis": _t(ln, "perfis"),
             **{c: _n(ln, c) for c, _ in COL_PERF_RES[2:] if _n(ln, c)}, "pagina": ln["_pagina"]}
            for ln in tabela(s["perf_resultado"], COL_PERF_RES, "n")]
    for nome, f in leitores.items():
        if nome in s:
            dados[nome] = f(s[nome])
    if "observacoes" in s:
        dados["observacoes"] = _texto_corrido(s["observacoes"])
    dados["apelidos"] = apelidos(dados)
    return dados


def ler(caminho: str) -> dict:
    import pymupdf
    try:
        doc = pymupdf.open(caminho)
    except Exception as e:  # noqa: BLE001 — PDF corrompido
        raise ErroRFP(f"Não consegui abrir o PDF: {e}") from e
    with doc:
        return ler_documento(doc)


# ---------------------------------------------------------------- itens para o banco
def itens(dados: dict) -> list[dict]:
    """Uma linha por dado com profundidade (tabela dados_poco). Campos: tipo, nome,
    prof_topo, prof_base, cota, valor, unidade, texto, extra (dict), pagina."""
    saida = []

    def add(tipo, **kw):
        kw.setdefault("extra", {})
        saida.append({"tipo": tipo, **kw})

    for t in dados.get("topos", []):
        if t["prof"] is None:
            continue
        add("topo", nome=t["unidade"], prof_topo=t["prof"], cota=t["cota"], pagina=t["pagina"],
            extra={"ordem": t["ordem"], "prev_medida": t["prev_medida"], "prev_cota": t["prev_cota"]})
    for i in dados.get("indicios", []):
        add("indicio", nome=i["unidade"], prof_topo=i["topo"], prof_base=i["base"], pagina=i["pagina"],
            texto=" · ".join(x for x in (i["ocorrencia"], i["tipo"], i["fluorescencia"], i["corte"],
                                         i["gas_total"]) if x) or None,
            extra={k: i[k] for k in ("ocorrencia", "tipo", "fluorescencia", "corte", "gas_total",
                                     "gas_parcial", "cromatografia")})
    for t in dados.get("testemunhos", []):
        add("testemunho", nome=t["unidade"], prof_topo=t["topo"], prof_base=t["base"], valor=t["recuperacao_pct"],
            unidade="%", texto=t["litologia"], pagina=t["pagina"], extra={"ordem": t["ordem"]})
    for a in dados.get("laterais", []):
        add("amostra_lateral", nome=a["unidade"], prof_topo=a["prof"], texto=a["litologia"], pagina=a["pagina"],
            extra={"ordem": a["ordem"]})
    for a in dados.get("analise_perfis", []):
        add("analise_perfil", nome=a["unidade"], prof_topo=a["topo"], prof_base=a["base"], texto=a["litologia"],
            pagina=a["pagina"])
    for t in dados.get("testes", []):
        add("teste_formacao", nome=t["tipo"], prof_topo=t["topo"], prof_base=t["base"],
            valor=t["pressao_estatica_kgf_cm2"], unidade="kgf/cm²", texto=t["fluido"], pagina=t["pagina"],
            extra={k: t[k] for k in ("vazao_m3_dia", "api", "deplecao_kgf_cm2", "prof_registrador")})
    for t in dados.get("temperaturas", []):
        if t["valor"] is None:
            continue
        add("temperatura", nome=t["origem"], prof_topo=t["prof"], cota=t["cota"], valor=t["valor"],
            unidade="°F" if t["unidade"] == "F" else ("°C" if t["unidade"] == "C" else t["unidade"]),
            texto=t["tipo"], pagina=t["pagina"])
    for c in dados.get("calha", []):
        add("calha", nome=None, prof_topo=c["topo"], prof_base=c["base"], texto=c["padrao"], pagina=c["pagina"])
    for r in dados.get("revestimentos", []):
        add("revestimento", nome=r["diametro"], prof_topo=r["topo"], prof_base=r["base"], valor=r["peso_lb_pe"],
            unidade="lb/pé", texto=r["grau"], pagina=r["pagina"])
    for c in dados.get("canhoneados", []):
        add("canhoneado", nome=c["unidade"], prof_topo=c["topo"], prof_base=c["base"],
            valor=c["densidade_tiros_pe"], unidade="tiros/pé", texto=c["canhao"], pagina=c["pagina"])
    for t in dados.get("testes_completacao", []):
        add("teste_completacao", nome=t["tipo"], prof_topo=t["prof_vertical"], valor=t["vazao_m3_dia"],
            unidade="m³/dia", texto=t["hc"], pagina=t["pagina"],
            extra={k: t[k] for k in ("abertura", "pressao_montante_kgf_cm2", "rgo_m3_m3", "bsw_pct", "areia_pct",
                                     "api", "densidade_gas", "pressao_fluxo_kgf_cm2")})
    for f in dados.get("fases", []):
        add("fase", nome=f"fase {f['fase']}" + (f" ({f['diametro']}\")" if f["diametro"] else ""),
            prof_topo=None, prof_base=f["prof"], valor=f["peso_lb_gal"], unidade="lb/gal" if f["peso_lb_gal"] else None,
            texto=f["fluido"], pagina=f["pagina"],
            extra={k: f[k] for k in ("fase", "diametro", "rev_diametro", "rev_prof", "cimento_topo", "prof_vertical")})
    for p in dados.get("perfilagens", []):
        add("perfilagem", nome=p["perfis"], prof_topo=p["topo"], prof_base=p["base"], texto=p["companhia"],
            pagina=p["pagina"], extra={k: p[k] for k in ("n", "tipo", "data", "ambiente", "operacao")})
    for n in dados.get("nao_conformidades", []):
        add("nao_conformidade", nome=n["unidade"], prof_topo=n["de"], prof_base=n["a"],
            valor=n["peso_depois_lb_gal"], unidade="lb/gal", pagina=n["pagina"],
            extra={"peso_antes_lb_gal": n["peso_antes_lb_gal"]})
    return saida
