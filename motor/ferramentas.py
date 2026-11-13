"""Esquemas de ferramentas (tool strings) do acervo REATE.

Cada corrida de perfilagem tem, na pasta "Esquema de Ferramentas" do poço, um PDF com
a coluna de ferramentas descida no poço: na Potiguar são 5.220 esquemas em 2.935 poços
(levantamento de 16/10/2026). O SIAPP usa esses esquemas para dizer **o que é cada
arquivo de perfil** do poço — perfilagem convencional, teste de formação a cabo,
imagem, ressonância… — e com quais ferramentas foi corrido.

Duas fontes, da mais barata para a mais cara:

1. **O nome do arquivo** (sem baixar nada): `7-cam-1130-rn_raw.pdf`, `..._sft_1_toolstring.pdf`,
   `..._rft1_esqfer.pdf`. O nome do esquema e o do perfil seguem o mesmo padrão, e é
   assim que um se liga ao outro (`raw1` ↔ `raw1-10028.dlis`, `RFT_tool` ↔ `RFT1..8.DLIS`,
   `AIT_tool` ↔ `AIT_P.DLIS` e `AIT_R.DLIS`).
2. **O conteúdo do PDF**: o texto embutido, quando há (desenho vetorial), ou OCR da
   imagem — a maioria é uma página escaneada, muitas vezes em baixa resolução
   (768 × 793 px). Dele saem os códigos das ferramentas (HILTB-FTB, DSLT-H, XPT-BA,
   FTT-CA…), o carimbo (data, poço, cadastro, operadora) e o diâmetro máximo da coluna.

O OCR erra letras parecidas (O/D, B/E, I/L) nos códigos pequenos; por isso cada código
lido é comparado com o dicionário de recursos/ferramentas.json tolerando essas trocas.
Só entra na lista o que bate com o dicionário — nada é inventado. Conferido em
16/10/2026 em 13 esquemas reais da Potiguar (Schlumberger, Tucker; 1 vetorial, 1 girado).
"""

from __future__ import annotations

import json
import os
import re

import numpy as np
import pymupdf

from .banco import Banco, agora
from .pocos import chave
from .texto import sem_acento as _sem_acento

VERSAO_LEITOR = 1
IDIOMA_OCR = "eng"          # os esquemas estão em inglês; o modelo inglês lê melhor os códigos
# O modelo "fast" do inglês (4 MB) leu mais códigos que o "best" (15 MB) e 6× mais rápido
# (13 esquemas reais, 16/10/2026): ~2 s por esquema
MODELOS_OCR = ("https://github.com/tesseract-ocr/tessdata_fast/raw/main/{idioma}.traineddata",
               "https://github.com/tesseract-ocr/tessdata/raw/main/{idioma}.traineddata")
EXTENSOES = (".pdf", ".tif", ".tiff", ".png", ".jpg", ".jpeg")
MAX_BYTES = 15 * 1024 * 1024    # maior que isso não é um esquema (é perfil em PDF: há de 86 MB)
MAX_PAGINAS = 4
MIN_TEXTO_EMBUTIDO = 40
RE_PASTA = re.compile(r"esquema|esq_?fer|tool", re.IGNORECASE)

# Palavras do nome que não dizem nada sobre a corrida
RUIDO_NOME = {"toolstring", "tool", "tools", "string", "strings", "esq", "esqfer", "esquema", "ferramentas",
              "ferramenta", "schematic", "diagram", "pub", "final", "field", "formato", "run",
              "de", "do", "da", "rn", "ce", "pdf", "dlis", "lis", "las", "tif", "tiff"}
# Palavras fracas: aparecem em quase toda corrida e sozinhas não ligam esquema a perfil
FRACAS = {"gr", "sp", "cal", "run"}
PASSADA = {"p": "principal", "main": "principal", "principal": "principal", "prin": "principal",
           "r": "repetida", "rep": "repetida", "repeat": "repetida", "repetida": "repetida"}
# Prioridade do tipo da corrida: o serviço especial manda (uma corrida de testador
# também leva raios gama, mas é corrida de testador)
ORDEM_TIPO = ("testador", "rmn", "imagem", "amostrador", "mergulho", "sismica", "cimentacao", "lwd")   # sismica: 0.63
FAMILIAS_CONVENCIONAL = {"inducao", "laterolog", "densidade", "neutron", "sonico", "micro"}

_RE_POCO_NO_NOME = re.compile(r"(?:^|(?<=[\W_]))\d[\W_]*[a-z]{1,6}[\W_]*\d{1,5}[a-z]{0,2}[\W_]*[a-z]{2}(?=[\W_]|$)")
_RE_POCO_NO_TEXTO = re.compile(r"\b\d\s*-\s*[A-Z]{1,6}\s*-\s*\d{1,5}[A-Z]{0,2}\s*-\s*[A-Z]{2}\b")
_RE_CODIGO = re.compile(r"(?<![A-Z0-9])([A-Z$][A-Z0-9$]{1,6})(-[A-Z0-9]{1,5})?(?![A-Z0-9])")
_RE_SUPERFICIE = re.compile(r"SURFACE\s+EQUIPMENT.*?(?=DOWNHOLE\s+EQUIPMENT)", re.IGNORECASE | re.DOTALL)
_LINHA_CARIMBO = re.compile(r"PO[CÇ]O|OPERADOR|CADASTRO|COMPANHIA|LOCACAO|APIN?\s*:", re.IGNORECASE)

# Trocas típicas do OCR em códigos de ferramenta: cada grupo vira um só símbolo
_CLASSE = str.maketrans({"0": "O", "D": "O", "Q": "O", "1": "I", "L": "I", "J": "I", "|": "I",
                         "E": "B", "8": "B", "5": "S", "$": "S", "6": "C", "G": "C", "2": "Z",
                         "V": "U", "¥": "U"})


class ErroEsquema(Exception):
    """Falha legível para o usuário."""


# ============================================================ dicionário
def ler_dicionario(caminho: str) -> dict:
    with open(caminho, encoding="utf-8") as f:
        d = json.load(f)
    d["_ferramentas"] = [{**fe, "_classe": _classe(fe["codigo"])} for fe in d.get("ferramentas", [])]
    d["_palavras"] = [(re.compile(p["padrao"], re.IGNORECASE), p["familia"]) for p in d.get("palavras", [])]
    d["_fabricantes"] = [(re.compile(p["padrao"], re.IGNORECASE), p["nome"]) for p in d.get("fabricantes", [])]
    return d


def _classe(s: str) -> str:
    return s.upper().translate(_CLASSE)


def eh_esquema(nome: str, pasta: str = "") -> bool:
    return bool(RE_PASTA.search(pasta or "")) and os.path.splitext(nome or "")[1].lower() in EXTENSOES


# ======================================================== nome do arquivo
def ler_nome(nome: str, dic: dict, pasta: str = "") -> dict:
    """O que o nome do arquivo diz da corrida (vale para esquema e para perfil).

    {"tokens": palavras que identificam a corrida, "servicos": as do dicionário,
     "tipo": tipo de corrida pelo nome, "corrida": nº, "passada": principal|repetida,
     "fase": diâmetro da broca em polegadas (875 -> 8.75)}"""
    base = os.path.splitext(os.path.basename(nome or ""))[0].lower()
    base = _RE_POCO_NO_NOME.sub(" ", base)          # o nome do poço, onde estiver (às vezes duas vezes)
    brutos = [t for t in re.split(r"[^a-z0-9]+", base) if t]
    tokens, corrida, passada, fase, run_explicito = [], None, None, None, None
    for i, t in enumerate(brutos):
        if t in PASSADA:                           # AIT_P / AIT_R: só a palavra inteira
            passada = PASSADA[t]
            continue
        partes = re.findall(r"[a-z]+|\d+", t)
        for k, p in enumerate(partes):
            if p.isdigit():
                if len(p) >= 5:                    # código do upload no portal (raw1-10028)
                    continue
                if len(p) >= 3:                    # fase: 875 = 8 ¾", 1225 = 12 ¼"
                    v = int(p) / 100
                    if 3 <= v <= 30:
                        fase = v
                    continue
                anterior = partes[k - 1] if k else (brutos[i - 1] if i else "")
                if anterior == "run":
                    run_explicito = int(p)
                elif corrida is None:
                    corrida = int(p)
            elif p not in RUIDO_NOME:
                tokens.append(p)
    servicos = [t for t in tokens if t in dic.get("nomes_arquivo", {})]
    tipo = None
    tipos = [dic["nomes_arquivo"][s] for s in servicos]
    for t in ORDEM_TIPO:
        if t in tipos:
            tipo = t
            break
    if tipo is None and tipos:
        # 'cbl_gr_ccl' = cimentação; 'raw' ou 'ait' + 'sdt' (vários serviços) = convencional
        tipo = "convencional" if "convencional" in tipos or len(set(tipos)) > 1 else tipos[0]
    if tipo is None and pasta:
        tipo = dic.get("pastas", {}).get(_sem_acento(pasta).lower().strip())
    return {"tokens": tokens, "servicos": servicos, "tipo": tipo,
            "corrida": run_explicito if run_explicito is not None else corrida,
            "passada": passada, "fase": fase}


# ================================================================ conteúdo
def _rgb(cinza: np.ndarray) -> pymupdf.Pixmap:
    # o OCR do PyMuPDF devolve texto vazio, sem erro, com imagem em tons de cinza
    h, w = cinza.shape
    pix = pymupdf.Pixmap(pymupdf.csRGB, w, h, np.repeat(cinza[:, :, None], 3, axis=2).tobytes(), False)
    pix.set_dpi(300, 300)
    return pix


def _dpi_nativo(page: pymupdf.Page) -> float | None:
    """Resolução da maior imagem da página (pontos por polegada como desenhada)."""
    melhor = None
    for info in page.get_image_info():
        w_pt = (info["bbox"][2] - info["bbox"][0]) or 1
        dpi = info["width"] / (w_pt / 72)
        if melhor is None or info["width"] * info["height"] > melhor[0]:
            melhor = (info["width"] * info["height"], dpi)
    return melhor[1] if melhor else None


def _imagem_ocr(page: pymupdf.Page, rotacao: int = 0) -> pymupdf.Pixmap:
    """Página pronta para o OCR. Imagem de baixa resolução (≤ 150 dpi) é ampliada 2×:
    nos esquemas de 768 px de largura, ampliar 2× quase dobrou os códigos lidos;
    mais que isso, ou binarizar, piorou (testado em 16/10/2026)."""
    nativo = _dpi_nativo(page)
    if nativo is None:
        dpi = 300                                   # desenho vetorial sem texto
    elif nativo <= 150:
        dpi = 2 * nativo
    else:
        dpi = min(nativo, 300)
    m = pymupdf.Matrix(dpi / 72, dpi / 72).prerotate(rotacao)
    pix = page.get_pixmap(matrix=m, colorspace=pymupdf.csGRAY, alpha=False)
    return _rgb(np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width))


def _ocr(pix: pymupdf.Pixmap, tessdata: str, idioma: str) -> str:
    doc = pymupdf.open("pdf", pix.pdfocr_tobytes(language=idioma, tessdata=tessdata))
    return doc[0].get_text()


def idioma_disponivel(tessdata: str, idioma: str = IDIOMA_OCR) -> bool:
    f = os.path.join(tessdata or "", f"{idioma}.traineddata")
    return os.path.isfile(f) and os.path.getsize(f) > 1_000_000


def _qualidade(texto: str, dic: dict) -> int:
    """Quanto o texto parece um esquema lido direito (para escolher a rotação)."""
    a = analisar_texto(texto, dic)
    extras = len(re.findall(r"EQUIPMENT|TOOL|ZERO|LENGTH|DIAMETER|MEASURE", texto, re.IGNORECASE))
    return 3 * len(a["ferramentas"]) + 2 * len(a["familias"]) + extras


def extrair_texto(caminho: str, dic: dict, tessdata: str | None, idioma: str = IDIOMA_OCR) -> tuple[str, str]:
    """(texto, método): "embutido", "ocr" ou "embutido+ocr". Sem o modelo do OCR,
    devolve só o texto embutido (pode ser vazio)."""
    try:
        doc = pymupdf.open(caminho)
    except Exception as e:  # noqa: BLE001 — PDF corrompido etc.
        raise ErroEsquema(f"Não foi possível abrir {os.path.basename(caminho)}: {e}") from e
    if doc.needs_pass:
        raise ErroEsquema(f"{os.path.basename(caminho)} é protegido por senha.")
    if not doc.is_pdf:                               # TIF/PNG/JPG: abre como documento de imagem
        doc = pymupdf.open("pdf", doc.convert_to_pdf())
    textos, metodos = [], set()
    for page in list(doc)[:MAX_PAGINAS]:
        embutido = page.get_text()
        rico = len(embutido.strip()) >= MIN_TEXTO_EMBUTIDO and len(analisar_texto(embutido, dic)["ferramentas"]) >= 2
        tem_imagem = bool(page.get_image_info())
        if rico or not (tessdata and idioma_disponivel(tessdata, idioma)) or (not tem_imagem and embutido.strip()):
            if embutido.strip():
                textos.append(embutido)
                metodos.add("embutido")
            continue
        melhor, nota = "", -1
        for rot in (0, 90, 270):
            t = _ocr(_imagem_ocr(page, rot), tessdata, idioma)
            q = _qualidade(t, dic)
            if q > nota:
                melhor, nota = t, q
            if nota >= 6:                            # leu direito: não precisa girar
                break
        if embutido.strip():                         # carimbo digital sobre a imagem escaneada
            textos.append(embutido)
            metodos.add("embutido")
        textos.append(melhor)
        metodos.add("ocr")
    metodo = "+".join(m for m in ("embutido", "ocr") if m in metodos) or "vazio"
    return "\n".join(textos), metodo


def _sem_carimbo(texto: str) -> str:
    """Tira as linhas do carimbo e os nomes de poço ('1-STAR-11-RN' não é a ferramenta STAR)
    e o equipamento de superfície dos esquemas da Schlumberger (NCT-B não é a NGT)."""
    texto = _RE_SUPERFICIE.sub("\n", texto)
    linhas = [ln for ln in texto.splitlines() if not _LINHA_CARIMBO.search(ln)]
    return _RE_POCO_NO_TEXTO.sub(" ", "\n".join(linhas))


def _distancia1(a: str, b: str) -> bool:
    """Distância de edição ≤ 1."""
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b)) <= 1
    if len(a) > len(b):
        a, b = b, a
    return any(b[:i] + b[i + 1:] == a for i in range(len(b)))


def reconhecer_codigo(token: str, sufixo: bool, dic: dict) -> dict | None:
    """O verbete do dicionário que corresponde a um código lido (ou None).

    - igual, tolerando as trocas típicas do OCR (OTC-H = DTC-H, HILTE = HILTB);
    - com uma letra a mais no fim, se tiver sufixo de peça (HGNSD-B = HGNS);
    - com uma letra errada, se tiver ≥ 5 letras e sufixo de peça."""
    c = _classe(token)
    fs = dic["_ferramentas"]
    for fe in fs:                     # grafia exata primeiro: NCT-B (superfície) não é NGT-D
        if fe["codigo"] == token.upper():
            return fe
    for fe in fs:
        if fe["_classe"] == c:
            return fe
    if not sufixo:
        return None
    candidatos = [fe for fe in fs if len(fe["_classe"]) >= 3 and c.startswith(fe["_classe"])
                  and len(c) - len(fe["_classe"]) <= 1]
    if candidatos:
        return max(candidatos, key=lambda fe: len(fe["_classe"]))
    if len(c) >= 5:
        for fe in fs:
            if len(fe["_classe"]) >= 5 and _distancia1(c, fe["_classe"]):
                return fe
    return None


def _numero(s: str) -> float | None:
    try:
        return float(s.replace(",", "."))
    except (TypeError, ValueError):
        return None


def carimbo(texto: str) -> dict:
    """Data, poço, cadastro e operadora do carimbo (Petrobras ou da empresa de perfilagem)."""
    out = {}
    m = (re.search(r"DATA\s*[:.]?\s*(\d{1,2})\s*/\s*(\d{1,2})\s*/\s*((?:19|20)\d\d)", texto, re.IGNORECASE)
         or re.search(r"\b(\d{2})/(\d{2})/((?:19|20)\d\d)\b", texto))
    if m and 1 <= int(m.group(1)) <= 31 and 1 <= int(m.group(2)) <= 12:
        out["data"] = f"{int(m.group(1)):02d}/{int(m.group(2)):02d}/{m.group(3)}"
    m = re.search(r"PO[CÇ]O\s*[:.]\s*(\d\s*-\s*[A-Z]{1,6}\s*[-.]\s*\d{1,5}[A-Z]{0,2}\s*-\s*[A-Z]{2})\b", texto,
                  re.IGNORECASE)
    if m:
        out["poco"] = re.sub(r"\s+", "", m.group(1)).replace(".", "-").upper()
    m = re.search(r"(?:CADASTRO|APIN?)\s*[:.]?\s*(\d{8,14})", texto, re.IGNORECASE)
    if m:
        out["cadastro"] = m.group(1)
    m = re.search(r"(?:OPERADORA?|COMPANHIA)\s*[:.]\s*([A-Z][A-Z0-9&.-]{2,30})", texto, re.IGNORECASE)
    if m:
        out["operadora"] = m.group(1).upper()
    return out


def analisar_texto(texto: str, dic: dict) -> dict:
    """Ferramentas, famílias, fabricante e medidas que o texto do esquema traz."""
    limpo = _sem_carimbo(texto or "").upper()
    vistos, ferramentas = set(), []
    for m in _RE_CODIGO.finditer(limpo):
        fe = reconhecer_codigo(m.group(1), bool(m.group(2)), dic)
        if fe and fe.get("superficie"):
            continue
        if fe and fe["codigo"] not in vistos:
            vistos.add(fe["codigo"])
            ferramentas.append({"codigo": fe["codigo"], "lido": m.group(0), "nome": fe["nome"],
                                "fabricante": fe.get("fabricante", ""), "familias": fe.get("familias", []),
                                "apoio": bool(fe.get("apoio"))})
    familias = []
    for fe in ferramentas:
        for f in fe["familias"]:
            if f not in familias:
                familias.append(f)
    for rx, f in dic["_palavras"]:
        if f not in familias and rx.search(texto or ""):
            familias.append(f)
    fabricante = next((nome for rx, nome in dic["_fabricantes"] if rx.search(texto or "")), "")
    if not fabricante:
        cont: dict[str, int] = {}
        for fe in ferramentas:
            if fe["fabricante"] and not fe["apoio"]:
                cont[fe["fabricante"]] = cont.get(fe["fabricante"], 0) + 1
        fabricante = max(cont, key=cont.get) if cont else ""
    medidas = {}
    m = re.search(r"MAXIMUM\s+STRING\s+DIAMETER\s+([\d.,]+)\s*IN", texto or "", re.IGNORECASE)
    if m and _numero(m.group(1)):
        medidas["diametro_max_pol"] = _numero(m.group(1))
    m = re.search(r"Maximum\s+Outside\s+diameter\s*-?\s*([\d.,]+)\s*\(?mm", texto or "", re.IGNORECASE)
    if m and _numero(m.group(1)) and "diametro_max_pol" not in medidas:
        medidas["diametro_max_pol"] = round(_numero(m.group(1)) / 25.4, 2)
    m = re.search(r"Total\s+Tool\s+Length\s*-?\s*([\d.,]+)\s*\(?M\b", texto or "", re.IGNORECASE)
    if m and _numero(m.group(1)):
        medidas["comprimento_m"] = _numero(m.group(1))
    m = re.search(r"FASE\s*[:.]\s*([\d.,]+)\s*IN", texto or "", re.IGNORECASE)
    if m and _numero(m.group(1)):
        medidas["fase_pol"] = _numero(m.group(1))
    return {"ferramentas": ferramentas, "familias": familias, "fabricante": fabricante, **medidas}


def tipo_pelas_familias(familias: list[str]) -> str | None:
    fs = set(familias)
    for t in ORDEM_TIPO:
        if t in fs:
            return t
    conv = fs & FAMILIAS_CONVENCIONAL
    if len(conv) >= 2:
        return "convencional"
    if conv & {"inducao", "laterolog", "micro"}:
        return "resistividade"
    if conv == {"sonico"}:
        return "sonico"
    if conv:
        return "convencional"
    if fs & {"gr", "gr_espectral", "ccl"}:
        return "correlacao"
    return None


def ler_esquema(caminho: str, nome: str, dic: dict, *, poco_id: str = "", pasta: str = "",
                tessdata: str | None = None, idioma: str = IDIOMA_OCR) -> dict:
    """Tudo o que o SIAPP tira de um esquema: nome + conteúdo."""
    pelo_nome = ler_nome(nome, dic, pasta)
    texto, metodo = extrair_texto(caminho, dic, tessdata, idioma)
    a = analisar_texto(texto, dic)
    c = carimbo(texto)
    if c.get("poco") and poco_id:
        c["confere"] = chave(c["poco"]) == chave(poco_id)
    tipo_conteudo = tipo_pelas_familias(a["familias"])
    aviso = ""
    if metodo == "vazio":
        aviso = ("Sem texto embutido e sem o modelo de OCR em inglês: só o nome do arquivo foi usado."
                 if not (tessdata and idioma_disponivel(tessdata, idioma)) else "Página sem texto legível.")
    elif not a["ferramentas"] and not a["familias"]:
        aviso = "Nenhuma ferramenta conhecida reconhecida (imagem ilegível ou fora do dicionário)."
    return {"nome": nome, "metodo": metodo, "pelo_nome": pelo_nome,
            "tipo": tipo_conteudo or pelo_nome["tipo"], "tipo_conteudo": tipo_conteudo,
            "carimbo": c, **a, "aviso": aviso, "caracteres": len(texto.strip())}


# ================================================================ vínculos
def _compativel(a, b) -> bool:
    return a is None or b is None or a == b


def combina(esq: dict, perfil: dict) -> bool:
    """O esquema (ler_nome) descreve o arquivo de perfil (ler_nome)?"""
    fortes = (set(esq["tokens"]) & set(perfil["tokens"])) - FRACAS
    return bool(fortes) and _compativel(esq["corrida"], perfil["corrida"]) and _compativel(esq["fase"], perfil["fase"])


def _semelhanca(a: dict, b: dict) -> float:
    ta, tb = set(a["tokens"]), set(b["tokens"])
    n = len(ta & tb) / (len(ta | tb) or 1)
    if a["corrida"] is not None and a["corrida"] == b["corrida"]:
        n += 0.5
    return n


def vincular(esquemas: list[dict], perfis: list[dict], dic: dict) -> dict[str, list[str]]:
    """{nome do esquema: [nomes dos perfis]} de um poço.

    `esquemas`: [{"nome", "pasta", "tipo" (lido do conteúdo, opcional)}];
    `perfis`: [{"nome", "pasta"}]. Liga pelo nome (as mesmas palavras e o mesmo nº de
    corrida); um esquema sem serviço no nome (`7et1585rn_esq.pdf`) se liga pelo tipo
    lido no conteúdo, se for o único esquema desse tipo no poço."""
    nomes_p = {p["nome"]: ler_nome(p["nome"], dic, p.get("pasta", "")) for p in perfis}
    nomes_e = {e["nome"]: ler_nome(e["nome"], dic) for e in esquemas}
    saida: dict[str, list[str]] = {e["nome"]: [] for e in esquemas}
    for p, np_ in nomes_p.items():
        # cada perfil vai para o(s) esquema(s) de nome mais parecido: raw2.dlis com
        # raw2_toolstring, e não com raw2_fmi-gpit_toolstring
        notas = {e: _semelhanca(ne, np_) for e, ne in nomes_e.items() if combina(ne, np_)}
        if notas:
            melhor = max(notas.values())
            for e, n in notas.items():
                if n == melhor:
                    saida[e].append(p)
    # 2ª passada, para o que o nome não ligou: pelo tipo da corrida, quando só um
    # esquema do poço é desse tipo (CONV_PRIN.DLIS com RAW_ToolString.pdf), ou quando
    # o poço tem um esquema só e o perfil não diz nada no nome (7_ARG_640_RN.lis)
    tipo_e = {e["nome"]: _grupo(e.get("tipo") or nomes_e[e["nome"]]["tipo"]) for e in esquemas}
    ligados = {p for lst in saida.values() for p in lst}
    for p, np_ in nomes_p.items():
        if p in ligados:
            continue
        t = _grupo(np_["tipo"])
        if t:
            mesmos = [e for e, te in tipo_e.items() if te == t]
            if len(mesmos) == 1:
                saida[mesmos[0]].append(p)
        elif len(esquemas) == 1 and not (set(np_["tokens"]) - FRACAS):
            saida[esquemas[0]["nome"]].append(p)
    return saida


def _grupo(tipo: str | None) -> str | None:
    """Resistividade e sônico avulsos contam como perfilagem convencional ao ligar."""
    return "convencional" if tipo in ("resistividade", "sonico") else tipo


def rotulo(tipo: str | None, dic: dict, *, corrida=None, passada=None, fase=None) -> str:
    partes = [dic.get("tipos", {}).get(tipo, "") if tipo else ""]
    if corrida is not None:
        partes.append(f"corrida {corrida}")
    if passada:
        partes.append(f"passada {passada}")
    if fase:
        partes.append(f"fase {fase:g}\"".replace(".", ","))
    return " · ".join(p for p in partes if p)


# =================================================================== banco
def caminho_local(pasta_projeto: str, bacia: str, poco: str, nome: str) -> str:
    seguro = lambda s: re.sub(r"[^\w .-]+", "_", s or "sem_poco")  # noqa: E731
    return os.path.join(pasta_projeto, "esquemas", seguro(bacia), seguro(poco), os.path.basename(nome))


def gravar(banco: Banco, *, bacia: str, caminho: str, poco_caminho: str, poco_id: str, nome: str,
           tamanho: int, arquivo_local: str = "", dados: dict | None = None, erro: str = "") -> None:
    with banco.conexao() as c:
        c.execute("""INSERT OR REPLACE INTO esquemas (bacia, caminho, poco_caminho, poco_id, nome, tamanho,
                         arquivo_local, leitor, metodo, tipo, dados, erro, lido_em)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                  (bacia, caminho, poco_caminho, poco_id, nome, tamanho, arquivo_local, VERSAO_LEITOR,
                   (dados or {}).get("metodo"), (dados or {}).get("tipo"),
                   json.dumps(dados, ensure_ascii=False) if dados else None, erro or None, agora()))


def lidos_do_poco(banco: Banco, poco_id: str) -> dict[str, dict]:
    """{caminho no portal: linha da tabela esquemas, com os dados lidos}."""
    with banco.conexao() as c:
        linhas = [dict(r) for r in c.execute("SELECT * FROM esquemas WHERE poco_id = ?", (poco_id,))]
    for r in linhas:
        r["dados"] = json.loads(r["dados"]) if r["dados"] else None
    return {r["caminho"]: r for r in linhas}


def arquivos_do_poco(banco: Banco, poco_id: str) -> list[dict]:
    """Todos os arquivos do poço no acervo levantado (esquemas e perfis)."""
    with banco.conexao() as c:
        return [dict(r) for r in c.execute(
            """SELECT a.bacia, a.caminho, a.poco_caminho, a.nome, a.pasta, a.ext, a.tamanho, a.candidato,
                      a.formato, p.poco_id
               FROM acervo_arquivos a JOIN acervo_pocos p ON p.bacia = a.bacia AND p.caminho = a.poco_caminho
               WHERE p.poco_id = ? ORDER BY a.caminho""", (poco_id,))]


def _eh_perfil(a: dict) -> bool:
    return bool(a.get("candidato")) and (a.get("formato") in ("dlis", "lis", "las", None)
                                         and (a.get("ext") or "").lower() not in (".pdf",))


def do_poco(banco: Banco, poco_id: str, dic: dict) -> dict:
    """Esquemas do poço (com o que foi lido) e o rótulo de cada arquivo de perfil.

    {"esquemas": [{nome, pasta, caminho, tamanho, pelo_nome, rotulo, lido?, dados?, erro?,
                   arquivo_local?, perfis: [nomes]}],
     "perfis": {nome do perfil: {"rotulo", "tipo", "esquema", "ferramentas": [códigos]}}}"""
    arqs = arquivos_do_poco(banco, poco_id)
    lidos = lidos_do_poco(banco, poco_id)
    esq = [a for a in arqs if eh_esquema(a["nome"], a["pasta"])]
    perfis = [a for a in arqs if _eh_perfil(a)]
    for e in esq:
        reg = lidos.get(e["caminho"])
        e["tipo"] = (reg or {}).get("tipo") or None
    vinc = vincular([{"nome": e["nome"], "pasta": e["pasta"], "tipo": e["tipo"]} for e in esq],
                    [{"nome": p["nome"], "pasta": p["pasta"]} for p in perfis], dic)
    saida_esq, rot_perfis = [], {}
    for e in esq:
        reg = lidos.get(e["caminho"]) or {}
        dados = reg.get("dados")
        pn = ler_nome(e["nome"], dic)
        tipo = (dados or {}).get("tipo") or pn["tipo"]
        item = {"nome": e["nome"], "pasta": e["pasta"], "caminho": e["caminho"], "bacia": e["bacia"],
                "poco_caminho": e["poco_caminho"], "tamanho": e["tamanho"], "pelo_nome": pn, "tipo": tipo,
                "rotulo": rotulo(tipo, dic, corrida=pn["corrida"], fase=pn["fase"]),
                "lido": bool(reg), "dados": dados, "erro": reg.get("erro"),
                "arquivo_local": reg.get("arquivo_local") or "", "perfis": vinc.get(e["nome"], [])}
        saida_esq.append(item)
        for p in item["perfis"]:
            rot_perfis.setdefault(p, []).append(item)
    saida_perfis = {}
    for p in perfis:
        pn = ler_nome(p["nome"], dic, p["pasta"])
        ligados = rot_perfis.get(p["nome"], [])
        tipo = next((i["tipo"] for i in ligados if i["tipo"]), None) or pn["tipo"]
        ferr = []
        for i in ligados:
            for fe in (i["dados"] or {}).get("ferramentas", []):
                if not fe.get("apoio") and fe["codigo"] not in ferr:
                    ferr.append(fe["codigo"])
        if not tipo and not ligados:
            continue
        saida_perfis[p["nome"]] = {
            "tipo": tipo, "esquemas": [i["nome"] for i in ligados], "ferramentas": ferr,
            "rotulo": rotulo(tipo, dic, corrida=pn["corrida"], passada=pn["passada"], fase=pn["fase"]),
            "fonte": "esquema lido" if any(i["dados"] for i in ligados) else ("nome do esquema" if ligados else "nome do arquivo")}
    return {"esquemas": saida_esq, "perfis": saida_perfis}


def pendentes(banco: Banco, bacia: str, categorias: list[str] | None = None, poco_id: str | None = None) -> list[dict]:
    """Esquemas do acervo ainda não lidos (ou lidos por um leitor mais antigo, ou que mudaram)."""
    cond, args = ["a.bacia = ?"], [bacia]
    if categorias:
        cond.append(f"p.categoria IN ({','.join('?' * len(categorias))})")
        args += list(categorias)
    if poco_id:
        cond.append("p.poco_id = ?")
        args.append(poco_id)
    with banco.conexao() as c:
        linhas = [dict(r) for r in c.execute(
            f"""SELECT a.caminho, a.nome, a.pasta, a.tamanho, a.poco_caminho, p.poco_id,
                       e.arquivo_local AS local_antigo, e.tamanho AS tamanho_antigo
                FROM acervo_arquivos a JOIN acervo_pocos p ON p.bacia = a.bacia AND p.caminho = a.poco_caminho
                LEFT JOIN esquemas e ON e.bacia = a.bacia AND e.caminho = a.caminho
                WHERE {' AND '.join(cond)}
                  AND (e.caminho IS NULL OR e.tamanho IS NOT a.tamanho OR coalesce(e.leitor, 0) < ?)
                ORDER BY a.caminho""", (*args, VERSAO_LEITOR))]
    return [r for r in linhas if eh_esquema(r["nome"], r["pasta"])]


def ler_do_portal(banco: Banco, cliente, bacia: str, itens: list[dict], dic: dict, *, pasta_projeto: str,
                  tessdata: str | None, progresso=None, cancelar=None) -> int:
    """Baixa (ou reaproveita a cópia local) e lê cada esquema de `itens` (de `pendentes`).
    A cópia fica em <projeto>/esquemas/<bacia>/<poço>/ para abrir depois."""
    feitos = 0
    for k, it in enumerate(itens, 1):
        if cancelar is not None and cancelar.is_set():
            break
        if progresso:
            progresso(k, len(itens), it["nome"])
        destino = caminho_local(pasta_projeto, bacia, it["poco_id"], it["nome"])
        local = os.path.relpath(destino, pasta_projeto).replace(os.sep, "/")
        dados, erro = None, ""
        try:
            if (it["tamanho"] or 0) > MAX_BYTES:
                raise ErroEsquema(f"Arquivo de {it['tamanho'] / 1e6:.0f} MB: grande demais para um esquema "
                                  "(costuma ser o perfil em PDF). Não foi baixado.")
            if not (os.path.isfile(destino) and os.path.getsize(destino) == it["tamanho"]):
                conteudo = cliente.ler_inicio(it["caminho"], max(1, it["tamanho"] or MAX_BYTES))
                os.makedirs(os.path.dirname(destino), exist_ok=True)
                with open(destino, "wb") as f:
                    f.write(conteudo)
            dados = ler_esquema(destino, it["nome"], dic, poco_id=it["poco_id"] or "", pasta=it["pasta"] or "",
                                tessdata=tessdata)
        except ErroEsquema as e:
            erro = str(e)
        except Exception as e:  # noqa: BLE001 — erro do portal ou do PDF não para a fila
            erro = f"{type(e).__name__}: {e}"
        gravar(banco, bacia=bacia, caminho=it["caminho"], poco_caminho=it["poco_caminho"],
               poco_id=it["poco_id"] or "", nome=it["nome"], tamanho=it["tamanho"] or 0,
               arquivo_local=local if os.path.isfile(destino) else "", dados=dados, erro=erro)
        feitos += 1
    return feitos


def resumo(banco: Banco, bacia: str) -> dict:
    with banco.conexao() as c:
        disp = sum(eh_esquema(n, p) for n, p in c.execute(
            "SELECT nome, pasta FROM acervo_arquivos WHERE bacia = ?", (bacia,)))
        lidos, com_ferr = c.execute(
            """SELECT count(*), sum(dados IS NOT NULL AND dados NOT LIKE '%"ferramentas": []%')
               FROM esquemas WHERE bacia = ?""", (bacia,)).fetchone()
        tipos = dict(c.execute("SELECT tipo, count(*) FROM esquemas WHERE bacia = ? AND tipo IS NOT NULL "
                               "GROUP BY tipo", (bacia,)).fetchall())
    return {"esquemas_disponiveis": disp, "esquemas_lidos": lidos or 0,
            "esquemas_com_ferramentas": com_ferr or 0, "esquemas_por_tipo": tipos}
