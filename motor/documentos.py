"""
Documentos do SIAPP: texto de PDFs e imagens (TIF), índice de busca e
visualização de página com o termo destacado.

Para cada página:
  1. Se o arquivo já tem texto embutido (PDF gerado por sistema, ex.: CDPE),
     usa esse texto — instantâneo e sem erro de reconhecimento.
  2. Se a página é só imagem (documento escaneado), faz OCR local com o motor
     Tesseract que vem embutido no PyMuPDF. Só precisa do arquivo de idioma
     (por.traineddata), baixado uma vez para recursos/tessdata/.

Antes do OCR, a grade das tabelas é apagada: nos formulários antigos, as
linhas da grade quebram a leitura (testado em 15/10/2026 no 7-GMR-13-RN —
ver nota "SIAPP — Tratamento por Tipo de Arquivo").

LIMITE QUE A INTERFACE DEVE SEMPRE DEIXAR CLARO: o OCR serve para BUSCAR e
CLASSIFICAR páginas. Números lidos por OCR (profundidades, por exemplo)
erram com frequência e precisam ser conferidos na imagem.
"""

from __future__ import annotations

import base64
import os
import queue
import re
import sqlite3
import threading
import time
import unicodedata
from datetime import datetime

import numpy as np
import pymupdf
import requests

EXTENSOES = (".pdf", ".tif", ".tiff", ".png", ".jpg", ".jpeg")
# Imagens grandes (perfil em papel escaneado em TIF chega a 2.500 × 80.000 px):
# nenhuma imagem enviada à janela passa destes limites de pixels.
PIXELS_PAGINA = 8_000_000
# Visor ampliado: a página é renderizada nesta largura e entregue em faixas
# quase quadradas, carregadas conforme a pessoa rola (perfil longo em TIF).
LARGURA_VISOR = 2400
IDIOMA = "por"
MODELOS_IDIOMA = (   # tenta na ordem: modelo mais preciso, depois o padrão
    "https://github.com/tesseract-ocr/tessdata_best/raw/main/{idioma}.traineddata",
    "https://github.com/tesseract-ocr/tessdata/raw/main/{idioma}.traineddata",
)
URLS_IDIOMA = tuple(u.format(idioma=IDIOMA) for u in MODELOS_IDIOMA)
MIN_CARACTERES_EMBUTIDO = 40   # menos que isso: página tratada como imagem
DPI_OCR = 300
VERSAO_EXTRACAO = 1


class ErroDocumento(Exception):
    """Falha legível para o usuário (arquivo corrompido, idioma ausente...)."""


class ProcessamentoCancelado(Exception):
    pass


def sem_acento(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto)
                   if unicodedata.category(c) != "Mn").lower()


# =========================================================== idioma do OCR
def caminho_idioma(tessdata: str, idioma: str = IDIOMA) -> str:
    return os.path.join(tessdata, f"{idioma}.traineddata")


def idioma_disponivel(tessdata: str, idioma: str = IDIOMA) -> bool:
    f = caminho_idioma(tessdata, idioma)
    return os.path.isfile(f) and os.path.getsize(f) > 1_000_000


def baixar_idioma(tessdata: str, progresso=None, idioma: str = IDIOMA, modelos=MODELOS_IDIOMA) -> None:
    """Baixa o modelo do idioma (português; inglês para os esquemas de ferramentas)
    do repositório oficial do Tesseract. `modelos`: endereços a tentar, na ordem."""
    os.makedirs(tessdata, exist_ok=True)
    destino = caminho_idioma(tessdata, idioma)
    ultimo_erro = ""
    for url in (u.format(idioma=idioma) for u in modelos):
        try:
            with requests.get(url, stream=True, timeout=(20, 120)) as r:
                if r.status_code != 200:
                    ultimo_erro = f"HTTP {r.status_code}"
                    continue
                total = int(r.headers.get("Content-Length") or 0)
                feito = 0
                with open(destino + ".part", "wb") as f:
                    for bloco in r.iter_content(256 * 1024):
                        f.write(bloco)
                        feito += len(bloco)
                        if progresso:
                            progresso(feito, total)
            if os.path.getsize(destino + ".part") < 1_000_000:
                ultimo_erro = "arquivo recebido pequeno demais"
                continue
            os.replace(destino + ".part", destino)
            return
        except requests.exceptions.RequestException as e:
            ultimo_erro = type(e).__name__
    nome = {"por": "português", "eng": "inglês"}.get(idioma, idioma)
    raise ErroDocumento(
        f"Não foi possível baixar o idioma {nome} do OCR ({ultimo_erro}). "
        f"Baixe manualmente {modelos[0].format(idioma=idioma)} e coloque o arquivo em {tessdata}")


# ======================================================== limpeza da imagem
def _abertura_1d(m: np.ndarray, comprimento: int, eixo: int) -> np.ndarray:
    """Mantém só traços contínuos com pelo menos `comprimento` pixels na
    direção do eixo (abertura morfológica linear, feita só com numpy)."""
    if eixo:
        m = m.T
    c = np.cumsum(np.pad(m.astype(np.int32), ((0, 0), (1, 0))), axis=1)
    erodido = (c[:, comprimento:] - c[:, :-comprimento]) == comprimento
    e = np.zeros(m.shape, dtype=np.int32)
    e[:, :erodido.shape[1]] = erodido
    c2 = np.cumsum(np.pad(e, ((0, 0), (comprimento, 0))), axis=1)
    r = (c2[:, comprimento:] - c2[:, :-comprimento]) > 0
    return r.T if eixo else r


def _imagem_para_ocr(page: pymupdf.Page) -> pymupdf.Pixmap:
    """Renderiza a página, binariza e apaga as linhas longas da grade."""
    pix = page.get_pixmap(dpi=DPI_OCR, colorspace=pymupdf.csGRAY)
    a = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width)
    tinta = a < 150
    traco = int(DPI_OCR * 0.3)                       # ~7,5 mm: maior que qualquer letra
    grade = _abertura_1d(tinta, traco, 0) | _abertura_1d(tinta, traco, 1)
    for _ in range(2):                               # engrossa para apagar a borda serrilhada
        grade = (grade | np.roll(grade, 1, 0) | np.roll(grade, -1, 0)
                 | np.roll(grade, 1, 1) | np.roll(grade, -1, 1))
    limpo = np.where(tinta & ~grade, 0, 255).astype(np.uint8)
    # ATENÇÃO: o OCR embutido do PyMuPDF devolve texto VAZIO, sem erro nenhum,
    # se receber imagem em tons de cinza. Tem que ser RGB. (testado 15/10/2026)
    rgb = np.repeat(limpo[:, :, None], 3, axis=2)
    out = pymupdf.Pixmap(pymupdf.csRGB, pix.width, pix.height, rgb.tobytes(), False)
    out.set_dpi(DPI_OCR, DPI_OCR)
    return out


# ============================================================ por página
def _titulo_provavel(palavras: list) -> str:
    """Linha com mais letras maiúsculas no terço superior da página: nos
    formulários, é o título ("DESCRIÇÃO DE AMOSTRAS DE CALHA")."""
    linhas: dict = {}
    for x0, y0, x1, y1, txt, bloco, linha in palavras:
        if y0 < 0.33:
            linhas.setdefault((bloco, linha), []).append((x0, txt))
    melhor, pontos = "", 0
    for itens in linhas.values():
        texto = " ".join(t for _, t in sorted(itens))
        maius = sum(1 for c in texto if c.isupper())
        if maius >= 8 and maius > pontos and maius >= 0.6 * sum(c.isalpha() for c in texto):
            melhor, pontos = texto, maius
    return melhor


def extrair_pagina(page: pymupdf.Page, tessdata: str) -> dict:
    texto = page.get_text()
    if len(texto.strip()) >= MIN_CARACTERES_EMBUTIDO:
        metodo, fonte = "embutido", page
        palavras_brutas = page.get_text("words")
    else:
        if not idioma_disponivel(tessdata):
            raise ErroDocumento("Idioma do OCR ausente.")
        ocr = pymupdf.open("pdf", _imagem_para_ocr(page).pdfocr_tobytes(
            language=IDIOMA, tessdata=tessdata))
        fonte = ocr[0]
        metodo, texto = "ocr", fonte.get_text()
        palavras_brutas = fonte.get_text("words")
    w, h = fonte.rect.width or 1, fonte.rect.height or 1
    palavras = [(round(p[0] / w, 4), round(p[1] / h, 4), round(p[2] / w, 4),
                 round(p[3] / h, 4), p[4], p[5], p[6]) for p in palavras_brutas]
    return {"metodo": metodo, "texto": texto, "titulo": _titulo_provavel(palavras),
            "palavras": [list(p[:5]) for p in palavras]}


def processar_arquivo(caminho: str, tessdata: str, progresso=None, cancelar=None) -> dict:
    try:
        doc = pymupdf.open(caminho)
    except Exception as e:
        raise ErroDocumento(f"Não foi possível abrir {os.path.basename(caminho)}: {e}") from e
    if doc.needs_pass:
        raise ErroDocumento(f"{os.path.basename(caminho)} é protegido por senha.")
    paginas = []
    for i, page in enumerate(doc):
        if cancelar is not None and cancelar.is_set():
            raise ProcessamentoCancelado()
        if progresso:
            progresso(i + 1, doc.page_count)
        paginas.append({"pagina": i + 1, **extrair_pagina(page, tessdata)})
    return {"n_paginas": doc.page_count, "idioma": IDIOMA, "versao_extracao": VERSAO_EXTRACAO,
            "processado_em": datetime.now().isoformat(timespec="seconds"),
            "bytes_origem": os.path.getsize(caminho), "paginas": paginas}


def precisa_ocr(caminho: str) -> bool:
    """Alguma página sem texto embutido? (rápido: não faz OCR)"""
    try:
        doc = pymupdf.open(caminho)
        return any(len(p.get_text().strip()) < MIN_CARACTERES_EMBUTIDO for p in doc)
    except Exception:
        return False


# ======================================================= imagem de página
def n_paginas(caminho: str) -> int:
    try:
        with pymupdf.open(caminho) as doc:
            return doc.page_count
    except Exception as e:
        raise ErroDocumento(f"Não foi possível abrir {os.path.basename(caminho)}: {e}") from e


def _escala(page: pymupdf.Page, largura: int, pixels_max: int) -> float:
    """Fator de zoom para a página ficar com `largura` px, sem passar de
    `pixels_max` no total (páginas muito compridas ficam mais estreitas)."""
    w, h = max(page.rect.width, 1), max(page.rect.height, 1)
    z = largura / w
    if w * h * z * z > pixels_max:
        z = 0.995 * (pixels_max / (w * h)) ** 0.5   # margem: o PyMuPDF arredonda para cima
    return max(z, 0.02)


def _abrir_pagina(caminho: str, n_pagina: int):
    try:
        doc = pymupdf.open(caminho)
    except Exception as e:
        raise ErroDocumento(f"Não foi possível abrir {os.path.basename(caminho)}: {e}") from e
    if doc.needs_pass:
        raise ErroDocumento(f"{os.path.basename(caminho)} é protegido por senha.")
    if not 1 <= n_pagina <= doc.page_count:
        raise ErroDocumento(f"Página {n_pagina} não existe (o arquivo tem {doc.page_count}).")
    try:
        return doc, doc[n_pagina - 1]
    except Exception as e:
        doc.close()
        raise ErroDocumento(f"{os.path.basename(caminho)}: o leitor de imagens não reconhece o conteúdo "
                            f"({e}). Use “No computador” para abrir em outro programa.") from e


# (preenchimento, borda) — as mesmas cores do texto reconhecido na janela (estilo.css)
CORES_CAIXA = {
    "busca": ((255, 217, 0), (217, 140, 0)),
    "auto": ((99, 176, 127), (29, 106, 61)),
    "usuario": ((108, 147, 214), (35, 78, 154)),
    "comunidade": ((156, 124, 200), (91, 47, 143)),
}


def _destacar(pix: pymupdf.Pixmap, caixas: list, cor: str = "busca", opacidade: float = 0.35,
              espessura: int = 1) -> pymupdf.Pixmap:
    """Pinta caixas translúcidas (com borda) sobre a imagem: amarelo para a busca,
    verde/azul/roxo para as palavras corrigidas. Feito nos pixels, e não com
    draw_rect: o PyMuPDF só desenha em PDF, e TIF/PNG/JPG falhariam com "is no PDF"."""
    a = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width, pix.n)[:, :, :3].astype(np.float32)
    fundo, borda = (np.array(c, np.float32) for c in CORES_CAIXA[cor])
    e = max(1, int(espessura))
    for x0, y0, x1, y1 in caixas:
        c0, c1 = max(0, int(x0 * pix.width) - 2), min(pix.width, int(x1 * pix.width) + 3)
        l0, l1 = max(0, int(y0 * pix.height) - 2), min(pix.height, int(y1 * pix.height) + 3)
        if c1 <= c0 or l1 <= l0:
            continue
        a[l0:l1, c0:c1] = a[l0:l1, c0:c1] * (1 - opacidade) + fundo * opacidade
        a[l0:l0 + e, c0:c1] = a[l1 - e:l1, c0:c1] = borda
        a[l0:l1, c0:c0 + e] = a[l0:l1, c1 - e:c1] = borda
    rgb = np.ascontiguousarray(a.astype(np.uint8))
    return pymupdf.Pixmap(pymupdf.csRGB, pix.width, pix.height, rgb.tobytes(), False)


def imagem_pagina(caminho: str, n_pagina: int, palavras: list, termo: str = "",
                  largura: int = 900, variacoes: list | None = None,
                  corrigidas: list | None = None) -> str:
    """PNG (data URL) da página, com as palavras que casam com o termo (ou com
    suas variações de OCR) destacadas em amarelo. Nada é gravado no arquivo.
    `palavras`: [x0,y0,x1,y1,texto] com coordenadas normalizadas; o texto pode
    trazer a forma original e a corrigida separadas por espaço.
    `corrigidas`: [x0,y0,x1,y1,tipo] das palavras que o corretor trocou
    (tipo auto/usuario/comunidade), contornadas na cor de cada origem."""
    doc, page = _abrir_pagina(caminho, n_pagina)
    try:
        z = _escala(page, largura, PIXELS_PAGINA)
        pix = page.get_pixmap(matrix=pymupdf.Matrix(z, z), colorspace=pymupdf.csRGB, alpha=False)
    finally:
        doc.close()
    for tipo in ("auto", "comunidade", "usuario"):
        caixas = [w[:4] for w in corrigidas or [] if w[4] == tipo]
        if caixas:
            pix = _destacar(pix, caixas, tipo, opacidade=0.28, espessura=2)
    tokens = [sem_acento(t) for t in re.findall(r"\w+", termo or "")] + list(variacoes or [])
    if tokens:
        caixas = [w[:4] for w in palavras if any(t in sem_acento(w[4]) for t in tokens)]
        if caixas:
            pix = _destacar(pix, caixas)
    return "data:image/png;base64," + base64.b64encode(pix.tobytes("png")).decode("ascii")


class _DocAberto:
    """Mantém o último documento aberto pelo visor: cada faixa de um TIF longo
    seria uma nova leitura do arquivo inteiro. Chamadas da janela chegam em
    threads diferentes, e o PyMuPDF não pode usar o mesmo documento em duas."""

    def __init__(self):
        self.trava = threading.Lock()
        self.chave = None
        self.doc = None

    def pagina(self, caminho: str, n_pagina: int):
        chave = (caminho, os.path.getmtime(caminho), os.path.getsize(caminho))
        if chave != self.chave:
            if self.doc is not None:
                self.doc.close()
            self.doc, self.chave = None, None
            self.doc = _abrir_pagina(caminho, n_pagina)[0]
            self.chave = chave
        if not 1 <= n_pagina <= self.doc.page_count:
            raise ErroDocumento(f"Página {n_pagina} não existe (o arquivo tem {self.doc.page_count}).")
        return self.doc[n_pagina - 1]


_visor = _DocAberto()


def _medidas_visor(page: pymupdf.Page, largura: int) -> tuple[float, int, int]:
    z = largura / max(page.rect.width, 1)
    return z, round(page.rect.width * z), round(page.rect.height * z)


def visor_info(caminho: str, n_pagina: int, largura: int = LARGURA_VISOR) -> dict:
    """Tamanho da página no visor e em quantas faixas ela vem."""
    with _visor.trava:
        page = _visor.pagina(caminho, n_pagina)
        _, w, h = _medidas_visor(page, largura)
        n_paginas = page.parent.page_count
    alt_faixa = largura
    return {"largura": w, "altura": h, "altura_faixa": alt_faixa,
            "faixas": max(1, -(-h // alt_faixa)), "n_paginas": n_paginas}


def visor_faixa(caminho: str, n_pagina: int, indice: int, largura: int = LARGURA_VISOR) -> str:
    """Faixa `indice` da página (JPEG, data URL): perfil escaneado fica ~10×
    menor que em PNG, e só as faixas que aparecem na tela são pedidas."""
    with _visor.trava:
        page = _visor.pagina(caminho, n_pagina)
        z, _, h = _medidas_visor(page, largura)
        alt = largura
        y0 = indice * alt
        if not 0 <= y0 < h:
            raise ErroDocumento(f"Faixa {indice} fora da página.")
        r = page.rect
        clip = pymupdf.Rect(r.x0, r.y0 + y0 / z, r.x1, r.y0 + min(h, y0 + alt) / z)
        pix = page.get_pixmap(matrix=pymupdf.Matrix(z, z), clip=clip)
    if pix.alpha or pix.n not in (1, 3):
        pix = pymupdf.Pixmap(pymupdf.csRGB, pix, 0) if pix.n > 3 or pix.n == 2 else pymupdf.Pixmap(pix, 0)
    return "data:image/jpeg;base64," + base64.b64encode(pix.tobytes("jpg", jpg_quality=85)).decode("ascii")


# ================================================================== índice
class Indice:
    """
    Busca em texto completo, sem acento e sem diferenciar maiúsculas (SQLite FTS5).

    Cada página entra com DUAS versões do texto: a corrigida (vocabulário +
    correções do usuário) e a original do OCR. A busca olha as duas, então uma
    correção automática errada nunca torna uma página impossível de achar.

    Tolerância a erro de OCR: cada termo buscado é expandido para as palavras do
    índice que diferem dele em 1 letra (termos de 5–8 letras) ou 2 (9+). Ex.:
    "barreiras" também acha "barigiras". As variações usadas são devolvidas
    para a interface mostrar.

    O índice é derivado (pode ser apagado e refeito a partir de texto/*.json).
    Se a estrutura mudar entre versões, ele é recriado automaticamente.
    """
    VERSAO = 3   # 3: ids de documento com "/" em qualquer sistema (SIAPP 0.7)

    def __init__(self, caminho: str):
        self.caminho = caminho
        os.makedirs(os.path.dirname(caminho), exist_ok=True)
        self._trava = threading.Lock()
        self.recriado = False
        with self._con() as c:
            c.execute("CREATE TABLE IF NOT EXISTS meta (chave TEXT PRIMARY KEY, valor TEXT)")
            v = c.execute("SELECT valor FROM meta WHERE chave='versao'").fetchone()
            if v is None or int(v[0]) != self.VERSAO:
                for t in ("paginas", "vocab", "paginas_simples"):
                    c.execute(f"DROP TABLE IF EXISTS {t}")
                self.recriado = True
            try:
                c.execute("""CREATE VIRTUAL TABLE IF NOT EXISTS paginas USING fts5(
                    texto, original, titulo, doc UNINDEXED, bacia UNINDEXED, poco UNINDEXED,
                    arquivo UNINDEXED, pagina UNINDEXED, metodo UNINDEXED,
                    tokenize='unicode61 remove_diacritics 2')""")
                c.execute("CREATE VIRTUAL TABLE IF NOT EXISTS vocab USING fts5vocab(paginas, 'row')")
                self.fts = True
            except sqlite3.OperationalError:
                c.execute("""CREATE TABLE IF NOT EXISTS paginas_simples(
                    texto, original, titulo, doc, bacia, poco, arquivo, pagina, metodo, norm)""")
                self.fts = False
            c.execute("INSERT OR REPLACE INTO meta VALUES ('versao', ?)", (str(self.VERSAO),))

    def _con(self):
        return sqlite3.connect(self.caminho, timeout=30)

    @staticmethod
    def _linhas(doc_id, bacia, poco, arquivo, paginas, corretor):
        from .vocabulario import titulo_confiavel
        for p in paginas:
            corrigido = corretor.corrigir(p["texto"]) if corretor else p["texto"]
            titulo = corretor.corrigir(p["titulo"]) if corretor else p["titulo"]
            titulo = titulo if titulo_confiavel(titulo) else ""
            yield (corrigido, p["texto"], titulo, doc_id, bacia, poco, arquivo, p["pagina"], p["metodo"])

    def substituir_documento(self, doc_id, bacia, poco, arquivo, paginas, corretor=None) -> None:
        with self._trava, self._con() as c:
            self._gravar(c, doc_id, bacia, poco, arquivo, paginas, corretor)

    def _gravar(self, c, doc_id, bacia, poco, arquivo, paginas, corretor):
        linhas = list(self._linhas(doc_id, bacia, poco, arquivo, paginas, corretor))
        if self.fts:
            c.execute("DELETE FROM paginas WHERE doc = ?", (doc_id,))
            c.executemany("INSERT INTO paginas VALUES (?,?,?,?,?,?,?,?,?)", linhas)
        else:
            c.execute("DELETE FROM paginas_simples WHERE doc = ?", (doc_id,))
            c.executemany("INSERT INTO paginas_simples VALUES (?,?,?,?,?,?,?,?,?,?)",
                          [(*l, sem_acento(l[0] + " " + l[1])) for l in linhas])

    def reconstruir(self, documentos, corretor) -> int:
        """Refaz o índice inteiro (ex.: depois de mudar o vocabulário).
        `documentos`: iterável de (doc_id, bacia, poco, arquivo, paginas)."""
        n = 0
        with self._trava, self._con() as c:
            c.execute("DELETE FROM paginas" if self.fts else "DELETE FROM paginas_simples")
            for doc_id, bacia, poco, arquivo, paginas in documentos:
                self._gravar(c, doc_id, bacia, poco, arquivo, paginas, corretor)
                n += len(paginas)
        return n

    def titulos(self, doc_id: str) -> dict:
        tabela = "paginas" if self.fts else "paginas_simples"
        with self._con() as c:
            return {int(p): t for p, t in c.execute(
                f"SELECT pagina, titulo FROM {tabela} WHERE doc = ?", (doc_id,))}

    # ------------------------------------------------------------- busca
    def expandir(self, termo: str) -> list[dict]:
        """Para cada palavra buscada, as variações do índice a 1–2 letras."""
        from .vocabulario import distancia
        tokens = [sem_acento(t) for t in re.findall(r"\w+", termo or "")]
        if not self.fts or not tokens:
            return [{"termo": t, "variacoes": []} for t in tokens]
        with self._con() as c:
            vocab = [r[0] for r in c.execute("SELECT term FROM vocab")]
        saida = []
        for t in tokens:
            lim = 0 if len(t) < 5 else (1 if len(t) <= 8 else 2)
            achadas = []
            if lim:
                for v in vocab:
                    if v.startswith(t) or abs(len(v) - len(t)) > lim:
                        continue                      # prefixo já é coberto pela busca normal
                    d = distancia(t, v, lim)
                    if 0 < d <= lim:
                        achadas.append((d, v))
            saida.append({"termo": t, "variacoes": [v for _, v in sorted(achadas)[:12]]})
        return saida

    def buscar(self, termo: str, limite: int = 300, tolerante: bool = True) -> dict:
        exp = self.expandir(termo) if tolerante else [
            {"termo": sem_acento(t), "variacoes": []} for t in re.findall(r"\w+", termo or "")]
        if not exp:
            return {"resultados": [], "expansoes": []}
        campos = "doc, bacia, poco, arquivo, pagina, metodo, titulo"
        with self._con() as c:
            if self.fts:
                partes = []
                for e in exp:
                    opcoes = [f'"{e["termo"]}"*'] + [f'"{v}"' for v in e["variacoes"]]
                    partes.append("(" + " OR ".join(opcoes) + ")")
                linhas = c.execute(
                    f"SELECT {campos}, snippet(paginas, -1, char(1), char(2), '…', 14) "
                    f"FROM paginas WHERE paginas MATCH ? ORDER BY rank LIMIT ?",
                    (" AND ".join(partes), limite)).fetchall()
            else:
                cond = " AND ".join("norm LIKE ?" for _ in exp)
                linhas = [(*l[:7], l[7][:200]) for l in c.execute(
                    f"SELECT {campos}, texto FROM paginas_simples WHERE {cond} LIMIT ?",
                    [f"%{e['termo']}%" for e in exp] + [limite]).fetchall()]
        return {"expansoes": [e for e in exp if e["variacoes"]],
                "resultados": [{"doc": l[0], "bacia": l[1], "poco": l[2], "arquivo": l[3],
                                "pagina": l[4], "metodo": l[5], "titulo": l[6],
                                "trecho": " ".join(l[7].split())} for l in linhas]}

    def contar(self, termo: str) -> int:
        """Nº de páginas com o termo (busca exata por prefixo, sem expansão)."""
        tokens = re.findall(r"\w+", termo or "")
        if not tokens:
            return 0
        with self._con() as c:
            if self.fts:
                return c.execute("SELECT count(*) FROM paginas WHERE paginas MATCH ?",
                                 (" AND ".join(f'"{t}"*' for t in tokens),)).fetchone()[0]
            cond = " AND ".join("norm LIKE ?" for _ in tokens)
            return c.execute(f"SELECT count(*) FROM paginas_simples WHERE {cond}",
                             [f"%{sem_acento(t)}%" for t in tokens]).fetchone()[0]


# =========================================================== fila de OCR
class FilaDocumentos:
    """Processa documentos em segundo plano, um por vez. Eventos (emitir):
        {"tipo": "idioma", "feito", "total"}            baixando o modelo de português
        {"tipo": "inicio", "doc", "nome", "indice", "total"}
        {"tipo": "pagina", "doc", "pagina", "paginas"}
        {"tipo": "fim", "doc", "n_paginas", "embutido", "ocr"}
        {"tipo": "erro", "doc", "erro"}
        {"tipo": "cancelado", "doc"}
        {"tipo": "ocioso", "processados", "erros", "cancelados"}
    Cada tarefa: {"doc", "caminho", "nome", "bacia", "poco", "salvar": callable(resultado)}
    """

    def __init__(self, tessdata: str, emitir):
        self._tessdata = tessdata
        self._emitir = emitir
        self._fila: queue.Queue = queue.Queue()
        self._cancelar = threading.Event()
        self._trava = threading.Lock()
        self._thread = None
        self._na_fila: set[str] = set()
        self._lote = {"total": 0, "indice": 0, "processados": 0, "erros": 0, "cancelados": 0}

    def adicionar(self, tarefas: list[dict]) -> int:
        novas = 0
        with self._trava:
            for t in tarefas:
                if t["doc"] in self._na_fila:
                    continue
                self._na_fila.add(t["doc"])
                self._fila.put(t)
                self._lote["total"] += 1
                novas += 1
            if novas and self._thread is None:
                self._cancelar.clear()
                self._thread = threading.Thread(target=self._trabalhar, daemon=True,
                                                name="siapp-documentos")
                self._thread.start()
        return novas

    def cancelar(self):
        self._cancelar.set()

    def _contar(self, campo):
        with self._trava:
            self._lote[campo] += 1

    def _trabalhar(self):
        while True:
            try:
                t = self._fila.get(timeout=0.5)
            except queue.Empty:
                with self._trava:                     # mesma lógica anti-órfão da fila de downloads
                    if not self._fila.empty():
                        continue
                    lote = self._lote
                    self._lote = {"total": 0, "indice": 0, "processados": 0, "erros": 0, "cancelados": 0}
                    self._cancelar.clear()
                    self._thread = None
                self._emitir({"tipo": "ocioso", **{k: lote[k] for k in ("processados", "erros", "cancelados")}})
                return
            try:
                self._processar(t)
            finally:
                with self._trava:
                    self._na_fila.discard(t["doc"])

    def _processar(self, t):
        if self._cancelar.is_set():
            self._contar("cancelados")
            self._emitir({"tipo": "cancelado", "doc": t["doc"]})
            return
        with self._trava:
            self._lote["indice"] += 1
            indice, total = self._lote["indice"], self._lote["total"]
        self._emitir({"tipo": "inicio", "doc": t["doc"], "nome": t["nome"],
                      "indice": indice, "total": total})
        try:
            if not idioma_disponivel(self._tessdata) and precisa_ocr(t["caminho"]):
                baixar_idioma(self._tessdata, progresso=lambda f, tot: self._emitir(
                    {"tipo": "idioma", "feito": f, "total": tot}))
            r = processar_arquivo(
                t["caminho"], self._tessdata, cancelar=self._cancelar,
                progresso=lambda p, n: self._emitir({"tipo": "pagina", "doc": t["doc"],
                                                     "pagina": p, "paginas": n}))
            t["salvar"](r)
        except ProcessamentoCancelado:
            self._contar("cancelados")
            self._emitir({"tipo": "cancelado", "doc": t["doc"]})
            return
        except (ErroDocumento, OSError, RuntimeError, ValueError) as e:
            self._contar("erros")
            self._emitir({"tipo": "erro", "doc": t["doc"], "erro": str(e)})
            return
        self._contar("processados")
        metodos = [p["metodo"] for p in r["paginas"]]
        self._emitir({"tipo": "fim", "doc": t["doc"], "n_paginas": r["n_paginas"],
                      "embutido": metodos.count("embutido"), "ocr": metodos.count("ocr")})
